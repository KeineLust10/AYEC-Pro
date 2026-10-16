import sqlite3

from src.utils.password_security import hash_password
from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_stock_action_accepts_current_admin_and_provisioned_master_passwords(
    monkeypatch, tmp_path
):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main._TENANT_LOCAL, "db_path", tenant_path, raising=False)
    with sqlite3.connect(tenant_path) as connection:
        connection.execute(
            "INSERT INTO settings(key,value) VALUES('admin_pass',?)",
            (hash_password("tenant-admin-secret"),),
        )

    monkeypatch.setenv("AYECPRO_MASTER_PASSWORD_HASH", hash_password("emergency-secret"))
    assert web_main.desktop_stock_action_password_valid("operator-test-pass", 2)
    assert web_main.desktop_stock_action_password_valid("tenant-admin-secret", 2)
    assert web_main.desktop_stock_action_password_valid("emergency-secret", 2)
    assert not web_main.desktop_stock_action_password_valid("wrong-pass", 2)
