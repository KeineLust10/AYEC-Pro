import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.dashboard import DashboardPage
import api_client


def test_dashboard_populates_metrics_logs_and_search(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "dashboard", lambda: {})
    monkeypatch.setattr(api_client, "live_status", lambda: [])
    page = DashboardPage()
    if page._thread:
        page._thread.wait(3000)
    persistent_qapplication.processEvents()
    page._latency_samples.clear()
    page._populate(
        {
            "total_companies": 4,
            "active_companies": 3,
            "inactive_companies": 1,
            "online_users": 7,
            "logins_today": 18,
            "disk_usage": "%30.3 (30.0 / 99.0 GB)",
            "backup_coverage": 2,
            "pending_commands": 5,
            "expiring_licenses": 2,
            "dashboard_latency_ms": 12.4,
            "recent_logs": [
                {"time": "2026-10-14 09:42", "action": "admin_license_updated", "company": "ASLAN TIC"},
                {"time": "2026-10-14 09:38", "action": "admin_notification_sent", "company": "Babali Servis"},
            ],
            "live_companies": [
                {"company_name": "ASLAN TIC", "online": True, "active_users": 2, "last_seen": "2 sn once"},
                {"company_name": "Babali Servis", "online": False, "active_users": 0, "last_seen": ""},
            ],
        }
    )

    assert page._primary_grid.count() == 4
    assert page._secondary_grid.count() == 5
    metric_titles = [card.findChild(QLabel, "metricTitle").text() for card in page._metric_cards]
    metric_values = [card.findChild(QLabel, "metricValue").text() for card in page._metric_cards]
    metric_details = [card.findChild(QLabel, "metricSub").text() for card in page._metric_cards]
    metric_icons = [card.findChild(QLabel, "metricIcon").accessibleName() for card in page._metric_cards]
    metric_badges = [card.findChild(QLabel, "metricBadge").text() for card in page._metric_cards]
    metric_states = [card.findChild(QLabel, "metricTrend").text() for card in page._metric_cards]
    assert metric_icons == metric_titles
    assert metric_badges[:4] == ["Tenant", "%75 Aktif", "3 Risk", "WebSocket Ba\u011fl\u0131"]
    assert metric_states[:4] == ["+1 bu ay", "Kontrol gerekli", "Kontrol", ""]
    assert metric_titles[:4] == [
        "Toplam Kay\u0131tl\u0131 Firma",
        "Aktif Lisansl\u0131 Firma",
        "Pasif / Ask\u0131da Firma",
        "Canl\u0131 \u0130stemci & Kullan\u0131c\u0131",
    ]
    assert metric_titles[4:] == [
        "Bug\u00fcn Giri\u015f",
        "Sunucu SSD Alan\u0131",
        "Yedek Kapsam\u0131",
        "Bekleyen Komut",
        "Lisans Biti\u015f Uyar\u0131s\u0131",
    ]
    assert metric_values == ["4", "3", "1", "7", "18", "%30.3 (30.0 / 99.0 GB)", "2 / 4 Firma", "5", "2"]
    assert metric_details[6] == "%50 Koruma (Bulut)"
    assert page._latency_average.text() == "Ortalama: 12.4ms"
    assert page._latency_chart._samples[-1][1] == 12.4
    page._search.clear()
    page.resize(1440, 900)
    page.show()
    persistent_qapplication.processEvents()
    assert not page._latency_chart.grab().toImage().isNull()
    assert page._log_table.rowCount() == 2
    assert page._log_table.columnCount() == 5
    assert page._log_table.item(0, 3).data(Qt.ItemDataRole.UserRole) == "Recorded"
    assert page._log_table.item(0, 4).text() == "System"
    assert page._log_table.cellWidget(0, 1) is not None
    assert page._log_table.cellWidget(0, 1).findChild(QLabel, "dashActionLabel").wordWrap()
    assert page._log_table.cellWidget(0, 2) is not None
    assert page._log_table.cellWidget(0, 3).findChild(QLabel, "dashStatusPill") is not None
    assert "1 / 2" in page._health_summary.text()
    company_rows = page.findChildren(QFrame, "dashCompanyRow")
    assert len(company_rows) == 2
    assert company_rows[0].findChild(QLabel, "dashCompanyMeta").text() == "2 aktif kullan\u0131c\u0131  |  Son g\u00f6r\u00fclme: 2 sn once"

    page._search.setText("ASLAN")
    visible = sum(not page._log_table.isRowHidden(row) for row in range(page._log_table.rowCount()))
    assert visible == 1

    page._search.setText("System")
    visible = sum(not page._log_table.isRowHidden(row) for row in range(page._log_table.rowCount()))
    assert visible == 2
    page._timer.stop()


