import os
import sys
import weakref
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QLabel,
    QStackedWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.pages.settings_widgets.background_settings import BackgroundSettingsWidget
from src.ui.pages.settings_widgets.company_settings_dialog import CompanySettingsDialog
from src.ui.mixins._main_window_base_mixin import MainWindowBaseMixin
from src.ui.pages.transaction_page_behaviors import TransactionPageBehaviorMixin
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.theme_filters import _StyleChangeFilter
from src.utils.theme_manager import ThemeManager


APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)


def test_theme_prewarm_builds_each_display_theme_cache():
    ThemeManager.invalidate_runtime_cache()
    ThemeManager._current_theme = "AYEC"

    ThemeManager.prewarm_themes()

    compiled_names = {key[0] for key in ThemeManager._compiled_stylesheet_cache}
    palette_names = {key[0] for key in ThemeManager._palette_cache}
    assert set(ThemeManager.DISPLAY_THEMES) <= compiled_names
    assert set(ThemeManager.DISPLAY_THEMES) <= palette_names


def test_apply_raw_skips_reinstalling_identical_application_stylesheet(monkeypatch):
    old_theme = ThemeManager._current_theme
    target_theme = "Koyu Mavi"
    ThemeManager._activate_runtime_cache(target_theme)
    stylesheet = ThemeManager.get_stylesheet(target_theme)
    target_palette = ThemeManager._build_palette(target_theme)
    calls = []
    fake_app = SimpleNamespace(
        palette=lambda: target_palette,
        styleSheet=lambda: stylesheet,
        setPalette=lambda _palette: None,
        setStyleSheet=lambda value: calls.append(value),
    )

    try:
        monkeypatch.setattr(ThemeManager, "_install_stylesheet_patch", lambda: None)
        ThemeManager._apply_raw(fake_app, target_theme, refresh_widgets=False)
        assert calls == []
    finally:
        ThemeManager._current_theme = old_theme

def test_reapplying_unchanged_stylesheet_skips_theme_transformation(monkeypatch):
    old_theme = ThemeManager._current_theme
    old_stylesheet = APP.styleSheet()
    target_theme = "Koyu Mavi"
    ThemeManager._activate_runtime_cache(target_theme)
    stylesheet = ThemeManager.get_stylesheet(target_theme)
    APP.setStyleSheet(stylesheet)
    widget = QWidget()
    widget.setStyleSheet("QWidget { color: @text; }")

    def fail_transform(*_args, **_kwargs):
        raise AssertionError("unchanged stylesheets should bypass transformation")

    try:
        monkeypatch.setattr(ThemeManager, "transform_qss", fail_transform)
        APP.setStyleSheet(stylesheet)
        widget.setStyleSheet("QWidget { color: @text; }")
    finally:
        monkeypatch.undo()
        widget.close()
        widget.deleteLater()
        ThemeManager._activate_runtime_cache(old_theme)
        APP.setStyleSheet(old_stylesheet)


def test_exchange_rate_banner_replays_semantic_theme_colors():
    previous_theme = ThemeManager._current_theme
    target_theme = "AYEC" if previous_theme != "AYEC" else "Koyu Mavi"
    raw_style = TransactionPageBehaviorMixin._exchange_rate_style("success")

    old_style = ThemeManager.transform_qss(raw_style, theme_name=previous_theme)
    new_style = ThemeManager.transform_qss(raw_style, theme_name=target_theme)

    assert new_style != old_style
    assert "@" not in new_style
    assert ThemeManager.get_palette_color(target_theme, "success_bg") in new_style


def test_main_window_theme_refresh_avoids_duplicate_appearance_pass(monkeypatch):
    calls = SimpleNamespace(appearance=[], chrome=[], shell=0, visible=[], sync=0)
    fake = SimpleNamespace(
        _theme_applying=False,
        db=SimpleNamespace(set_setting=lambda *args: None),
        apply_appearance_mode=lambda mode, force_tree=False: calls.appearance.append(
            (mode, force_tree)
        ),
        _apply_shell_theme_styles=lambda: setattr(calls, "shell", calls.shell + 1),
        _refresh_theme_chrome=lambda refresh_appearance=True: calls.chrome.append(
            refresh_appearance
        ),
        _refresh_visible_top_level_themes=lambda mode: calls.visible.append(mode),
        sync_theme_toggle_button=lambda: setattr(calls, "sync", calls.sync + 1),
    )
    monkeypatch.setattr(ThemeManager, "apply_theme", lambda *args, **kwargs: None)
    monkeypatch.setattr(AppearanceModeManager, "current", lambda db: "modern")

    MainWindowBaseMixin.apply_theme(fake, "AYEC")

    assert calls.appearance == [("modern", False)]
    assert calls.chrome == [False]
    assert calls.shell == 1
    assert calls.visible == ["modern"]
    assert calls.sync == 1


