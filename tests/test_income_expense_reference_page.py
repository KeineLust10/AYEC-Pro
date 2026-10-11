import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QDate
from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import QApplication
from src.utils.reference_typography import apply_reference_font
from src.utils.theme_manager import ThemeManager

import src.ui.pages.income_expense_page as page_module


class FakeDb:
    def __init__(self):
        self.saved = []
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()

    def get_bank_accounts(self):
        return [{
            "id": 4, "bank_name": "Test Bank", "account_holder": "AYEC",
            "is_active": 1,
        }]

    def add_transaction(self, **values):
        self.saved.append(values)
        return len(self.saved)


class FakeFinance:
    def __init__(self, db):
        self.db = db

    def get_financial_summary(self, period):
        return {
            "gross_revenue": 250, "expenses": 70, "pocket_net": 180,
            "pending": 30,
        }

    def get_unified_ledger(self, **_kwargs):
        month = QDate.currentDate().toString("yyyy-MM-dd")
        return [
            {
                "date": month, "category": "Rent", "description": "Office rent",
                "amount_try": 70, "color_code": "red", "type_label": "Gider",
            },
            {
                "date": month, "category": "Service", "description": "Repair",
                "amount_try": 250, "color_code": "green", "type_label": "Gelir",
            },
        ]


def test_income_expense_page_filters_and_saves(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(page_module, "FinanceManager", FakeFinance)
    monkeypatch.setattr(page_module, "show_success", lambda *_args: None)
    db = FakeDb()
    page = page_module.IncomeExpensePage(db)
    assert page.table.rowCount() == 2
    page.filter_buttons[1].click()
    assert page.table.rowCount() == 1
    assert page.table.item(0, 1).text() == "Rent"
    page.bank.setCurrentIndex(1)
    page.amount.setValue(17.5)
    page.reference.setText("PAPER-01")
    page._save_expense()
    assert db.saved[0]["t_type"] == "Gider"
    assert db.saved[0]["bank_account_id"] == 4
    assert db.saved[0]["amount"] == 17.5
    page.close()
    app.processEvents()


def test_quick_expense_keeps_selected_receipt(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(page_module, "FinanceManager", FakeFinance)
    monkeypatch.setattr(page_module, "show_success", lambda *_args: None)
    db = FakeDb()
    page = page_module.IncomeExpensePage(db)
    receipt = tmp_path / "expense.pdf"
    receipt.write_bytes(b"%PDF-1.4\n")
    page._receipt_path = str(receipt)
    page.bank.setCurrentIndex(1)
    page.amount.setValue(22)
    page.reference.setText("INV-22")
    page._save_expense()
    db.cursor.execute(
        "SELECT filename, content FROM accounting_receipts WHERE accounting_id=1"
    )
    assert db.cursor.fetchone() == ("expense.pdf", b"%PDF-1.4\n")
    assert db.saved[0]["ref_no"] == "INV-22"
    exported = tmp_path / "exported.pdf"
    monkeypatch.setattr(
        page_module.QFileDialog, "getSaveFileName",
        lambda *_args: (str(exported), ""),
    )
    page._display_rows = [{"source": "accounting", "id": 1}]
    page._export_row_receipt(0, 0)
    assert exported.read_bytes() == b"%PDF-1.4\n"
    page.close()
    app.processEvents()


def test_income_expense_page_is_readable_in_light_theme(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    previous_palette = QPalette(app.palette())
    previous_stylesheet = app.styleSheet()
    previous_theme = ThemeManager._current_theme
    ThemeManager.apply_theme(app, "AYEC", animate=False)
    monkeypatch.setattr(page_module, "FinanceManager", FakeFinance)
    page = page_module.IncomeExpensePage(FakeDb())
    page.setAttribute(page_module.Qt.WidgetAttribute.WA_DontShowOnScreen)
    page.resize(1440, 900)
    page.show()
    app.processEvents()
    try:
        assert "QWidget{background-color:" in page.styleSheet()
        assert "color:" in page.styleSheet()
        assert "QTableWidget::item:alternate" in page.table.styleSheet()
        initial_style_length = len(page.styleSheet())
        page.resize(1200, 820)
        app.processEvents()
        assert len(page.styleSheet()) == initial_style_length
        page.grab().save(str(tmp_path / "income_expense_light.png"))
    finally:
        page.close()
        app.setPalette(previous_palette)
        app.setStyleSheet(previous_stylesheet)
        ThemeManager._current_theme = previous_theme
        app.processEvents()
