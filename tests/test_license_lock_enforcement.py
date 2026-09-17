import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from src.services.license_service import LicenseService
from src.ui.dialogs.license_lock_screen import LicenseRequestDialog
from src.utils import mail_manager
from src.utils.mail_manager import MailWorker
from src.utils.web_sync_client import WebSyncClient


_QT_APP = None


def _app():
    global _QT_APP
    _QT_APP = QApplication.instance() or QApplication([])
    return _QT_APP


def test_locked_license_dialog_shows_request_flow_and_exit(monkeypatch):
    _app()
    monkeypatch.setattr(LicenseRequestDialog, "_load_catalog", lambda _self: None)

    dialog = LicenseRequestDialog("1234567890123456", locked=True)

    assert dialog.locked_mode is True
    assert dialog.lbl_title.text() == "Lisans S\u00fcresi Sona Erdi"
    assert dialog.footer_layout.itemAt(0).widget().text() == "Programdan \u00c7\u0131k"
    assert dialog.btn_paid.text() == "\u00d6deme Yapt\u0131m - Talep Et"
    assert dialog.isModal()


def test_periodic_expiry_check_requests_application_lock():
    _app()

    class Manager:
        def check_license_status(self):
            return {"status": "expired", "type": "TRIAL"}

    window = QWidget()
    window.db = object()
    window.license_manager = Manager()
    service = LicenseService(window)
    results = []
    service.on_license_check_result = lambda ok, message: results.append((ok, message))

    service._enforce_local_expiry()

    assert results and results[0][0] is False
    assert "sona ermi\u015ftir" in results[0][1]


def test_web_sync_client_has_no_license_operations():
    assert not hasattr(WebSyncClient, "license_catalog")
    assert not hasattr(WebSyncClient, "create_license_order")
    assert not hasattr(WebSyncClient, "report_license_payment")


def test_mail_worker_uses_existing_ayec_mail_fallback():
    worker = MailWorker("ayecpro@gmail.com", "Test", "Body")

    assert worker.smtp_server
    assert worker.system_email == "ayecpro@gmail.com"
    assert worker.app_password


def test_registration_notification_passes_database_to_mail_worker(monkeypatch):
    created = []

    class FakeWorker:
        def __init__(self, *args, **kwargs):
            created.append((args, kwargs))

        def start(self):
            return None

    class FakeDb:
        def get_setting(self, _key, default=""):
            return default

    fake_db = FakeDb()
    monkeypatch.setattr(mail_manager, "MailWorker", FakeWorker)

    mail_manager.send_registration_emails_async(
        {
            "company_name": "Test Company",
            "full_name": "Test User",
            "email": "",
            "phone": "5550000000",
            "purpose": "service",
        },
        db=fake_db,
    )

    assert len(created) == 1
    assert created[0][1]["recipient"] == "ayecpro@gmail.com"
    assert created[0][1]["db"] is fake_db
