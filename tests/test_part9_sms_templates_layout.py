import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication
from src.ui.pages.settings_widgets.sms_settings import SMSTemplatesWidget
from src.utils.reference_typography import apply_reference_font

APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)
apply_reference_font(APP)


class TemplateCursorStub:
    def __init__(self):
        self.rows = [
            (1, "MANUEL BORC EKLEME", "Say\u0131n {musteri}; {tutar} TL bor\u00e7 sistemine i\u015flenmi\u015ftir. Kalan borcunuz: {bakiye} TL. Detay: {odeme_linki}"),
            (2, "RANDEVU IPTAL SMS MUSTERIYE", "Say\u0131n {musteri}; {randevu_araligi} tarihli teknik servis randevunuz talebiniz \u00fczerine iptal edilmi\u015ftir."),
            (3, "CIHAZ KABUL BILDIRIMI", "Say\u0131n {musteri}; {cihaz} cihaz\u0131n\u0131z {servis_no} takip numaras\u0131yla servisimize kabul edilmi\u015ftir. Durum takibi: {takip_linki}"),
            (4, "ONARIM TAMAMLANDI & HAZIR", "Say\u0131n {musteri}; {cihaz} onar\u0131m\u0131n\u0131z tamamlanm\u0131\u015f olup teslim almaya haz\u0131rd\u0131r. Tutar: {tutar} TL."),
        ]
        self.result = None

    def execute(self, query, _params=()):
        self.result = [(len(self.rows),)] if "COUNT(*)" in query else list(self.rows)

    def fetchone(self):
        return self.result[0]

    def fetchall(self):
        return list(self.result)


class TemplateDatabaseStub:
    def __init__(self):
        self.cursor = TemplateCursorStub()
        self.conn = type("Connection", (), {"commit": lambda _self: None})()

    def add_template(self, name, content):
        self.cursor.rows.append((len(self.cursor.rows) + 1, name, content))

    def delete_template(self, template_id):
        self.cursor.rows = [row for row in self.cursor.rows if row[0] != template_id]


class Part9SmsTemplatesLayoutTests(unittest.TestCase):
    def setUp(self):
        self.db = TemplateDatabaseStub()
        self.widget = SMSTemplatesWidget(self.db)

    def tearDown(self):
        self.widget.close()

    def test_reference_toolbar_token_pool_table_and_capture(self):
        self.assertEqual(self.widget.table.columnCount(), 6)
        self.assertEqual(self.widget.table.rowCount(), 4)
        self.assertEqual(self.widget.table.item(0, 2).foreground().color().name(), "#dee2f6")
        self.assertEqual(len(self.widget.token_buttons), 8)
        self.assertTrue(hasattr(self.widget, "btn_copy"))
        self.assertTrue(hasattr(self.widget, "btn_excel"))
        self.assertTrue(hasattr(self.widget, "btn_pdf"))
        self.widget.inp_search.setText("onarim")
        APP.processEvents()
        self.assertEqual(self.widget.table.rowCount(), 1)
        self.widget.inp_search.clear()
        font = QFont()
        font.setFamilies(["Segoe UI", "Arial"])
        self.widget.setFont(font)
        self.widget.resize(1336, 970)
        self.widget.show()
        APP.processEvents()
        self.assertGreaterEqual(self.widget.table.height(), 500)
        output = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "sms-templates-desktop.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.widget.grab().save(str(output), "PNG"))

    def test_variable_tokens_copy_to_clipboard(self):
        self.widget.token_buttons[0].click()
        APP.processEvents()
        self.assertEqual(QApplication.clipboard().text(), "{musteri}")


if __name__ == "__main__":
    unittest.main()
