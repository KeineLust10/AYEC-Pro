import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from pages.customer_360 import Customer360Page
from PyQt6.QtWidgets import QBoxLayout


def test_customer_360_binds_isolated_tenant_signals(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(Customer360Page, "_load_companies", lambda self: None)
    page = Customer360Page()
    page._show_customer(
        {
            "company": {"id": "tenant-1", "company_name": "ASLAN TIC", "license_end": "2027-10-14"},
            "summary": {"user_count": 3, "backup_count": 2, "error_count": 1, "audit_count": 8, "online": True},
            "licenses": [{"license_type": "Pro", "status": "active"}],
            "backups": [{"filename": "latest.db"}],
            "live_status": {"hardware_id": "WS-01"},
            "error_logs": [{"message": "Timeout"}],
            "audit_logs": [{"action": "admin_license_updated"}],
            "users": [{"id": 7, "full_name": "Engin ASLAN", "username": "engin", "role": "tenant_admin", "active": 1}],
        }
    )

    assert "8" in page._audit_total.text()
    assert page._company_label.text() == "ASLAN TIC"
    assert page._detail_fields["license"].text() == "Pro / 2027-10-14"
    assert page._company_status.text() == "AKTIF"
    values = [page._table.item(row, 1).text() for row in range(page._table.rowCount())]
    assert "latest.db" in values
    assert "WS-01" in values
    assert "admin_license_updated" in values
    assert page._users_table.rowCount() == 1
    assert page._users_table.item(0, 2).text() == "engin"
    page._password_assign.click()
    assert "kimlik servisi" in page._status.text()


def test_customer_360_company_filters_and_search(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(Customer360Page, "_load_companies", lambda self: None)
    page = Customer360Page()
    page._companies = [
        {"id": "a", "company_name": "Alpha", "active": True, "email": "ops@alpha.test"},
        {"id": "b", "company_name": "Beta", "active": False, "email": "admin@beta.test"},
    ]
    page._company_combo.addItem("Alpha", "a")
    page._company_combo.addItem("Beta", "b")
    page._company_list.addItem("Alpha")
    page._company_list.item(0).setData(256, "a")
    page._company_list.item(0).setData(257, page._companies[0])
    page._company_list.addItem("Beta")
    page._company_list.item(1).setData(256, "b")
    page._company_list.item(1).setData(257, page._companies[1])

    page._set_company_filter("inactive")
    assert page._company_list.item(0).isHidden()
    assert not page._company_list.item(1).isHidden()
    page._company_search.setText("alpha")
    assert page._company_list.item(0).isHidden()
    assert page._company_list.item(1).isHidden()


def test_customer_360_company_actions_route_to_company_management(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(Customer360Page, "_load_companies", lambda self: None)
    page = Customer360Page()
    requested = []
    page.navigate_requested.connect(requested.append)

    page._new_company.click()
    page._add_user.click()

    assert requested == ["companies", "companies"]


def test_customer_360_sector_update_refreshes_selected_company(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(Customer360Page, "_load_companies", lambda self: None)
    page = Customer360Page()
    refreshed = []
    page._companies = [{"id": "tenant-1", "company_name": "ASLAN TIC", "sector": "automotive"}]
    page._payload = {"company": {"id": "tenant-1", "company_name": "ASLAN TIC"}}
    monkeypatch.setattr(page, "_load_customer", refreshed.append)

    page._sector_updated("tenant-1", {})

    assert page._companies[0]["sector"] == page._sector_combo.currentData()
    assert refreshed == ["tenant-1"]
    assert "g\u00fcncellendi" in page._status.text()


def test_customer_360_reflows_and_scrolls_on_mobile(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(Customer360Page, "_load_companies", lambda self: None)
    page = Customer360Page()
    page.resize(390, 844)
    page.show()
    persistent_qapplication.processEvents()

    assert page._workspace_layout.direction() == QBoxLayout.Direction.TopToBottom
    assert page._page_scroll.horizontalScrollBar().maximum() == 0
    assert page._page_scroll.verticalScrollBar().maximum() > 0


def test_customer_360_desktop_detail_stack_matches_reference_spacing(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(Customer360Page, "_load_companies", lambda self: None)
    page = Customer360Page()
    page.resize(1440, 1000)
    page.show()
    persistent_qapplication.processEvents()

    assert page._detail_layout.spacing() == 12
    assert page._users_table.height() == 150
