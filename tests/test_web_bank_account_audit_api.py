import sqlite3
import threading
from contextlib import closing
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_bank_account_delete_records_authenticated_audit_event(monkeypatch, tmp_path):
    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with closing(sqlite3.connect(tenant_path)) as conn:
        account_id = conn.execute(
            "INSERT INTO bank_accounts(bank_name,account_holder,iban,account_number,branch_code,currency,is_active,created_at,current_balance,is_deleted) "
            "VALUES(?,?,?,?,?,?,?,?,?,0)",
            ("QA Bank", "QA Holder", "TR000", "000", "001", "TRY", 1, "2026-01-01", 0),
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

        updated = session.post(
            f"{base_url}/api/desktop/table/bank_accounts",
            json={"id": account_id, "bank_name": "QA Updated Bank", "_action": "update"},
        )
        assert updated.status_code == 200, updated.text

        inserted = session.post(
            f"{base_url}/api/desktop/table/bank_accounts",
            json={"bank_name": "QA Added Bank", "currency": "USD", "_action": "insert"},
        )
        assert inserted.status_code == 200, inserted.text

        response = session.post(
            f"{base_url}/api/desktop/table/bank_accounts",
            json={"id": account_id, "_action": "delete"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["action"] == "delete"

        with closing(sqlite3.connect(tenant_path)) as conn:
            account = conn.execute(
                "SELECT is_deleted FROM bank_accounts WHERE id=?", (account_id,)
            ).fetchone()
            audits = conn.execute(
                "SELECT user_id,table_name,action,details FROM audit_logs "
                "WHERE table_name='bank_accounts' ORDER BY id"
            ).fetchall()

        assert account == (1,)
        assert audits == [
            (str(actor["id"]), "bank_accounts", "UPDATE", f"Account ID {account_id} updated: QA Updated Bank"),
            (str(actor["id"]), "bank_accounts", "INSERT", "New account: QA Added Bank"),
            (str(actor["id"]), "bank_accounts", "DELETE", f"Account ID {account_id} deleted"),
        ]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
