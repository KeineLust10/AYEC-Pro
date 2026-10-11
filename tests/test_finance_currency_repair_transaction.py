import sqlite3

from src.database import Database
from src.utils.finance_manager import FinanceManager


def insert_legacy_foreign_row(db):
    db.conn.execute("INSERT INTO accounting(date,description,amount,type,currency,exchange_rate,original_amount,try_equivalent) VALUES ('2026-10-01','Legacy foreign fixture',100,'Gelir','USD',44,100,100)")
    db.conn.commit()


def test_finance_reads_without_repair_do_not_hold_a_write_lock(tmp_path):
    path = tmp_path / "finance_read_lock.db"
    db = Database(str(path))
    other = None
    try:
        manager = FinanceManager(db)
        manager.get_financial_summary("fiscal")
        manager.get_unified_ledger(100)
        assert not db.conn.in_transaction
        other = sqlite3.connect(str(path), timeout=0.1)
        other.execute("INSERT INTO accounting(date,description,amount,type) VALUES ('2026-10-01','Independent writer',12,'Gelir')")
        other.commit()
        assert db.conn.execute("SELECT COUNT(*) FROM accounting").fetchone()[0] == 1
    finally:
        if other is not None:
            other.close()
        db.close()


def test_currency_repair_does_not_commit_the_callers_pending_transaction(tmp_path):
    db = Database(str(tmp_path / "finance_repair_caller.db"))
    try:
        insert_legacy_foreign_row(db)
        db.conn.execute("INSERT INTO customers(name) VALUES ('Uncommitted customer')")
        assert db.conn.in_transaction
        FinanceManager(db)._repair_accounting_currency_values()
        assert db.conn.in_transaction
        assert db.conn.execute("SELECT amount FROM accounting").fetchone()[0] == 4400
        db.conn.rollback()
        assert db.conn.execute("SELECT amount FROM accounting").fetchone()[0] == 100
        assert db.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0
    finally:
        db.close()


def test_owned_currency_repair_commits_and_releases_its_transaction(tmp_path):
    path = tmp_path / "finance_repair_owned.db"
    db = Database(str(path))
    try:
        insert_legacy_foreign_row(db)
        FinanceManager(db)._repair_accounting_currency_values()
        assert not db.conn.in_transaction
        with sqlite3.connect(str(path), timeout=0.1) as other:
            assert other.execute("SELECT amount,try_equivalent FROM accounting").fetchone() == (4400, 4400)
    finally:
        db.close()
