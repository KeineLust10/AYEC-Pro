import os
import sys
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent
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


def test_table_cell_hover_rules_are_removed_globally():
    qss = """
        QTableWidget::item:hover, QListWidget::item:hover {
            background: #112233;
        }
        QComboBox QAbstractItemView::item:hover {
            background: #334455;
        }
    """

    transformed = ThemeManager.transform_qss(qss)

    assert "QTableWidget::item:hover" not in transformed
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
