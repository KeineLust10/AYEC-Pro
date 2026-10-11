import os
import sqlite3
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QPushButton

from src.ui.pages.product_groups_page import ProductGroupsPage
from src.utils.page_config import PAGE_MAPPING
from src.utils.reference_typography import apply_reference_font


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


def test_product_group_reference_fields_use_live_catalog_and_service_counts():
    db = _Db()
    db.conn.execute("UPDATE device_brands SET is_active=0 WHERE device_type='Group 01'")
    db.conn.executemany('INSERT INTO device_brands(device_type,brand,is_active) VALUES(?,?,?)', [
        ('Group 01', 'Alpha', 1), (' group 01 ', 'alpha', 1),
        ('Group 01', 'Beta', 1), ('Group 01', 'Retired', 0),
    ])
    db.conn.execute('CREATE TABLE devices(device_type TEXT, is_deleted INTEGER DEFAULT 0)')
    db.conn.executemany('INSERT INTO devices VALUES(?,?)', [
        ('Group 01', 0), ('Group 01', 0), ('Group 02', 0), ('Group 02', 1),
    ])
    page = ProductGroupsPage(db)
    try:
        assert page.table.columnCount() == 6
        assert page._linked_brands_for('Group 01') == ['Alpha', 'Beta']
        assert page.table.item(0, 1).text() == 'Group 01'
        assert page.table.item(0, 2).text() == '2 Marka (Alpha, Beta)'
        assert page.metric_device_inventory.metric_value.text() == '3'
        assert page.metric_service_volume.metric_value.text() == 'Group 01'
        assert page.active_group_summary.text() == '15 grup son 30 g\u00fcnde eklendi'
        assert page._export_rows()[0] == ('Group 01', 'Alpha, Beta', 'Aktif')
        assert '<td>Alpha, Beta</td>' in page._html_document()
        actions = []
        page.edit_group = lambda gid, name: actions.append(('edit', gid, name))
        page.delete_group = lambda gid, name: actions.append(('delete', gid, name))
        gid = page.table.item(0, 1).data(256)
        action_buttons = page.table.cellWidget(0, 5).findChildren(QPushButton)
        action_buttons[0].click()
        action_buttons[1].click()
        assert actions == [('edit', gid, 'Group 01'), ('delete', gid, 'Group 01')]
    finally:
        page.close()
        db.conn.close()


def test_product_group_card_mode_keeps_paging_filtering_and_actions(monkeypatch):
    apply_reference_font(APP)
    actions = []
    monkeypatch.setattr(ProductGroupsPage, 'edit_group', lambda self, gid, name: actions.append(('edit', gid, name)))
    monkeypatch.setattr(ProductGroupsPage, 'delete_group', lambda self, gid, name: actions.append(('delete', gid, name)))
    db = _Db()
    page = ProductGroupsPage(db)
    try:
        page.resize(760, 900)
        page.show()
        page.view_tabs.setCurrentIndex(1)
        APP.processEvents()
        assert page.width() == 760
        assert page.views.currentWidget() is page.cards_scroll
        assert len(page._group_cards) == 10
        assert page.cards_grid.getItemPosition(1)[:2] == (0, 1)
        first = page._group_cards[0]
        assert first.geometry().right() <= page.cards_scroll.viewport().width()
        buttons = first.findChildren(QPushButton)
        buttons[0].click()
        buttons[1].click()
        group_id = page.table.item(0, 1).data(256)
        assert actions == [('edit', group_id, 'Group 01'), ('delete', group_id, 'Group 01')]
        page.next_page()
        assert len(page._group_cards) == 5
        assert page.views.currentIndex() == 1
        page.search.setText('Group 15')
        assert page.current_page == 0
        assert len(page._group_cards) == 1
        assert page.table.rowCount() == 1
        page.search.setText('No matching group')
        APP.processEvents()
        assert len(page._group_cards) == 0
        assert page.cards_empty.isVisible()
        page.view_tabs.setCurrentIndex(0)
        assert page.views.currentIndex() == 0
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
