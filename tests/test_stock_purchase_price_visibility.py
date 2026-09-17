import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from src.ui.pages._stock_list_tab import StockListTabMixin


app = QApplication.instance() or QApplication([])


class StockVisibilityHarness(StockListTabMixin):
    def __init__(self):
        self.current_page = 0
        self.page_limit = 50
        self.table_stock = QTableWidget(2, 3)
        self.table_stock.setHorizontalHeaderLabels(
            ["S.No", "Name", "Al\u0131\u015f \U0001f441"]
        )
        self._stock_column_map = {"purchase_price": 2}
        for row, (part_id, price) in enumerate(((101, 200.0), (202, 125.0))):
            number = QTableWidgetItem(str(row + 1))
            number.setData(Qt.ItemDataRole.UserRole, part_id)
            self.table_stock.setItem(row, 0, number)
            self.table_stock.setItem(row, 1, QTableWidgetItem(f"Part {part_id}"))
            purchase = QTableWidgetItem()
            purchase.setData(Qt.ItemDataRole.UserRole, price)
            self.table_stock.setItem(row, 2, purchase)
            self._update_purchase_price_cell(row)


def _purchase_texts(page):
    return [page.table_stock.item(row, 2).text() for row in range(2)]


def test_purchase_header_reveals_and_hides_every_row():
    page = StockVisibilityHarness()

    assert all(text.startswith("***") for text in _purchase_texts(page))

    page._on_stock_header_section_clicked(2)
    assert _purchase_texts(page)[0].startswith("200.00")
    assert _purchase_texts(page)[1].startswith("125.00")

    page._on_stock_cell_clicked_toggle_purchase_price(0, 2)
    assert _purchase_texts(page)[0].startswith("200.00")
    assert _purchase_texts(page)[1].startswith("125.00")

    app.processEvents()
    assert all(not text.startswith("***") for text in _purchase_texts(page))

    page._on_stock_header_section_clicked(2)
    assert all(text.startswith("***") for text in _purchase_texts(page))


def test_header_clears_mixed_row_visibility_and_sorting_keeps_part_state():
    page = StockVisibilityHarness()
    page._on_stock_cell_clicked_toggle_purchase_price(0, 2)
    assert _purchase_texts(page)[0].startswith("200.00")
    assert _purchase_texts(page)[1].startswith("***")

    page.table_stock.setSortingEnabled(True)
    page.table_stock.sortItems(1, Qt.SortOrder.DescendingOrder)
    page._refresh_all_purchase_price_cells()
    visible_by_id = {
        page._stock_part_id_from_row(row): page.table_stock.item(row, 2).text()
        for row in range(2)
    }
    assert visible_by_id[101].startswith("200.00")
    assert visible_by_id[202].startswith("***")

    page._on_stock_header_section_clicked(2)
    assert all(not text.startswith("***") for text in _purchase_texts(page))
    assert page._revealed_purchase_price_ids == set()
