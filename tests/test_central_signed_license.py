"""Signed license lifecycle against disposable central registry databases."""

from contextlib import closing
from datetime import timedelta

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ayec_core.entitlements import EntitlementVerifier
from ayec_core.license_cache import LicenseCache
from tests.test_vendor_management_center import _setup_tenant
from Web_Arayuzu import Main as web


@pytest.fixture
def license_device(monkeypatch, tmp_path):
    _setup_tenant(monkeypatch, tmp_path)
    key = Ed25519PrivateKey.generate()
    private_path = tmp_path / "test-signing.pem"
    private_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                                              serialization.PrivateFormat.PKCS8,
                                              serialization.NoEncryption()))
    monkeypatch.setenv("AYEC_LICENSE_SIGNING_KEY_FILE", str(private_path))
    monkeypatch.setenv("AYEC_LICENSE_SIGNING_KEY_ID", "test-only")
    public_pem = key.public_key().public_bytes(serialization.Encoding.PEM,
                                             serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")
    with closing(web.registry_connect()) as conn:
        conn.execute("UPDATE tenants SET product_code='elek',license_code='fixture-central-key',"
                     "license_type='monthly',license_start=?,license_end=? WHERE id='tenant-1'",
                     ((web.utc_now() - timedelta(days=1)).isoformat(),
                      (web.utc_now() + timedelta(days=29)).isoformat()))
        conn.commit()
    payload = {"tenant_id": "tenant-1", "product_code": "elek",
               "requester_email": "customer@example.com", "hardware_id": "fixture-device-1234",
               "installation_id": "installation-1", "license_key": "fixture-central-key"}
    return payload, EntitlementVerifier({"test-only": public_pem})


def test_signed_activation_offline_revocation_and_restart(license_device):
    payload, verifier = license_device
    response = web.license_status_from_device(payload)
    cache = LicenseCache(product_code="elek", hardware_id=payload["hardware_id"],
                         tenant_id="tenant-1", installation_id="installation-1",
                         require_signature=True)
    assert cache.apply(response, verify_signature=verifier)["state"] == "ACTIVE_ONLINE"
    assert cache.transport_failure()["state"] == "ACTIVE_OFFLINE"
    with closing(web.registry_connect()) as conn:
        conn.execute("UPDATE tenants SET active=0,license_status='Inactive' WHERE id='tenant-1'")
        conn.commit()
    response = web.license_status_from_device(dict(payload, license_key=""))
    assert verifier(response["access"])
    assert cache.apply(response, verify_signature=verifier)["state"] == "REVOKED"
    saved = cache.export()
    assert cache.load(saved, verify_signature=verifier)["state"] == "REVOKED"


def test_device_product_installation_and_key_cannot_grant_another_license(license_device):
    payload, _ = license_device
    with pytest.raises(PermissionError):
        web.license_status_from_device(dict(payload, license_key="made-up-key"))
    with pytest.raises(PermissionError):
        web.license_status_from_device(dict(payload, product_code="ciro"))
    web.license_status_from_device(payload)
    with pytest.raises(PermissionError):
        web.license_status_from_device(dict(payload, installation_id="other"))
    with pytest.raises(PermissionError):
        web.license_status_from_device(dict(payload, hardware_id="other-device-1234", license_key=""))


def test_expired_response_is_signed_and_not_revoked(license_device):
    payload, verifier = license_device
    with closing(web.registry_connect()) as conn:
        conn.execute("UPDATE tenants SET license_end=? WHERE id='tenant-1'",
                     ((web.utc_now() - timedelta(minutes=1)).isoformat(),))
        conn.commit()
    response = web.license_status_from_device(payload)
    assert verifier(response["access"])
    assert response["access"]["allowed"] is False
    assert response["access"]["reason_code"] == "expired"


def test_missing_server_signer_does_not_emit_unsigned_license(license_device, monkeypatch):
    payload, _ = license_device
    monkeypatch.delenv("AYEC_LICENSE_SIGNING_KEY_FILE")
    with pytest.raises(RuntimeError):
        web.license_status_from_device(payload)
    with closing(web.registry_connect()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM license_device_bindings").fetchone()[0] == 0


def test_central_admin_can_grant_catalog_license_directly_to_hwid(license_device):
    payload, verifier = license_device
    actor = {"id": 2, "_tenant_id": "tenant-1", "role": "Admin"}
    hardware_id = "center-granted-device-1234"

    result = web.admin_grant_hwid_license({
        "tenant_id": "tenant-1",
        "product_code": "elek",
        "hardware_id": hardware_id,
        "plan_code": "monthly",
    }, actor)

    assert result["order"]["status"] == "active"
    assert result["order"]["hardware_id"] == hardware_id
    assert result["order"]["plan_code"] == "monthly"
    assert result["order"]["payment_reported_at"] == ""
    access = web.license_status_from_device(dict(payload, hardware_id=hardware_id, license_key=""))
    assert verifier(access["access"])
    assert access["access"]["allowed"] is True


def test_direct_hwid_grant_requires_control_admin_and_tenant_product(license_device):
    _payload, _verifier = license_device
    with pytest.raises(PermissionError):
        web.admin_grant_hwid_license({
            "tenant_id": "tenant-1", "hardware_id": "center-granted-device-1234",
            "plan_code": "monthly",
        }, {"id": 1, "_tenant_id": "tenant-1", "role": "Admin"})
    with pytest.raises(ValueError, match="Urun firmayla eslesmiyor"):
        web.admin_grant_hwid_license({
            "tenant_id": "tenant-1", "product_code": "ciro",
            "hardware_id": "center-granted-device-1234", "plan_code": "monthly",
        }, {"id": 2, "_tenant_id": "tenant-1", "role": "Admin"})


def test_admin_license_push_notifies_only_selected_tenant_and_requires_control_admin(license_device, monkeypatch):
    _payload, _verifier = license_device
    actor = {"id": 2, "_tenant_id": "tenant-1", "role": "Admin"}
    events = []

    def publish(tenant_id, payload, source_device_id=""):
        events.append((tenant_id, payload, source_device_id))
        return 2

    monkeypatch.setattr(web.SYNC_EVENT_HUB, "publish", publish)
    result = web.admin_push_license("tenant-1", actor)

    assert result["ok"] is True
    assert result["delivered_sessions"] == 2
    assert result["license"]["license_code"] == "fixture-central-key"
    assert len(events) == 1
    assert events[0][0] == "tenant-1"
    assert events[0][1]["type"] == "license_updated"
    assert events[0][1]["license"] == result["license"]
    assert events[0][2] == ""

    with pytest.raises(PermissionError):
        web.admin_push_license("tenant-1", {"id": 1, "_tenant_id": "tenant-1", "role": "Admin"})
    with pytest.raises(LookupError):
        web.admin_push_license("missing-tenant", actor)
    assert len(events) == 1


def test_license_approval_starts_catalog_term_on_approval_date(license_device, monkeypatch):
    old_expiry = web.utc_now() + timedelta(days=365)
    now = web.utc_now().isoformat(timespec="seconds")
    with closing(web.registry_connect()) as conn:
        conn.execute("UPDATE tenants SET license_end=? WHERE id='tenant-1'",
                     (old_expiry.isoformat(timespec="seconds"),))
        conn.execute(
            "INSERT INTO license_orders "
            "(request_no,tenant_id,requester_name,requester_email,hardware_id,plan_code,plan_label,"
            "duration_months,amount_try,currency,payment_reference,status,created_at,updated_at,product_code) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("REQ-APPROVAL-START", "tenant-1", "Test Customer", "customer@example.com",
             "approval-device-1234", "monthly", "Monthly", 1, 790, "TRY",
             "PAY-APPROVAL-START", "payment_reported", now, now, "elek"),
        )
        conn.commit()
    monkeypatch.setattr(web, "send_license_email", lambda *_args: (True, "sent"))

    lower_bound = web.utc_now().replace(microsecond=0)
    result = web.approve_license_order(
        1, {"plan_code": "monthly"}, {"id": 2, "_tenant_id": "tenant-1", "role": "Admin"}
    )
    approved_at = web.datetime.fromisoformat(result["order"]["approved_at"])
    license_start = web.datetime.fromisoformat(result["order"]["license_start"])
    license_end = web.datetime.fromisoformat(result["order"]["license_end"])
    upper_bound = web.utc_now()

    assert result["order"]["status"] == "active"
    assert license_start == approved_at
    assert lower_bound <= license_start <= upper_bound
    assert license_end == web._license_add_months(license_start, 1)
    assert license_end < old_expiry
    with closing(web.registry_connect()) as conn:
        tenant = dict(conn.execute(
            "SELECT license_start,license_end FROM tenants WHERE id='tenant-1'"
        ).fetchone())
    assert tenant["license_start"] == result["order"]["license_start"]
    assert tenant["license_end"] == result["order"]["license_end"]
