import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QAbstractAnimation, QPropertyAnimation, Qt
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import QApplication, QComboBox, QDateEdit, QDialog, QFrame, QGraphicsBlurEffect, QGraphicsDropShadowEffect, QLineEdit, QPushButton, QVBoxLayout, QWidget

from src.utils._theme_color_utils import contrast_ratio
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.theme_manager import ThemeManager
from tools.quality.desktop_visual_acceptance import capture_combo_calendar_popups, capture_form_control_states


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


def test_classic_palette_is_readable_and_flat_for_every_display_theme():
    previous_theme = ThemeManager._current_theme
    try:
        for theme_name in ThemeManager.DISPLAY_THEMES:
            ThemeManager._current_theme = theme_name
            tokens = AppearanceModeManager.classic_tokens()
            stylesheet = AppearanceModeManager.classic_qss()

            for background in ("window", "surface", "surface_alt"):
                assert contrast_ratio(tokens["text"], tokens[background]) >= 4.5
            assert contrast_ratio(tokens["text_muted"], tokens["surface"]) >= 4.5
            assert contrast_ratio(tokens["disabled_text"], tokens["disabled_bg"]) >= 4.5
            assert contrast_ratio(tokens["selection_text"], tokens["selection_bg"]) >= 4.5
            assert not re.search(
                r"background(?:-color)?\s*:\s*#ffffff\b", stylesheet, re.IGNORECASE
            )
            assert "qlineargradient" not in stylesheet.lower()
            assert "rgba(" not in stylesheet.lower()
            assert "transparent" not in stylesheet.lower()
            radii = set(re.findall(r"border-radius\s*:\s*([^;]+)", stylesheet))
            assert radii <= {"0px"}
    finally:
        ThemeManager._current_theme = previous_theme


def test_classic_theme_switch_refreshes_tokens_and_modern_removes_classic_styles():
    root = QWidget()
    previous_theme = ThemeManager._current_theme
    previous_mode = APP.property("appearanceMode") or AppearanceModeManager.MODERN
    try:
        for theme_name in ThemeManager.DISPLAY_THEMES:
            ThemeManager.apply_theme(APP, theme_name, window=root, animate=False)
            AppearanceModeManager.apply(
                app=APP,
                root=root,
                mode=AppearanceModeManager.CLASSIC,
            )
            tokens = AppearanceModeManager.classic_tokens()
            assert APP.property("appearanceMode") == AppearanceModeManager.CLASSIC
            assert f"background-color: {tokens['surface']};" in APP.styleSheet()
            assert f"color: {tokens['text']};" in APP.styleSheet()

        AppearanceModeManager.apply(
            app=APP,
            root=root,
            mode=AppearanceModeManager.MODERN,
        )
        assert AppearanceModeManager._STYLE_MARKER_START not in APP.styleSheet()
    finally:
        ThemeManager.apply_theme(APP, previous_theme, window=root, animate=False)
        AppearanceModeManager.apply(app=APP, root=root, mode=previous_mode)
        root.close()


def test_appearance_mode_refreshes_component_theme_hooks_on_mode_switch():
    class ThemeAwareWidget(QWidget):
        def __init__(self):
            super().__init__()
            self.observed_modes = []

        def apply_theme_styles(self):
            self.observed_modes.append(APP.property("appearanceMode"))

    root = ThemeAwareWidget()
    previous_mode = APP.property("appearanceMode") or AppearanceModeManager.MODERN
    try:
        AppearanceModeManager.apply(app=APP, root=root, mode=AppearanceModeManager.CLASSIC)
        AppearanceModeManager.apply(app=APP, root=root, mode=AppearanceModeManager.MODERN)
        assert root.observed_modes == [
            AppearanceModeManager.CLASSIC,
            AppearanceModeManager.MODERN,
        ]
    finally:
        AppearanceModeManager.apply(app=APP, root=root, mode=previous_mode)
        root.close()


def test_classic_widget_overrides_flatten_sidebar_and_kanban_styles():
    cases = (
        (QFrame, "SideMenu"),
        (QFrame, "KanbanCard"),
        (QPushButton, "KanbanAction"),
    )
    for widget_type, name in cases:
        widget = widget_type()
        widget.setObjectName(name)
        widget.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #FFFFFF, stop:1 #000000);"
            "border-radius: 12px; color: rgba(0, 0, 0, 0.5);"
        )
        classic_style = AppearanceModeManager._widget_classic_qss(widget).lower()
        assert "qlineargradient" not in classic_style
        assert "rgba(" not in classic_style
        assert "border-radius: 0px" in classic_style
        widget.close()


def test_classic_mode_disables_and_restores_all_widget_graphics_effects():
    root = QWidget()
    shadow_widget = QWidget(root)
    blur_widget = QWidget(root)
    shadow = QGraphicsDropShadowEffect(shadow_widget)
    blur = QGraphicsBlurEffect(blur_widget)
    shadow_widget.setGraphicsEffect(shadow)
    blur_widget.setGraphicsEffect(blur)
    try:
        assert shadow.isEnabled()
        assert blur.isEnabled()
        AppearanceModeManager.apply(app=APP, root=root, mode=AppearanceModeManager.CLASSIC)
        assert not shadow.isEnabled()
        assert not blur.isEnabled()
        AppearanceModeManager.apply(app=APP, root=root, mode=AppearanceModeManager.MODERN)
        assert shadow.isEnabled()
        assert blur.isEnabled()
    finally:
        root.close()


