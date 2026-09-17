import importlib.util
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
WEB_MAIN = ROOT / "Web_Arayuzu" / "Main.py"


def _load_web_module(monkeypatch, tmp_path):
    monkeypatch.setenv("AYEC_DB_PATH", str(tmp_path / "registry.db"))
    monkeypatch.setenv("AYEC_TENANT_DIR", str(tmp_path / "tenants"))
    monkeypatch.setenv("AYEC_PROVISION_INVITES_REQUIRED", "1")
    (tmp_path / "tenants").mkdir()
    name = "ayec_web_provisioning_test"
    spec = importlib.util.spec_from_file_location(name, WEB_MAIN)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_provision_invite_is_hashed_and_single_use(monkeypatch, tmp_path):
    module = _load_web_module(monkeypatch, tmp_path)
    module.is_control_admin = lambda _actor: True
    actor = {"id": 7, "_tenant_id": "vendor"}

    created = module.control_create_provision_invite(
        actor,
        {"expires_in_hours": 24, "max_uses": 1},
    )
    code = created["invite_code"]

    with module.closing(module.registry_connect()) as connection:
        row = connection.execute(
            "SELECT code_hash,use_count,max_uses FROM provision_invites"
        ).fetchone()
    assert row["code_hash"] != code
    assert row["use_count"] == 0
    assert row["max_uses"] == 1

    module._claim_provision_invite(code)
    with pytest.raises(PermissionError):
        module._claim_provision_invite(code)


def test_provision_rate_limit_blocks_sixth_attempt(monkeypatch, tmp_path):
    module = _load_web_module(monkeypatch, tmp_path)

    for _ in range(module.PROVISION_RATE_MAX_ATTEMPTS):
        module.consume_provision_rate_limit("203.0.113.9", "device-one")

    with pytest.raises(PermissionError):
        module.consume_provision_rate_limit("203.0.113.9", "device-one")
