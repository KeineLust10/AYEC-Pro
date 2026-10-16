import sqlite3
import threading
from datetime import datetime
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_accounting_receipt_download_is_authenticated_tenant_scoped_and_listed(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    current_date = datetime.now().strftime("%Y-%m-%d")
    receipt_bytes = b"%PDF-1.4 accounting receipt fixture"
    with sqlite3.connect(tenant_path) as conn:
        accounting_id = conn.execute(
            "INSERT INTO accounting(type,category,amount,description,date) VALUES(?,?,?,?,?)",
            ("Gider", "Supplies", 125, "Receipt fixture", current_date),
        ).lastrowid
        conn.execute(
            "CREATE TABLE accounting_receipts (accounting_id INTEGER PRIMARY KEY, filename TEXT NOT NULL, mime_type TEXT NOT NULL, content BLOB NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO accounting_receipts VALUES(?,?,?,?,?)",
            (accounting_id, "expense-receipt.pdf", "application/pdf", receipt_bytes, current_date),
        )
        conn.commit()

    tenant2_path = tmp_path / "Kullanicilar" / "Second Company.db"
    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active) VALUES(?,?,?,?,1)",
            ("tenant-2", "Second Company", tenant2_path.name, "2026-01-02T00:00:00"),
        )
    tenant2_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(tenant2_path) as conn:
        web_main.ensure_operational_schema(conn)
        web_main.ensure_web_schema(conn)
        conn.execute(
            "INSERT INTO users(username,password,email,phone,role,active) VALUES(?,?,?,?,?,1)",
            ("second-admin", web_main.password_hash("second-operator-pass"), "second@example.com", "", "Admin"),
        )
        second_accounting_id = conn.execute(
            "INSERT INTO accounting(type,category,amount,description,date) VALUES(?,?,?,?,?)",
            ("Gider", "Supplies", 125, "Receipt fixture", current_date),
        ).lastrowid
        conn.execute(
            "CREATE TABLE accounting_receipts (accounting_id INTEGER PRIMARY KEY, filename TEXT NOT NULL, mime_type TEXT NOT NULL, content BLOB NOT NULL, created_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO accounting_receipts VALUES(?,?,?,?,?)",
            (second_accounting_id, "tenant-two-receipt.pdf", "application/pdf", b"%PDF-1.4 tenant two", current_date),
        )
        conn.commit()
    assert second_accounting_id == accounting_id

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        endpoint = f"{base_url}/api/desktop/accounting/{accounting_id}/receipt/download"
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(endpoint).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        download = session.get(endpoint)
        assert download.status_code == 200
        assert download.content == receipt_bytes
        assert download.headers["Content-Type"] == "application/pdf"
        assert "filename*=UTF-8''expense-receipt.pdf" in download.headers["Content-Disposition"]
        assert session.get(f"{base_url}/api/desktop/accounting/{accounting_id + 9000}/receipt/download").status_code == 404

        second_session = requests.Session()
        second_session.headers["Origin"] = base_url
        second_login = second_session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "second-admin", "password": "second-operator-pass", "tenant_id": "tenant-2"},
        )
        assert second_login.status_code == 200
        second_download = second_session.get(f"{base_url}/api/desktop/accounting/{accounting_id}/receipt/download")
        assert second_download.status_code == 200
        assert second_download.content == b"%PDF-1.4 tenant two"
        assert "filename*=UTF-8''tenant-two-receipt.pdf" in second_download.headers["Content-Disposition"]

        ledger = session.post(
            f"{base_url}/api/desktop/accounting/ledger/page",
            json={"period": "year", "search": "Receipt fixture", "page": 0},
        )
        assert ledger.status_code == 200
        matching = [row for row in ledger.json()["rows"] if row["id"] == accounting_id]
        assert len(matching) == 1 and matching[0]["receipt_available"] is True
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
