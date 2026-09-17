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
