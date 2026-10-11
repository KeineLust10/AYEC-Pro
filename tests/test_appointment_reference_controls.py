import os
import sys
import unittest
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

from src.database import Database
from src.ui.pages.appointments_page import AppointmentsPage, CalendarCard
from src.utils.design_system import DesignTokens


APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)


class NavigationStub:
    def __init__(self):
        self.visited_pages = []

    def switch_page(self, page_id):
        self.visited_pages.append(page_id)


class AppointmentReferenceControlTests(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.db.conn.execute(
            "INSERT INTO personnel (name, role, active) VALUES (?, ?, 1)",
            ("Tech One", "Field Technician"),
        )
        self.location_id = self.db.create_stock_location("Main Warehouse")
        self.navigation = NavigationStub()
        self.page = AppointmentsPage(self.db, self.navigation)

    def tearDown(self):
        self.page.close()
        self.db.close()

    def test_personnel_and_location_filters_update_calendar_state(self):
        self.page.calendar_personnel_combo.setCurrentIndex(1)
        location_index = self.page.calendar_location_combo.findData(self.location_id)
        self.page.calendar_location_combo.setCurrentIndex(location_index)

        self.assertEqual(self.page.calendar_personnel_filter, "Tech One")
        self.assertEqual(self.page.calendar_location_filter, self.location_id)

    def test_map_action_navigates_to_field_service(self):
        self.page.btn_open_field_service_map.click()

        self.assertEqual(self.navigation.visited_pages, [61])

    def test_calendar_density_fonts_and_literal_card_identity(self):
        self.page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.page.resize(928, 988)
        self.page.show()
        APP.processEvents()
        for button in self.page.calendar_view_buttons:
            self.assertGreaterEqual(button.width(), button.fontMetrics().horizontalAdvance(button.text()) + 18)
            self.assertTrue(self.page.rect().contains(button.mapTo(self.page, button.rect().bottomRight())))
        self.assertFalse(self.page.table.alternatingRowColors())
        self.assertEqual(self.page.table.columnCount(), 8)
        for row in range(self.page.table.rowCount()):
            self.assertEqual(self.page.table.item(row, 0).font().family(), DesignTokens.MONO_FONT_NAME)
        record = {'id': 73, 'customer_name': '<Customer>', 'description': '<Service>', 'time': '10:30',
                  'personnel_name': 'Tech One'}
        card = CalendarCard(record)
        card.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        calls = []
        card.clicked.connect(calls.append)
        try:
            card.resize(160, 104)
            card.show()
            APP.processEvents()
            labels = card.findChildren(QLabel)
            self.assertEqual(labels[0].text(), '<Customer>')
            self.assertEqual(labels[1].text(), '10:30  <Service>')
            self.assertEqual(labels[2].text(), 'Tech One')
            self.assertEqual(labels[2].toolTip(), 'Tech One')
            self.assertTrue(all(label.textFormat() == Qt.TextFormat.PlainText for label in labels))
            self.assertTrue(all(label.font().family() == DesignTokens.FONT_NAME for label in labels))
            QTest.mouseDClick(card, Qt.MouseButton.LeftButton)
            self.assertEqual(calls, [73])
            self.assertEqual(card.data, record)
            self.assertFalse(card.grab().isNull())
            card.resize(70, 104)
            APP.processEvents()
            for label in labels:
                self.assertTrue(card.rect().contains(label.geometry()))
                self.assertGreaterEqual(label.height(), label.fontMetrics().height())
                self.assertFalse(label.wordWrap())
                self.assertEqual(label.toolTip(), label.text())
        finally:
            card.close()

    def test_week_metrics_use_actual_filtered_records_and_no_capacity_assumption(self):
        today = date.today().isoformat()
        for name, status, urgency in (
            ('Tech One', 'Tamamlandi', 'Acil'),
            ('Tech One', 'Bekliyor', 'Normal'),
            ('Tech Two', 'Tamamlandi', 'Kritik'),
        ):
            self.db.conn.execute(
                'INSERT INTO appointments (customer_name, date, time, description, status, urgency, personnel_name) '
                'VALUES (?, ?, ?, ?, ?, ?, ?)',
                ('Client', today, '10:00', 'Service', status, urgency, name),
            )
        self.db.conn.commit()
        before = self.db.conn.total_changes
        self.page.refresh_calendar()
        self.assertEqual([label.text() for label in self.page.appointment_kpi_values],
                         ['3 Randevu', '2 G\u00f6revli', '%67', '2 Servis'])
        self.page.calendar_personnel_filter = 'Tech One'
        self.page.refresh_calendar()
        self.assertEqual([label.text() for label in self.page.appointment_kpi_values],
                         ['2 Randevu', '1 G\u00f6revli', '%50', '1 Servis'])
        self.page.calendar_personnel_filter = 'Missing Tech'
        self.page.refresh_calendar()
        self.assertEqual([label.text() for label in self.page.appointment_kpi_values],
                         ['0 Randevu', '0 G\u00f6revli', '%0', '0 Servis'])
        self.assertEqual(self.db.conn.total_changes, before)

    def test_today_card_exposes_reference_departure_and_detail_actions(self):
        today = date.today().strftime("%Y-%m-%d")
        self.db.conn.execute(
            "INSERT INTO appointments "
            "(customer_name, phone, personnel_name, date, time, description, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("Client One", "", "Tech One", today, "10:00", "On-site service", "Bekliyor"),
        )
        self.db.conn.execute(
            "INSERT INTO appointment_plan_items "
            "(appointment_id, name, source_location_id, created_at, updated_at) "
            "VALUES (1, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            ("On-site service", self.location_id),
        )
        self.db.conn.commit()
        opened = []
        self.page.open_edit_dialog = lambda appointment_id: opened.append(appointment_id)

        self.page.refresh_side_panel()
        buttons = self.page.side_panel.findChildren(QPushButton)
        departure = next(button for button in buttons if button.text() == "Yola \u00c7\u0131k\u0131ld\u0131")
        details = next(button for button in buttons if button.text() == "Detay G\u00f6r")
        labels = [label.text() for label in self.page.side_panel.findChildren(QLabel)]

        self.assertIn("1 Randevu", labels)
        self.assertTrue(any("Main Warehouse" in label for label in labels))
        self.assertTrue(any("Tech One" in label for label in labels))

        details.click()
        departure.click()

        self.assertEqual(opened, [1])
        status = self.db.conn.execute(
            "SELECT status FROM appointments WHERE id=1"
        ).fetchone()[0]
        self.assertEqual(status, "Gidildi")


if __name__ == "__main__":
    unittest.main()
