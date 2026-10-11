import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication, QWidget, QLabel
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from src.utils.theme_colors import theme_qss, tc
from src.utils.theme_manager import ThemeManager
from src.ui.widgets.animated_toggle import AnimatedToggle


@pytest.mark.parametrize("class_name", ("TechnicianWizardPage1", "TechnicianWizardPage2", "TechnicianWizardPage3"))
def test_technician_wizard_tokens_resolve_and_refresh_without_losing_raw_palette_keys(class_name):
    app = QApplication.instance() or QApplication([])
    previous_theme = ThemeManager._current_theme
    ThemeManager._install_stylesheet_patch()
    root = type(class_name, (QWidget,), {})()
    label = QLabel("Actual field", root)
    root.setStyleSheet(theme_qss("QWidget{background:@finance_surface;border:1px solid @finance_outline;}"))
    label.setStyleSheet(theme_qss("QLabel{color:@finance_text;font-size:10px;}"))
    try:
        for name in ("Koyu Mavi", "AYEC", "Koyu Mavi"):
            ThemeManager.apply_theme(app, name, window=root, animate=False)
            ThemeManager.refresh_widget_tree(root)
            root.show()
            app.processEvents()
            QTest.qWait(80)
            assert "@finance_" not in root.styleSheet()
            assert "@finance_" not in label.styleSheet()
            assert ThemeManager.get_palette_color(name, "finance_surface").lower() in root.styleSheet().lower()
            assert ThemeManager.get_palette_color(name, "finance_text").lower() in label.styleSheet().lower()
            assert "@finance_surface" in root._theme_raw_stylesheet
            assert "@finance_text" in label._theme_raw_stylesheet
    finally:
        root.close()
        root.deleteLater()
        app.processEvents()
        ThemeManager.apply_theme(app, previous_theme, animate=False)


def test_setup_wizard_literal_styles_still_bypass_legacy_color_conversion():
    app = QApplication.instance() or QApplication([])
    root = type("SetupWizard", (QWidget,), {})()
    label = QLabel("Setup field", root)
    try:
        literal = "QLabel{color:#123456;background:#654321;}"
        label.setStyleSheet(theme_qss(literal))
        assert label.styleSheet() == literal
    finally:
        root.close()
        root.deleteLater()
        app.processEvents()


def test_reference_checkbox_retains_native_click_keyboard_and_read_only_behavior():
    app = QApplication.instance() or QApplication([])
    previous_theme = ThemeManager._current_theme
    toggle = AnimatedToggle()
    toggle.setProperty("referenceCheckbox", True)
    toggle.setFixedSize(18, 18)
    states = []
    toggle.toggled.connect(states.append)
    try:
        toggle.show()
        app.processEvents()
        QTest.mouseClick(toggle, Qt.MouseButton.LeftButton)
        assert toggle.isChecked()
        assert states == [True]
        for name in ("Koyu Mavi", "AYEC"):
            ThemeManager.apply_theme(app, name, animate=False)
            app.processEvents()
            assert toggle.grab().toImage().pixelColor(4, 4) == QColor(tc("accent"))
        QTest.keyClick(toggle, Qt.Key.Key_Space)
        assert not toggle.isChecked()
        assert states == [True, False]
        toggle.setEnabled(False)
        QTest.mouseClick(toggle, Qt.MouseButton.LeftButton)
        assert states == [True, False]
        assert not toggle.isChecked()
    finally:
        toggle.close()
        toggle.deleteLater()
        app.processEvents()
        ThemeManager.apply_theme(app, previous_theme, animate=False)


def test_accent_soft_uses_theme_fallback_without_unknown_token_warning(caplog):
    from src.utils._theme_qss_transformer import ThemeQSSTransformer

    resolved = ThemeQSSTransformer._resolve_palette_token(
        "accent_soft",
        {"text": "#111827", "surface_alt": "#E5E7EB"},
        lambda _key, fallback="": "#DCE8FB" if fallback else "",
    )

    assert resolved == "#DCE8FB"
    assert "Unknown QSS theme token '@accent_soft'" not in caplog.text
