import sys
from pathlib import Path
from PyQt6.QtWidgets import QLabel

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.server_settings import ServerSettingsPage, _ServerMetricIcon


def test_server_status_binds_resource_and_identity_values(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(ServerSettingsPage, "_refresh_status", lambda self: None)
    page = ServerSettingsPage()
    assert [icon._kind for icon in page.findChildren(_ServerMetricIcon)] == ["cpu", "ram", "disk", "database", "network"]
    page._populate(
        {
            "cpu_percent": 23,
            "ram_percent": 51,
            "disk_percent": 30,
            "disk_usage": "30%",
            "version": "2.4.0",
            "uptime": "4 days",
            "db_path": "C:/data/admin.db",
            "tenant_count": 12,
        }
    )

    assert page._cpu_bar.value() == 23
    assert page._ram_bar.value() == 51
    assert page._disk_bar.value() == 30
    assert page._database_lbl.text() == "Veri yok"
    assert page._network_lbl.text() == "Veri yok"
    assert len(page._metric_cards) == 5
    page.resize(1440, 1000)
    page._apply_responsive_layout()
    assert page._page_layout.contentsMargins().left() == 44
    assert page._page_layout.contentsMargins().right() == 0
    assert page._page_layout.contentsMargins().top() == 20
    assert all(card.minimumHeight() >= 186 for card in page._metric_cards)
    page.resize(390, 844)
    page._apply_responsive_layout()
    assert page._page_layout.contentsMargins().left() == 20
    assert page._page_layout.contentsMargins().right() == 20
    assert all(card.minimumHeight() == 136 for card in page._metric_cards)
    assert not page._database_bar.isVisible()
    assert not page._network_bar.isVisible()
    assert page._topology_layout.count() == 2
    assert page._topology_layout.stretch(0) == 2
    assert page._topology_layout.stretch(1) == 1
    assert page._main_row.stretch(0) == page._main_row.stretch(1) == 1
    assert page._srv_version.text() == "2.4.0"
    assert page._srv_uptime.text() == "4 days"
    assert page._srv_db.text() == "C:/data/admin.db"
    assert page._srv_tenants.text() == "12"


def test_server_settings_formats_database_and_network_values_without_false_percentages(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(ServerSettingsPage, "_refresh_status", lambda self: None)
    page = ServerSettingsPage()
    page._populate({"database_size_bytes": 1572864, "network_mbps": 12.5})
    assert page._database_lbl.text() == "1.50 MB"
    assert page._network_lbl.text() == "1.56 MB/s"
    assert not page._database_bar.isVisible()
    assert not page._network_bar.isVisible()


def test_server_settings_signals_validate_and_persist_supported_connection_values(persistent_qapplication, monkeypatch):
    refresh_calls = []
    writes = []
    monkeypatch.setattr(ServerSettingsPage, "_refresh_status", lambda self: refresh_calls.append(True))
    monkeypatch.setattr("pages.server_settings.config.set", lambda key, value: writes.append((key, value)))
    page = ServerSettingsPage()
    assert page._topology_layout.count() == 2
    page._timer.stop()
    refresh_calls.clear()

    page._refresh_button.click()
    assert refresh_calls == [True]

    page._srv_url.setText("https://example.com/api/admin/login")
    page._timeout_input.setText("25")
    page._save_button.click()
    assert writes == [("server_url", "https://example.com"), ("timeout", 25)]
    assert page._status_lbl.text() == "Ba\u011flant\u0131 ayarlar\u0131 kaydedildi."

    writes.clear()
    page._timeout_input.setText("301")
    page._save_button.click()
    assert writes == []
    assert "1 ile 300" in page._status_lbl.text()
    assert not any(button.isEnabled() for button in page._maintenance_buttons)

    page._show_error("offline")
    assert page._api_state.text() == "API DURUMU: HATA"
    assert "offline" in page._status_lbl.text()


def test_server_settings_topology_uses_explicit_unavailable_states_and_mobile_reflows(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(ServerSettingsPage, "_refresh_status", lambda self: None)
    page = ServerSettingsPage()
    topology_labels = [label.text() for label in page._infrastructure_panel.findChildren(QLabel)]
    assert "ANA D\u00dc\u011e\u00dcM" in topology_labels
    assert "API VER\u0130S\u0130 YOK" in topology_labels
    assert all("API verisi yok" in label.text() for label in page._replication_panel.findChildren(QLabel) if label.objectName() == "topologyState")
    page.resize(390, 844)
    page._apply_responsive_layout()
    assert page._metric_columns == 1
    assert page._topology_layout.direction().name == "TopToBottom"
