from contextlib import closing
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from Web_Arayuzu import Main as web_main
from src.ui.dialogs.license_lock_screen import LicenseRequestDialog
from src.utils.license_api_client import LicenseApiClient

_QT_APP = None


def _app():
    global _QT_APP
    _QT_APP = QApplication.instance() or QApplication([])
    return _QT_APP


def test_license_client_uses_dedicated_device_endpoint():
    calls = []

    class RecordingClient(LicenseApiClient):
        def _request(self, path, method="GET", payload=None):
            calls.append((path, method, payload))
            return {"ok": True}

    payload = {"hardware_id": "1234567890123456", "plan_code": "one_year"}
    result = RecordingClient("http://license.test").create_order(payload)

    assert result["ok"] is True
    assert calls == [("/api/license/orders/device", "POST", payload)]


def test_missing_device_company_can_be_provisioned_for_license_order(monkeypatch):
    class EmptyRegistry:
        def execute(self, *args, **kwargs):
            return []

        def close(self):
            return None

    class TenantDatabase:
        def close(self):
            return None

    tenant = {"id": "tenant-new", "company_name": "New Company"}
    monkeypatch.setattr(web_main, "registry_connect", lambda: EmptyRegistry())
    monkeypatch.setattr(
        web_main,
        "provision_desktop_tenant",
        lambda payload: {"tenant": tenant, "user": {"username": payload["username"]}},
    )
    monkeypatch.setattr(web_main, "tenant_by_id", lambda tenant_id: tenant)
    monkeypatch.setattr(web_main, "set_tenant_context", lambda value: None)
    monkeypatch.setattr(web_main, "db_connect", lambda: TenantDatabase())
    monkeypatch.setattr(
        web_main,
        "find_account_by_identifier",
        lambda conn, identifier: {
            "id": 1,
            "username": identifier,
            "full_name": "New User",
            "email": "new@example.com",
        },
    )

    user = web_main.license_user_from_device(
        {
            "hardware_id": "1234567890123456",
            "company_name": "New Company",
            "requester_name": "New User",
            "requester_email": "new@example.com",
            "identifier": "newuser",
            "password": "Secret123",
        },
        allow_provision=True,
    )

    assert user["_tenant_id"] == "tenant-new"
    assert user["username"] == "newuser"


def test_paid_license_order_is_atomic_and_emails_vendor(tmp_path, monkeypatch):
    web_main.DB_PATH = tmp_path / "registry.db"
    web_main.TENANT_ROOT = tmp_path / "tenants"
    with closing(web_main.registry_connect()) as conn:
        conn.execute(
            "INSERT INTO tenants "
            "(id,company_name,db_filename,created_at,active) VALUES (?,?,?,?,1)",
            ("tenant-1", "Test Company", "tenant.db", "2026-08-17T12:00:00"),
        )
        conn.commit()

    sent_messages = []

    def fake_send(_tenant_id, recipient, subject, text):
        sent_messages.append((recipient, subject, text))
        return True, "Email sent."

    monkeypatch.setattr(web_main, "send_license_email", fake_send)
    monkeypatch.setattr(web_main, "_support_audit", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        web_main,
        "license_payment_profile",
        lambda: {
            "bank_name": "Vak\u0131fBank",
            "account_holder": "Engin ASLAN",
            "iban": "TR66 0001 5001 5800 7321 0690 01",
            "notification_email": web_main.VENDOR_EMAIL,
        },
    )

    result = web_main.create_license_order(
        {
            "_tenant_id": "tenant-1",
            "id": 9,
            "username": "engin",
            "full_name": "Engin ASLAN",
            "email": "customer@example.com",
            "phone": "5550000000",
        },
        {
            "hardware_id": "1234567890123456",
            "plan_code": "one_year",
            "payment_reported": True,
        },
    )

    assert result["order"]["status"] == "payment_reported"
    assert result["order"]["payment_reported_at"]
    assert result["mail"]["admin_sent"] is True
    assert result["mail"]["admin_recipient"] == "ayecpro@gmail.com"
    assert len(sent_messages) == 2
    assert sent_messages[1][0] == "ayecpro@gmail.com"
    assert "Odeme Yapildi" in sent_messages[1][1]
    assert "Tarih/Saat:" in sent_messages[1][2]


def test_smtp_environment_aliases_are_supported(monkeypatch):
    class FakeConnection:
        def close(self):
            return None

    monkeypatch.setattr(web_main, "registry_connect", FakeConnection)
    monkeypatch.setattr(web_main, "_tenant_row_any", lambda _conn, _tenant_id: None)
    monkeypatch.setenv("AYECPRO_SMTP_SERVER", "smtp.example.com")
    monkeypatch.setenv("AYECPRO_SMTP_PORT", "2525")
    monkeypatch.setenv("AYECPRO_SMTP_EMAIL", "sender@example.com")
    monkeypatch.setenv("AYECPRO_SMTP_APP_PASSWORD", "secret")

    settings = web_main._license_smtp_settings("tenant-1")

    assert settings["host"] == "smtp.example.com"
    assert settings["port"] == "2525"
    assert settings["from"] == "sender@example.com"
    assert settings["username"] == "sender@example.com"
    assert settings["password"] == "secret"


def test_license_buttons_stay_enabled_when_catalog_is_offline(monkeypatch):
    _app()
    monkeypatch.setattr(
        LicenseRequestDialog,
        "_connect_client",
        lambda _self: (_ for _ in ()).throw(RuntimeError("offline")),
    )

    dialog = LicenseRequestDialog("1234567890123456")

    assert dialog.btn_paid.isEnabled()
    assert dialog.btn_unpaid.isEnabled()
    assert "yeniden denenecek" in dialog.status_label.text()


def test_license_api_payment_flow_uses_mail_fallback(monkeypatch):
    _app()
    monkeypatch.setattr(LicenseRequestDialog, "_load_catalog", lambda _self: None)
    dialog = LicenseRequestDialog("1234567890123456")
    class LicenseClient:
        def create_order(self, payload):
            assert payload["payment_reported"] is True
            return {
                "order": {
                    "id": 17,
                    "status": "payment_reported",
                    "plan_label": "1 Yillik Profesyonel",
                    "amount_try": 9900,
                },
                "mail": {"admin_sent": False, "admin_message": "SMTP missing"},
            }

    dialog.client = LicenseClient()
    monkeypatch.setattr(
        dialog,
        "_send_admin_email_fallback",
        lambda order, paid: (True, "Email sent."),
    )

    dialog._submit(True)

    assert dialog.fallback_mail_sent is True
    assert "ayecpro@gmail.com" in dialog.status_label.text()
