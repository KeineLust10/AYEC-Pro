from unittest.mock import MagicMock, patch

import pytest

from Web_Arayuzu.Main import send_smtp_test_message


def _payload(**updates):
    values = {
        "host": "smtp.example.test",
        "port": "465",
        "username": "sender@example.test",
        "password": "app-secret",
        "sender": "sender@example.test",
        "sender_name": "AYEC Pro",
        "recipient": "target@example.test",
        "security": "ssl",
        "timeout": "15",
        "auth_required": True,
    }
    values.update(updates)
    return values


def test_smtp_test_uses_ssl_auth_sender_name_and_timeout():
    server = MagicMock()
    server.__enter__.return_value = server
    with patch("smtplib.SMTP_SSL", return_value=server) as smtp_ssl:
        recipient = send_smtp_test_message(_payload())

    assert recipient == "target@example.test"
    smtp_ssl.assert_called_once()
    assert smtp_ssl.call_args.kwargs["timeout"] == 15
    server.login.assert_called_once_with("sender@example.test", "app-secret")
    message = server.send_message.call_args.args[0]
    assert message["From"] == "AYEC Pro <sender@example.test>"


def test_smtp_test_supports_starttls_without_authentication():
    server = MagicMock()
    server.__enter__.return_value = server
    with patch("smtplib.SMTP", return_value=server) as smtp:
        send_smtp_test_message(
            _payload(port="587", security="starttls", auth_required=False)
        )

    smtp.assert_called_once()
    server.starttls.assert_called_once()
    server.login.assert_not_called()
    server.send_message.assert_called_once()


@pytest.mark.parametrize("mode", ["plain", "broken"])
def test_smtp_test_rejects_unsupported_security_modes(mode):
    with pytest.raises(ValueError, match="security mode is invalid"):
        send_smtp_test_message(_payload(security=mode))


def test_smtp_test_requires_credentials_when_authentication_is_enabled():
    with patch("smtplib.SMTP_SSL") as smtp_ssl:
        with pytest.raises(ValueError, match="username and password are required"):
            send_smtp_test_message(_payload(password=""))

    smtp_ssl.assert_called_once()
