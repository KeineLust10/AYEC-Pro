import json
import sqlite3
import threading
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer

import pytest
import requests

from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def test_report_template_usage_is_tenant_persisted_and_resets_daily(monkeypatch, tmp_path):
    today = datetime.now().date().isoformat()
    tenant_a = tmp_path / "tenant-a.db"
    tenant_b = tmp_path / "tenant-b.db"
    active_database = [tenant_a]
    for database_path in (tenant_a, tenant_b):
        with sqlite3.connect(database_path) as connection:
            connection.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    with sqlite3.connect(tenant_a) as connection:
        connection.execute(
            "INSERT INTO settings(key,value) VALUES(?,?)",
            ("report_template_usage_metrics", json.dumps({"date": today, "count": 2, "average_seconds": 1.5})),
        )
    monkeypatch.setattr(web_main, "db_connect", lambda: sqlite3.connect(active_database[0]))

    updated = web_main.desktop_record_report_template_usage(3.0)

    assert updated["date"] == today
    assert updated["count"] == 3
    assert updated["average_seconds"] == 2.0
    with sqlite3.connect(tenant_a) as connection:
        persisted = json.loads(
            connection.execute(
                "SELECT value FROM settings WHERE key=?", ("report_template_usage_metrics",)
            ).fetchone()[0]
        )
    assert persisted == updated

    active_database[0] = tenant_b
    tenant_b_metrics = web_main.desktop_record_report_template_usage(0.01)
    assert tenant_b_metrics["date"] == today
    assert tenant_b_metrics["count"] == 1
    assert tenant_b_metrics["average_seconds"] == 0.1
    with sqlite3.connect(tenant_b) as connection:
        tenant_b_saved = json.loads(
            connection.execute(
                "SELECT value FROM settings WHERE key=?", ("report_template_usage_metrics",)
            ).fetchone()[0]
        )
    assert tenant_b_saved == tenant_b_metrics

    yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
    active_database[0] = tenant_a
    with sqlite3.connect(tenant_a) as connection:
        connection.execute(
            "UPDATE settings SET value=? WHERE key=?",
            (json.dumps({"date": yesterday, "count": 50, "average_seconds": 12.0}), "report_template_usage_metrics"),
        )

    reset = web_main.desktop_record_report_template_usage(0.01)

    assert reset["date"] == today
    assert reset["count"] == 1
    assert reset["average_seconds"] == 0.1


@pytest.mark.parametrize("elapsed", [None, "invalid", float("nan"), float("inf")])
def test_report_template_usage_rejects_invalid_elapsed_time(elapsed):
    with pytest.raises(ValueError):
        web_main.desktop_record_report_template_usage(elapsed)


def test_report_template_usage_endpoint_authenticates_and_checks_origin(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as connection:
        connection.execute(
            "UPDATE users SET role=? WHERE email=?", ("Teknisyen", web_main.VENDOR_EMAIL)
        )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = base_url + "/api/desktop/report-template-usage"
    try:
        assert requests.post(endpoint, json={"elapsed_seconds": 1.0}).status_code == 401
        session = requests.Session()
        login = session.post(
            base_url + "/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        assert login.json()["user"]["role"] == "Teknisyen"
        session.headers["Origin"] = base_url
        first = session.post(endpoint, json={"elapsed_seconds": 0.01})
        assert first.status_code == 200, first.text
        assert first.json()["count"] == 1
        assert first.json()["average_seconds"] == 0.1
        second = session.post(endpoint, json={"elapsed_seconds": 2.1})
        assert second.status_code == 200, second.text
        assert second.json()["count"] == 2
        assert second.json()["average_seconds"] == 1.1
        rejected = session.post(
            endpoint,
            json={"elapsed_seconds": 2.0},
            headers={"Origin": "http://example.com"},
        )
        assert rejected.status_code == 403
        with sqlite3.connect(tenant_path) as connection:
            persisted = json.loads(
                connection.execute(
                    "SELECT value FROM settings WHERE key=?", ("report_template_usage_metrics",)
                ).fetchone()[0]
            )
        assert persisted == second.json()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
