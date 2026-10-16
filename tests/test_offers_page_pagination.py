import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtWidgets import QHeaderView
from PyQt6.QtTest import QTest

from src.services.offer_service import OfferService
from src.ui.pages.offer_pages import OffersPage
from src.utils.theme_manager import ThemeManager


APP = QApplication.instance() or QApplication([])


class _NavigationStub:
    def __init__(self):
        self.page_ids = []

    def on_menu_click(self, page_id):
        self.page_ids.append(page_id)


class _Db:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.executescript(
            """
            CREATE TABLE offers (
                id INTEGER PRIMARY KEY,
                offer_no TEXT,
                customer_name TEXT,
                company_name TEXT,
                currency_code TEXT,
                total REAL DEFAULT 0,
                total_try REAL DEFAULT 0,
                status TEXT,
                created_at TEXT
            );
            CREATE TABLE offer_items (
                id INTEGER PRIMARY KEY,
                offer_id INTEGER,
                description TEXT
            );
            """
        )


def test_offers_page_matches_reference_rows_and_preserves_pagination():
    ThemeManager._install_stylesheet_patch()
    db = _Db()
    for offer_id in range(1, 26):
        db.cursor.execute(
            """
            INSERT INTO offers (
                id, offer_no, customer_name, company_name, currency_code,
                total, total_try, status, created_at
            )
            VALUES (?, ?, 'Customer', 'Company', 'TRY',
                    1200, 1200, 'created', '2026-07-30 12:00:00')
            """,
            (offer_id, f"OFF-{offer_id:03d}"),
        )
    db.conn.commit()

    navigation = _NavigationStub()
    page = OffersPage(db, navigation)

    page.btn_quick_basket.click()
    page.btn_reports.click()
    page.btn_add_to_basket.click()
    assert navigation.page_ids == [150, 314, 150]
    assert page.btn_header_export.isEnabled()
    assert page.preview_fields["customer"].text() == "Customer | Company"
    assert page.preview_fields["currency"].text() == "TRY"
    assert page.preview_total.text().endswith("1,200.00 \u20ba")
    assert page.preview_amounts["discount"].text() == "0.00 \u20ba"
    page.btn_bulk_select.click()
    assert page.table.selectionMode().name == "MultiSelection"

    assert page.table.rowCount() == 6
    assert page.page_number.text() == "1 / 5"
    assert page.btn_previous.isEnabled() is False
    assert page.btn_next.isEnabled() is True
    open_button = page.table.cellWidget(0, 8)
    edit_button = page.table.cellWidget(0, 9)
    assert isinstance(open_button, QPushButton)
    assert isinstance(edit_button, QPushButton)
    assert open_button.text() == "A\u00e7"
    assert edit_button.text() == "D\u00fczenle"
    assert open_button.height() == 26
    assert edit_button.height() == 26
    assert page.table.columnWidth(8) == 66
    assert page.table.columnWidth(9) == 88
    assert page.table.horizontalHeader().sectionResizeMode(2) == QHeaderView.ResizeMode.Stretch
    page.resize(1600, 900)
    page.show()
    APP.processEvents()
    assert sum(page.table.columnWidth(column) for column in range(page.table.columnCount())) >= page.table.viewport().width() - 2
    assert page.table.alternatingRowColors() is True
    assert page.table.verticalHeader().defaultSectionSize() == 46
    assert "QTableWidget::item:hover" not in page.table.styleSheet()

    page.btn_next.click()
    assert page.table.rowCount() == 6
    assert page.page_number.text() == "2 / 5"
    assert page.btn_previous.isEnabled() is True
    page.btn_previous.click()
    assert page.page_number.text() == "1 / 5"


def test_offer_service_returns_only_the_requested_filtered_page():
    db = _Db()
    for offer_id in range(1, 15):
        status = "Onayland\u0131" if offer_id % 2 else "created"
        currency = "USD" if offer_id % 2 else "TRY"
        db.cursor.execute(
            """
            INSERT INTO offers (
                id, offer_no, customer_name, company_name, currency_code,
                total, total_try, status, created_at
            ) VALUES (?, ?, 'Customer', 'Company', ?, 100, 100, ?, '2026-07-30')
            """,
            (offer_id, f"OFF-{offer_id:03d}", currency, status),
        )
    db.conn.commit()

    total, rows = OfferService(db).offers_page(
        status_filter="accepted", currency_filter="USD", limit=3, offset=3
    )

    assert total == 7
    assert len(rows) == 3
    assert all(row["currency_code"] == "USD" for row in rows)
    assert all(row["status"] == "Onayland\u0131" for row in rows)


def test_offer_service_does_not_commit_when_schema_is_already_current():
    class Cursor:
        def execute(self, _query):
            return self

        def fetchall(self):
            return [(0, "id"), (1, "created_by")]

    class Connection:
        commits = 0

        def commit(self):
            self.commits += 1

    connection = Connection()
    OfferService(type("Db", (), {"cursor": Cursor(), "conn": connection})())

    assert connection.commits == 0


def test_offer_search_debounces_rapid_input():
    db = _Db()
    page = OffersPage(db, _NavigationStub())
    calls = []
    original = page.store.offers_page

    def counted_query(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    page.store.offers_page = counted_query
    page.search.setText("OFF")
    page.search.setText("OFF-0")
    assert calls == []

    for _ in range(20):
        if calls:
            break
        QTest.qWait(25)

    assert len(calls) == 1
    page.close()