def test_theme_switch_refreshes_active_page_and_defers_hidden_pages(monkeypatch):
    refreshed = []
    pages = [SimpleNamespace(), SimpleNamespace(), SimpleNamespace()]
    content_area = SimpleNamespace(currentWidget=lambda: pages[1])
    fake = SimpleNamespace(
        _theme_applying=False,
        db=SimpleNamespace(set_setting=lambda *args: None),
        pages={index: page for index, page in enumerate(pages)},
        content_area=content_area,
        _refresh_page_theme=lambda page: refreshed.append(page),
        apply_appearance_mode=lambda *args, **kwargs: None,
        _refresh_theme_chrome=lambda **kwargs: None,
        _refresh_visible_top_level_themes=lambda mode: None,
        sync_theme_toggle_button=lambda: None,
    )
    monkeypatch.setattr(ThemeManager, "apply_theme", lambda *args, **kwargs: None)
    monkeypatch.setattr(AppearanceModeManager, "current", lambda db: "modern")

    MainWindowBaseMixin.apply_theme(fake, "AYEC")

    assert refreshed == [pages[1]]
    assert fake._theme_revision == 1


def test_cached_page_is_rethemed_on_first_navigation_after_theme_change():
    from src.ui.mixins._main_window_nav_mixin import MainWindowNavMixin

    class FakeWindow(MainWindowNavMixin):
        def __init__(self, page):
            self.pages = {42: page}
            self._theme_revision = 3
            self.refreshed = []

        def _refresh_page_theme(self, page):
            self.refreshed.append(page)
            page._ayec_theme_revision = self._theme_revision

    page = SimpleNamespace(_ayec_theme_revision=2)
    window = FakeWindow(page)

    assert window.get_page(42) is page
    assert window.refreshed == [page]
    assert page._ayec_theme_revision == 3


def test_deferred_cached_page_retheme_resolves_styles_before_display():
    from src.ui.mixins._main_window_nav_mixin import MainWindowNavMixin

    class FakeWindow(MainWindowBaseMixin, MainWindowNavMixin):
        def __init__(self, stack, pages):
            self.db = SimpleNamespace(get_setting=lambda _key, default=None: default)
            self._theme_applying = False
            self._theme_revision = 1
            self._appearance_mode = AppearanceModeManager.MODERN
            self._current_theme_name = ThemeManager._current_theme
            self.pages = pages
            self.content_area = stack

        def isVisible(self):
            return False

        def apply_appearance_mode(self, *_args, **_kwargs):
            return AppearanceModeManager.MODERN

        def _apply_shell_theme_styles(self):
            pass

        def _refresh_theme_chrome(self, **_kwargs):
            pass

        def _refresh_visible_top_level_themes(self, _mode):
            pass

        def sync_theme_toggle_button(self):
            pass

    previous_theme = ThemeManager._current_theme
    stack = QStackedWidget()
    pages = {}
    labels = {}
    try:
        ThemeManager.apply_theme(APP, "Koyu Mavi")
        for page_id in (1, 2):
            page = QWidget()
            layout = QVBoxLayout(page)
            label = QLabel("Theme test")
            label.setStyleSheet(
                "QLabel{color:@text;background:@surface;border:1px solid @border;}"
            )
            layout.addWidget(label)
            pages[page_id] = page
            labels[page_id] = label
            stack.addWidget(page)
        stack.setCurrentWidget(pages[1])
        window = FakeWindow(stack, pages)
        hidden_dark_style = labels[2].styleSheet()
        window.apply_theme("AYEC")
        APP.processEvents()

        assert pages[1]._ayec_theme_revision == window._theme_revision
        assert getattr(pages[2], "_ayec_theme_revision", None) != window._theme_revision
        assert labels[2].styleSheet() == hidden_dark_style

        assert window.get_page(2) is pages[2]
        APP.processEvents()
        assert pages[2]._ayec_theme_revision == window._theme_revision
        assert labels[2].styleSheet() != hidden_dark_style
        assert "@" not in labels[2].styleSheet()
    finally:
        ThemeManager.apply_theme(APP, previous_theme)
        stack.close()


