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
