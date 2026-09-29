import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import sqlite3
from src.db.mixins.currency_mixin import CurrencyMixin
from src.ui.dialogs.payment_dialog import ModernPaymentDialog
from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit

APP = QApplication.instance() or QApplication([])

class Ledger(CurrencyMixin):
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        self.cursor.executescript('''
            CREATE TABLE currency_transactions(id INTEGER PRIMARY KEY, customer_id INTEGER,
                amount REAL, currency TEXT, description TEXT, tracking_no TEXT,
                created_at TEXT, current_balance REAL, transaction_type TEXT);
            CREATE TABLE payment_debt_links(payment_txn_id INTEGER, debt_txn_id INTEGER, amount REAL);
            INSERT INTO currency_transactions VALUES
                (1,37,4000,'TRY','','','2026-09-21',-4000,'DEBIT'),
                (2,37,7093.70,'TRY','','','2026-09-21',-11093.70,'DEBIT'),
                (3,37,191,'USD','','','2026-09-21',-191,'DEBIT'),
                (4,25,6546.94,'TRY','','','2026-09-21',-6546.94,'DEBIT');
        ''')


def test_debt_selection_uses_item_remainders_not_running_balance():
    db = Ledger()
    debts = db.get_unpaid_debts(37, 'TRY')
    assert round(sum(-row[6] for row in debts), 2) == 11093.70
    dialog = ModernPaymentDialog.__new__(ModernPaymentDialog)
    dialog.db = db
    dialog.debt_items = debts
    dialog.selected_debts = {1, 2}
    dialog.selected_currency = 'TRY'
    dialog.lbl_selected_total = QLabel()
    dialog.inp_amount = QLineEdit()
    dialog._update_selected_total()
    assert dialog.inp_amount.text() == '11.093,70'
    db.conn.close()


def test_credit_cannot_exceed_open_balance():
    db = Ledger()
    db.get_customer_currency_balance = lambda _cid, _cur: -100.0
    assert db.add_currency_transaction(37, 101, "TRY", "CREDIT", exchange_rate=1.0) is False
    db.conn.close()


def test_partial_and_full_allocations_and_currency_isolation():
    db = Ledger()
    db.cursor.executemany('INSERT INTO payment_debt_links VALUES (?,?,?)',
                         [(10, 1, 4000), (10, 2, 1000)])
    debts = db.get_unpaid_debts(37, 'TRY')
    assert len(debts) == 1
    assert debts[0][6] == -6093.70
    db.cursor.execute('INSERT INTO payment_debt_links VALUES (11,2,6093.70)')
    assert db.get_unpaid_debts(37, 'TRY') == []
    assert db.get_unpaid_debts(37, 'USD')[0][6] == -191
    assert db.get_unpaid_debts(25, 'TRY')[0][6] == -6546.94
    db.conn.close()
