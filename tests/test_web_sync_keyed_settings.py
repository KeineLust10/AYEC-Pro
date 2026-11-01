import json
import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
from src.utils.web_sync_client import WebSyncClient
import Web_Arayuzu.Main as web_main


def test_authenticated_desktop_sync_upserts_tenant_settings_by_key(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        manifest = session.get(f"{base_url}/api/sync/manifest")
        assert manifest.status_code == 200
        sync_epoch = manifest.json()["sync_epoch"]
        first_value = json.dumps({"scenarios": {"Desktop first": {"triggers": ["first"]}}})
        change = {
            "table": "settings",
            "row": {"key": "voice_command_settings", "value": first_value},
            "action": "upsert",
            "source_id": "desktop:qa:settings:key:voice_command_settings:first",
        }
        pushed = session.post(f"{base_url}/api/sync/push", json={"sync_epoch": sync_epoch, "changes": [change]})
        assert pushed.status_code == 200
        assert pushed.json()["applied"] == 1
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute(
                "SELECT value FROM settings WHERE key='voice_command_settings'"
            ).fetchone()[0] == first_value

        second_value = json.dumps({"scenarios": {"Desktop second": {"triggers": ["second"]}}})
        updated = {**change, "row": {"key": "voice_command_settings", "value": second_value}, "source_id": "desktop:qa:settings:key:voice_command_settings:second"}
        update_result = session.post(
            f"{base_url}/api/sync/push",
            json={"sync_epoch": sync_epoch, "changes": [updated]},
        )
        assert update_result.status_code == 200
        assert update_result.json()["applied"] == 1
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute(
                "SELECT value FROM settings WHERE key='voice_command_settings'"
            ).fetchone()[0] == second_value
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_desktop_sync_client_and_web_settings_share_voice_scenarios(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with sqlite3.connect(tenant_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)",
                ("voice_command_settings", '{"scenarios":{"Web initial":{}}}'),
            )

        desktop_db = tmp_path / "desktop.db"
        with sqlite3.connect(desktop_db) as conn:
            conn.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)")
        desktop = WebSyncClient(base_url, verify_tls=False, timeout=5)
        login = desktop.login(web_main.VENDOR_EMAIL, "operator-test-pass", tenant_id="tenant-1")
        desktop.tenant_id = login["user"]["tenant_id"]
        state_path = tmp_path / "desktop-sync-state.json"
        initial = desktop.sync_sqlite(desktop_db, state_path, push_local=False)
        assert initial["ok"] is True
        with sqlite3.connect(desktop_db) as conn:
            assert "Web initial" in conn.execute(
                "SELECT value FROM settings WHERE key='voice_command_settings'"
            ).fetchone()[0]

        desktop_value = '{"scenarios":{"Desktop update":{}}}'
        with sqlite3.connect(desktop_db) as conn:
            conn.execute(
                "UPDATE settings SET value=? WHERE key='voice_command_settings'",
                (desktop_value,),
            )
        pushed = desktop.sync_sqlite(desktop_db, state_path)
        assert pushed["ok"] is True
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute(
                "SELECT value FROM settings WHERE key='voice_command_settings'"
            ).fetchone()[0] == desktop_value

        web = requests.Session()
        web.headers["Origin"] = base_url
        web_login = web.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert web_login.status_code == 200
        web_value = '{"scenarios":{"Web update":{}}}'
        web_update = web.post(
            f"{base_url}/api/desktop/table/settings",
            json={"key": "voice_command_settings", "value": web_value},
        )
        assert web_update.status_code == 200

        pulled = desktop.sync_sqlite(desktop_db, state_path)
        assert pulled["ok"] is True
        with sqlite3.connect(desktop_db) as conn:
            assert conn.execute(
                "SELECT value FROM settings WHERE key='voice_command_settings'"
            ).fetchone()[0] == web_value
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
