import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QWidget

from src.ui.dialogs import sale_payment_dialog
from src.ui.dialogs.sale_payment_dialog import SalePaymentDialog
from src.ui.pages import transaction_page_behaviors
from src.ui.pages.transaction_page_behaviors import TransactionPageBehaviorMixin


APP = QApplication.instance() or QApplication([])


def test_partial_payment_keeps_remaining_debt():
    dialog = SalePaymentDialog(
        total=10000,
        currency_code="TRY",
        customer_name="Test Customer",
    )

    dialog.spin_payment.setValue(5000)
    APP.processEvents()

    assert dialog.lbl_remaining.text() == "5,000.00 \u20ba"
    dialog._accept_values()
    assert dialog.payment_amount == 5000
    assert dialog.payment_method == "Nakit"


class _Combo:
    def __init__(self, text, data=None):
        self._text = text
        self._data = data

    def currentIndex(self):
        return 0

    def currentText(self):
        return self._text

    def currentData(self):
        return self._data


class _Connection:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class _PaymentDb:
    def __init__(self):
        self.conn = _Connection()
        self.currency_calls = []
        self.allocation = None

    def create_payment_debt_links_table(self):
        return True

    def add_currency_transaction(self, **kwargs):
        self.currency_calls.append(kwargs)
        return True

    def get_last_currency_transaction_id(self):
        return 100 + len(self.currency_calls)

    def add_transaction(self, **_kwargs):
        return 200

    def apply_payment_to_debts(self, **kwargs):
        self.allocation = kwargs
        return {"ok": True, "allocated": kwargs["payment_amount"]}

    def notify_jarvis(self, *_args, **_kwargs):
        return None


class _TransactionHarness(QWidget, TransactionPageBehaviorMixin):
    def __init__(self):
        QWidget.__init__(self)
        self.db = _PaymentDb()
        self.cmb_customer = _Combo("Test Customer", 7)
        self.cmb_currency = _Combo("TRY - Turkish Lira")
        self.current_exchange_rate = 1.0
        self.cart_items = [
            {
                "type": "service",
                "service": "Service",
                "qty": 1,
                "price": 10000,
            }
        ]
        self.cleared = False
        self.main_window = None

    def calculate_cart_total(self):
        return 10000

    def clear_cart(self):
        self.cleared = True


def test_save_and_pay_allocates_only_entered_amount_to_new_debt(monkeypatch):
    class _Dialog:
        def __init__(self, **_kwargs):
            self.payment_amount = 5000
            self.payment_method = "Nakit"
            self.payment_note = "Partial"

        def exec(self):
            return 1

    messages = []
    monkeypatch.setattr(sale_payment_dialog, "SalePaymentDialog", _Dialog)
    monkeypatch.setattr(
        transaction_page_behaviors,
        "show_success",
        lambda _parent, message: messages.append(message),
    )
    harness = _TransactionHarness()

    harness.save_and_pay()

    assert [call["transaction_type"] for call in harness.db.currency_calls] == [
        "DEBIT",
        "CREDIT",
    ]
    assert harness.db.currency_calls[1]["amount"] == 5000
    assert harness.db.allocation["payment_amount"] == 5000
    assert harness.db.allocation["selected_debt_ids"] == [101]
    assert harness.db.conn.commits == 1
    assert harness.cleared is True
    assert "Kalan borc: 5000.00 TRY" in messages[0]