def test_dashboard_metrics_and_workspace_reflow_at_mobile_width(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "dashboard", lambda: {})
    monkeypatch.setattr(api_client, "live_status", lambda: [])
    page = DashboardPage()
    page.resize(390, 844)
    page.show()
    persistent_qapplication.processEvents()
    page._populate({"total_companies": 4, "active_companies": 3, "backup_coverage": 2})
    persistent_qapplication.processEvents()

    assert page._primary_count == 1
    assert page._secondary_count == 1
    assert page._dashboard_root_layout.contentsMargins().top() == 0
    assert page._narrow_table
    assert page._log_table.horizontalScrollBar().maximum() > 0
    assert page._dashboard_scroll.horizontalScrollBar().maximum() == 0
    assert page._primary_grid.getItemPosition(3)[:2] == (3, 0)
    assert page._secondary_grid.getItemPosition(4)[:2] == (4, 0)
    page.resize(560, 900)
    persistent_qapplication.processEvents()
    assert page._log_table.horizontalScrollBar().maximum() > 0
    page.resize(390, 844)
    persistent_qapplication.processEvents()
    assert page._dashboard_scroll.horizontalScrollBar().maximum() == 0
    page._timer.stop()
    page.close()


def test_dashboard_quick_actions_emit_navigation(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "dashboard", lambda: {})
    monkeypatch.setattr(api_client, "live_status", lambda: [])
    page = DashboardPage()
    destinations = []
    page.navigate_requested.connect(destinations.append)
    buttons = page.findChildren(QPushButton, "dashActionButton")

    assert len(buttons) == 4
    buttons[1].click()
    assert destinations == ["backups"]


def test_dashboard_health_rows_show_client_version_ping_and_seen_state(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "dashboard", lambda: {})
    monkeypatch.setattr(api_client, "live_status", lambda: [])
    page = DashboardPage()
    if page._thread:
        page._thread.wait(3000)
    persistent_qapplication.processEvents()
    page._populate({"live_companies": [{
        "company_name": "ASLAN TIC",
        "client_version": "v2.0 Pro",
        "ping_ms": 11,
        "online": True,
        "active_users": 2,
        "last_seen": "2 sn \u00f6nce",
    }]})

    row = page.findChild(QFrame, "dashCompanyRow")
    assert row.findChild(QLabel, "dashCompanyMeta").text() == "v2.0 Pro \u2022 Ping: 11ms"
    assert row.findChild(QLabel, "dashCompanyStatus").text() == "Online"
    assert row.findChild(QLabel, "dashCompanySeen").text() == "2 sn \u00f6nce"


def test_dashboard_reference_header_metrics_and_activity_panel_geometry(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "dashboard", lambda: {})
    monkeypatch.setattr(api_client, "live_status", lambda: [])
    page = DashboardPage()
    page.resize(1440, 1000)
    page.show()
    if page._thread:
        page._thread.wait(3000)
    persistent_qapplication.processEvents()
    page._populate({
        "total_companies": 4,
        "active_companies": 3,
        "recent_logs": [
            {"time": f"2026-10-14 08:0{index}:12", "action": "admin_license_updated", "company": "ASLAN TIC", "status": "Completed", "operator": "Root Admin"}
            for index in range(6)
        ],
    })
    persistent_qapplication.processEvents()
    assert page._top_strip.height() == 56
    assert page._dashboard_root_layout.contentsMargins().top() == 0
    assert page._metric_cards[0].height() == 108
    assert page._metric_cards[4].height() == 106
    assert page._log_panel.maximumHeight() == 568
    assert page._log_table.horizontalHeader().height() == 32
    assert page._log_table.rowHeight(0) >= 49
    assert not page._log_table.alternatingRowColors()
    assert "QTableWidget#dashTable::item { background: #090e1c;" in page.styleSheet()
    assert page._latency_average.text().endswith("ms")
    assert page._latency_average.width() >= 116
    page.close()
