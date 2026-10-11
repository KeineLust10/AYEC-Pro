import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QPushButton, QHeaderView, QStyleOptionViewItem
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtCore import Qt

from src.ui.dialogs.brand_edit_dialog import BrandEditDialog
from src.ui.pages.brands_page import BrandsPage, _DeviceGroupDelegate
from src.utils.reference_typography import apply_reference_font
from src.ui.widgets.reference_status_delegate import ReferenceStatusDelegate


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


def test_brand_table_stops_at_content_height_and_keeps_footer_close():
    db = _Db()
    page = BrandsPage(db)
    try:
        page.resize(1600, 850)
        page.show()
        APP.processEvents()
        previous_height = page.table.height()
        page.resize(1600, 1050)
        APP.processEvents()
        assert page.table.height() > previous_height
        assert page.table.height() == (
            page.table.horizontalHeader().height()
            + page.table.rowCount() * page.table.verticalHeader().defaultSectionSize()
            + 2
        )
        assert page.pagination_controls.y() - page.table_frame.geometry().bottom() < 50
    finally:
        page.close()
        db.conn.close()


def test_device_group_text_uses_active_theme_palette():
    option = QStyleOptionViewItem()
    expected = QColor("#172033")
    palette = option.palette
    palette.setColor(QPalette.ColorRole.Text, expected)
    option.palette = palette

    assert _DeviceGroupDelegate._label_color(option) == expected


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
        assert page.table.rowCount() == 10
        assert page.table.columnCount() == 6
        assert page.btn_next.isEnabled()

        page.cmb_group.setCurrentText("Laptop")

        assert page.current_page == 0
        assert page.table.rowCount() == 10
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


def test_brand_reference_pagination_filters_and_original_actions(monkeypatch):
    apply_reference_font(APP)
    calls = []
    for method in ('export_excel', 'export_pdf', 'print_list'):
        monkeypatch.setattr(BrandsPage, method, lambda self, _checked=False, name=method: calls.append(name))
    db = _Db()
    db.cursor.execute("UPDATE device_brands SET is_active=0 WHERE brand='Brand 01'")
    page = BrandsPage(db)
    try:
        page.resize(760, 900)
        page.show()
        APP.processEvents()
        assert page.width() == 760
        assert page.header_grid.indexOf(page.header_actions) >= 0
        assert page.header_actions.y() >= page.header_title.geometry().bottom()
        assert page.inp_search.geometry().bottom() < page.cmb_group.y()
        assert page.table.verticalHeader().defaultSectionSize() == 66
        assert not page.table.alternatingRowColors()
        assert isinstance(page.table.itemDelegateForColumn(4), ReferenceStatusDelegate)
        for button in page.export_buttons:
            button.click()
        assert calls == ['export_excel', 'export_pdf', 'print_list']
        page.cmb_page_size.setCurrentIndex(1)
        assert page.PAGE_SIZE == 20
        assert page.table.rowCount() == 15
        page.cmb_page_size.setCurrentIndex(0)
        assert page.PAGE_SIZE == 10
        assert page.table.rowCount() == 10
        page.btn_next.click()
        assert page.current_page == 1
        assert page.table.rowCount() == 5
        page.cmb_group.setCurrentText('Laptop')
        page.cmb_status.setCurrentIndex(page.cmb_status.findData('inactive'))
        assert page.current_page == 0
        assert page.table.rowCount() == 1
        selected = []
        page.open_edit_dialog = lambda group, brand: selected.append(('edit', group, brand))
        page.delete_row = lambda group, brand: selected.append(('delete', group, brand))
        buttons = page.table.cellWidget(0, 5).findChildren(QPushButton)
        buttons[0].click()
        buttons[1].click()
        assert selected == [('edit', 'Laptop', 'Brand 01'), ('delete', 'Laptop', 'Brand 01')]
        page.inp_search.setText('Display')
        assert page.table.rowCount() == 0
        assert page.table.columnCount() == 6
    finally:
        page.close()
        db.conn.close()


def test_brand_service_counts_are_scoped_and_exclude_deleted_records():
    db = _Db()
    db.conn.execute('CREATE TABLE devices(device_type TEXT, device_brand TEXT, is_deleted INTEGER DEFAULT 0)')
    db.conn.executemany('INSERT INTO devices VALUES(?,?,?)', [
        ('Laptop', 'Brand 01', 0), (' laptop ', 'brand 01', 0),
        ('Monitor', 'Brand 01', 0), ('Laptop', 'Brand 01', 1),
    ])
    db.conn.executemany('INSERT INTO devices VALUES(?,?,?)', [('Laptop', 'Brand 02', 0)] * 11)
    page = BrandsPage(db)
    try:
        page.resize(1920, 1080)
        page.show()
        APP.processEvents()
        assert page.table.horizontalHeader().sectionResizeMode(2) == QHeaderView.ResizeMode.Stretch
        assert sum(page.table.columnWidth(column) for column in range(6)) >= page.table.viewport().width() - 2
        assert page._service_count('Laptop', 'Brand 01') == 2
        assert page._service_count('Monitor', 'Brand 01') == 1
        assert page._service_count('Laptop', 'Brand 03') == 0
        page.table.sortItems(3, Qt.SortOrder.DescendingOrder)
        assert page.table.item(0, 2).data(Qt.ItemDataRole.UserRole) == 'Brand 02'
        assert page.table.item(0, 3).text() == '11 Fi\u015f'
        page.inp_search.setText('Brand 01')
        assert page.table.rowCount() == 1
        assert page.table.item(0, 3).text() == '2 Fi\u015f'
        assert page.table.item(0, 4).text() == 'Aktif'
        assert page._export_rows() == [('Laptop', 'Brand 01', 2, 'Aktif')]
        assert '<td>2</td>' in page._html_document()
    finally:
        page.close()
        db.conn.close()
