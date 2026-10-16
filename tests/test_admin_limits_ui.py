import sys
from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.limits import LimitsPage


def test_limits_summary_detects_any_exhausted_quota_and_filters(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(LimitsPage, "_load", lambda self: None)
    page = LimitsPage()
    page._populate(
        [
            {
                "company_name": "ASLAN TIC",
                "db_size_mb": 12,
                "users_count": 2,
                "users_limit": 10,
                "devices_count": 3,
                "devices_limit": 100,
                "services_count": 10,
                "services_limit": 1000,
            },
            {
                "company_name": "Babali Servis",
                "db_size_mb": 20,
                "users_count": 10,
                "users_limit": 10,
                "devices_count": 2,
                "devices_limit": 100,
                "services_count": 20,
                "services_limit": 1000,
            },
        ]
    )

    assert page._metric_tenants.text() == "2"
    assert page._metric_critical.text() == "1"
    assert page._metric_db.text() == "32.00 MB / 100 GB"
    assert page._table.item(1, 5).data(Qt.ItemDataRole.UserRole + 1) == "Limit A\u015f\u0131m\u0131/Kritik"
    assert page._metric_devices.text() == "5 / 400 Cihaz"
    assert page._metric_services.text() == "30 / 4,000 Fis"
    assert len(page._policy_controls) == 3
    toggle = page._policy_controls[0]
    assert toggle.accessibleName() == "Veritabani %90 doldugunda firmaya bildirim gonder"
    assert toggle.size().width() == 42
    toggle.click()
    assert not toggle.isChecked()
    toggle.click()
    assert toggle.isChecked()
    assert page._upgrade_total.text() == "$ 750 / Ay"
    page._upgrade_options[0].setChecked(False)
    assert page._upgrade_total.text() == "$ 300 / Ay"
    page._upgrade_options[0].setChecked(True)
    page._search.setText("aslan")
    assert not page._table.isRowHidden(0)
    assert page._table.isRowHidden(1)


def test_limits_do_not_invent_database_cap_and_switch_to_full_width_mobile_cards(persistent_qapplication, monkeypatch):
    loads = []
    monkeypatch.setattr(LimitsPage, "_load", lambda self: loads.append(True))
    page = LimitsPage()
    loads.clear()
    page._populate(
        [
            {
                "tenant_id": "tenant-a",
                "company_name": "ASLAN TIC",
                "db_size_mb": 640,
                "users_count": 1,
                "users_limit": 10,
                "devices_count": 1,
                "devices_limit": 100,
                "services_count": 1,
                "services_limit": 1000,
            }
        ]
    )
    assert page._metric_critical.text() == "0"
    assert page._table.item(0, 0).data(Qt.ItemDataRole.UserRole)["tenant_id"] == "tenant-a"
    row_action = page._table.cellWidget(0, 6).findChild(QPushButton, "limitsRowAction")
    assert row_action is not None
    row_action.click()
    assert page._upgrade_tenant.currentData() == "tenant-a"
    page._refresh_button.click()
    assert loads == [True]
    assert all(not button.isEnabled() for panel in (page._policy_panel, page._upgrade_panel) for button in panel.findChildren(QPushButton))
    page.resize(390, 844)
    page.show()
    persistent_qapplication.processEvents()
    assert page._data_stack.currentWidget() is page._mobile_list
    assert page._scroll.horizontalScrollBar().maximum() == 0
    assert page._mobile_layout.itemAt(0).widget().isVisible()
