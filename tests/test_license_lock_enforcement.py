import os
import threading
import time
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QWidget

from src.services.license_service import LicenseService
from src.ui.dialogs.license_lock_screen import LicenseRequestDialog
from src.utils import mail_manager
from src.utils.mail_manager import MailWorker
from src.utils.web_sync_client import WebSyncClient
from src.utils import license_api_client


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


def test_startup_expired_license_is_still_reported_from_worker():
    app = _app()
    main_thread = threading.get_ident()

    class Manager:
        def check_license_status(self):
            assert threading.get_ident() != main_thread
            return {"status": "expired", "message": "License expired."}

        def _license_device_identity(self):
            return None

    window = QWidget()
    window.db = object()
    window.license_manager = Manager()
    service = LicenseService(window)
    results = []
    service.on_license_check_result = lambda ok, message: results.append(
        (ok, message, threading.get_ident())
    )

    service.start_license_check()
    deadline = time.monotonic() + 2
    while service._local_license_worker is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()

    assert results == [(False, "License expired.", main_thread)]
    service.enforcement_timer.stop()
    window.close()


def test_startup_license_refresh_fetches_network_state_on_worker(monkeypatch):
    app = _app()
    main_thread = threading.get_ident()
    network_threads = []
    local_threads = []
    applied = []

    class _Client:
        def __init__(self, timeout):
            assert timeout == 5

        def status_for_device(self, identity):
            network_threads.append(threading.get_ident())
            assert identity == {"hardware_id": "DEVICE"}
            time.sleep(0.05)
            return {"access": {"allowed": True, "license_type": "lifetime"}}

    class _Manager:
        def _license_device_identity(self):
            local_threads.append(threading.get_ident())
            assert threading.get_ident() != main_thread
            return {"hardware_id": "DEVICE"}

        def apply_server_entitlement(self, payload):
            applied.append(payload)
            return True, "License activated."

        def check_license_status(self):
            local_threads.append(threading.get_ident())
            assert threading.get_ident() != main_thread
            return {"status": "active", "message": "License active."}

    window = QWidget()
    window.db = object()
    window.license_manager = _Manager()
    service = LicenseService(window)
    results = []
    service.on_license_check_result = lambda ok, message: results.append((ok, message))
    monkeypatch.setattr(license_api_client, "LicenseApiClient", _Client)

    service.start_license_check()
    assert results == []
    deadline = time.monotonic() + 2
    while (
        service._local_license_worker is not None
        or service._license_check_worker is not None
    ) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()

    assert local_threads and all(thread_id != main_thread for thread_id in local_threads)
    assert network_threads and network_threads[0] != main_thread
    assert applied == [{"access": {"allowed": True, "license_type": "lifetime"}}]
    assert results and results[-1] == (True, "License active.")
    service.enforcement_timer.stop()
    window.close()


def test_credential_license_refresh_uses_worker_and_returns_to_ui(monkeypatch):
    app = _app()
    main_thread = threading.get_ident()
    network_threads = []
    applied = []
    callbacks = []

    class _Client:
        def __init__(self, timeout):
            assert timeout == 5

        def status_for_credentials(self, identifier, password, tenant_id):
            network_threads.append(threading.get_ident())
            assert (identifier, password, tenant_id) == ("operator", "secret", "tenant")
            return {"access": {"allowed": True, "license_type": "lifetime"}}

        def status_for_device(self, _identity):
            raise AssertionError("credential refresh must not use device identity")

    class _Manager:
        def _license_device_identity(self):
            raise AssertionError("credential refresh must not read device identity")

        def apply_server_entitlement(self, payload):
            assert threading.get_ident() == main_thread
            applied.append(payload)
            return True, "License activated."

        def check_license_status(self):
            return {"status": "active", "message": "License active."}

    window = QWidget()
    window.db = object()
    window.license_manager = _Manager()
    service = LicenseService(window)
    service.on_license_check_result = lambda *_args: None
    monkeypatch.setattr(license_api_client, "LicenseApiClient", _Client)

    assert service.refresh_server_entitlement_async(
        "operator", "secret", "tenant", on_complete=lambda *args: callbacks.append(args)
    )
    deadline = time.monotonic() + 2
    while (
        service._local_license_worker is not None
        or service._license_check_worker is not None
    ) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()

    assert network_threads and network_threads[0] != main_thread
    assert applied == [{"access": {"allowed": True, "license_type": "lifetime"}}]
    assert callbacks and callbacks[0][0] is True
    service.enforcement_timer.stop()
    window.close()


def test_web_sync_client_has_no_license_operations():
    assert not hasattr(WebSyncClient, "license_catalog")
    assert not hasattr(WebSyncClient, "create_license_order")
    assert not hasattr(WebSyncClient, "report_license_payment")


def test_mail_worker_uses_official_mailbox_without_embedded_password():
    worker = MailWorker("ayecpro@gmail.com", "Test", "Body")

    assert worker.smtp_server
    assert worker.system_email == "info@ayecpro.com"
    assert worker.app_password == ""


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
    assert created[0][1]["recipient"] == "destek@ayecpro.com"
    assert created[0][1]["db"] is fake_db
