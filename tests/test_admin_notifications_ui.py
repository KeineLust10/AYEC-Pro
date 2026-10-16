import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from PyQt6.QtWidgets import QWidget
from pages import notifications


class _FakePage:
    def __init__(self):
        self.scripts = []

    def runJavaScript(self, script):
        self.scripts.append(script)


class _FakeView:
    def __init__(self):
        self.page_object = _FakePage()

    def page(self):
        return self.page_object


def test_notification_bridge_sends_selected_companies_and_updates_status(persistent_qapplication, monkeypatch):
    sent = []
    monkeypatch.setattr(
        notifications.api_client,
        "send_notification",
        lambda target, title, body, icon, popup: sent.append((target, title, body, icon, popup)) or {"sent_to": 2},
    )
    page = notifications.NotificationsPage.__new__(notifications.NotificationsPage)
    QWidget.__init__(page)
    page._view = _FakeView()
    page._thread = None

    page.sendFromReference('["tenant-a","tenant-b"]', "Maintenance", "Restart at 18:00", "warning", False, False)
    page._thread.wait(3000)
    persistent_qapplication.processEvents()

    assert sent == [
        ("tenant-a", "Maintenance", "Restart at 18:00", "warning", False),
        ("tenant-b", "Maintenance", "Restart at 18:00", "warning", False),
    ]
    assert any("Bildirim API" in script for script in page._view.page_object.scripts)


def test_notification_reference_is_utf8_and_uses_responsive_layout():
    html = notifications.REFERENCE.read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert "lg:grid-cols-12" in html
    assert "\u0130stemci Masa\u00fcst\u00fc \u00d6nizlemesi" in html
