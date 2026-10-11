import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QStyle, QStyleOptionComboBox

from src.ui.widgets.modern_inputs import ModernComboBox
from src.utils.theme_manager import ThemeManager


def test_reference_chevron_preserves_native_popup_and_selection_signals():
    app = QApplication.instance() or QApplication([])
    for name in ("AYEC", "Koyu Mavi"):
        combo = ModernComboBox(items=["First", "Second"])
        combo.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        combo.set_reference_chevron()
        source = combo.styleSheet()
        combo.set_reference_chevron()
        assert combo.styleSheet() == source
        combo.resize(240, 32)
        combo.show()
        ThemeManager.apply_theme(app, name, window=combo, animate=False)
        ThemeManager.refresh_widget_tree(combo)
        app.processEvents()
        changes = []
        combo.currentTextChanged.connect(changes.append)
        try:
            assert combo.property("referenceChevron") is True
            option = QStyleOptionComboBox()
            combo.initStyleOption(option)
            arrow = combo.style().subControlRect(
                QStyle.ComplexControl.CC_ComboBox, option,
                QStyle.SubControl.SC_ComboBoxArrow, combo)
            assert arrow.isValid()
            assert not combo.grab().isNull()
            QTest.mouseClick(combo, Qt.MouseButton.LeftButton, pos=arrow.center())
            app.processEvents()
            assert combo.view().isVisible()
            QTest.keyClick(combo.view(), Qt.Key.Key_Down)
            QTest.keyClick(combo.view(), Qt.Key.Key_Return)
            app.processEvents()
            assert combo.currentText() == "Second"
            assert changes == ["Second"]
            combo.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            app.processEvents()
            assert not combo.grab().isNull()
            combo.setEnabled(False)
            app.processEvents()
            assert not combo.grab().isNull()
        finally:
            combo.hidePopup()
            combo.close()
            combo.deleteLater()
            app.processEvents()
