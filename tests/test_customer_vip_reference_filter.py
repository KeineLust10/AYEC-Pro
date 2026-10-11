import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.ui.pages._cpp_worker import CustomerWorker


class CustomerDatabase:
    _db_name = ":memory:"

    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute(
            "CREATE TABLE customers ("
            "id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT, "
            "company_name TEXT, type TEXT, is_partner INTEGER, is_deleted INTEGER)"
        )
        self.conn.execute(
            "CREATE TABLE customer_currency_balances ("
            "customer_id INTEGER, currency TEXT, balance REAL)"
        )
        self.conn.execute(
            "CREATE TABLE devices ("
            "id INTEGER PRIMARY KEY, customer_id INTEGER, customer_name TEXT, "
            "status TEXT, is_deleted INTEGER, is_archived INTEGER)"
        )
        self.conn.executemany(
            "INSERT INTO customers VALUES (?, ?, '', '', '', ?, 0, 0)",
            (
                (1, "Corporate Account", "Kurumsal"),
                (2, "Individual Account", "Bireysel"),
                (3, "VIP Account", "VIP"),
                (4, "Partner Account", "Kurumsal"),
            ),
        )
        self.conn.execute("UPDATE customers SET is_partner=1 WHERE id=4")
        self.conn.executemany(
            "INSERT INTO devices VALUES (?, ?, ?, ?, 0, 0)",
            (
                (1, 1, "Corporate Account", "Tamirde"),
                (2, 1, "Corporate Account", "Teslim Edildi"),
            ),
        )
        self.conn.commit()

    def get_setting(self, _key, default=""):
        return default


def test_vip_filter_returns_corporate_and_explicit_vip_customers_only():
    db = CustomerDatabase()
    worker = CustomerWorker(db, 50, 0, "", "VIP")
    result = {}
    worker.data_loaded.connect(lambda rows, total: result.update(rows=rows, total=total))

    worker.run()

    assert result["total"] == 2
    assert [row["name"] for row in result["rows"]] == [
        "Corporate Account",
        "VIP Account",
    ]
    assert [row["open_service_count"] for row in result["rows"]] == [1, 0]
