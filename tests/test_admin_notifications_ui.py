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
    toasts = []
    monkeypatch.setattr(notifications, "show_toast", lambda _parent, message, level: toasts.append((message, level)))
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
    assert toasts == [
        ("Bildirim kuyruga ekleniyor...", "success"),
        ("Bildirim API tarafindan kabul edildi.", "success"),
    ]


def test_reference_icon_normalization_observes_late_text_updates_and_aligns_content():
    page = notifications.NotificationsPage.__new__(notifications.NotificationsPage)
    QWidget.__init__(page)
    page._ready = False
    page._view = _FakeView()
    page._companies = []

    page._on_loaded(True)

    bootstrap = page._view.page_object.scripts[0]
    assert "main{width:calc(100% - 288px)!important;margin-left:288px!important;padding-top:0!important}" in bootstrap
    assert "characterData:true" in bootstrap
    assert "root?.matches?.('.material-symbols-outlined')" in bootstrap
    assert "@media(max-width:760px){main{width:100%!important;margin-left:0!important" in bootstrap


def test_material_icon_fallback_covers_reference_glyphs():
    html = notifications.REFERENCE.read_text(encoding="utf-8")
    icons = set(__import__("re").findall(r'material-symbols-outlined[^>]*>([^<]+)</span>', html))

    assert icons <= set(notifications.ICON_FALLBACKS)


def test_notification_reference_is_utf8_and_uses_responsive_layout():
    html = notifications.REFERENCE.read_text(encoding="utf-8")
    assert 'name="viewport"' in html
    assert "lg:grid-cols-12" in html
    assert "\u0130stemci Masa\u00fcst\u00fc \u00d6nizlemesi" in html


def test_notification_canvas_preserves_reference_viewport_breakpoints(persistent_qapplication):
    canvas = notifications._NotificationCanvas()
    view = QWidget(canvas)
    canvas.set_view(view)
    canvas.resize(1176, 944)
    canvas.show()
    persistent_qapplication.processEvents()
    assert (view.x(), view.width(), view.height()) == (-264, 1440, 944)
    canvas.resize(390, 844)
    persistent_qapplication.processEvents()
    assert (view.x(), view.width(), view.height()) == (0, 390, 844)