def test_cached_theme_switch_updates_existing_widgets_in_place():
    ThemeManager._install_stylesheet_patch()
    root = QWidget()
    layout = QVBoxLayout(root)
    label = QLabel("Theme test")
    layout.addWidget(label)
    label.setStyleSheet(
        "QLabel { color: @text; background-color: @surface; "
        "border: 1px solid @border; }"
    )
    root.show()
    APP.processEvents()

    ThemeManager.prewarm_themes()
    label_id = id(label)
    ThemeManager.apply_theme(APP, "Koyu Mavi")
    APP.processEvents()

    assert ThemeManager._current_theme == "Koyu Mavi"
    assert id(label) == label_id
    assert "@" not in label.styleSheet()
    assert APP.palette().color(QPalette.ColorRole.Window).isValid()
    root.close()


def test_reapplying_identical_application_stylesheet_skips_qt_cascade(monkeypatch):
    ThemeManager._install_stylesheet_patch()
    previous_stylesheet = APP.styleSheet()
    original_setter = ThemeManager._original_app_set_stylesheet
    calls = []

    def counted_setter(target, stylesheet):
        calls.append(stylesheet)
        return original_setter(target, stylesheet)

    monkeypatch.setattr(ThemeManager, "_original_app_set_stylesheet", counted_setter)
    stylesheet = "QWidget { color: #123456; background-color: #abcdef; }"
    APP.setStyleSheet(stylesheet)
    APP.setStyleSheet(stylesheet)

    assert len(calls) == 1

    APP.setStyleSheet(previous_stylesheet)


def test_theme_switch_suspends_top_level_paints_during_qss_cascade(monkeypatch):
    root = QWidget()
    root.show()
    APP.processEvents()
    original_setter = ThemeManager._original_app_set_stylesheet
    updates_during_cascade = []

    def counted_setter(target, stylesheet):
        updates_during_cascade.append(
            [(widget, widget.updatesEnabled()) for widget in APP.topLevelWidgets()]
        )
        return original_setter(target, stylesheet)

    monkeypatch.setattr(
        ThemeManager, "_original_app_set_stylesheet", counted_setter
    )
    previous_theme = ThemeManager._current_theme
    target_theme = "AYEC" if previous_theme != "AYEC" else "Koyu Mavi"

    try:
        ThemeManager.apply_theme(APP, target_theme, window=root)
        APP.processEvents()

        assert updates_during_cascade
        assert all(not enabled for _widget, enabled in updates_during_cascade[-1])
        assert root.updatesEnabled()
    finally:
        ThemeManager.apply_theme(APP, previous_theme, window=root)
        root.close()


def test_window_scoped_theme_switch_skips_global_widget_replay(monkeypatch):
    root = QWidget()
    root.show()
    APP.processEvents()
    calls = []
    monkeypatch.setattr(
        ThemeManager,
        "refresh_all_widgets",
        lambda app=None: calls.append(app),
    )
    target_theme = (
        "AYEC"
        if ThemeManager._current_theme != "AYEC"
        else "Koyu Mavi"
    )

    ThemeManager.apply_theme(APP, target_theme, window=root)
    APP.processEvents()

    assert calls == []
    root.close()


def test_hidden_page_local_style_refreshes_when_page_becomes_visible():
    previous_theme = ThemeManager._current_theme
    target_theme = "AYEC" if previous_theme != "AYEC" else "Koyu Mavi"
    ThemeManager._install_stylesheet_patch()
    stack = QStackedWidget()
    first = QWidget()
    hidden = QWidget()
    hidden_layout = QVBoxLayout(hidden)
    hidden_label = QLabel("Hidden theme test")
    hidden_layout.addWidget(hidden_label)
    hidden_label.setStyleSheet(
        "QLabel { color: @text; background-color: @surface; }"
    )
    stack.addWidget(first)
    stack.addWidget(hidden)
    stack.setCurrentWidget(first)
    stack.show()
    APP.processEvents()

    try:
        old_generation = hidden_label._theme_applied_generation
        ThemeManager.apply_theme(APP, target_theme)
        APP.processEvents()
        assert hidden_label._theme_applied_generation == old_generation

        stack.setCurrentWidget(hidden)
        APP.processEvents()
        assert (
            hidden_label._theme_applied_generation
            == ThemeManager._theme_generation
        )
    finally:
        ThemeManager._activate_runtime_cache(previous_theme)
        stack.close()


