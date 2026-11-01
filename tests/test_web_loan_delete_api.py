import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_web_loan_delete_matches_desktop_soft_delete_and_preserves_installments(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    loan_id = 9731
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO loans(id,bank_name,amount,interest_rate,term_months,start_date,total_payment,description,status) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (loan_id, "QA Bank", 1200, 4.5, 2, "2026-10-01", 1240, "QA loan", "Aktif"),
        )
        conn.execute(
            "INSERT INTO loan_installments(loan_id,installment_no,due_date,total_amount,principal_part,interest_part) "
            "VALUES(?,?,?,?,?,?)",
            (loan_id, 1, "2026-11-01", 620, 600, 20),
        )

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

        response = session.post(
            f"{base_url}/api/desktop/table/loans",
            json={"id": loan_id, "_action": "delete"},
        )

        assert response.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(loans)")}
            assert {"is_deleted", "deleted_at"}.issubset(columns)
            loan = conn.execute("SELECT is_deleted,deleted_at FROM loans WHERE id=?", (loan_id,)).fetchone()
            installment_count = conn.execute("SELECT COUNT(*) FROM loan_installments WHERE loan_id=?", (loan_id,)).fetchone()[0]
        assert loan and loan[0] == 1 and loan[1]
        assert installment_count == 1
        listed = session.get(f"{base_url}/api/desktop/table/loans?limit=1000")
        assert listed.status_code == 200
        assert loan_id not in {row["id"] for row in listed.json()["rows"]}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
