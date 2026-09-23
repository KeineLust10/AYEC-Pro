"""Temporary password delivery must not lock customers out on SMTP failure."""

import importlib.util
import re
from datetime import timedelta
from contextlib import closing
from pathlib import Path

import pytest


WEB_MAIN = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "Main.py"


@pytest.fixture
def web_main(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("ayec_web_temp_password_test", WEB_MAIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "registry.db")
    monkeypatch.setattr(module, "TENANT_ROOT", tmp_path / "tenants")
    monkeypatch.setattr(module, "DEMO_TEMPLATE_PATH", tmp_path / "no-demo.db")
    module._SCHEMA_READY_PATHS.clear()
    monkeypatch.setattr(module, "send_registration_emails", lambda *_args: (True, "sent"))
    return module


def _setup(web_main):
    result = web_main.setup_application({
        "sector": "teknik_servis",
        "company_name": "Temporary Password Test",
        "company_email": "company@example.com",
        "phone": "5550000000",
        "company_address": "Test address",
        "currency": "TRY",
        "full_name": "Test User",
        "username": "testuser",
        "email": "user@example.com",
        "password": "Original123!",
    })
    return result["tenant"]["id"]


def test_temporary_password_email_failure_preserves_existing_login(web_main, monkeypatch):
    tenant_id = _setup(web_main)
    monkeypatch.setattr(web_main, "send_license_email", lambda *_args: (False, "SMTP unavailable"))

    result = web_main.admin_send_temporary_password(tenant_id, 1)

    assert result["mail_sent"] is False
    assert web_main.authenticate_account("testuser", "Original123!", tenant_id)
    with closing(web_main._raw_connect(web_main._tenant_path(web_main.tenant_by_id(tenant_id)))) as conn:
        assert conn.execute("SELECT must_change_password FROM users WHERE id=1").fetchone()[0] == 0


def test_temporary_password_email_success_sets_change_flag(web_main, monkeypatch):
    tenant_id = _setup(web_main)
    delivered = []
    monkeypatch.setattr(
        web_main,
        "send_license_email",
        lambda _tenant, recipient, _subject, body: (delivered.append((recipient, body)) or True, "sent"),
    )

    result = web_main.admin_send_temporary_password(tenant_id, 1)

    assert result["mail_sent"] is True
    assert delivered and delivered[0][0] == "user@example.com"
    assert not web_main.authenticate_account("testuser", "Original123!", tenant_id)
    temporary_password = re.search(r"Gecici parolaniz: (.+)", delivered[0][1]).group(1)
    assert web_main.authenticate_account("testuser", temporary_password, tenant_id)["must_change_password"] == 1
    changed = web_main.complete_temporary_password_change({
        "tenant_id": tenant_id,
        "identifier": "testuser",
        "temporary_password": temporary_password,
        "new_password": "Replacement123!",
    })
    assert changed["ok"] is True
    assert not web_main.authenticate_account("testuser", temporary_password, tenant_id)
    assert not web_main.authenticate_account("testuser", "Replacement123!", "other-tenant")
    assert web_main.authenticate_account("testuser", "Replacement123!", tenant_id)["must_change_password"] == 0
    with closing(web_main._raw_connect(web_main._tenant_path(web_main.tenant_by_id(tenant_id)))) as conn:
        assert conn.execute("SELECT must_change_password FROM users WHERE id=1").fetchone()[0] == 0


def test_temporary_password_expires_after_thirty_minutes(web_main, monkeypatch):
    tenant_id = _setup(web_main)
    delivered = []
    monkeypatch.setattr(
        web_main,
        "send_license_email",
        lambda _tenant, _recipient, _subject, body: (delivered.append(body) or True, "sent"),
    )
    web_main.admin_send_temporary_password(tenant_id, 1)
    temporary_password = re.search(r"Gecici parolaniz: (.+)", delivered[0]).group(1)
    with closing(web_main._raw_connect(web_main._tenant_path(web_main.tenant_by_id(tenant_id)))) as conn:
        expired = (web_main.utc_now() - timedelta(minutes=31)).isoformat(timespec="seconds")
        conn.execute("UPDATE users SET temporary_password_expires_at=? WHERE id=1", (expired,))
        conn.commit()
    assert web_main.authenticate_account("testuser", temporary_password, tenant_id) is None
