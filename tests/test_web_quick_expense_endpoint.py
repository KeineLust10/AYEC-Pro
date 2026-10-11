import base64
import sqlite3

import src.database as database_module
from Web_Arayuzu import Main as web_main


class FakeExpenseDatabase:
    instance = None

    def __init__(self, db_name, init_mode):
        assert init_mode == "connection_only"
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            "CREATE TABLE bank_accounts (id INTEGER PRIMARY KEY, is_active INTEGER, current_balance REAL)"
        )
        self.cursor.execute(
            "INSERT INTO bank_accounts VALUES (4, 1, 1000)"
        )
        self.cursor.execute(
            "CREATE TABLE accounting (id INTEGER PRIMARY KEY, category TEXT, amount REAL)"
        )
        self.conn.commit()
        self.notification = None
        FakeExpenseDatabase.instance = self

    def add_transaction(self, **values):
        assert values["commit"] is False
        self.cursor.execute(
            "INSERT INTO accounting (category, amount) VALUES (?, ?)",
            (values["category"], values["amount"]),
        )
        self.cursor.execute(
            "UPDATE bank_accounts SET current_balance=current_balance-? WHERE id=?",
            (values["amount"], values["bank_account_id"]),
        )
        return self.cursor.lastrowid

    def notify_jarvis(self, message, category, is_income):
        self.notification = (message, category, is_income)

    def close(self):
        pass


def test_quick_expense_endpoint_saves_bank_and_receipt_without_server(monkeypatch, tmp_path):
    monkeypatch.setattr(database_module, "Database", FakeExpenseDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    monkeypatch.setattr(web_main, "clear_tenant_context", lambda: None)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/accounting/quick-expense"
    handler.headers = {"Content-Length": "512"}
    handler.current_user = lambda: {"id": 1, "role": "admin"}
    handler.same_origin = lambda: True
    handler.read_json = lambda: {
        "amount": 25, "category": "Supplies", "bank_account_id": 4,
        "ref_no": "EXP-1", "receipt_name": "expense.pdf",
        "receipt_base64": base64.b64encode(b"%PDF-1.4\n").decode("ascii"),
    }
    sent = []
    handler.send_json = lambda payload, status=200: sent.append((status, payload))
    handler.do_POST()
    assert sent[-1][0] == 200
    assert sent[-1][1]["ok"] is True
    db = FakeExpenseDatabase.instance
    assert db.cursor.execute(
        "SELECT current_balance FROM bank_accounts WHERE id=4"
    ).fetchone()[0] == 975
    assert db.cursor.execute(
        "SELECT filename, content FROM accounting_receipts WHERE accounting_id=1"
    ).fetchone() == ("expense.pdf", b"%PDF-1.4\n")
    assert db.notification[2] is False
