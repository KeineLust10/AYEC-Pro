from datetime import datetime

from Web_Arayuzu import Main as web_main
from src.database import Database


def test_voice_financial_summary_uses_read_only_monthly_desktop_ledger(monkeypatch):
    calls = {"period": None, "query_only": False, "closed": False}

    class FakeConnection:
        def execute(self, statement):
            calls["query_only"] = statement == "PRAGMA query_only=ON"

    class FakeDatabase:
        def __init__(self, *, db_name, init_mode):
            calls["db_name"] = db_name
            calls["init_mode"] = init_mode
            self.conn = FakeConnection()

        def close(self):
            calls["closed"] = True

    class FakeFinanceManager:
        def __init__(self, database):
            calls["database"] = database

        def get_financial_summary(self, period):
            calls["period"] = period
            return {"gross_revenue": 4250.5, "expenses": 1820.25}

    monkeypatch.setattr("src.database.Database", FakeDatabase)
    monkeypatch.setattr("src.utils.finance_manager.FinanceManager", FakeFinanceManager)
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: 71)
    monkeypatch.setattr(web_main, "active_db_path", lambda: "tenant-71.db")

    assert web_main.desktop_voice_financial_summary() == {
        "gross_revenue": 4250.5,
        "expenses": 1820.25,
        "net": 2430.25,
        "period": "month",
    }
    assert calls["period"] == "month"
    assert calls["query_only"]
    assert calls["closed"]
    assert calls["init_mode"] == "connection_only"


def test_voice_financial_summary_reads_monthly_tenant_ledger(tmp_path, monkeypatch):
    database_path = tmp_path / "voice_finance.db"
    database = Database(db_name=str(database_path), init_mode="full")
    today = datetime.now().strftime("%Y-%m-%d")
    database.cursor.executemany(
        "INSERT INTO accounting(type,category,amount,description,date) VALUES(?,?,?,?,?)",
        [
            ("Gelir", "Diger", 480.5, "QA current-month income", today),
            ("Gider", "Diger", 125.25, "QA current-month expense", today),
        ],
    )
    database.conn.commit()
    database.close()
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: 71)
    monkeypatch.setattr(web_main, "active_db_path", lambda: str(database_path))

    assert web_main.desktop_voice_financial_summary() == {
        "gross_revenue": 480.5,
        "expenses": 125.25,
        "net": 355.25,
        "period": "month",
    }


def test_voice_financial_summary_stays_in_selected_tenant_database(tmp_path, monkeypatch):
    today = datetime.now().strftime("%Y-%m-%d")
    tenant_paths = {71: tmp_path / "tenant-71.db", 72: tmp_path / "tenant-72.db"}
    for tenant_id, revenue in ((71, 150.0), (72, 900.0)):
        database = Database(db_name=str(tenant_paths[tenant_id]), init_mode="full")
        database.cursor.execute(
            "INSERT INTO accounting(type,category,amount,description,date) VALUES(?,?,?,?,?)",
            ("Gelir", "Diger", revenue, "Tenant-specific QA income", today),
        )
        database.conn.commit()
        database.close()
    selected_tenant = [71]
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: selected_tenant[0])
    monkeypatch.setattr(web_main, "active_db_path", lambda: str(tenant_paths[selected_tenant[0]]))

    first = web_main.desktop_voice_financial_summary()
    selected_tenant[0] = 72
    second = web_main.desktop_voice_financial_summary()

    assert first["gross_revenue"] == 150.0
    assert second["gross_revenue"] == 900.0
    assert first["gross_revenue"] != second["gross_revenue"]


def test_voice_financial_summary_route_requires_authentication(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/voice/financial-summary"
    handler.headers = {}
    handler.current_user = lambda: None
    sent = []
    handler.send_json = lambda *args, **kwargs: sent.append((args, kwargs))
    monkeypatch.setattr(
        web_main,
        "desktop_voice_financial_summary",
        lambda: (_ for _ in ()).throw(AssertionError("anonymous request reached tenant data")),
    )

    handler.do_GET()

    assert sent[0][0][1] == 401

    authorized = object.__new__(web_main.AYECRequestHandler)
    authorized.path = handler.path
    authorized.headers = {}
    authorized.current_user = lambda: {"id": 7, "role": "User", "_tenant_id": 71}
    authorized_sent = []
    authorized.send_json = lambda *args, **kwargs: authorized_sent.append((args, kwargs))
    monkeypatch.setattr(
        web_main,
        "desktop_voice_financial_summary",
        lambda: {"gross_revenue": 3000.0, "expenses": 1500.0, "net": 1500.0, "period": "month"},
    )

    authorized.do_GET()

    assert authorized_sent[0][0][0]["gross_revenue"] == 3000.0

\n