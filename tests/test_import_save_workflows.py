import os
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog, QPushButton

from src.database import Database
from src.ui.dialogs.customer_import_dialog import CustomerImportDialog
from src.ui.dialogs.stock_import_preview_dialog import StockImportPreviewDialog
from src.ui.pages.customers_page import CustomersPage
from src.ui.pages.stock_page import StockPage


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


def test_stock_import_save_persists_row_and_accepts_dialog():
    db = Database(":memory:", init_mode="full")
    parse_result = {
        "rows": [
            {
                "name": "Import Test Part",
                "category": "General",
                "stock": "3",
                "purchase_price": "80",
                "price": "125.5",
                "currency": "TRY",
                "code": "IMP-001",
                "shelf": "A1",
                "_from_invoice": True,
            }
        ],
        "raw_rows": [],
        "detected_columns": [],
        "suggested_mapping": {},
        "metadata": {},
        "warnings": [],
        "source_path": "",
        "source_type": "",
    }

    try:
        dialog = StockImportPreviewDialog(parse_result=parse_result, db=db)
        with patch(
            "src.ui.dialogs._sipd_logic_mixin.show_success"
        ) as show_success:
            dialog.save_rows()

        saved = db.cursor.execute(
            """
            SELECT name, stock, price, purchase_price, currency, code, shelf_number
            FROM parts
            WHERE code=?
            """,
            ("IMP-001",),
        ).fetchone()
        movement_count = db.cursor.execute(
            """
            SELECT COUNT(*)
            FROM stock_movements
            WHERE part_id=(SELECT id FROM parts WHERE code=?)
            """,
            ("IMP-001",),
        ).fetchone()[0]

        assert tuple(saved) == (
            "Import Test Part",
            3,
            125.5,
            80.0,
            "TRY",
            "IMP-001",
            "A1",
        )
        assert movement_count == 1
        assert dialog.result() == QDialog.DialogCode.Accepted
        show_success.assert_called_once()
    finally:
        db.close()


def test_smart_import_selection_mode_returns_rows_without_stock_write():
    db = Database(":memory:", init_mode="full")
    parse_result = {
        "rows": [
            {
                "name": "Purchase Invoice Part",
                "stock": "4",
                "purchase_price": "12.50",
                "currency": "USD",
                "code": "PO-IMP-1",
            }
        ],
        "raw_rows": [],
        "detected_columns": [],
        "suggested_mapping": {},
        "metadata": {},
        "warnings": [],
        "source_path": "",
        "source_type": "xlsx",
    }

    try:
        dialog = StockImportPreviewDialog(
            parse_result=parse_result,
            db=db,
            selection_only=True,
        )
        dialog.save_rows()

        assert dialog.result() == QDialog.DialogCode.Accepted
        assert dialog.selected_rows[0]["name"] == "Purchase Invoice Part"
        assert dialog.selected_rows[0]["purchase_price"] == "12.50"
        assert db.cursor.execute(
            "SELECT COUNT(*) FROM parts WHERE code='PO-IMP-1'"
        ).fetchone()[0] == 0
    finally:
        db.close()


