import sqlite3
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


class _MemoryDatabase:
    instances = []

    def __init__(self, **kwargs):
        self.conn = sqlite3.connect(":memory:")
        self.closed = False
        self.report_rows = []
        self.instances.append(self)

    def close(self):
        try:
            self.report_rows = self.conn.execute(
                "SELECT period_year,total_income,total_expense,cogs,taxable_income,calculated_tax,"
                "income_type,withheld_tax,payable_tax FROM financial_reports"
            ).fetchall()
        except sqlite3.Error:
            pass
        self.closed = True
        self.conn.close()


class _FinanceManager:
    def __init__(self, database):
        self.database = database

    def get_financial_summary(self, period):
        assert period == "year"
        return {"revenue": 1000, "expenses": 100}

    def _get_date_range(self, period):
        assert period == "year"
        return "2026-01-01", "2026-12-31"

    def calculate_cogs(self, start, end):
        assert (start, end) == ("2026-01-01", "2026-12-31")
        return 200


class _TariffService:
    def available_years(self):
        return [2025, 2026]

    def calculate(self, tax_base, year, income_type):
        return {
            "year": year,
            "income_type": income_type,
            "tax_base": tax_base,
            "tax": tax_base * 0.2,
            "brackets": [],
            "source": "test",
        }


def _patch_services(monkeypatch):
    _MemoryDatabase.instances.clear()
    monkeypatch.setattr("src.database.Database", _MemoryDatabase)
    monkeypatch.setattr("src.utils.finance_manager.FinanceManager", _FinanceManager)
    monkeypatch.setattr("src.utils.income_tax_tariff_service.IncomeTaxTariffService", _TariffService)
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-1")
    monkeypatch.setattr(web_main, "active_db_path", lambda: "tenant.db")


def test_tax_analysis_loads_current_tenant_summary_read_only(monkeypatch):
    _patch_services(monkeypatch)
    result = web_main.desktop_finance_tax_analysis({"_tenant_id": "tenant-1"})

    assert result["year"] == 2026
    assert result["income"] == 1000
    assert result["expense"] == 100
    assert result["cogs"] == 200
    assert result["result"]["tax_base"] == 700
    assert result["result"]["tax"] == 140
    assert result["saved"] is False


def test_tax_analysis_calculation_clamps_withheld_tax_and_saves_tenant_report(monkeypatch):
    _patch_services(monkeypatch)
    result = web_main.desktop_finance_tax_analysis(
        {"_tenant_id": "tenant-1"},
        {
            "year": 2025,
            "income_type": "wage",
            "income": 1000,
            "expense": 100,
            "cogs": 200,
            "withheld": 999,
            "save": True,
        },
    )

    assert result["year"] == 2025
    assert result["income_type"] == "wage"
    assert result["result"]["tax_base"] == 700
    assert result["withheld"] == 140
    assert result["result"]["payable"] == 0
    assert result["saved"] is True
    assert result["report_id"] == 1
    assert _MemoryDatabase.instances[-1].report_rows == [
        (2025, 1000.0, 100.0, 200.0, 700.0, 140.0, "wage", 140.0, 0.0)
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"year": 1900},
        {"year": 2026, "income_type": "invalid"},
        {"year": 2026, "income": -1},
        {"year": 2026, "income": "nan"},
    ],
)
def test_tax_analysis_rejects_invalid_inputs_before_opening_database(monkeypatch, payload):
    _patch_services(monkeypatch)

    with pytest.raises(ValueError):
        web_main.desktop_finance_tax_analysis({"_tenant_id": "tenant-1"}, payload)


def test_tax_analysis_rejects_cross_tenant_actor(monkeypatch):
    _patch_services(monkeypatch)

    with pytest.raises(PermissionError):
        web_main.desktop_finance_tax_analysis({"_tenant_id": "tenant-2"})


def test_tax_tariff_scheduler_refreshes_in_background_and_stops(monkeypatch):
    refreshed = threading.Event()

    class _RefreshService:
        def refresh_if_due(self):
            refreshed.set()

    monkeypatch.setattr(
        "src.utils.income_tax_tariff_service.IncomeTaxTariffService", _RefreshService
    )
    scheduler = web_main.IncomeTaxTariffScheduler(interval_seconds=10)
    scheduler.interval_seconds = 0.01
    scheduler.start()

    try:
        assert refreshed.wait(1)
    finally:
        scheduler.stop()

    assert not scheduler._thread.is_alive()


def test_tax_analysis_http_endpoints_require_login_and_save_to_active_tenant(monkeypatch, tmp_path):
    _, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/accounting/tax-analysis"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(endpoint).status_code == 401
        assert anonymous.post(endpoint, json={}).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200
        loaded = session.get(endpoint)
        assert loaded.status_code == 200
        live = loaded.json()
        assert isinstance(live["years"], list) and live["years"]
        assert live["year"] in live["years"]

        payload = {
            "year": live["year"],
            "income_type": "non_wage",
            "income": 1200,
            "expense": 100,
            "cogs": 25,
            "withheld": 10,
            "save": True,
        }
        saved = session.post(endpoint, json=payload)
        assert saved.status_code == 200
        saved_data = saved.json()
        assert saved_data["saved"] is True
        assert saved_data["result"]["tax_base"] == 1075
        with sqlite3.connect(tenant_path) as conn:
            row = conn.execute(
                "SELECT period_year,total_income,total_expense,cogs,taxable_income,"
                "calculated_tax,income_type,withheld_tax,payable_tax "
                "FROM financial_reports WHERE id=?",
                (saved_data["report_id"],),
            ).fetchone()
        assert row == (
            live["year"], 1200, 100, 25, 1075, saved_data["result"]["tax"],
            "non_wage", 10, saved_data["result"]["payable"],
        )
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
