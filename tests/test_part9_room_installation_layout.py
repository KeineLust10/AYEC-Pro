import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication
from src.ui.pages.project_management.project_detail_components import UnitProductsDialog
from src.utils.reference_typography import apply_reference_font

APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)
apply_reference_font(APP)


class RoomInstallDatabaseStub:
    def __init__(self):
        self.products = [
            {"id": 20, "unit_id": 2, "part_name": "Ak\u0131ll\u0131 Dokunmatik Panel 10\" Pro", "part_code": "AES-101", "quantity": 1, "notes": "IP: 192.168.1.120; Port 8080; v2.4 Firmware", "status": "\u00c7evrimi\u00e7i"},
            {"id": 21, "unit_id": 2, "part_name": "4 Kanall\u0131 Dimmer Mod\u00fcl\u00fc (KNX/DALI)", "part_code": "AES-040", "quantity": 2, "notes": "Hat 1.1.20; Spot & Gizli I\u015f\u0131k Kanal\u0131", "status": "\u00c7evrimi\u00e7i"},
        ]
        self.parts = [{"id": 7, "name": "Ak\u0131ll\u0131 Ev Sistemleri \u00dcr\u00fcn 01", "code": "AES-001", "stock": 51}]
        self.note = "Kullan\u0131c\u0131 paneli Salon giri\u015f kap\u0131s\u0131 sa\u011f\u0131na 140cm montaj y\u00fcksekli\u011fi ile konumland\u0131r\u0131ld\u0131. KNX hatt\u0131 devrede."
        self.added = []

    def get_project_details(self, _project_id):
        return (5, "Demo Proje 01")

    def get_unit_products(self, unit_id):
        return [row for row in self.products if row["unit_id"] == unit_id]

    def get_parts_paginated(self, limit=300, search_query=""):
        return self.parts, len(self.parts)

    def get_unit_rooms(self, _unit_id):
        return [
            {"id": 2, "unit_no": "Salon"},
            {"id": 3, "unit_no": "Mutfak"},
            {"id": 4, "unit_no": "Koridor & Giri\u015f"},
            {"id": 5, "unit_no": "Ebeveyn Yatak Odas\u0131"},
        ]

    def get_project_unit(self, unit_id):
        return {"id": unit_id, "description": self.note}

    def update_project_unit_note(self, _unit_id, note):
        self.note = note
        return True

    def add_unit_product(self, payload):
        self.added.append(payload)
        return True

    def remove_unit_product(self, _entry_id):
        return True

    def update_unit_product_note(self, _entry_id, _note):
        return True


class Part9RoomInstallationLayoutTests(unittest.TestCase):
    def setUp(self):
        self.db = RoomInstallDatabaseStub()
        self.dialog = UnitProductsDialog(self.db, 5, {"id": 1, "unit_no": "A-1", "block_name": "A"})

    def tearDown(self):
        self.dialog.close()

    def test_reference_table_footer_and_room_targets(self):
        self.assertEqual(self.dialog.table_installed.columnCount(), 6)
        self.assertTrue(self.dialog.table_installed.verticalHeader().isHidden())
        self.assertIn("Daire: A-1", self.dialog.lbl_title.text())
        self.assertIn("Demo Proje 01", self.dialog.lbl_target_info.text())
        self.assertIn("Blok A", self.dialog.lbl_target_info.text())
        self.assertIn("Aktif Kurulum", self.dialog.lbl_install_status.text())
        self.assertIn("Teknik Not", self.dialog.table_installed.horizontalHeaderItem(3).text())
        self.assertEqual(self.dialog.cmb_target_room.count(), 5)
        self.dialog.cmb_target_room.setCurrentIndex(1)
        APP.processEvents()
        self.assertEqual(self.dialog.table_installed.rowCount(), 2)
        self.assertEqual(self.dialog.table_installed.rowHeight(0), 46)
        self.assertEqual(self.dialog.table_installed.item(0, 4).text(), "\u00c7evrimi\u00e7i")
        self.assertIn("Salon", self.dialog.cmb_target_room.currentText())
        self.assertEqual(self.dialog.footer_layout.count(), 6)
        self.assertEqual(self.dialog.txt_general_note.toPlainText(), self.db.note)
        self.assertIn("0 se\u00e7ili", self.dialog.lbl_stock_count.text())
        self.dialog.list_stock.item(0).setCheckState(Qt.CheckState.Checked)
        APP.processEvents()
        self.assertIn("1 se\u00e7ili", self.dialog.lbl_stock_count.text())
        font = QFont()
        font.setFamilies(["Segoe UI", "Arial"])
        self.dialog.setFont(font)
        self.dialog.show()
        APP.processEvents()
        self.dialog.setMaximumSize(1200, 720)
        self.dialog.resize(1200, 720)
        APP.processEvents()
        self.dialog.txt_general_note.setPlainText("Updated installation note")
        with patch("src.ui.pages.project_management.project_detail_components.show_success"):
            self.dialog.save_general_note()
        self.assertEqual(self.db.note, "Updated installation note")
        self.dialog.txt_general_note.setPlainText("Kullan\u0131c\u0131 paneli Salon giri\u015f kap\u0131s\u0131 sa\u011f\u0131na 140cm montaj y\u00fcksekli\u011fi ile konumland\u0131r\u0131ld\u0131. KNX hatt\u0131 devrede.")
        output = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "project-room-installation-desktop.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.dialog.grab().save(str(output), "PNG"))

    def test_selected_stock_is_added_to_active_room(self):
        self.dialog.list_stock.item(0).setCheckState(Qt.CheckState.Checked)
        self.dialog.add_selected_items()
        self.assertEqual(self.db.added[0]["part_id"], 7)
        self.assertEqual(self.db.added[0]["unit_id"], 1)


if __name__ == "__main__":
    unittest.main()
