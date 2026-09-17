import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QCoreApplication, QEvent, QPoint
from PyQt6.QtWidgets import QApplication, QCheckBox, QSpinBox, QWidget

from src.ui.pages.smart_home_sales_page import SmartHomeProductPoolDialog


APP = QApplication.instance() or QApplication([])


class _FakeSmartHomePage(QWidget):
    def __init__(self):
        super().__init__()
        self.filtered_products = []

    def _refresh_product_table(self, query=""):
        self.filtered_products = [
            {
                "id": index,
                "code": f"AE-{index:03d}",
                "name": f"Product {index}",
                "category": "Smart Home",
                "stock": 30,
                "price": 20.0 + index,
                "currency": "EUR",
            }
            for index in range(1, 13)
        ]

    def _append_product_to_offer(self, **kwargs):
        return None

    def _refresh_selected_table(self):
        return None

    def _update_offer_badge(self):
        return None


def test_product_pool_quantity_controls_stay_in_quantity_column_after_refresh():
    page = _FakeSmartHomePage()
    dialog = SmartHomeProductPoolDialog(page)
    dialog.show()

    try:
        for _ in range(6):
            dialog.refresh_table()

            assert dialog.tbl_products.rowCount() == len(page.filtered_products)
            visible_qty_spins = [
                spin
                for spin in dialog.tbl_products.findChildren(
                    QSpinBox,
                    "productPoolRowQty",
                )
                if spin.isVisible()
            ]
            assert len(visible_qty_spins) == len(page.filtered_products)
            for row_index in range(dialog.tbl_products.rowCount()):
                check_holder = dialog.tbl_products.cellWidget(row_index, 0)
                qty_holder = dialog.tbl_products.cellWidget(row_index, 8)
                assert check_holder is not None
                assert qty_holder is not None
                assert check_holder.findChild(QCheckBox, "productPoolRowCheck") is not None

                qty_spin = qty_holder.findChild(QSpinBox, "productPoolRowQty")
                assert qty_spin is not None
                viewport_position = qty_spin.mapTo(
                    dialog.tbl_products.viewport(),
                    QPoint(2, 2),
                )
                assert dialog.tbl_products.indexAt(viewport_position).column() == 8

            APP.processEvents()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
            APP.processEvents()
    finally:
        dialog.close()
        page.close()
