import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication, QFrame, QLabel
from src.ui.pages.settings_widgets.sms_settings import SMSTemplatesWidget
from src.utils.reference_typography import apply_reference_font
from src.utils.theme_manager import ThemeManager

APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)
apply_reference_font(APP)


class TemplateCursorStub:
    def __init__(self):
        self.rows = [
            (1, "MANUEL BOR\u00c7 EKLEME", "Say\u0131n {musteri}; {tutar} TL bor\u00e7 sisteme i\u015flenmi\u015ftir. Kalan borcunuz: {bakiye} TL. Detay: {odeme_linki}"),
            (2, "RANDEVU \u0130PTAL SMS MUSTER\u0130YE", "Say\u0131n {musteri}; {randevu_araligi} tarihli teknik servis randevunuz talebiniz \u00fczerine iptal edilmi\u015ftir."),
            (3, "C\u0130HAZ KABUL B\u0130LD\u0130R\u0130M\u0130", "Say\u0131n {musteri}, {cihaz} cihaz\u0131n\u0131z {servis_no} takip numaras\u0131yla servisimize kabul edilmi\u015ftir. Durum takibi: {takip_linki}"),
            (4, "ONARIM TAMAMLANDI & HAZIR", "Say\u0131n {musteri}, {cihaz} onar\u0131m\u0131 tamamlanm\u0131\u015f olup teslim almaya haz\u0131rd\u0131r. Tutar: {tutar} TL."),
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
        self.assertEqual(self.widget.table.rowCount(), 10)
        self.assertEqual(self.widget.table.horizontalHeaderItem(0).text(), "NO")
        self.assertFalse(self.widget.table.horizontalHeader().isHidden())
        self.assertEqual(self.widget.table.horizontalHeader().height(), 28)
        self.assertEqual(
            self.widget.table.horizontalHeaderItem(0).foreground().color().name().lower(),
            ThemeManager.get_palette_color(ThemeManager._current_theme, "text_muted").lower(),
        )
        self.assertEqual(
            self.widget.table.item(0, 2).foreground().color().name().lower(),
            ThemeManager.get_palette_color(ThemeManager._current_theme, "text").lower(),
        )
        self.assertEqual(len(self.widget.token_buttons), 8)
        self.assertTrue(hasattr(self.widget, "btn_copy"))
        self.assertTrue(hasattr(self.widget, "btn_excel"))
        self.assertTrue(hasattr(self.widget, "btn_pdf"))
        self.widget.inp_search.setText("tamamlanm")
        APP.processEvents()
        self.assertEqual(self.widget.table.rowCount(), 1)
        self.widget.inp_search.clear()
        font = QFont()
        font.setFamilies(["Segoe UI", "Arial"])
        self.widget.setFont(font)
        self.widget.resize(1336, 970)
        self.widget.show()
        APP.processEvents()
        APP.processEvents()
        footer = self.widget.findChild(QFrame, "smsTemplateFooter")
        self.assertGreaterEqual(self.widget.table.height(), 700)
        self.assertGreaterEqual(self.widget.table.rowHeight(0), 60)
        self.assertLessEqual(self.widget.table.rowHeight(0), 72)
        self.assertLessEqual(self.widget.height() - footer.geometry().bottom(), 10)
        output = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "sms-templates-desktop.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        self.assertTrue(self.widget.grab().save(str(output), "PNG"))
        self.widget.resize(1590, 960)
        APP.processEvents()
        APP.processEvents()
        self.assertGreaterEqual(self.widget.table.rowHeight(0), 60)
        self.assertLessEqual(self.widget.table.rowHeight(0), 72)
        self.assertFalse(self.widget.table.verticalScrollBar().isVisible())
        full_form = output.with_name("sms-templates-full-form-1590x960.png")
        self.assertTrue(self.widget.grab().save(str(full_form), "PNG"))
        self.widget.resize(1076, 570)
        APP.processEvents()
        APP.processEvents()
        self.assertGreaterEqual(self.widget.table.rowHeight(0), 60)
        self.assertLessEqual(self.widget.table.rowHeight(0), 72)
        self.assertGreaterEqual(self.widget.table.height(), 316)
        reference_crop = output.with_name("sms-templates-content-reference.png")
        self.assertTrue(self.widget.grab().save(str(reference_crop), "PNG"))

    def test_default_scenarios_are_added_without_duplicates(self):
        self.widget.init_default_templates()
        self.assertEqual(len(self.db.cursor.rows), 10)
        names = [row[1] for row in self.db.cursor.rows]
        self.assertIn("RANDEVU ONAYLANDI", names)
        self.assertIn("ODEME ALINDI", names)

    def test_template_colors_follow_light_and_dark_themes(self):
        previous_theme = ThemeManager._current_theme
        self.widget.show()
        try:
            for theme_name in ("AYEC", "Koyu Mavi"):
                ThemeManager.apply_theme(APP, theme_name, animate=False)
                self.widget.apply_theme_styles()
                APP.processEvents()
                text_color = ThemeManager.get_palette_color(theme_name, "text").lower()
                accent_color = ThemeManager.get_palette_color(theme_name, "accent").lower()
                self.assertEqual(
                    self.widget.table.item(0, 2).foreground().color().name().lower(),
                    text_color,
                )
                self.assertIn(text_color, self.widget.table.cellWidget(0, 2).styleSheet().lower())
                trigger_badge = self.widget.table.cellWidget(0, 1).findChild(QLabel)
                self.assertIn(accent_color, trigger_badge.styleSheet().lower())
        finally:
            ThemeManager.apply_theme(APP, previous_theme, animate=False)
            self.widget.apply_theme_styles()
            APP.processEvents()

    def test_variable_tokens_copy_to_clipboard(self):
        self.widget.token_buttons[0].click()
        APP.processEvents()
        self.assertEqual(QApplication.clipboard().text(), "{musteri}")

    def test_hidden_table_presentation_keeps_export_values(self):
        content, trigger = self.widget._template_rows()[0]
        self.assertIn("{bakiye}", content)
        self.assertEqual(trigger, "MANUEL BOR\u00c7 EKLEME")


if __name__ == "__main__":
    unittest.main()
