from unittest.mock import MagicMock, patch

from src.utils.email_manager import EmailManager


class SettingsDB:
    def __init__(self, values):
        self.values = values

    def get_setting(self, key, default=""):
        return self.values.get(key, default)


def test_email_manager_applies_tls_sender_name_and_archive_bcc():
    db = SettingsDB({
        "smtp_server": "smtp.example.test",
        "smtp_port": "465",
        "smtp_email": "sender@example.test",
        "smtp_password": "secret",
        "smtp_sender_name": "AYEC Pro",
        "smtp_security": "ssl",
        "smtp_timeout": "22",
        "smtp_auth_required": "1",
        "smtp_auto_bcc": "1",
        "company_email": "archive@example.test",
    })
    server = MagicMock()
    with patch("src.utils.secure_setting_store.SecureSettingStore.get", return_value="secret"), patch(
        "src.utils.email_manager.smtplib.SMTP_SSL", return_value=server
    ) as smtp_ssl:
        manager = EmailManager(db)
        manager._send_email_thread("customer@example.test", "Subject", "Body", False)

    smtp_ssl.assert_called_once()
    assert smtp_ssl.call_args.kwargs["timeout"] == 22
    server.login.assert_called_once_with("sender@example.test", "secret")
    recipients = server.sendmail.call_args.args[1]
    message = server.sendmail.call_args.args[2]
    assert recipients == ["customer@example.test", "archive@example.test"]
    assert "AYEC Pro" in message
    assert "archive@example.test" not in message


def test_email_manager_supports_starttls_without_authentication():
    db = SettingsDB({
        "smtp_server": "smtp.example.test",
        "smtp_port": "587",
        "smtp_email": "sender@example.test",
        "smtp_security": "starttls",
        "smtp_timeout": "99",
        "smtp_auth_required": "0",
    })
    server = MagicMock()
    with patch("src.utils.secure_setting_store.SecureSettingStore.get", return_value=""), patch(
        "src.utils.email_manager.smtplib.SMTP", return_value=server
    ) as smtp:
        manager = EmailManager(db)
        manager._send_email_thread("customer@example.test", "Subject", "Body", False)

    assert smtp.call_args.kwargs["timeout"] == 60
    server.starttls.assert_called_once()
    server.login.assert_not_called()
    server.sendmail.assert_called_once()
