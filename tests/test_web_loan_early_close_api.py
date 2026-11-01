import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_early_close_updates_all_installments_and_accounting_atomically(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    loan_id = 9741
    bank_account_id = 1421
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO bank_accounts(id,bank_name,account_holder,current_balance) VALUES(?,?,?,?)",
            (bank_account_id, "QA Bank", "QA Tenant", 10000),
        )
        conn.execute(
            "INSERT INTO loans(id,bank_name,bank_account_id,amount,interest_rate,term_months,start_date,total_payment,description,status) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (loan_id, "QA Bank", bank_account_id, 1200, 4.5, 5, "2026-10-01", 1840, "QA loan", "Aktif"),
        )
        conn.executemany(
            "INSERT INTO loan_installments(loan_id,installment_no,due_date,total_amount,principal_part,interest_part,status) "
            "VALUES(?,?,?,?,?,?,?)",
            [
                (loan_id, 1, "2026-11-01", 620, 600, 20, "Bekliyor"),
                (loan_id, 2, "2026-12-01", 620, 600, 20, "Bekliyor"),
                (loan_id, 3, "2027-01-01", 200, 200, 0, "Paid"),
                (loan_id, 4, "2027-02-01", 200, 200, 0, "dendi"),
                (loan_id, 5, "2027-03-01", 200, 200, 0, "\u00d6dendi"),
            ],
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

        response = session.post(f"{base_url}/api/desktop/loans/{loan_id}/early-close", json={})

        assert response.status_code == 200
        assert len(response.json()["paid_installment_ids"]) == 2
        with sqlite3.connect(tenant_path) as conn:
            statuses = conn.execute(
                "SELECT status, paid_date FROM loan_installments WHERE loan_id=? ORDER BY installment_no",
                (loan_id,),
            ).fetchall()
            installment_ids = [row[0] for row in conn.execute(
                "SELECT id FROM loan_installments WHERE loan_id=? ORDER BY installment_no",
                (loan_id,),
            )]
            loan_status = conn.execute("SELECT status FROM loans WHERE id=?", (loan_id,)).fetchone()[0]
            expense_count = conn.execute(
                "SELECT COUNT(*) FROM accounting WHERE category=? AND description LIKE ?",
                ("Kredi Taksit \u00d6demesi", f"Kredi QA Bank % Taksit \u00d6demesi"),
            ).fetchone()[0]
            balance = conn.execute("SELECT current_balance FROM bank_accounts WHERE id=?", (bank_account_id,)).fetchone()[0]
        assert len(statuses) == 5
        assert all(status == "\u00d6dendi" and paid_date for status, paid_date in statuses[:2])
        assert statuses[2:] == [("Paid", None), ("dendi", None), ("\u00d6dendi", None)]
        assert response.json()["paid_installment_ids"] == installment_ids[:2]
        assert loan_status == "Erken Kapat\u0131ld\u0131"
        assert expense_count == 2
        assert balance == 8760

        rollback_loan_id = loan_id + 1
        with sqlite3.connect(tenant_path) as conn:
            conn.execute(
                "INSERT INTO loans(id,bank_name,bank_account_id,amount,interest_rate,term_months,start_date,total_payment,description,status) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (rollback_loan_id, "QA Rollback Bank", bank_account_id, 1200, 4.5, 2, "2026-10-01", 1240, "QA loan", "Aktif"),
            )
            conn.executemany(
                "INSERT INTO loan_installments(loan_id,installment_no,due_date,total_amount,principal_part,interest_part,status) VALUES(?,?,?,?,?,?,?)",
                [
                    (rollback_loan_id, 1, "2026-11-01", 620, 600, 20, "Bekliyor"),
                    (rollback_loan_id, 2, "2026-12-01", 620, 600, 20, "Bekliyor"),
                ],
            )
        from src.database import Database

        add_transaction = Database.add_transaction
        calls = 0

        def fail_second_transaction(database, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("simulated accounting failure")
            return add_transaction(database, *args, **kwargs)

        monkeypatch.setattr(Database, "add_transaction", fail_second_transaction)
        failed = session.post(f"{base_url}/api/desktop/loans/{rollback_loan_id}/early-close", json={})
        assert failed.status_code == 400
        with sqlite3.connect(tenant_path) as conn:
            statuses = conn.execute(
                "SELECT status FROM loan_installments WHERE loan_id=? ORDER BY installment_no",
                (rollback_loan_id,),
            ).fetchall()
            loan_status = conn.execute("SELECT status FROM loans WHERE id=?", (rollback_loan_id,)).fetchone()[0]
            rollback_expenses = conn.execute(
                "SELECT COUNT(*) FROM accounting WHERE description LIKE ?",
                ("Kredi QA Rollback Bank %",),
            ).fetchone()[0]
            balance_after_rollback = conn.execute("SELECT current_balance FROM bank_accounts WHERE id=?", (bank_account_id,)).fetchone()[0]
        assert statuses == [("Bekliyor",), ("Bekliyor",)]
        assert loan_status == "Aktif"
        assert rollback_expenses == 0
        assert balance_after_rollback == 8760
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
