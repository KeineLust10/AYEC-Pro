import importlib.util
from pathlib import Path

import pytest


WEB_MAIN = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "Main.py"


@pytest.fixture
def web_main(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("ayec_web_mute_test", WEB_MAIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "registry.db")
    monkeypatch.setattr(module, "TENANT_ROOT", tmp_path / "tenants")
    monkeypatch.setattr(module, "DEMO_TEMPLATE_PATH", tmp_path / "no-demo.db")
    module._SCHEMA_READY_PATHS.clear()
    monkeypatch.setattr(module, "send_registration_emails", lambda *_args: (True, "sent"))
    return module


def _tenant(web_main):
    result = web_main.setup_application({
        "sector": "teknik_servis", "company_name": "Mute Test", "company_email": "company@example.com",
        "phone": "5550000000", "company_address": "Test address", "currency": "TRY",
        "full_name": "Test User", "username": "testuser", "email": "user@example.com",
        "password": "Original123!",
    })
    return result["tenant"]["id"]


def test_muted_tenant_blocks_access_and_license_order(web_main):
    tenant_id = _tenant(web_main)
    web_main.admin_update_company(tenant_id, {"muted": True})
    tenant = web_main.tenant_by_id(tenant_id)
    access = web_main.tenant_access_summary(tenant)
    assert access["allowed"] is False
    assert access["reason_code"] == "muted"
    assert "Yonetici ile iletisime gecin" in access["message"]
    user = web_main.authenticate_account("testuser", "Original123!", tenant_id)
    with pytest.raises(PermissionError, match="susturuldu"):
        web_main.create_license_order(user, {"plan_code": "monthly", "hardware_id": "hardware-id-12345"})


def test_unmuting_restores_normal_access_evaluation(web_main):
    tenant_id = _tenant(web_main)
    web_main.admin_update_company(tenant_id, {"muted": True})
    web_main.admin_update_company(tenant_id, {"muted": False})
    tenant = web_main.tenant_by_id(tenant_id)
    assert tenant["muted"] == 0
    assert web_main.tenant_access_summary(tenant)["reason_code"] == ""


def test_deactivated_tenant_can_be_reactivated(web_main):
    tenant_id = _tenant(web_main)
    result = web_main.admin_update_company(tenant_id, {"active": False})
    assert result["active"] == 0
    with web_main.closing(web_main.registry_connect()) as conn:
        assert dict(conn.execute("SELECT active FROM tenants WHERE id=?", (tenant_id,)).fetchone())["active"] == 0
    result = web_main.admin_update_company(tenant_id, {"active": True})
    assert result["active"] == 1
    tenant = web_main.tenant_by_id(tenant_id)
    assert tenant["active"] == 1
    assert web_main.tenant_access_summary(tenant)["allowed"] is True


def test_hardware_mute_blocks_device_entitlement(web_main, monkeypatch):
    tenant_id = _tenant(web_main)
    user = web_main.authenticate_account("testuser", "Original123!", tenant_id)
    hardware = "hardware-device-12345"
    installation = "install-1"
    web_main.admin_update_company(tenant_id, {"hardware_id": hardware, "installation_id": installation, "muted": True})
    key_path = Path(web_main.DB_PATH).with_name("signing.key")
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization
    key_path.write_bytes(ed25519.Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    monkeypatch.setenv("AYEC_LICENSE_SIGNING_KEY_FILE", str(key_path))
    monkeypatch.setenv("AYEC_LICENSE_SIGNING_KEY_ID", "test")
    result = web_main.license_status_from_device({
            "tenant_id": tenant_id,
            "requester_email": user["email"],
            "requester_name": "Test User",
            "password": "Original123!",
            "hardware_id": hardware,
            "installation_id": installation,
            "product_code": "teknik_servis",
        })
    assert result["access"]["allowed"] is False
    assert "Yonetici ile iletisime gecin" in result["access"]["message"]


def test_hardware_unmute_without_installation_identity_removes_device_mute(web_main):
    tenant_id = _tenant(web_main)
    hardware = "hardware-device-98765"
    web_main.admin_update_company(
        tenant_id,
        {"hardware_id": hardware, "installation_id": "install-live", "muted": True},
    )
    result = web_main.admin_update_company(
        tenant_id,
        {"hardware_id": hardware, "muted": False},
    )
    assert result["muted"] is False
    with web_main.closing(web_main.registry_connect()) as conn:
        assert conn.execute(
            "SELECT 1 FROM muted_devices WHERE tenant_id=? AND hardware_id=?",
            (tenant_id, hardware),
        ).fetchone() is None


def test_hardware_unmute_with_installation_identity_removes_wildcard_and_exact_rows(web_main):
    tenant_id = _tenant(web_main)
    hardware = "hardware-device-24680"
    web_main.admin_update_company(tenant_id, {"hardware_id": hardware, "muted": True})
    web_main.admin_update_company(
        tenant_id,
        {"hardware_id": hardware, "installation_id": "install-live", "muted": True},
    )
    web_main.admin_update_company(
        tenant_id,
        {"hardware_id": hardware, "installation_id": "install-live", "muted": False},
    )
    with web_main.closing(web_main.registry_connect()) as conn:
        assert conn.execute(
            "SELECT 1 FROM muted_devices WHERE tenant_id=? AND hardware_id=?",
            (tenant_id, hardware),
        ).fetchone() is None
