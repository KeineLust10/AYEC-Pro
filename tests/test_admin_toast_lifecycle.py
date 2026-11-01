import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication, QEvent, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QWidget


ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from toast import show_toast


def _process_deferred_deletes(app):
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    app.processEvents()


def test_admin_toast_timer_expires_and_hides_empty_host():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    parent.show()

    show_toast(parent, "Saved", "success", duration=1000)
    host = parent._admin_toast_host
    assert host._layout.count() == 1

    QTest.qWait(1150)
    _process_deferred_deletes(app)

    assert host._layout.count() == 0
    assert not host.isVisible()
    parent.close()
    parent.deleteLater()
    _process_deferred_deletes(app)


def test_admin_toast_parent_can_close_before_timer_expires():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    parent.show()

    show_toast(parent, "Pending", "info", duration=1000)
    parent.close()
    parent.deleteLater()
    _process_deferred_deletes(app)

    QTest.qWait(1150)
    _process_deferred_deletes(app)
