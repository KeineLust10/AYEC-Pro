import sys
from pathlib import Path

ADMIN_ROOT = Path(__file__).resolve().parents[1] / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from PyQt6.QtWidgets import QLabel, QMainWindow

from toast import show_toast


def test_admin_toast_uses_bottom_right_window_overlay(persistent_qapplication):
    window = QMainWindow()
    window.resize(1200, 800)
    window.show()
    persistent_qapplication.processEvents()

    toast = show_toast(window, "License request failed", "error", duration=60000)
    persistent_qapplication.processEvents()

    host = window._admin_toast_host
    assert host.geometry() == window.rect()
    assert host.layout().alignment().value & 0x2
    assert toast.isVisible()
    assert toast.findChild(QLabel, "adminToastText").text() == "License request failed"
    host._remove(toast)
    persistent_qapplication.processEvents()
    assert host.layout().count() == 0
    window.close()
    window.deleteLater()
    persistent_qapplication.processEvents()
