import os
import sqlite3
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.pages.product_groups_page import ProductGroupsPage
from src.utils.page_config import PAGE_MAPPING


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class _Db:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
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
            VALUES (?, 'Test Brand', 1)
            """,
            [(f"Group {index:02d}",) for index in range(1, 16)],
        )
        self.conn.commit()


def test_product_groups_page_is_registered_and_paginated():
    assert PAGE_MAPPING[146][1] == "ProductGroupsPage"
    db = _Db()
    page = ProductGroupsPage(db)
    try:
        assert page.total_count == 15
        assert page.table.rowCount() == 10
        assert page.btn_next.isEnabled()

        page.next_page()

        assert page.current_page == 1
        assert page.table.rowCount() == 5
    finally:
        page.close()
        db.conn.close()


def test_product_group_add_edit_delete_flow():
    db = _Db()
    page = ProductGroupsPage(db)
    try:
        with patch(
            "src.ui.pages.product_groups_page.ModernInputDialog.get_text",
            return_value=("New Group", True),
        ), patch(
            "src.ui.pages.product_groups_page.show_success"
        ):
            page.add_group()

        row = db.cursor.execute(
            "SELECT id, name FROM product_groups WHERE name='New Group'"
        ).fetchone()
        assert row is not None

        with patch(
            "src.ui.pages.product_groups_page.ModernInputDialog.get_text",
            return_value=("Renamed Group", True),
        ), patch(
            "src.ui.pages.product_groups_page.show_info"
        ):
            page.edit_group(row[0], row[1])

        renamed = db.cursor.execute(
            "SELECT id FROM product_groups WHERE name='Renamed Group'"
        ).fetchone()
        assert renamed is not None

        with patch(
            "src.ui.pages.product_groups_page.SimpleConfirmDialog"
        ) as confirm_dialog, patch(
            "src.ui.pages.product_groups_page.show_success"
        ):
            confirm_dialog.return_value.exec.return_value = 1
            page.delete_group(renamed[0], "Renamed Group")

        assert db.cursor.execute(
            "SELECT id FROM product_groups WHERE id=?",
            (renamed[0],),
        ).fetchone() is None
    finally:
        page.close()
        db.conn.close()
