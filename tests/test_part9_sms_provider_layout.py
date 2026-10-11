import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from src.ui.pages.settings_widgets.sms_settings import SMSSettingsWidget
from src.utils.reference_typography import apply_reference_font

APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)
apply_reference_font(APP)


class CursorStub:
    def execute(self, _query):
        return None

    def fetchall(self):
        return [("Repair update",), ("Approval request",)]

    def fetchone(self):
        return (4,)


class SmsSettingsDatabaseStub:
    def __init__(self):
        self.cursor = CursorStub()
        self.settings = {
            "sms_username": "provider-user",
            "sms_password": "secret-value",
            "sms_title": "AYECSERVIS",
            "sms_active": "1",
            "loop_repaired": "3",
            "loop_approval": "1",
            "loop_parts": "2",
            "loop_testing": "1",
            "loop_done": "0",
        }
        self.writes = []

    def get_setting(self, key, default=""):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value
        self.writes.append((key, value))


class Part9SmsProviderLayoutTests(unittest.TestCase):
    def setUp(self):
        self.db = SmsSettingsDatabaseStub()
        self.widget = SMSSettingsWidget(self.db)

    def tearDown(self):
        self.widget.close()

    def test_provider_fields_cycle_cards_metrics_and_full_width_capture(self):
        self.assertEqual(self.widget.inp_title.maxLength(), 11)
        self.assertEqual(len(self.widget._loop_template_widgets), 5)
        self.assertEqual(self.widget.metric_values[0].text(), "4")
        self.assertTrue(self.widget.btn_test_sms.isEnabled())
        font = QFont()
        font.setFamilies(["Segoe UI", "Arial"])
        self.widget.setFont(font)
        self.widget.resize(1440, 920)
        self.widget.show()
        APP.processEvents()
        output = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "sms-provider-desktop.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.widget.grab().save(str(output), "PNG"))

    def test_credentials_and_loop_settings_are_saved(self):
        self.widget.inp_user.setText("new-api-user")
        self.widget.inp_title.setText("aslanbilisim")
        self.widget.save_credentials()
        self.assertEqual(self.db.get_setting("sms_username"), "new-api-user")
        self.assertEqual(self.widget.inp_title.text(), "ASLANBILISI")
        self.widget.spn_repaired.setValue(5)
        self.widget._loop_active_widgets["repaired"].setChecked(False)
        self.widget.save_loops()
        self.assertEqual(self.db.get_setting("loop_repaired"), "5")
        self.assertEqual(self.db.get_setting("loop_active_repaired"), "0")


if __name__ == "__main__":
    unittest.main()
