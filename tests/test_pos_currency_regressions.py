import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest
from PyQt6.QtWidgets import QApplication, QTableWidget

from src.database import Database
from src.ui.pages import quick_sale_page
from src.ui.pages.quick_sale_page import QuickSalePage


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _page_without_init():
    page = QuickSalePage.__new__(QuickSalePage)
    page.cart_items = []
    page.all_products = []
    page.selected_customer = None
    page.window = lambda: None
    page.clear_cart = lambda: None
    page.load_products = lambda: None
    return page


def test_pos_refuses_mixed_currency_cart_without_writing(monkeypatch):
    page = _page_without_init()
    page.cart_items = [
        {"id": 1, "name": "USD item", "price": 10, "qty": 1, "total": 10, "currency": "USD"},
        {"id": 2, "name": "TRY item", "price": 400, "qty": 1, "total": 400, "currency": "TRY"},
    ]
    writes = []
    page.db = object()
    monkeypatch.setattr(quick_sale_page, "show_error", lambda *args: writes.append(args))

    page.finish_sale("Cash")

    assert len(writes) == 1


def test_pos_cogs_records_original_stock_currency_and_try_equivalent(
    tmp_path, monkeypatch, qapp
):
    db = Database(str(tmp_path / "pos-currency.db"))
    part_id = db.add_part(
        "USD stock", "General", 2, 20, purchase_price=5, currency="USD", code="USD-POS"
    )
    db.cursor.execute(
        "INSERT INTO exchange_rates(currency,selling_rate,created_at) VALUES ('USD',40,'2026-09-28')"
    )
    db.conn.commit()

    page = _page_without_init()
    page.db = db
    page.table = QTableWidget(0, 4)
    page.cart_items = [
        {"id": part_id, "name": "USD stock", "price": 20, "qty": 1, "total": 20, "currency": "USD"}
    ]
    monkeypatch.setattr(quick_sale_page, "show_success", lambda *args: None)
    monkeypatch.setattr(quick_sale_page, "show_error", lambda *args: pytest.fail(str(args)))

    page.finish_sale("Cash")

    expense = db.cursor.execute(
        "SELECT amount,original_amount,try_equivalent,currency,exchange_rate "
        "FROM accounting WHERE category='Satılan Malın Maliyeti'"
    ).fetchone()
    assert tuple(expense[:3]) == pytest.approx((200, 5, 200))
    assert expense[3] == "USD"
    assert float(expense[4]) == pytest.approx(40)
    db.close()
