import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication, QPushButton

from src.ui.widgets.themed_tooltip import ThemedToolTipFilter


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class _ClassicDb:
    def get_setting(self, key, default=None):
        if key == "appearance_mode":
            return "classic"
        return default


def test_themed_tooltip_uses_light_surface_in_classic_mode():
    button = QPushButton()
    button.resize(36, 36)
    tooltip = ThemedToolTipFilter(
        button,
        "Yeni Cihaz Ekle",
        _ClassicDb(),
    )
    try:
        QApplication.sendEvent(button, QEvent(QEvent.Type.Enter))
        APP.processEvents()
        assert button.toolTip() == ""
        assert tooltip.label.isVisible()
        assert tooltip.label.text() == "Yeni Cihaz Ekle"
        assert tooltip.label.property("skipThemeTransform") is True
        assert "background-color: #FFFFFF" in tooltip.label.styleSheet()
        QApplication.sendEvent(button, QEvent(QEvent.Type.Leave))
        APP.processEvents()
        assert not tooltip.label.isVisible()
    finally:
        button.close()
