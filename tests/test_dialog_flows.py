# -*- coding: utf-8 -*-

import os
import sqlite3
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts"))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtCore import QCoreApplication, qInstallMessageHandler
from PyQt6.QtWidgets import QApplication

from src.ui.dialogs.add_customer_dialog import AddCustomerDialog
from src.ui.dialogs.new_service_dialog import NewServiceDialog


app = QApplication.instance() or QApplication(sys.argv)
app.setQuitOnLastWindowClosed(False)


def _qt_test_message_filter(_msg_type, _context, message):
    ignored_tokens = (
        "Could not parse stylesheet",
        "QFontDatabase: Cannot find font directory",
        "QObject::stopTimer()",
        "QThreadStorage: entry",
    )
    if any(token in message for token in ignored_tokens):
        return
    sys.stderr.write(message + "\n")


qInstallMessageHandler(_qt_test_message_filter)


def _cleanup_qt_app():
    qt_app = QApplication.instance()
    if qt_app is None:
        return
    try:
        qt_app.closeAllWindows()
        QCoreApplication.sendPostedEvents(None, 0)
        qt_app.processEvents()
        qt_app.quit()
        qt_app.processEvents()
    except Exception:
        return


def tearDownModule():
    _cleanup_qt_app()


class DialogTestDb:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                phone TEXT,
                email TEXT,
                type TEXT,
                tax_id TEXT,
                address TEXT,
                created_at TEXT,
                tax_office TEXT,
                district TEXT,
                city TEXT,
                neighborhood TEXT,
                notes TEXT,
                term_days INTEGER,
                limit_amount REAL,
                sms_enabled INTEGER,
                is_problematic INTEGER,
                phone2 TEXT,
                zip_code TEXT,
                tc_no TEXT,
                company_name TEXT,
                street TEXT,
                service_type TEXT,
                commission_rate REAL
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                customer_name TEXT,
                device_brand TEXT,
                device_model TEXT,
                serial_no TEXT,
                fault_description TEXT,
                urgency TEXT,
                technician TEXT,
                internal_notes TEXT,
                repair_details TEXT,
                accessories TEXT,
                pattern_lock TEXT,
                device_type TEXT,
                photo_path TEXT,
                photo_paths TEXT,
                device_password TEXT,
                status TEXT,
                approval_status TEXT,
                entry_date TEXT
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                photo_path TEXT,
                label TEXT,
                stage TEXT
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE device_brands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_type TEXT,
                brand TEXT,
                is_active INTEGER
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                is_active INTEGER
            )
            """
        )
        self.cursor.executemany(
            "INSERT INTO device_brands (device_type, brand, is_active) VALUES (?, ?, 1)",
            [
                ("Telefon", "Apple"),
                ("Telefon", "Samsung"),
                ("Laptop", "Dell"),
            ],
        )
        self.cursor.executemany(
            "INSERT INTO personnel (name, is_active) VALUES (?, 1)",
            [("Teknisyen 1",), ("Teknisyen 2",)],
        )
        self.conn.commit()
        self.reject_add_customer = False
        self.reject_add_device = False
        self.next_service_number = 1000

    def get_setting(self, key, default=""):
        return default

    def add_customer(self, data):
        if self.reject_add_customer:
            return False
        columns = list(data.keys())
        placeholders = ", ".join(["?"] * len(columns))
        self.cursor.execute(
            f"INSERT INTO customers ({', '.join(columns)}) VALUES ({placeholders})",
            [data[column] for column in columns],
        )
        self.conn.commit()
        return True

    def get_customers(self):
        rows = self.cursor.execute("SELECT id, name FROM customers ORDER BY id").fetchall()
        return [(row["id"], row["name"]) for row in rows]

    def get_all_personnel(self):
        rows = self.cursor.execute("SELECT id, name FROM personnel WHERE is_active=1 ORDER BY id").fetchall()
        return [(row["id"], row["name"]) for row in rows]

    def get_fast_notes(self, category):
        if category == "Aksesuar":
            return [
                (1, category, "SIM Kart", 1),
                (2, category, "Şarj Aleti", 1),
            ]
        if category == "Arıza Notu":
            return [
                (1, category, "EKRAN KIRIK", 1),
                (2, category, "ŞARJ ALMIYOR", 1),
            ]
        return []

    def get_quick_notes(self, key):
        return []

    def get_next_service_number(self):
        self.next_service_number += 1
        return f"SRV{self.next_service_number}"

    def add_device(self, data):
        if self.reject_add_device:
            return False
        columns = list(data.keys())
        placeholders = ", ".join(["?"] * len(columns))
        self.cursor.execute(
            f"INSERT INTO devices ({', '.join(columns)}) VALUES ({placeholders})",
            [data[column] for column in columns],
        )
        self.conn.commit()
        return True

    def add_photo(self, tracking_no, path, label, stage):
        self.cursor.execute(
            "INSERT INTO photos (tracking_no, photo_path, label, stage) VALUES (?, ?, ?, ?)",
            (tracking_no, path, label, stage),
        )
        self.conn.commit()

    def insert_customer(self, **overrides):
        data = {
            "name": "Test User",
            "phone": "05550001122",
            "email": "",
            "type": "Bireysel",
            "tax_id": "",
            "address": "Adres",
            "created_at": "2026-03-11 10:00:00",
            "tax_office": "",
            "district": "Gönen",
            "city": "Balıkesir",
            "neighborhood": "Akçaali",
            "notes": "",
            "term_days": 0,
            "limit_amount": 0.0,
            "sms_enabled": 1,
            "is_problematic": 0,
            "phone2": "",
            "zip_code": "",
            "tc_no": "",
            "company_name": "",
            "street": "Cumhuriyet Caddesi",
            "service_type": "Genel",
            "commission_rate": 0.0,
        }
        data.update(overrides)
        self.add_customer(data)
        return self.cursor.execute("SELECT * FROM customers ORDER BY id DESC LIMIT 1").fetchone()

    def insert_device(self, **overrides):
        data = {
            "tracking_no": "SRV9999",
            "customer_name": "Test User",
            "device_brand": "Apple",
            "device_model": "iPhone",
            "serial_no": "12345",
            "fault_description": "EKRAN KIRIK",
            "urgency": "Normal",
            "technician": "Teknisyen 1",
            "internal_notes": "",
            "repair_details": "",
            "accessories": "SIM Kart",
            "pattern_lock": "1,2,3",
            "device_type": "Telefon",
            "photo_path": "",
            "photo_paths": "",
            "device_password": "0000",
            "status": "Bekliyor",
            "approval_status": "Bekleme",
            "entry_date": "2026-03-11",
        }
        data.update(overrides)
        self.add_device(data)
        return self.cursor.execute("SELECT * FROM devices ORDER BY id DESC LIMIT 1").fetchone()


class ComboStub:
    def __init__(self):
        self.current_text = ""

    def setCurrentText(self, text):
        self.current_text = text

    def currentText(self):
        return self.current_text


class TextValueStub:
    def __init__(self, value=""):
        self.value = value

    def text(self):
        return self.value

    def toPlainText(self):
        return self.value


class PatternLockStub:
    def __init__(self, value=""):
        self.value = value

    def get_pattern_string(self):
        return self.value


class TestDialogFlows(unittest.TestCase):
    def setUp(self):
        self.db = DialogTestDb()
        self._dialogs = []

    def tearDown(self):
        for dialog in self._dialogs:
            try:
                dialog.close()
                dialog.deleteLater()
            except Exception:
                pass
        app.processEvents()
        self.db.conn.close()

    def track_dialog(self, dialog):
        self._dialogs.append(dialog)
        return dialog

    def create_service_dialog(self, device_data=None):
        if not self.db.get_customers():
            self.db.insert_customer(name="Servis Müşterisi")
        dialog = NewServiceDialog(self.db, device_data=device_data)
        app.processEvents()
        return self.track_dialog(dialog)

    def test_add_customer_dialog_failed_create_stays_open(self):
        dialog = self.track_dialog(AddCustomerDialog(self.db))
        self.db.reject_add_customer = True
        dialog.inp_name.setText("Başarısız Test")

        with patch("src.ui.dialogs.add_customer_dialog.show_error") as show_error:
            dialog.save()

        self.assertFalse(dialog.result())
        self.assertIsNone(dialog.saved_customer_id)
        show_error.assert_called_once()

    def test_add_customer_dialog_success_create_saves_customer_identity(self):
        dialog = self.track_dialog(AddCustomerDialog(self.db))
        dialog.inp_name.setText("Yeni Müşteri")

        with patch("src.ui.dialogs.add_customer_dialog.show_success"), patch(
            "src.ui.dialogs.add_customer_dialog.show_error"
        ):
            dialog.save()

        saved_row = self.db.cursor.execute(
            "SELECT id, name FROM customers ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertTrue(dialog.result())
        self.assertEqual(dialog.saved_customer_id, saved_row["id"])
        self.assertEqual(dialog.saved_customer_name, "Yeni Müşteri")

    def test_add_customer_dialog_success_update_persists_changes(self):
        row = self.db.insert_customer(name="Eski İsim", phone="05550001122")
        dialog = self.track_dialog(AddCustomerDialog(self.db, customer_data=row))
        app.processEvents()
        dialog.inp_name.setText("Yeni İsim")
        dialog.inp_phone.setText("05559998877")

        with patch("src.ui.dialogs.add_customer_dialog.show_info"), patch(
            "src.ui.dialogs.add_customer_dialog.show_error"
        ):
            dialog.save()

        updated = self.db.cursor.execute(
            "SELECT name, phone FROM customers WHERE id=?", (row["id"],)
        ).fetchone()
        self.assertTrue(dialog.result())
        self.assertEqual(dialog.saved_customer_id, row["id"])
        self.assertEqual(dialog.saved_customer_name, "Yeni İsim")
        self.assertEqual(updated["name"], "Yeni İsim")
        self.assertEqual(updated["phone"], "05559998877")

    def test_add_customer_dialog_load_preserves_neighborhood(self):
        row = self.db.insert_customer(
            name="Mahalle Test",
            city="Balıkesir",
            district="Gönen",
            neighborhood="Akçaali",
        )

        dialog = self.track_dialog(AddCustomerDialog(self.db, customer_data=row))
        app.processEvents()

        self.assertEqual(dialog.cmb_city.currentText(), "Balıkesir")
        self.assertEqual(dialog.cmb_district.currentText(), "Gönen")
        self.assertEqual(dialog.cmb_neighborhood.currentText(), "Akçaali")

    def test_add_customer_dialog_invalid_phone_blocks_save(self):
        dialog = self.track_dialog(AddCustomerDialog(self.db))
        dialog.inp_name.setText("Telefon Test")
        dialog.inp_phone.setText("123")

        with patch("src.ui.dialogs.add_customer_dialog.show_error") as show_error:
            dialog.save()

        count = self.db.cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        self.assertEqual(count, 0)
        self.assertFalse(dialog.result())
        show_error.assert_called_once()

    def test_add_customer_dialog_invalid_email_blocks_save(self):
        dialog = self.track_dialog(AddCustomerDialog(self.db))
        dialog.inp_name.setText("Mail Test")
        dialog.inp_email.setText("invalid-mail")

        with patch("src.ui.dialogs.add_customer_dialog.show_error") as show_error:
            dialog.save()

        count = self.db.cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        self.assertEqual(count, 0)
        self.assertFalse(dialog.result())
        show_error.assert_called_once()

    def test_add_customer_dialog_address_handlers_refresh_inputs(self):
        dialog = self.track_dialog(AddCustomerDialog(self.db))
        dialog.city_changed("İstanbul")

        district_items = [dialog.cmb_district.itemText(i) for i in range(dialog.cmb_district.count())]
        self.assertEqual(district_items, ["Merkez", "Diğer"])

        dialog.city_changed("Balıkesir")
        dialog.district_changed("Gönen")

        neighborhood_items = [
            dialog.cmb_neighborhood.itemText(i) for i in range(dialog.cmb_neighborhood.count())
        ]
        self.assertGreater(len(neighborhood_items), 0)
        self.assertIn("Akçaköy", neighborhood_items)

    def test_add_customer_dialog_customer_type_toggles_field_states(self):
        dialog = self.track_dialog(AddCustomerDialog(self.db))

        dialog.rb_corporate.setChecked(True)
        app.processEvents()
        self.assertTrue(dialog.inp_company.isEnabled())
        self.assertTrue(dialog.inp_tax_no.isEnabled())
        self.assertTrue(dialog.inp_tax_office.isEnabled())
        self.assertFalse(dialog.inp_tc.isEnabled())

        dialog.rb_individual.setChecked(True)
        app.processEvents()
        self.assertFalse(dialog.inp_company.isEnabled())
        self.assertFalse(dialog.inp_tax_no.isEnabled())
        self.assertFalse(dialog.inp_tax_office.isEnabled())
        self.assertTrue(dialog.inp_tc.isEnabled())

    def test_add_customer_dialog_status_checkboxes_update_tooltips(self):
        dialog = self.track_dialog(AddCustomerDialog(self.db))

        dialog.chk_sms.setChecked(False)
        dialog.chk_problem.setChecked(True)
        app.processEvents()

        self.assertIn("kapal", dialog.chk_sms.toolTip().lower())
        self.assertIn("sorunlu", dialog.chk_problem.toolTip().lower())

    def test_new_service_dialog_quick_add_customer_selects_saved_customer(self):
        fake_dialog_class_calls = []

        class FakeAddCustomerDialog:
            def __init__(self, db, parent=None):
                fake_dialog_class_calls.append((db, parent))
                self.saved_customer_name = "Seçilen Müşteri"

            def exec(self):
                return True

        fake_self = type("FakeServiceDialog", (), {})()
        fake_self.db = self.db
        fake_self.cmb_customer = ComboStub()
        fake_self.load_customers_called = 0

        def load_customers():
            fake_self.load_customers_called += 1

        fake_self.load_customers = load_customers

        with patch(
            "src.ui.dialogs.add_customer_dialog.AddCustomerDialog",
            FakeAddCustomerDialog,
        ):
            NewServiceDialog.quick_add_customer(fake_self)

        self.assertEqual(len(fake_dialog_class_calls), 1)
        self.assertEqual(fake_self.load_customers_called, 1)
        self.assertEqual(fake_self.cmb_customer.current_text, "Seçilen Müşteri")

    def test_new_service_dialog_quick_add_customer_cancel_does_not_reload(self):
        class FakeAddCustomerDialog:
            def __init__(self, db, parent=None):
                self.saved_customer_name = "Seçilmemeli"

            def exec(self):
                return False

        fake_self = type("FakeServiceDialog", (), {})()
        fake_self.db = self.db
        fake_self.cmb_customer = ComboStub()
        fake_self.load_customers_called = 0

        def load_customers():
            fake_self.load_customers_called += 1

        fake_self.load_customers = load_customers

        with patch(
            "src.ui.dialogs.add_customer_dialog.AddCustomerDialog",
            FakeAddCustomerDialog,
        ):
            NewServiceDialog.quick_add_customer(fake_self)

        self.assertEqual(fake_self.load_customers_called, 0)
        self.assertEqual(fake_self.cmb_customer.current_text, "")

    def test_new_service_dialog_validation_blocks_missing_customer(self):
        dialog = self.create_service_dialog()
        dialog.cmb_customer.clear()
        dialog.cmb_brand.setCurrentText("Apple")
        dialog.txt_fault.setText("Arıza var")

        with patch("src.ui.dialogs.new_service_dialog.ToastManager.error") as toast_error:
            result = dialog.validate_form()

        self.assertFalse(result)
        toast_error.assert_called_once()

    def test_new_service_dialog_validation_blocks_missing_brand(self):
        dialog = self.create_service_dialog()
        dialog.cmb_customer.setCurrentText("Servis Müşterisi")
        dialog.cmb_brand.setCurrentText("")
        dialog.txt_fault.setText("Arıza var")

        with patch("src.ui.dialogs.new_service_dialog.ToastManager.error") as toast_error:
            result = dialog.validate_form()

        self.assertFalse(result)
        toast_error.assert_called_once()

    def test_new_service_dialog_validation_blocks_missing_fault_description(self):
        dialog = self.create_service_dialog()
        dialog.cmb_customer.setCurrentText("Servis Müşterisi")
        dialog.cmb_brand.setCurrentText("Apple")
        dialog.txt_fault.setText("")

        with patch("src.ui.dialogs.new_service_dialog.ToastManager.error") as toast_error:
            result = dialog.validate_form()

        self.assertFalse(result)
        toast_error.assert_called_once()

    def test_new_service_dialog_success_create_persists_record(self):
        dialog = self.create_service_dialog()
        dialog.cmb_customer.setCurrentText("Servis Müşterisi")
        dialog.cmb_brand.setCurrentText("Apple")
        dialog.cmb_device.setCurrentText("Telefon")
        dialog.inp_model.setText("iPhone 15")
        dialog.inp_serial.setText("IMEI123")
        dialog.cmb_personnel.setCurrentText("Teknisyen 1")
        dialog.txt_fault.setText("Ekran kırık")
        dialog.txt_public_note.setText("Müşteri notu")
        dialog.txt_tech_note.setText("Teknik not")
        if "SIM Kart" in dialog.accessory_checkboxes:
            dialog.accessory_checkboxes["SIM Kart"].setChecked(True)
        if "Şarj Aleti" in dialog.accessory_checkboxes:
            dialog.accessory_checkboxes["Şarj Aleti"].setChecked(True)

        with patch("src.ui.dialogs.new_service_dialog.ToastManager.error"), patch.object(
            dialog, "_refresh_customer_list_if_loaded"
        ) as refresh_mock:
            dialog.save()

        saved = self.db.cursor.execute(
            "SELECT * FROM devices ORDER BY id DESC LIMIT 1"
        ).fetchone()
        self.assertTrue(dialog.result())
        self.assertEqual(saved["customer_name"], "Servis Müşterisi")
        self.assertEqual(saved["device_brand"], "Apple")
        self.assertEqual(saved["device_model"], "iPhone 15")
        self.assertIn("Ekran kırık", saved["fault_description"])
        self.assertIn("[NOT]: Müşteri notu", saved["fault_description"])
        self.assertIn("[TEKNİK]: Teknik not", saved["fault_description"])
        self.assertIn("SIM Kart", saved["accessories"])
        self.assertIn("Şarj Aleti", saved["accessories"])
        refresh_mock.assert_called_once()

    def test_new_service_dialog_failed_create_stays_open(self):
        dialog = self.create_service_dialog()
        self.db.reject_add_device = True
        dialog.cmb_customer.setCurrentText("Servis Müşterisi")
        dialog.cmb_brand.setCurrentText("Apple")
        dialog.txt_fault.setText("Arıza var")

        with patch("src.ui.dialogs.new_service_dialog.ToastManager.error") as toast_error:
            dialog.save()

        self.assertFalse(dialog.result())
        toast_error.assert_called_once()

    def test_new_service_dialog_success_update_persists_changes(self):
        self.db.insert_customer(name="Servis Müşterisi")
        existing = self.db.insert_device(customer_name="Servis Müşterisi", device_model="Eski Model")
        fake_self = type("FakeServiceDialogUpdate", (), {})()
        fake_self.db = self.db
        fake_self.device_data = (existing["id"], existing["tracking_no"])
        fake_self.photo_path = ""
        fake_self.photo_paths = []
        fake_self.validate_form = lambda: True
        fake_self._device_columns = lambda: {"photo_paths"}
        fake_self._compose_fault_description = lambda: "Şarj olmuyor"
        fake_self._sync_photos_table = lambda tracking_no: None
        fake_self._refresh_customer_list_if_loaded = lambda: None
        fake_self.accept_called = False
        fake_self.accept = lambda: setattr(fake_self, "accept_called", True)
        fake_self.cmb_customer = ComboStub()
        fake_self.cmb_customer.setCurrentText("Servis Müşterisi")
        fake_self.cmb_brand = ComboStub()
        fake_self.cmb_brand.setCurrentText("Samsung")
        fake_self.cmb_device = ComboStub()
        fake_self.cmb_device.setCurrentText("Telefon")
        fake_self.cmb_urgency = ComboStub()
        fake_self.cmb_urgency.setCurrentText("Normal")
        fake_self.cmb_personnel = ComboStub()
        fake_self.cmb_personnel.setCurrentText("Teknisyen 1")
        fake_self.inp_model = TextValueStub("Yeni Model")
        fake_self.inp_serial = TextValueStub("NEW123")
        fake_self.inp_password = TextValueStub("9999")
        fake_self.txt_public_note = TextValueStub("Güncel not")
        fake_self.txt_tech_note = TextValueStub("")
        fake_self.pattern_lock = PatternLockStub("")
        fake_self._collect_selected_accessories = lambda: "SIM Kart"

        with patch("src.ui.dialogs.new_service_dialog.ToastManager.success") as toast_success, patch(
            "src.ui.dialogs.new_service_dialog.ToastManager.error"
        ):
            NewServiceDialog.save(fake_self)

        updated = self.db.cursor.execute(
            "SELECT * FROM devices WHERE id=?", (existing["id"],)
        ).fetchone()
        self.assertTrue(fake_self.accept_called)
        self.assertEqual(updated["device_brand"], "Samsung")
        self.assertEqual(updated["device_model"], "Yeni Model")
        self.assertEqual(updated["serial_no"], "NEW123")
        self.assertEqual(updated["device_password"], "9999")
        self.assertIn("Şarj olmuyor", updated["fault_description"])
        self.assertIn("[NOT]: Güncel not", updated["fault_description"])
        toast_success.assert_called_once()


if __name__ == "__main__":
    unittest.main()
