import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QWidget, QListWidget
from src.utils.appearance_mode import AppearanceModeManager
from src.ui.pages._dashboard_data_mixin import DashboardDataMixin
from src.ui.pages.service_list_page import ServiceListPage

APP = QApplication.instance() or QApplication([])


class Db:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE devices (id INTEGER PRIMARY KEY, tracking_no TEXT, status TEXT, is_deleted INTEGER DEFAULT 0, is_archived INTEGER DEFAULT 0)")
        self.cursor.executemany("INSERT INTO devices (tracking_no, status) VALUES (?, ?)", [("A", "Test Surecinde"), ("B", "Tamirde"), ("C", "Parca Bekliyor")])

    def get_setting(self, key, default=None):
        return default


class Dashboard(QWidget, DashboardDataMixin):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self._status_tiles = {key: {"count": QLabel("0", self)} for key in ("test", "tamirde", "parca", "bekliyor")}


def test_dashboard_filter_return_preserves_live_counts_and_real_zero():
    db = Db()
    dashboard = Dashboard(db)
    service = ServiceListPage(db)
    AppearanceModeManager.apply_to_widget_tree(dashboard, "modern")
    for mode in ("modern", "classic", "modern"):
        dashboard.update_dashboard_status_tiles()
        service.refresh_data()
        service.set_filter_category("test")
        assert len(service._filtered_records) == 1
        dashboard.update_dashboard_status_tiles()
        AppearanceModeManager.apply_to_widget_tree(dashboard, mode)
        assert {key: tile["count"].text() for key, tile in dashboard._status_tiles.items()} == {"test": "1", "tamirde": "1", "parca": "1", "bekliyor": "0"}
    db.cursor.execute("DELETE FROM devices")
    dashboard.update_dashboard_status_tiles()
    AppearanceModeManager.apply_to_widget_tree(dashboard, "modern")
    assert all(tile["count"].text() == "0" for tile in dashboard._status_tiles.values())
    dashboard.close()
    service.close()


def test_appearance_preserves_updated_button_and_list_text():
    root = QWidget()
    button = QPushButton("All (0)", root)
    items = QListWidget(root)
    items.addItem("Before")
    AppearanceModeManager.apply_to_widget_tree(root, "modern")
    button.setText("All (15)")
    items.item(0).setText("After")
    AppearanceModeManager.apply_to_widget_tree(root, "classic")
    AppearanceModeManager.apply_to_widget_tree(root, "modern")
    assert button.text() == "All (15)"
    assert items.item(0).text() == "After"
