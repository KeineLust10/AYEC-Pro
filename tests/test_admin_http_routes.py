import json
import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

import Web_Arayuzu.Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def test_admin_http_routes_cover_login_customer360_backup_restore_and_update(
    monkeypatch, tmp_path
):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    source = tmp_path / "http-route-backup.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE sample(value INTEGER)")
        conn.execute("INSERT INTO sample(value) VALUES(11)")
    stored = web_main.support_store_backup(actor, source.read_bytes(), "Firma.db")

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        forbidden = session.get(f"{base_url}/api/admin/customer-360/tenant-1")
        assert forbidden.status_code == 403

        login = session.post(
            f"{base_url}/api/admin/login",
            json={
                "email": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
            },
        )
        assert login.status_code == 200
        assert login.json()["ok"] is True

        customer_360 = session.get(
            f"{base_url}/api/admin/customer-360/tenant-1"
        )
        assert customer_360.status_code == 200
        assert customer_360.json()["company"]["id"] == "tenant-1"

        backup_list = session.get(f"{base_url}/api/admin/backups/tenant-1")
        assert backup_list.status_code == 200
        item = next(
            item
            for item in backup_list.json()["backups"]
            if item.get("backup_id") == stored["backup_id"]
        )

        restore = session.post(
            f"{base_url}/api/admin/backups/tenant-1/restore",
            json={"backup_index": item["index"], "backup_id": item["backup_id"]},
        )
        assert restore.status_code == 200
        assert restore.json()["ok"] is True

        deploy = session.post(
            f"{base_url}/api/admin/updates/deploy",
            json={
                "version": "2.0.6",
                "targets": ["tenant-1"],
                "changelog": "HTTP route smoke test",
                "channel": "pilot",
            },
        )
        assert deploy.status_code == 200
        assert deploy.json()["targets"] == ["tenant-1"]

        with web_main.registry_connect() as registry:
            commands = registry.execute(
                "SELECT command_type,status,payload_json FROM desktop_commands "
                "WHERE tenant_id=? ORDER BY id DESC LIMIT 2",
                ("tenant-1",),
            ).fetchall()
        assert {row[0] for row in commands} == {"restore_backup", "deploy_update"}
        assert all(row[1] == "pending" for row in commands)
        assert any(json.loads(row[2]).get("version") == "2.0.6" for row in commands)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