def test_classic_mode_pauses_running_animations_and_modern_resumes_them():
    root = QWidget()
    target = QWidget(root)
    animation = QPropertyAnimation(target, b"minimumWidth", target)
    animation.setDuration(1000)
    animation.setStartValue(100)
    animation.setEndValue(200)
    try:
        animation.start()
        assert animation.state() == QAbstractAnimation.State.Running
        AppearanceModeManager.apply(app=APP, root=root, mode=AppearanceModeManager.CLASSIC)
        assert animation.state() == QAbstractAnimation.State.Paused
        AppearanceModeManager.apply(app=APP, root=root, mode=AppearanceModeManager.MODERN)
        assert animation.state() == QAbstractAnimation.State.Running
    finally:
        animation.stop()
        root.close()


def test_classic_mode_pauses_animations_started_after_mode_switch():
    root = QWidget()
    target = QWidget(root)
    animation = QPropertyAnimation(target, b"minimumWidth", target)
    animation.setDuration(1000)
    animation.setStartValue(100)
    animation.setEndValue(200)
    try:
        AppearanceModeManager.apply(app=APP, root=root, mode=AppearanceModeManager.CLASSIC)
        animation.start()
        assert animation.state() == QAbstractAnimation.State.Paused
        AppearanceModeManager.apply(app=APP, root=root, mode=AppearanceModeManager.MODERN)
        assert animation.state() == QAbstractAnimation.State.Running
    finally:
        animation.stop()
        root.close()


def test_classic_mode_guards_animations_created_after_a_widget_is_shown():
    root = QWidget()
    target = QWidget(root)
    root.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    root.resize(120, 80)
    animation = None
    try:
        AppearanceModeManager.apply(app=APP, root=root, mode=AppearanceModeManager.CLASSIC)
        root.show()
        APP.processEvents()
        animation = QPropertyAnimation(target, b"minimumWidth", target)
        APP.processEvents()
        animation.setDuration(1000)
        animation.setStartValue(20)
        animation.setEndValue(80)
        animation.start()
        assert animation.state() == QAbstractAnimation.State.Paused
    finally:
        if animation is not None:
            animation.stop()
        root.close()
        AppearanceModeManager.apply(app=APP, mode=AppearanceModeManager.MODERN)


def test_new_dialog_is_classic_before_its_first_offscreen_paint(tmp_path):
    class LateStyledDialog(QDialog):
        def showEvent(self, event):
            self.setStyleSheet(
                "QDialog { background-color: #FFFFFF; border-radius: 15px; }"
            )
            super().showEvent(event)

    previous_mode = APP.property("appearanceMode") or AppearanceModeManager.MODERN
    previous_theme = ThemeManager._current_theme
    dialog = LateStyledDialog()
    dialog.resize(160, 100)
    try:
        ThemeManager._current_theme = "AYEC"
        AppearanceModeManager.apply(
            app=APP,
            root=dialog,
            mode=AppearanceModeManager.CLASSIC,
        )
        dialog.show()
        APP.processEvents()

        image = QImage(dialog.size(), QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        dialog.render(painter)
        painter.end()
        screenshot = tmp_path / "classic_first_paint.png"
        assert image.save(str(screenshot))
        assert screenshot.is_file()
        assert AppearanceModeManager._STYLE_MARKER_START in dialog.styleSheet()
        assert "QDialog {" in dialog.styleSheet()
        assert "border-radius: 0px" in dialog.styleSheet()
        expected = AppearanceModeManager.classic_tokens()["surface"]
        assert image.pixelColor(80, 50).name().upper() == expected.upper()
    finally:
        dialog.close()
        ThemeManager._current_theme = previous_theme
        AppearanceModeManager.apply(app=APP, mode=previous_mode)


def test_combo_and_calendar_popups_are_captured_offscreen_in_classic(tmp_path):
    root = QWidget()
    layout = QVBoxLayout(root)
    combo = QComboBox(root)
    combo.addItems(["First", "Second", "Third"])
    date_edit = QDateEdit(root)
    date_edit.setCalendarPopup(True)
    line_edit = QLineEdit(root)
    layout.addWidget(combo)
    layout.addWidget(date_edit)
    layout.addWidget(line_edit)
    root.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    root.resize(240, 100)
    try:
        AppearanceModeManager.apply(
            app=APP,
            root=root,
            mode=AppearanceModeManager.CLASSIC,
        )
        root.show()
        APP.processEvents()
        result = capture_combo_calendar_popups(root, tmp_path, "AYEC", "popup_probe")
        assert result["combos"] == 1
        assert result["calendars"] == 1
        assert result["captures"] == 2
        assert result["failures"] == []
        assert len(list((tmp_path / "popup_states").glob("*.png"))) == 2
        input_result = capture_form_control_states(root, tmp_path, "AYEC", "popup_probe")
        assert input_result["controls"] == 2
        assert input_result["captures"] == 4
        assert input_result["failures"] == []
    finally:
        root.close()
        AppearanceModeManager.apply(app=APP, mode=AppearanceModeManager.MODERN)
