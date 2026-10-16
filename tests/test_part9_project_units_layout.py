import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from src.ui.pages.project_management.project_detail_components import UnitsTab
from src.utils.reference_typography import apply_reference_font


APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)
apply_reference_font(APP)


class UnitsDatabaseStub:
    def __init__(self):
        statuses = ["Devam Ediyor", "Tamamland\u0131", "Bekliyor", "Devam Ediyor",
                    "Tamamland\u0131", "Devam Ediyor", "Bekliyor", "Devam Ediyor"]
        completion = [50, 100, 0, 35, 100, 45, 0, 60]
        directions = ["Guneydogu", "Kuzey", "Dogu", "Bati", "Guney", "Kuzey",
                      "Cati Dubleks", "Penthouse"]
        self.units = [
            {"id": unit_id, "project_id": 5, "block_name": "A Blok", "unit_no": f"A-{unit_id}",
             "floor_no": (unit_id + 1) // 2, "unit_kind": directions[unit_id - 1],
             "status": statuses[unit_id - 1], "completion_percent": completion[unit_id - 1],
             "responsible_name": ["Engin A.", "Murat K.", "Atanmadi", "Engin A.",
                                  "Kadir S.", "Engin A.", "Atanmadi", "Engin A."][unit_id - 1]}
            for unit_id in range(1, 9)
        ]

    def get_project_root_units(self, _project_id):
        return list(self.units)

    def get_unit_total_product_count(self, unit_id):
        return {1: 4, 2: 6, 4: 2, 5: 5, 6: 3, 8: 8}.get(unit_id, 0)

    def get_unit_rooms(self, unit_id):
        room_counts = {1: ["Salon", "Mutfak", "Hol"], 2: ["Tam Konfig."],
                       4: ["Salon", "Hol"], 5: ["Oda 1", "Oda 2", "Oda 3"],
                       6: ["Mutfak", "Salon"], 8: ["Teras", "Salon", "Oda"]}
        return [{"name": name} for name in room_counts.get(unit_id, [])]

    def set_unit_install_status(self, unit_id, status):
        for unit in self.units:
            if unit["id"] == unit_id:
                unit["status"] = status


class Part9ProjectUnitsLayoutTests(unittest.TestCase):
    def setUp(self):
        self.db = UnitsDatabaseStub()
        self.page = UnitsTab(self.db, 5)

    def tearDown(self):
        self.page.close()

    def test_reference_toolbar_status_filter_and_responsive_cards(self):
        self.assertTrue(hasattr(self.page, "btn_add_single"))
        self.assertTrue(hasattr(self.page, "btn_bulk_status"))
        self.assertEqual(self.page.grid.count(), 8)
        self.assertEqual(self.page.status_filter_buttons["all"].text(), "T\u00fcm\u00fc (8)")
        self.assertIn("Ortalama Tamamlanma %48.8", self.page.block_summary.text())
        self.assertEqual(self.page.block_progress.value(), 49)
        self.assertEqual(self.page.status_filter_buttons["active"].text(), "Devam Eden (4)")
        self.page.status_filter_buttons["completed"].click()
        APP.processEvents()
        self.assertEqual(self.page.grid.count(), 2)
        self.page.filter_status.setCurrentIndex(0)
        APP.processEvents()
        self.page.search_inp.setText("A-2")
        APP.processEvents()
        self.assertEqual(self.page.grid.count(), 1)
        self.assertEqual(self.page.block_summary.text().split("|")[1].strip(), "8 Ba\u011f\u0131ms\u0131z B\u00f6l\u00fcm")
        self.page.search_inp.clear()
        APP.processEvents()
        self.page.resize(1280, 800)
        screenshot_font = QFont()
        screenshot_font.setFamilies(["Segoe UI", "Arial"])
        screenshot_font.setPointSize(10)
        self.page.setFont(screenshot_font)
        self.page.show()
        APP.processEvents()
        positions = [self.page.grid.getItemPosition(index)[1] for index in range(self.page.grid.count())]
        self.assertEqual(max(positions), 3)
        output = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "project-units-desktop.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.page.grab().save(str(output), "PNG"))
        self.page.resize(1052, 690)
        APP.processEvents()
        positions = [self.page.grid.getItemPosition(index)[1] for index in range(self.page.grid.count())]
        self.assertEqual(max(positions), 3)
        reference_crop = output.with_name("project-inside-content-reference.png")
        self.assertTrue(self.page.grab().save(str(reference_crop), "PNG"))

    def test_compact_mode_uses_single_full_width_column(self):
        self.page.btn_view_mode.setChecked(True)
        APP.processEvents()
        positions = [self.page.grid.getItemPosition(index)[1] for index in range(self.page.grid.count())]
        self.assertTrue(all(column == 0 for column in positions))

    def test_wide_screen_uses_four_card_columns(self):
        self.page.resize(1280, 800)
        self.page.show()
        APP.processEvents()
        positions = [self.page.grid.getItemPosition(index)[1] for index in range(self.page.grid.count())]
        self.assertEqual(max(positions), 3)


if __name__ == "__main__":
    unittest.main()
