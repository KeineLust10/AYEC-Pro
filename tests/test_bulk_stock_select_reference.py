import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QPushButton

from src.database import Database
from src.ui.dialogs.bulk_stock_select_dialog import BulkStockSelectDialog


def test_bulk_selection_controls_keep_selection_quantity_and_filter_state(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "bulk_select.db"))
    db.conn.execute(
        "INSERT INTO exchange_rates(currency,buying_rate,selling_rate,effective_date,created_at) "
        "VALUES (?,?,?,?,?)",
        ("USD", 44.0, 44.0, "2026-10-12", "2026-10-12"),
    )
    db.conn.commit()
    parts = {
        "Router One": {
            "id": "router-1",
            "name": "Router One",
            "category": "Network",
            "stock": 12,
            "price": 20,
            "currency": "TRY",
        },
        "Router Two": {
            "id": "router-2",
            "name": "Router Two",
            "category": "Network",
            "stock": 8,
            "price": 30,
            "currency": "TRY",
        },
    }
    dialog = BulkStockSelectDialog(None, db, {}, parts)
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        assert dialog.tree.topLevelItemCount() == 2
        first = dialog.tree.topLevelItem(0)
        checkbox_cell = dialog.tree.itemWidget(first, 0)
        checkbox = checkbox_cell.findChild(QPushButton)
        checkbox.click()
        quantity = dialog.tree.itemWidget(first, 5)
        quantity.setValue(3)

        dialog._populate()
        selected = dialog.get_selected_items()
        assert len(selected) == 1
        assert selected[0]["id"] == "router-1"
        assert selected[0]["qty"] == 3

        dialog._toggle_visible_rows(Qt.CheckState.Checked.value)
        assert {item["id"] for item in dialog.get_selected_items()} == {"router-1", "router-2"}
        dialog.search_input.setText("Router Two")
        app.processEvents()
        assert dialog.tree.topLevelItem(0).isHidden()
        assert not dialog.tree.topLevelItem(1).isHidden()
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
