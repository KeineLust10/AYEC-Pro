import sqlite3
from datetime import datetime, timezone

from Web_Arayuzu import Main as web_main


class _RowConnection(sqlite3.Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.row_factory = sqlite3.Row


class _Cursor:
    def __init__(self, value):
        self.value = value

    def fetchone(self):
        return (self.value,)


class _Registry:
    def __init__(self):
        self.queries = []

    def execute(self, query, params):
        self.queries.append((query, params))
        value = 2 if "last_seen" in query else 8
        return _Cursor(value)

    def close(self):
        pass


def test_dashboard_distinguishes_active_sessions_from_last_24_hour_sessions(monkeypatch):
    registry = _Registry()
    now = datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(web_main, "_admin_tenants_all", lambda: [])
    monkeypatch.setattr(web_main, "registry_connect", lambda: registry)
    monkeypatch.setattr(web_main, "utc_now", lambda: now)
    monkeypatch.setattr(web_main, "scalar", lambda _conn, _query, default=0: default)
    monkeypatch.setattr(web_main, "rows", lambda _conn, _query: [])

    result = web_main.admin_dashboard()

    assert result["online_users"] == 2
    assert result["logins_today"] == 8
    login_query, login_params = registry.queries[1]
    assert "created_at >= ?" in login_query
    assert login_params == ("2026-10-13T12:00:00+00:00",)


def test_live_status_returns_tenant_isolated_recent_session_details(tmp_path, monkeypatch):
    registry_path = tmp_path / "registry.db"
    connection = sqlite3.connect(registry_path)
    connection.row_factory = sqlite3.Row
    connection.executescript(
        "CREATE TABLE sessions (id TEXT, user_id INTEGER, tenant_id TEXT, created_at TEXT, "
        "last_seen TEXT, user_agent TEXT, ip TEXT, expires_at TEXT);"
    )
    connection.executemany(
        "INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)",
        [
            ("s1", 7, "tenant-a", "2026-10-14T11:59:00+00:00", "2026-10-14T11:59:30+00:00", "AYEC Desktop", "192.168.1.108", "2026-10-15T11:59:00+00:00"),
            ("s2", 8, "tenant-b", "2026-10-14T11:20:00+00:00", "2026-10-14T11:20:00+00:00", "Old Client", "10.0.0.8", "2026-10-15T11:20:00+00:00"),
        ],
    )
    connection.commit()
    connection.close()
    monkeypatch.setattr(web_main, "_admin_tenants_all", lambda: [
        {"id": "tenant-a", "company_name": "ASLAN TIC", "sector": "teknik_servis", "db_filename": "aslan.db"},
        {"id": "tenant-b", "company_name": "Babali Servis", "sector": "otomotiv", "db_filename": "babali.db"},
    ])
    monkeypatch.setattr(web_main, "registry_connect", lambda: sqlite3.connect(registry_path, factory=_RowConnection))
    monkeypatch.setattr(web_main, "utc_now", lambda: datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc))

    result = web_main.admin_live_status()

    assert result[0]["online"] is True
    assert result[0]["active_users"] == 1
    assert result[0]["sector"] == "teknik_servis"
    assert result[0]["db_filename"] == "aslan.db"
    assert result[0]["user_id"] == 7
    assert result[0]["ip_address"] == "192.168.1.108"
    assert result[0]["user_agent"] == "AYEC Desktop"
    assert result[1]["online"] is False
    assert result[1]["active_users"] == 0
    assert result[1]["last_seen"] == "2026-10-14T11:20:00+00:00"
