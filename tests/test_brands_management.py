import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.dialogs.brand_edit_dialog import BrandEditDialog
from src.ui.pages.brands_page import BrandsPage


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class _Db:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE device_brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_type TEXT,
                brand TEXT,
                is_active INTEGER DEFAULT 1
            )
            """
        )
        self.cursor.executemany(
            """
            INSERT INTO device_brands (device_type, brand, is_active)
            VALUES ('Laptop', ?, 1)
            """,
            [(f"Brand {index:02d}",) for index in range(1, 16)],
        )
        self.cursor.execute(
            """
            INSERT INTO device_brands (device_type, brand, is_active)
            VALUES ('Monitor', 'Display Brand', 1)
            """
        )
        self.conn.commit()


def test_brands_page_fits_rows_on_one_page_and_filters_by_product_group():
    db = _Db()
    page = BrandsPage(db)
    try:
        assert page.total_count == 16
        assert page.table.rowCount() == 16
        assert page.table.columnCount() == 5
        assert not page.btn_next.isEnabled()

        page.cmb_group.setCurrentText("Laptop")

        assert page.current_page == 0
        assert page.table.rowCount() == 15
    finally:
        page.close()
        db.conn.close()


def test_brand_edit_dialog_updates_existing_definition():
    db = _Db()
    dialog = BrandEditDialog(
        db,
        initial_device_type="Laptop",
        initial_brand="Brand 01",
        edit_mode=True,
    )
    try:
        dialog.inp_device_type.setText("Monitor")
        dialog.inp_brand.setText("Updated Brand")
        dialog.save()

        updated = db.cursor.execute(
            """
            SELECT device_type, brand
            FROM device_brands
            WHERE brand='Updated Brand'
            """
        ).fetchone()
        assert tuple(updated) == ("Monitor", "Updated Brand")
        assert db.cursor.execute(
            """
            SELECT id
            FROM device_brands
            WHERE device_type='Laptop' AND brand='Brand 01'
            """
        ).fetchone() is None
    finally:
        dialog.close()
        db.conn.close()
