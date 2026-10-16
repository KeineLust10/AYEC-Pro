import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Admin_Konsol"))

from PyQt6.QtWidgets import QApplication

from pages import companies as companies_module


def test_company_filters_metrics_and_license_copy(monkeypatch):
    app = QApplication.instance() or QApplication([])
    rows = [
        {"id": "active-1", "company_name": "Active One", "active": 1},
        {"id": "inactive-1", "company_name": "Inactive One", "active": 0},
    ]
    monkeypatch.setattr(companies_module.api_client, "companies", lambda *args: rows)
    monkeypatch.setattr(companies_module.api_client, "company_users", lambda _tenant: [])
    monkeypatch.setattr(
        companies_module.api_client,
        "customer_360",
        lambda tenant: {
            "summary": {"user_count": 2, "backup_count": 1, "error_count": 0, "online": True},
            "backups": [{"filename": "daily.db"}],
            "live_status": {"ping_ms": 12},
            "licenses": [{"license_code": "LICENSE-001"}],
        },
    )

    page = companies_module.CompaniesPage()
    assert page._thread.wait(3000)
    app.processEvents()
    assert len(page._company_group.buttons()) == 2

    page._set_company_filter("inactive")
    app.processEvents()
    assert [button.isHidden() for button in page._company_group.buttons()] == [True, False]

    page._select_company(rows[0])
    assert page._thread.wait(3000)
    for worker in tuple(page._overview_workers):
        assert worker.wait(3000)
    app.processEvents()

    assert page._metric_values["user_count"][0].text() == "2"
    assert page._metric_values["backup_count"][1].text() == "daily.db"
    assert page._license_key_value.text() == "LICENSE-001"
    assert page._copy_license_button.isEnabled()
    page._copy_license_button.click()
    assert QApplication.clipboard().text() == "LICENSE-001"

    page.close()
    app.processEvents()
