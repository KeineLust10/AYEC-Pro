import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_loaner_return_updates_transaction_and_inventory_in_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS loaner_devices (id INTEGER PRIMARY KEY, device_type TEXT, brand_model TEXT, status TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS loaner_transactions (id INTEGER PRIMARY KEY, device_id INTEGER, date_returned TEXT, condition_in TEXT, penalty_applied REAL, status TEXT)")
        conn.execute("INSERT INTO loaner_devices(id,device_type,brand_model,serial_mac,status) VALUES(41,'Laptop','Test Device','TEST-SN-41','Musteride')")
        conn.execute("INSERT INTO loaner_transactions(id,device_id,customer_name,status) VALUES(91,41,'Test Customer','Aktif')")
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.post(f"{base_url}/api/desktop/loaners/return", json={"transaction_id": 91}).status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        response = session.post(
            f"{base_url}/api/desktop/loaners/return",
            json={"transaction_id": 91, "condition_in": "Screen checked", "penalty_applied": 275},
        )
        assert response.status_code == 200
        assert response.json()["device_id"] == 41
        with sqlite3.connect(tenant_path) as conn:
            transaction = conn.execute("SELECT date_returned,condition_in,penalty_applied,status FROM loaner_transactions WHERE id=91").fetchone()
            device_status = conn.execute("SELECT status FROM loaner_devices WHERE id=41").fetchone()[0]
        assert transaction[0]
        assert transaction[1:] == ("Screen checked", 275.0, "Tamamland\u0131")
        assert device_status == "Depoda"
        assert session.post(f"{base_url}/api/desktop/loaners/return", json={"transaction_id": 999}).status_code == 404
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_loaner_assignment_saves_desktop_fields_and_claims_available_device_atomically(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS loaner_devices (id INTEGER PRIMARY KEY, device_type TEXT, brand_model TEXT, serial_mac TEXT, status TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS loaner_transactions (id INTEGER PRIMARY KEY, device_id INTEGER, customer_name TEXT, customer_phone TEXT, tracking_no TEXT, condition_out TEXT, expected_return TEXT, status TEXT DEFAULT 'Aktif')")
        conn.execute("INSERT INTO loaner_devices(id,device_type,brand_model,serial_mac,status) VALUES(42,'Laptop','Available Device','TEST-SN-42','Depoda')")
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.post(f"{base_url}/api/desktop/loaners/assign", json={"device_id": 42}).status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        missing_name = session.post(
            f"{base_url}/api/desktop/loaners/assign",
            json={"device_id": 42, "expected_return": "2026-10-17T12:00"},
        )
        assert missing_name.status_code == 400
        invalid_date = session.post(
            f"{base_url}/api/desktop/loaners/assign",
            json={"device_id": 42, "customer_name": "Test Customer", "expected_return": "not-a-date"},
        )
        assert invalid_date.status_code == 400
        response = session.post(
            f"{base_url}/api/desktop/loaners/assign",
            json={"device_id": 42, "customer_name": "Test Customer", "customer_phone": "5550102", "tracking_no": "SRV-42", "condition_out": "Screen intact", "expected_return": "2026-10-17T12:00"},
        )
        assert response.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            transaction = conn.execute("SELECT device_id,customer_name,customer_phone,tracking_no,condition_out,expected_return,status FROM loaner_transactions").fetchone()
            device_status = conn.execute("SELECT status FROM loaner_devices WHERE id=42").fetchone()[0]
        assert transaction == (42, "Test Customer", "5550102", "SRV-42", "Screen intact", "2026-10-17 12:00:00", "Aktif")
        assert device_status == "M\u00fc\u015fteride"
        assert session.post(
            f"{base_url}/api/desktop/loaners/assign",
            json={"device_id": 42, "customer_name": "Second Customer", "expected_return": "2026-10-18T12:00"},
        ).status_code == 409
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
