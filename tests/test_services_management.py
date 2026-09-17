import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.db.mixins.services_mixin import ServicesMixin
from src.ui.dialogs.add_service_definition_dialog import AddServiceDefinitionDialog
from src.ui.pages.services_page import ServicesPage


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class _Db(ServicesMixin):
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()


def test_service_schema_migrates_legacy_price_and_saves_three_currencies():
    db = _Db()
    try:
        db.cursor.execute(
            """
            CREATE TABLE services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                price REAL DEFAULT 0,
                currency TEXT DEFAULT 'TRY',
                description TEXT,
                barcode TEXT,
                created_at TEXT,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
            """
        )
        db.cursor.execute(
            """
            INSERT INTO services (name, price, currency, is_deleted)
            VALUES ('Legacy Labor', 250, 'TRY', 0)
            """
        )
        service_id = db.add_service(
            "Three Currency Labor",
            500,
            currency="TRY",
            price_try=500,
            price_usd=20,
            price_eur=18,
            is_active=0,
        )

        rows = {row["name"]: row for row in db.get_services_list()}
        assert rows["Legacy Labor"]["price_try"] == 250
        assert rows["Three Currency Labor"]["id"] == service_id
        assert rows["Three Currency Labor"]["price_usd"] == 20
        assert rows["Three Currency Labor"]["price_eur"] == 18
        assert rows["Three Currency Labor"]["is_active"] == 0
    finally:
        db.conn.close()


def test_labor_dialog_and_page_expose_extended_management_fields():
    dialog = AddServiceDefinitionDialog(
        service_data={
            "name": "Labor",
            "price_try": 150,
            "price_usd": 7,
            "price_eur": 6,
            "is_active": 0,
        }
    )
    db = _Db()
    page = None
    try:
        data = dialog.get_data()
        assert data["price_try"] == 150
        assert data["price_usd"] == 7
        assert data["price_eur"] == 6
        assert data["is_active"] == 0

        for index in range(1, 13):
            db.add_service(
                f"Labor {index:02d}",
                index * 10,
                price_try=index * 10,
                price_usd=index,
                price_eur=index - 1,
                is_active=index % 2,
            )
        page = ServicesPage(db)
        page.load_services()
        assert page.table.columnCount() == 8
        assert page.table.rowCount() == 10
        assert page.total_count == 12
        assert page.btn_next.isEnabled()
        assert page.table.cellWidget(0, 6).text() == "D\u00fczenle"
        output_rows = page._collect_service_rows()
        assert len(output_rows) == 12
        assert list(output_rows[0]) == [
            "\u0130\u015f\u00e7ilik Ad\u0131",
            "TL",
            "USD",
            "EURO",
            "Durum",
        ]

        page.next_page()
        assert page.current_page == 2
        assert page.table.rowCount() == 2
    finally:
        dialog.close()
        if page is not None:
            page.close()
        db.conn.close()
