import sqlite3
import threading
from contextlib import closing
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_dashboard_service_delete_archives_device_and_records_desktop_audit_events(monkeypatch, tmp_path):
    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    tracking_no = "QA-SRV-DELETE-AUDIT"
    with closing(sqlite3.connect(tenant_path)) as conn:
        columns = {row[1] for row in conn.execute('PRAGMA table_info("devices")')}
        assert "is_archived" in columns
        device_id = conn.execute(
            "INSERT INTO devices(tracking_no,customer_name,status,is_archived) VALUES(?,?,?,0)",
            (tracking_no, "QA Customer", "Bekliyor"),
        ).lastrowid
        conn.commit()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
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
        assert login.status_code == 200, login.text

        response = session.post(
            f"{base_url}/api/desktop/table/devices",
            json={"id": device_id, "_action": "delete"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["action"] == "delete"

        with closing(sqlite3.connect(tenant_path)) as conn:
            device_columns = {row[1] for row in conn.execute('PRAGMA table_info("devices")')}
            selected_columns = ["tracking_no", "is_archived"]
            if "is_deleted" in device_columns:
                selected_columns.append("is_deleted")
            device = conn.execute(
                f'SELECT {",".join(selected_columns)} FROM devices WHERE id=?', (device_id,)
            ).fetchone()
            audit_events = conn.execute(
                "SELECT user_id,table_name,action,details FROM audit_logs "
                "WHERE table_name='devices' ORDER BY id"
            ).fetchall()

        assert device is not None
        assert device[0] == tracking_no
        if "is_deleted" in device_columns:
            assert device[1] == 0
            assert device[2] == 1
        else:
            assert device[1] == 1
        assert audit_events == [
            (
                "Sistem",
                "devices",
                "UPDATE",
                f"Device archived (soft delete): {tracking_no}",
            ),
            (
                str(actor["id"]),
                "devices",
                "DELETE",
                f"Tracking number: {tracking_no} device record deleted.",
            ),
        ]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
