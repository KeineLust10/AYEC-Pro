import json
import unittest
from unittest.mock import patch

from Web_Arayuzu.Main import test_telegram_bot_connection as verify_telegram_bot_connection
from Web_Arayuzu.Main import get_telegram_bot_status
from Web_Arayuzu.Main import update_telegram_bot_webhook
from Web_Arayuzu.Main import protect_telegram_bot_token
from src.utils.secure_setting_store import SecureSettingStore


class TelegramResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"ok": True, "result": {"username": "ayec_bot", "first_name": "AYEC"}}).encode("utf-8")


class TelegramConnectionTests(unittest.TestCase):
    def test_webhook_status_reports_real_endpoint_and_pending_count(self):
        class WebhookResponse(TelegramResponse):
            def read(self):
                return json.dumps({"ok": True, "result": {
                    "url": "https://example.test/telegram/inbound",
                    "pending_update_count": 3,
                    "last_error_message": "",
                }}).encode("utf-8")

        with patch("Web_Arayuzu.Main.urlopen", return_value=WebhookResponse()) as open_url:
            result = get_telegram_bot_status({"token": "123456:Abc_def-123"})

        self.assertEqual(result, {
            "ok": True,
            "url": "https://example.test/telegram/inbound",
            "pending_update_count": 3,
            "last_error_message": "",
            "last_error_date": 0,
        })
        self.assertIn("/getWebhookInfo", open_url.call_args.args[0].full_url)

    def test_valid_token_returns_bot_identity(self):
        with patch("Web_Arayuzu.Main.urlopen", return_value=TelegramResponse()) as open_url:
            result = verify_telegram_bot_connection({"token": "123456:Abc_def-123"})

        self.assertEqual(result, {"ok": True, "username": "ayec_bot", "name": "AYEC"})
        self.assertEqual(open_url.call_args.kwargs["timeout"], 10)

    def test_invalid_token_is_rejected_before_network_call(self):
        with patch("Web_Arayuzu.Main.urlopen") as open_url:
            with self.assertRaises(ValueError):
                verify_telegram_bot_connection({"token": "invalid"})

        open_url.assert_not_called()

    def test_webhook_update_can_drop_pending_and_preserves_https_target(self):
        with patch("Web_Arayuzu.Main.urlopen", return_value=TelegramResponse()) as open_url:
            result = update_telegram_bot_webhook({
                "token": "123456:Abc_def-123",
                "url": "https://api.ayecpro.com.tr/v4/telegram/webhook/inbound",
                "drop_pending_updates": True,
            })

        request = open_url.call_args.args[0]
        self.assertEqual(result, {"ok": True, "drop_pending_updates": True})
        self.assertTrue(request.full_url.endswith("/setWebhook"))
        self.assertIn(b"drop_pending_updates=true", request.data)
        self.assertIn(b"url=https%3A%2F%2Fapi.ayecpro.com.tr", request.data)

    def test_webhook_update_rejects_non_https_url_before_network_call(self):
        with patch("Web_Arayuzu.Main.urlopen") as open_url:
            with self.assertRaises(ValueError):
                update_telegram_bot_webhook({
                    "token": "123456:Abc_def-123",
                    "url": "https://",
                })

        open_url.assert_not_called()

    def test_webhook_update_does_not_treat_false_string_as_drop_request(self):
        with patch("Web_Arayuzu.Main.urlopen", return_value=TelegramResponse()) as open_url:
            result = update_telegram_bot_webhook({
                "token": "123456:Abc_def-123",
                "url": "https://api.ayecpro.com.tr/v4/telegram/webhook/inbound",
                "drop_pending_updates": "false",
            })

        self.assertFalse(result["drop_pending_updates"])
        self.assertIn(b"drop_pending_updates=false", open_url.call_args.args[0].data)

    def test_web_token_storage_uses_the_shared_encrypted_setting_format(self):
        encrypted = protect_telegram_bot_token("123456:Abc_def-123")

        self.assertTrue(SecureSettingStore.is_encrypted(encrypted))
        self.assertNotIn("123456:Abc_def-123", encrypted)
        restored = SecureSettingStore._fernet().decrypt(
            encrypted[len(SecureSettingStore.PREFIX):].encode("ascii")
        ).decode("utf-8")
        self.assertEqual(restored, "123456:Abc_def-123")


if __name__ == "__main__":
    unittest.main()