def test_theme_preview_does_not_run_full_settings_save():
    applied = []
    writes = []
    fake = SimpleNamespace(
        cmb_theme=SimpleNamespace(currentText=lambda: "Forest"),
        main_window=SimpleNamespace(apply_theme=applied.append),
        db=SimpleNamespace(set_setting=lambda key, value: writes.append((key, value))),
    )

    BackgroundSettingsWidget._on_theme_preview_changed(fake, 2)

    assert applied == ["Forest"]
    assert writes == []


def test_company_theme_preview_only_applies_selected_theme():
    applied = []
    writes = []
    fake = SimpleNamespace(
        cmb_theme=SimpleNamespace(currentText=lambda: "Forest"),
        main_window=SimpleNamespace(
            _current_theme_name="AYEC",
            apply_theme=applied.append,
        ),
        db=SimpleNamespace(
            get_setting=lambda key, default=None: default,
            set_setting=lambda key, value: writes.append((key, value)),
        ),
    )

    CompanySettingsDialog._preview_theme(fake, 2)

    assert applied == ["Forest"]
    assert writes == []


def test_interface_scale_normalizes_to_supported_steps():
    assert ThemeManager.normalize_interface_scale("bad") == 100
    assert ThemeManager.normalize_interface_scale(84) == 80
    assert ThemeManager.normalize_interface_scale(126) == 130
    assert ThemeManager.normalize_interface_scale(999) == 140


def test_interface_scale_changes_qss_font_size_without_compounding():
    previous_scale = ThemeManager.interface_scale_percent()
    raw_style = "QLabel { font-size: 10px; }"
    try:
        ThemeManager._interface_scale_percent = 120
        first = ThemeManager._sanitize_qss(raw_style)
        second = ThemeManager._sanitize_qss(raw_style)
        assert "font-size: 12px" in first
        assert second == first

        ThemeManager._interface_scale_percent = 80
        smaller = ThemeManager._sanitize_qss(raw_style)
        assert "font-size: 8px" in smaller
    finally:
        ThemeManager._interface_scale_percent = previous_scale
        ThemeManager.invalidate_runtime_cache()


def test_classic_appearance_compacts_layout_and_modern_restores_it():
    root = QWidget()
    layout = QVBoxLayout(root)
    layout.setContentsMargins(20, 16, 20, 16)
    layout.setSpacing(12)

    AppearanceModeManager.apply_to_widget_tree(root, AppearanceModeManager.CLASSIC)
    assert layout.contentsMargins().left() == 8
    assert layout.contentsMargins().top() == 8
    assert layout.spacing() == 4

    AppearanceModeManager.apply_to_widget_tree(root, AppearanceModeManager.MODERN)
    assert layout.contentsMargins().left() == 20
    assert layout.contentsMargins().top() == 16
    assert layout.spacing() == 12
    root.close()


def test_classic_spacing_keeps_default_layouts_readable_and_restores_default():
    root = QWidget()
    layout = QVBoxLayout(root)
    original_spacing = layout.spacing()

    AppearanceModeManager.apply_to_widget_tree(root, AppearanceModeManager.CLASSIC)
    assert layout.spacing() == 4

    AppearanceModeManager.apply_to_widget_tree(root, AppearanceModeManager.MODERN)
    assert layout.spacing() == original_spacing
    root.close()