def test_stock_import_preserves_usd_and_stock_table_renders_rows():
    db = Database(":memory:", init_mode="full")
    parse_result = {
        "rows": [
            {
                "name": "USD Import Part",
                "category": "General",
                "stock": "2",
                "purchase_price": "100",
                "price": "150",
                "currency": "USD",
                "code": "USD-IMP-001",
            }
        ],
        "raw_rows": [],
        "detected_columns": [],
        "suggested_mapping": {},
        "metadata": {},
        "warnings": [],
        "source_path": "",
        "source_type": "",
    }
    page = None
    try:
        dialog = StockImportPreviewDialog(parse_result=parse_result, db=db)
        with patch(
            "src.ui.dialogs._sipd_logic_mixin.show_success"
        ), patch(
            "src.ui.dialogs._sipd_logic_mixin.show_warning"
        ):
            dialog.save_rows()

        saved = db.cursor.execute(
            """
            SELECT currency, purchase_price, price
            FROM parts
            WHERE code=?
            """,
            ("USD-IMP-001",),
        ).fetchone()
        assert tuple(saved) == ("USD", 100.0, 150.0)

        second_import = dict(parse_result)
        second_import["rows"] = [
            {
                "name": "USD Import Part",
                "category": "General",
                "stock": "3",
                "purchase_price": "110",
                "price": "165",
                "currency": "USD",
                "code": "USD-IMP-001",
            }
        ]
        second_dialog = StockImportPreviewDialog(
            parse_result=second_import,
            db=db,
        )
        with patch(
            "src.ui.dialogs._sipd_logic_mixin.show_success"
        ), patch(
            "src.ui.dialogs._sipd_logic_mixin.show_warning"
        ):
            second_dialog.save_rows()

        merged = db.cursor.execute(
            """
            SELECT COUNT(*), MAX(stock), MAX(purchase_price), MAX(price),
                   MAX(currency)
            FROM parts
            WHERE code=?
            """,
            ("USD-IMP-001",),
        ).fetchone()
        assert tuple(merged) == (1, 5, 110.0, 165.0, "USD")

        finance_rows = db.cursor.execute(
            """
            SELECT original_amount, currency, exchange_rate, try_equivalent
            FROM accounting
            WHERE category='Stok Alimi'
            ORDER BY id
            """
        ).fetchall()
        assert [tuple(row) for row in finance_rows] == [
            (200.0, "USD", 1.0, 200.0),
            (330.0, "USD", 1.0, 330.0),
        ]

        stats = db.get_stock_stats()
        assert stats["total_types"] == 1
        assert stats["total_value_try"] == 550.0

        page = StockPage(db)
        page.reload_data()
        assert page.table_stock.rowCount() >= 1
        assert page.table_stock.updatesEnabled()
        currency_column = (page._stock_column_map or {}).get("currency", 8)
        currency_values = {
            page.table_stock.item(row, currency_column).text()
            for row in range(page.table_stock.rowCount())
            if page.table_stock.item(row, currency_column)
        }
        assert "USD" in currency_values
    finally:
        if page is not None:
            page.close()
        db.close()


def test_customer_csv_import_persists_all_rows_and_accepts_dialog():
    db = Database(":memory:", init_mode="full")
    with tempfile.TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / "customers.csv"
        source_path.write_text(
            "Musteri,Telefon,E-posta,Firma,Adres,Vergi No,Sehir,Tur,Not\n"
            "Ada Test,5550000001,ada@example.com,Ada Ltd,Address 1,111,Istanbul,"
            "Kurumsal,First\n"
            "Bora Test,5550000002,bora@example.com,,Address 2,222,Ankara,"
            "Bireysel,Second\n",
            encoding="utf-8",
        )

        try:
            dialog = CustomerImportDialog(db, source_path)
            with patch(
                "src.ui.dialogs.customer_import_dialog.show_success"
            ) as show_success:
                dialog.save_rows()

            rows = db.cursor.execute(
                """
                SELECT name, phone, email, company_name, tax_no, city, type, notes
                FROM customers
                WHERE name IN (?, ?)
                ORDER BY name
                """,
                ("Ada Test", "Bora Test"),
            ).fetchall()

            assert [tuple(row) for row in rows] == [
                (
                    "Ada Test",
                    "5550000001",
                    "ada@example.com",
                    "Ada Ltd",
                    "111",
                    "Istanbul",
                    "Kurumsal",
                    "First",
                ),
                (
                    "Bora Test",
                    "5550000002",
                    "bora@example.com",
                    "",
                    "222",
                    "Ankara",
                    "Bireysel",
                    "Second",
                ),
            ]
            assert dialog.result() == QDialog.DialogCode.Accepted
            show_success.assert_called_once()
        finally:
            db.close()


def test_customer_list_import_button_opens_dialog_and_requests_reload():
    db = Database(":memory:", init_mode="full")
    page = CustomersPage(db)
    import_buttons = [
        button
        for button in page.findChildren(QPushButton)
        if button.toolTip() == "M\u00fc\u015fteri I\u00e7e Aktar"
    ]

    try:
        assert len(import_buttons) == 1
        with patch(
            "src.ui.pages._customers_func_mixin.QFileDialog.getOpenFileName",
            return_value=("customers.csv", ""),
        ), patch(
            "src.ui.dialogs.customer_import_dialog.CustomerImportDialog"
        ) as dialog_class, patch.object(
            page, "request_reload"
        ) as request_reload, patch.object(
            page, "_emit_financial_data_changed"
        ) as emit_financial_data_changed:
            dialog_class.return_value.exec.return_value = (
                QDialog.DialogCode.Accepted
            )
            import_buttons[0].click()

        dialog_class.assert_called_once_with(db, "customers.csv", page)
        request_reload.assert_called_once_with()
        emit_financial_data_changed.assert_called_once_with()
    finally:
        page.close()
        db.close()
