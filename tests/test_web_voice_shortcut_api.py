import json
import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_voice_shortcuts_round_trip_through_authenticated_tenant_settings(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    session = requests.Session()
    session.headers["Origin"] = base_url
    try:
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200

        with sqlite3.connect(tenant_path) as connection:
            connection.execute(
                "INSERT OR REPLACE INTO scheduled_alerts (alert_type,trigger_time,is_enabled,is_critical) VALUES (?,?,?,?)",
                ("service_delivery", "17:30", 0, 0),
            )
            connection.execute(
                "INSERT OR REPLACE INTO scheduled_alerts (alert_type,trigger_time,is_enabled,is_critical) VALUES (?,?,?,?)",
                ("loan_reminder", "11:00", 1, 0),
            )

        configuration = {
            "custom_stock": {
                "triggers": ["stock now", "low stock"],
                "action": {"type": "builtin", "name": "list_critical_stock"},
            }
        }
        save = session.post(
            f"{base_url}/api/desktop/table/settings",
            json={"key": "voice_assistant_shortcuts", "value": json.dumps(configuration)},
        )
        assert save.status_code == 200, save.text

        bootstrap = session.get(f"{base_url}/api/desktop/bootstrap")
        assert bootstrap.status_code == 200, bootstrap.text
        reloaded = json.loads(bootstrap.json()["settings"]["voice_assistant_shortcuts"])
        assert reloaded == configuration
        alert_rows = bootstrap.json()["scheduled_alerts"]
        assert {row["alert_type"] for row in alert_rows} >= {"loan_reminder", "service_delivery"}
        service_alert = next(row for row in alert_rows if row["alert_type"] == "service_delivery")
        assert service_alert["trigger_time"] == "17:30"
        assert service_alert["is_enabled"] == 0
        triggered_at = "2026-10-17T17:30:00"
        mark_triggered = session.post(
            f"{base_url}/api/desktop/table/scheduled_alerts",
            json={"id": service_alert["id"], "last_triggered": triggered_at, "_action": "update"},
        )
        assert mark_triggered.status_code == 200, mark_triggered.text
        invalid_time = session.post(
            f"{base_url}/api/desktop/table/scheduled_alerts",
            json={"id": service_alert["id"], "trigger_time": "25:99", "_action": "update"},
        )
        assert invalid_time.status_code == 400, invalid_time.text
        refreshed_alerts = session.get(f"{base_url}/api/desktop/bootstrap").json()["scheduled_alerts"]
        service_alert = next(row for row in refreshed_alerts if row["alert_type"] == "service_delivery")
        assert service_alert["last_triggered"] == triggered_at
        assert service_alert["trigger_time"] == "17:30"

        with sqlite3.connect(tenant_path) as connection:
            stored = connection.execute(
                "SELECT value FROM settings WHERE key='voice_assistant_shortcuts'"
            ).fetchone()
        assert stored is not None
        assert json.loads(stored[0]) == configuration
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
