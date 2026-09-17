import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QPushButton

from src.ui.pages.offer_pages import OffersPage
from src.utils.theme_manager import ThemeManager


APP = QApplication.instance() or QApplication([])


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


def test_offers_page_matches_compact_single_page_reference():
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

    page = OffersPage(db)

    assert page.table.rowCount() == 25
    assert page.page_number.text() == "1 / 1"
    assert page.btn_previous.isEnabled() is False
    assert page.btn_next.isEnabled() is False
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
    assert page.table.alternatingRowColors() is True
    assert page.table.verticalHeader().defaultSectionSize() == 34
    assert "QTableWidget::item:hover" not in page.table.styleSheet()
