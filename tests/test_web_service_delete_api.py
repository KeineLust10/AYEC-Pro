import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_device_delete_requires_authentication_and_stays_in_the_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO users(username,password,email,phone,role,active) VALUES(?,?,?,?,?,1)",
            ("tenant-manager", web_main.password_hash("manager-test-pass"), "manager@example.com", "", "Manager"),
        )
        device_ids = {}
        for tracking_no in ("QA-DELETE-MANAGER", "QA-DELETE-ADMIN", "QA-DELETE-ANONYMOUS"):
            cursor = conn.execute(
                "INSERT INTO devices(tracking_no,status,is_deleted) VALUES(?,?,0)",
                (tracking_no, "Bekliyor"),
            )
            device_ids[tracking_no] = cursor.lastrowid

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    table_url = f"{base_url}/api/desktop/table/devices"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        anonymous_response = anonymous.post(
            table_url, json={"id": device_ids["QA-DELETE-ANONYMOUS"], "_action": "delete"}
        )
        assert anonymous_response.status_code == 401

        manager = requests.Session()
        manager.headers["Origin"] = base_url
        login = manager.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "tenant-manager", "password": "manager-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200, login.text
        manager_delete = manager.post(
            table_url, json={"id": device_ids["QA-DELETE-MANAGER"], "_action": "delete"}
        )
        assert manager_delete.status_code == 200, manager_delete.text

        admin = requests.Session()
        admin.headers["Origin"] = base_url
        login = admin.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200, login.text
        admin_delete = admin.post(
            table_url, json={"id": device_ids["QA-DELETE-ADMIN"], "_action": "delete"}
        )
        assert admin_delete.status_code == 200, admin_delete.text
        with sqlite3.connect(tenant_path) as conn:
            for tracking_no in ("QA-DELETE-MANAGER", "QA-DELETE-ADMIN"):
                deleted, archived = conn.execute(
                    "SELECT is_deleted,is_archived FROM devices WHERE id=?", (device_ids[tracking_no],)
                ).fetchone()
                assert deleted == 1
                assert archived == 0
            assert conn.execute(
                "SELECT is_deleted FROM devices WHERE id=?",
                (device_ids["QA-DELETE-ANONYMOUS"],),
            ).fetchone()[0] == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
