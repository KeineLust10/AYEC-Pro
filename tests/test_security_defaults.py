from backend.app.core.config import Settings
from src.utils.mail_manager import MailWorker


def test_backend_secret_is_random_and_not_a_known_default():
    first = Settings(_env_file=None)
    second = Settings(_env_file=None)

    assert len(first.SECRET_KEY) >= 48
    assert first.SECRET_KEY != "ayecpro-secret-key-change-in-production"
    assert first.SECRET_KEY != second.SECRET_KEY
    assert first.DEBUG is False


def test_mail_worker_has_no_embedded_smtp_password(monkeypatch):
    monkeypatch.delenv("AYECPRO_SMTP_EMAIL", raising=False)
    monkeypatch.delenv("AYECPRO_SMTP_APP_PASSWORD", raising=False)

    worker = MailWorker("user@example.com", "subject", "body")

    assert worker.system_email == ""
    assert worker.app_password == ""