def test_classic_mode_disables_and_modern_restores_qt_effects():
    effect_names = (
        "UI_AnimateCombo",
        "UI_AnimateMenu",
        "UI_AnimateToolBox",
        "UI_AnimateTooltip",
        "UI_FadeMenu",
        "UI_FadeTooltip",
    )
    original_mode = APP.property("appearanceMode") or AppearanceModeManager.MODERN
    expected = {
        name: QApplication.isEffectEnabled(getattr(Qt.UIEffect, name))
        for name in effect_names
        if hasattr(Qt.UIEffect, name)
    }
    try:
        AppearanceModeManager.apply(app=APP, mode=AppearanceModeManager.CLASSIC)
        assert all(
            not QApplication.isEffectEnabled(getattr(Qt.UIEffect, name))
            for name in expected
        )
        AppearanceModeManager.apply(app=APP, mode=AppearanceModeManager.MODERN)
        assert {
            name: QApplication.isEffectEnabled(getattr(Qt.UIEffect, name))
            for name in expected
        } == expected
    finally:
        AppearanceModeManager.apply(app=APP, mode=original_mode)


def test_scoped_widget_tree_refresh_replays_nested_styles():
    ThemeManager._install_stylesheet_patch()
    previous_theme = ThemeManager._current_theme
    root = QWidget()
    layout = QVBoxLayout(root)
    label = QLabel("Scoped theme test")
    layout.addWidget(label)

    try:
        ThemeManager._activate_runtime_cache("Koyu Mavi")
        label.setStyleSheet(
            "QLabel { color: @text; background-color: @surface; }"
        )
        dark_style = label.styleSheet()

        ThemeManager._activate_runtime_cache("AYEC")
        ThemeManager.refresh_widget_tree(root, include_root=False)
        light_style = label.styleSheet()

        assert dark_style != light_style
        assert "@" not in light_style
    finally:
        ThemeManager._activate_runtime_cache(previous_theme)
        root.close()


def test_full_theme_refresh_visits_each_styled_widget_owner_once(monkeypatch):
    ThemeManager._install_stylesheet_patch()
    previous_theme = ThemeManager._current_theme

    class CountingLabel(QLabel):
        def __init__(self, parent=None):
            super().__init__("Theme refresh", parent)
            self.window_lookups = 0

        def window(self):
            self.window_lookups += 1
            return super().window()

    root = QWidget()
    other_root = QWidget()
    label = CountingLabel(root)
    label.setStyleSheet("QLabel { color: @text; }")
    label.window_lookups = 0
    monkeypatch.setattr(ThemeManager, "_styled_widgets", weakref.WeakSet([label]))

    try:
        root.show()
        other_root.show()
        APP.processEvents()
        ThemeManager._activate_runtime_cache("AYEC")
        ThemeManager.refresh_all_widgets(APP)
        assert label.window_lookups == 1
        assert "@" not in label.styleSheet()
    finally:
        root.close()
        other_root.close()
        ThemeManager._activate_runtime_cache(previous_theme)


def test_style_filter_skips_text_repair_during_theme_style_change(monkeypatch):
    root = QWidget()
    repaired = []
    monkeypatch.setattr(
        ThemeManager,
        "_repair_widget_texts",
        lambda widget: repaired.append(widget),
    )

    style_filter = _StyleChangeFilter()
    style_filter.eventFilter(root, QEvent(QEvent.Type.StyleChange))

    assert repaired == []


def test_style_filter_repairs_widget_only_once_when_shown(monkeypatch):
    root = QWidget()
    repaired = []
    monkeypatch.setattr(
        ThemeManager,
        "_repair_widget_texts",
        lambda widget: repaired.append(widget),
    )

    style_filter = _StyleChangeFilter()
    style_filter.eventFilter(root, QEvent(QEvent.Type.Show))
    style_filter.eventFilter(root, QEvent(QEvent.Type.Show))

    assert repaired == [root]


def test_table_cell_hover_rules_survive_theme_transformation():
    qss = """
        QTableWidget::item:hover, QListWidget::item:hover {
            background: #112233;
        }
        QComboBox QAbstractItemView::item:hover {
            background: #334455;
        }
    """

    transformed = ThemeManager.transform_qss(qss)

    assert "QTableWidget::item:hover" in transformed
    assert "QListWidget::item:hover" in transformed
    assert "QComboBox QAbstractItemView::item:hover" in transformed


def test_style_filter_forces_table_row_selection():
    table = QTableWidget(2, 2)
    table.setSelectionBehavior(
        QAbstractItemView.SelectionBehavior.SelectItems
    )

    style_filter = _StyleChangeFilter()
    style_filter.eventFilter(table, QEvent(QEvent.Type.Polish))

    assert (
        table.selectionBehavior()
        == QAbstractItemView.SelectionBehavior.SelectRows
    )
