import sys
from pathlib import Path

from PyQt6.QtWidgets import QLabel, QPushButton

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.live_status import LiveStatusPage, _status_card
import api_client


def test_live_status_counters_filters_and_navigation(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "live_status", lambda: [])
    page = LiveStatusPage()
    if page._thread:
        page._thread.wait(3000)
    persistent_qapplication.processEvents()
    page._populate(
        [
            {"id": "a1", "company_name": "ASLAN TIC", "sector": "teknik_servis", "db_filename": "aslan.db", "user_id": 7, "ip_address": "192.168.1.108", "user_agent": "AYEC Pro Desktop", "last_seen": "2026-10-14T08:11:02Z", "dashboard_version": "v2.0.1 (Pilot)", "uptime_text": "14G 06S 22D", "online": True, "active_users": 2, "ping_ms": 11, "data_rate": 1.4, "unsynced_queue": 0},
            {"id": "c3", "company_name": "Bulut Bilisim", "online": True, "active_users": 1, "ping_ms": 92, "data_rate": 1.4, "unsynced_queue": 0},
            {"id": "b2", "company_name": "Babali Servis", "online": False, "active_users": 0, "unsynced_queue": 1},
        ]
    )

    assert [widget.text() for widget in page._metric_widgets] == ["2 / 3 Online", "52 ms", "1.4 MB/s", "1 Paket"]
    assert page._latency_history == [52]
    aslan_card = next(card for company, card in page._company_widgets if company["id"] == "a1")
    assert aslan_card.findChild(QLabel, "cardSector").text() == "TEKN\u0130K SERV\u0130S"
    assert "ID: a1" in aslan_card.findChild(QLabel, "cardMeta").text()
    assert aslan_card.findChild(QLabel, "cardHeartbeat").text() == "Heartbeat: 2026-10-14T08:11:02Z"
    assert [label.text() for label in aslan_card.findChildren(QLabel, "telemetryValue")] == ["11 ms", "v2.0.1 (Pilot)", "14G 06S 22D", "192.168.1.108"]
    assert any("192.168.1.108" in label.text() for label in aslan_card.findChildren(QLabel, "cardDetail"))
    offline_card = next(card for company, card in page._company_widgets if company["id"] == "b2")
    assert [label.text() for label in offline_card.findChildren(QLabel, "telemetryValue")] == ["--", "--", "--", "--"]
    assert page._event_feed.count() == 3
    assert any("ASLAN TIC" in page._event_feed.item(index).text() for index in range(page._event_feed.count()))
    page._clear_events()
    assert page._event_feed.count() == 0
    page.resize(390, 844)
    page.show()
    persistent_qapplication.processEvents()
    assert page._page_scroll.horizontalScrollBar().maximum() == 0, {
        "page": page.width(),
        "scroll": page._page_scroll.width(),
        "viewport": page._page_scroll.viewport().width(),
        "content": page._page_scroll.widget().width(),
        "content_hint": page._page_scroll.widget().sizeHint().width(),
        "inner": page._inner.width(),
        "inner_hint": page._inner.sizeHint().width(),
        "grid_hint": page._grid_lay.sizeHint().width(),
        "scroll_max": page._page_scroll.horizontalScrollBar().maximum(),
    }
    assert all(card.width() <= page._page_scroll.viewport().width() for _, card in page._company_widgets)
    assert len({card.geometry().x() for _, card in page._company_widgets}) == 1
    page._set_filter("offline")
    assert sum(not card.isHidden() for _, card in page._company_widgets) == 1
    page._set_filter("online")
    assert sum(not card.isHidden() for _, card in page._company_widgets) == 1
    page._set_filter("slow")
    assert sum(not card.isHidden() for _, card in page._company_widgets) == 1
    page._search.setText("ASLAN")
    assert sum(not card.isHidden() for _, card in page._company_widgets) == 0

    destinations = []
    page.navigate_requested.connect(destinations.append)
    actions = page.findChildren(QPushButton, "livePrimary")
    actions[0].click()
    assert destinations == ["notifications"]


def test_live_status_card_actions_match_root_and_tenant_reference(persistent_qapplication):
    destinations = []
    root = _status_card(
        {"id": "tenant-root", "company_name": "Root", "online": True, "is_platform_root": True},
        navigate=destinations.append,
    )
    tenant = _status_card(
        {"id": "tenant-client", "company_name": "Client", "online": True},
        navigate=destinations.append,
    )

    assert [button.text() for button in root._action_buttons] == [
        "Ping G\u00f6nder",
        "Uzaktan Te\u015fhis",
        "Masa\u00fcst\u00fc Mesaj\u0131",
        "Yedek Tetikle",
    ]
    assert [button.text() for button in tenant._action_buttons] == [
        "Ping G\u00f6nder",
        "Mesaj G\u00f6nder",
        "\u0130ncele & Loglar",
    ]
    root._action_buttons[-1].click()
    tenant._action_buttons[-1].click()
    assert destinations == ["backups", "audit_logs"]


def test_live_status_reference_header_keeps_compact_action_ribbon(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "live_status", lambda: [])
    page = LiveStatusPage()
    if page._thread:
        page._thread.wait(3000)
    page.resize(1440, 1000)
    page.show()
    persistent_qapplication.processEvents()
    actions = [button.text() for button in page._header_actions.findChildren(QPushButton)]
    assert actions == ["Manuel Yenile", "Acil Anons G\u00f6nder"]
    assert page._counter.height() < 50
    assert page._header_actions.objectName() == "liveHeaderActions"
    margins = page._page_scroll.widget().layout().contentsMargins()
    assert (margins.left(), margins.right()) == (40, 16)
    page.resize(390, 844)
    persistent_qapplication.processEvents()
    margins = page._page_scroll.widget().layout().contentsMargins()
    assert (margins.left(), margins.right()) == (16, 16)
    assert page._page_scroll.horizontalScrollBar().maximum() == 0
