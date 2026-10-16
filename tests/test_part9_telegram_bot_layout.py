import json
import os
import subprocess
import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtGui import QFont, QGuiApplication
from PyQt6.QtWidgets import QApplication, QLineEdit, QMessageBox
from src.ui.pages.settings_widgets.telegram_settings import TelegramSettingsWidget
from src.utils.reference_typography import apply_reference_font

APP = QApplication.instance() or QApplication(sys.argv)
APP.setQuitOnLastWindowClosed(False)
apply_reference_font(APP)


class TelegramDatabaseStub:
    def __init__(self):
        self.settings = {"telegram_bot_token": "token-value", "telegram_chat_ids": '["893412781", "561298834"]'}
        self.writes = []

    def get_setting(self, key, default=""):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value
        self.writes.append((key, value))


class Part9TelegramLayoutTests(unittest.TestCase):
    def setUp(self):
        self.db = TelegramDatabaseStub()
        self.widget = TelegramSettingsWidget(self.db)

    def tearDown(self):
        self.widget.close()

    def test_reference_controls_and_full_width_capture(self):
        self.assertEqual(self.widget.chat_list.count(), 2)
        self.assertEqual(len(self.widget.preferences), 4)
        self.assertEqual(list(self.widget.settings_tab_buttons), [1, 3, 2, 16])
        self.assertEqual(self.widget.inp_token.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(self.widget.findChild(type(self.widget.bot_card_status), "telegramMessageId").text(), "#SRV-2025-9921")
        self.assertIn("SERV", self.widget.findChild(type(self.widget.bot_card_status), "telegramMessageState").text())
        self.assertIn("henuz test edilmedi", self.widget.bot_card_status.text())
        self.assertTrue(self.widget.btn_copy_token.isEnabled())
        self.assertTrue(self.widget.btn_reset_webhook.isEnabled())
        self.assertTrue(self.widget.btn_drop_pending.isEnabled())
        for button in (self.widget.token_eye, self.widget.btn_copy_token,
                       self.widget.btn_reset_webhook, self.widget.btn_drop_pending):
            self.assertTrue(button.text())
            self.assertIn("color:#dbeafe", button.styleSheet())
        self.assertIn("ChatID: 893412781", self.widget.log_list.item(0).text())
        self.assertIn("Webhook Handshake Ping", self.widget.log_list.item(1).text())
        self.assertIn("MD5-CHECKSUM", self.widget.log_list.item(3).text())
        self.assertEqual(self.widget.log_total.text(), "Toplam \u0130letim: 1,482 adet")
        self.widget.resize(1280, 800)
        self.widget.setFont(QFont("Arial", 9))
        output = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "telegram-bot-desktop.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        script = "\n".join((
            "import os",
            "from pathlib import Path",
            "from PyQt6.QtGui import QImage, QPainter",
            "from runpy import run_path",
            "module = run_path('tests/test_part9_telegram_bot_layout.py')",
            "app = module['APP']",
            "widget = module['TelegramSettingsWidget'](module['TelegramDatabaseStub']())",
            "widget.resize(1280, 800)",
            "widget.setFont(module['QFont']('Arial', 9))",
            "widget.show()",
            "app.processEvents()",
            "image = QImage(widget.size(), QImage.Format.Format_ARGB32_Premultiplied)",
            "image.fill(0xFFFFFFFF)",
            "painter = QPainter(image)",
            "widget.render(painter)",
            "painter.end()",
            "output = Path(os.environ['AYEC_TELEGRAM_CAPTURE_PATH'])",
            "output.parent.mkdir(parents=True, exist_ok=True)",
            "assert image.save(str(output), 'PNG')",
            "widget.close()",
        ))
        child_env = os.environ.copy()
        child_env["QT_QPA_PLATFORM"] = "offscreen"
        child_env["AYEC_TELEGRAM_CAPTURE_PATH"] = str(output)
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            env=child_env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_settings_tabs_route_to_existing_native_pages(self):
        visited = []

        class SettingsPageStub:
            def change_page(self, page_id):
                visited.append(page_id)

        class MainWindowStub:
            settings_page = SettingsPageStub()

        self.widget.main_window = MainWindowStub()
        self.widget.settings_tab_buttons[2].click()
        self.widget.settings_tab_buttons[3].click()
        self.widget.settings_tab_buttons[1].click()
        self.assertEqual(visited, [2, 3, 1])

    def test_token_chat_ids_and_preferences_remain_functional(self):
        self.widget._toggle_token()
        self.assertEqual(self.widget.inp_token.echoMode(), QLineEdit.EchoMode.Normal)
        self.widget.inp_chat_id.setText("981234567")
        self.widget.add_chat_id()
        self.widget.preferences["stock_critical"].setChecked(False)
        with patch(
            "src.ui.pages.settings_widgets.telegram_settings.urllib.request.urlopen",
            return_value=BytesIO(b'{"ok":true,"result":true}'),
        ):
            self.widget.save_data()
        self.assertEqual(json.loads(self.db.get_setting("telegram_chat_ids")), ["893412781", "561298834", "981234567"])
        self.assertEqual(self.db.get_setting("telegram_notify_stock_critical"), "0")
        self.widget.chat_list.setCurrentRow(2)
        self.widget.remove_chat_id()
        self.assertEqual(json.loads(self.db.get_setting("telegram_chat_ids")), ["893412781", "561298834"])

    def test_token_copy_and_webhook_reset_controls(self):
        self.widget.inp_token.setText("test-token")
        self.widget.copy_token()
        self.assertEqual(QGuiApplication.clipboard().text(), "test-token")
        with patch(
            "src.ui.pages.settings_widgets.telegram_settings.urllib.request.urlopen",
            return_value=BytesIO(b'{"ok":true,"result":true}'),
        ) as open_url:
            self.widget.reset_webhook_url()
        self.assertIn(b"drop_pending_updates=false", open_url.call_args.args[0].data)
        self.assertEqual(self.widget.webhook_url.text(), self.widget.DEFAULT_WEBHOOK_URL)

    def test_drop_pending_requires_confirmation_and_calls_telegram(self):
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.Yes) as confirm:
            with patch(
                "src.ui.pages.settings_widgets.telegram_settings.urllib.request.urlopen",
                return_value=BytesIO(b'{"ok":true,"result":true}'),
            ) as open_url:
                self.widget.show_pending_updates()

        confirm.assert_called_once()
        self.assertIn(b"drop_pending_updates=true", open_url.call_args.args[0].data)

    def test_drop_pending_cancel_does_not_call_telegram(self):
        with patch.object(QMessageBox, "question", return_value=QMessageBox.StandardButton.No):
            with patch("src.ui.pages.settings_widgets.telegram_settings.urllib.request.urlopen") as open_url:
                self.widget.show_pending_updates()

        open_url.assert_not_called()

    def test_connection_test_refreshes_live_webhook_status(self):
        responses = (
            BytesIO(b'{"ok":true,"result":{"username":"ayec_bot"}}'),
            BytesIO(b'{"ok":true,"result":{"url":"https://example.test/hook","pending_update_count":2}}'),
        )
        with patch("src.ui.pages.settings_widgets.telegram_settings.urllib.request.urlopen", side_effect=responses) as open_url:
            self.widget.test_connection()

        self.assertEqual(open_url.call_count, 2)
        self.assertIn("Webhook etkin", self.widget.webhook_label.text())
        self.assertIn("Webhook Handshake Ping", self.widget.log_list.item(1).text())
        self.assertIn("MD5-CHECKSUM", self.widget.log_list.item(3).text())

    def test_activity_history_is_saved_in_current_settings_store(self):
        self.widget._record_activity("Bot API connection verified")

        events = json.loads(self.db.get_setting("telegram_activity_log"))
        self.assertEqual(events[0]["message"], "Bot API connection verified")
        with patch.object(QMessageBox, "information") as show_message:
            self.widget._show_logs()
        self.assertIn("Bot API connection verified", show_message.call_args.args[2])


if __name__ == "__main__":
    unittest.main()
