import sqlite3

from src.db.mixins.currency_mixin import CurrencyMixin


class Ledger(CurrencyMixin):
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        self.cursor.executescript(
            """
            CREATE TABLE currency_transactions(
                id INTEGER PRIMARY KEY, customer_id INTEGER,
                transaction_type TEXT, amount REAL, currency TEXT,
                exchange_rate REAL, try_equivalent REAL, description TEXT,
                tracking_no TEXT, created_at TEXT, current_balance REAL,
                is_invoiced INTEGER
            );
            CREATE TABLE customer_currency_balances(
                id INTEGER PRIMARY KEY, customer_id INTEGER, currency TEXT,
                balance REAL, last_updated TEXT,
                UNIQUE(customer_id, currency)
            );
            CREATE TABLE payment_debt_links(
                id INTEGER PRIMARY KEY, payment_txn_id INTEGER,
                debt_txn_id INTEGER, amount REAL, created_at TEXT
            );
            INSERT INTO currency_transactions VALUES
                (1, 7, 'DEBIT', 900, 'TRY', 1, 900, 'service', 'S-1', 'now', -900, 0);
            INSERT INTO customer_currency_balances VALUES
                (1, 7, 'TRY', -900, 'now');
            """
        )


def test_atomic_payment_links_credit_and_debt():
    db = Ledger()
    result = db.record_customer_payment(
        customer_id=7,
        amount=900,
        currency="TRY",
        description="collection",
        tracking_no="S-1",
        selected_debt_ids=[1],
    )
    assert result["ok"] is True
    assert db.get_unpaid_debts(7, "TRY") == []
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM payment_debt_links"
    ).fetchone()[0] == 1


def test_atomic_payment_rolls_back_when_over_balance():
    db = Ledger()
    result = db.record_customer_payment(
        customer_id=7,
        amount=901,
        currency="TRY",
        description="too much",
        tracking_no="S-1",
        selected_debt_ids=[1],
    )
    assert result["ok"] is False
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM currency_transactions WHERE transaction_type='CREDIT'"
    ).fetchone()[0] == 0


def test_ledger_balance_does_not_add_legacy_totals_again():
    db = Ledger()
    db.cursor.execute(
        "CREATE TABLE devices(customer_id INTEGER, tracking_no TEXT, labor_cost REAL, cargo_fee REAL)"
    )
    db.cursor.execute(
        "CREATE TABLE used_parts(tracking_no TEXT, price REAL, quantity REAL, is_deleted INTEGER)"
    )
    db.cursor.execute(
        "INSERT INTO devices VALUES (7, 'S-1', 900, 0)"
    )
    assert db.get_customer_total_balance_in_try(7) == -900.0


def test_linked_and_legacy_credits_cannot_reopen_same_debt():
    db = Ledger()
    db.cursor.execute(
        "INSERT INTO currency_transactions VALUES "
        "(2, 7, 'CREDIT', 900, 'TRY', 1, 900, 'linked', 'S-1', 'now', 0, 0)"
    )
    db.cursor.execute(
        "INSERT INTO payment_debt_links(payment_txn_id,debt_txn_id,amount,created_at) "
        "VALUES (2,1,900,'now')"
    )
    db.cursor.execute(
        "INSERT INTO currency_transactions VALUES "
        "(3, 7, 'CREDIT', 900, 'TRY', 1, 900, 'legacy', 'S-1', 'now', 0, 0)"
    )
    db.conn.commit()
    assert db.get_unpaid_debts(7, "TRY") == []
    result = db.record_customer_payment(
        customer_id=7,
        amount=1,
        currency="TRY",
        description="duplicate attempt",
        tracking_no="S-1",
        selected_debt_ids=[1],
    )
    assert result["ok"] is False
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM currency_transactions WHERE transaction_type='CREDIT'"
    ).fetchone()[0] == 2


def test_currency_reversal_appends_opposite_entry_without_deleting_original():
    db = Ledger()
    db.add_currency_transaction(
        customer_id=7,
        amount=25,
        currency="TRY",
        transaction_type="DEBIT",
        description="Original debt",
        tracking_no="REV-1",
    )
    tx_id = db.get_last_currency_transaction_id()
    reversal_id = db.reverse_currency_transaction(tx_id, "duplicate debt")
    assert reversal_id and reversal_id != tx_id
    rows = db.cursor.execute(
        "SELECT id, transaction_type, amount, tracking_no "
        "FROM currency_transactions ORDER BY id"
    ).fetchall()
    assert any(row[0] == tx_id and row[1] == "DEBIT" for row in rows)
    assert any(
        row[1] == "CREDIT" and row[2] == 25 and row[3] == f"REVERSAL-{tx_id}"
        for row in rows
    )
