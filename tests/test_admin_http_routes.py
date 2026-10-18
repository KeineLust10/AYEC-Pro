import json
import shutil
import sqlite3
import threading
from contextlib import closing
from http.server import ThreadingHTTPServer

import requests

import Web_Arayuzu.Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def test_admin_http_routes_cover_login_customer360_backup_restore_and_update(
    monkeypatch, tmp_path
):
    actor, tenant_one_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "send_license_email", lambda *_args: (True, "sent"))
    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active,product_code) "
            "VALUES(?,?,?,?,1,?)",
            ("tenant-2", "Second Company", "Second Company.db", "2026-01-02T00:00:00", "teknik_servis"),
        )
        registry.commit()
    tenant_two_path = web_main._tenant_path(web_main.tenant_by_id("tenant-2"))
    tenant_two_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tenant_one_path, tenant_two_path)
    with closing(sqlite3.connect(tenant_two_path)) as tenant:
        tenant.execute("UPDATE users SET email='operator2@example.com' WHERE id=2")
        tenant.commit()
    source = tmp_path / "http-route-backup.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE sample(value INTEGER)")
        conn.execute("INSERT INTO sample(value) VALUES(11)")
    stored = web_main.support_store_backup(actor, source.read_bytes(), "Firma.db")

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        forbidden = session.get(f"{base_url}/api/admin/customer-360/tenant-1")
        assert forbidden.status_code == 403
        anonymous_backup = session.post(
            f"{base_url}/api/control/backups/create", json={"tenant_id": "tenant-1"}
        )
        assert anonymous_backup.status_code == 401

        login = session.post(
            f"{base_url}/api/admin/login",
            json={
                "email": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
            },
        )
        assert login.status_code == 200
        assert login.json()["ok"] is True

        tenant_session = requests.Session()
        tenant_login = tenant_session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-2"},
        )
        assert tenant_login.status_code == 200

        temporary_password = session.post(
            f"{base_url}/api/admin/users/temporary-password",
            json={"tenant_id": "tenant-1", "user_id": 1},
        )
        assert temporary_password.status_code == 200
        assert temporary_password.json()["mail_sent"] is True
        assert temporary_password.json()["recipient"] == "customer@example.com"

        self_mute = session.post(
            f"{base_url}/api/admin/companies/tenant-1", json={"muted": True}
        )
        assert self_mute.status_code == 403

        created_backup = session.post(
            f"{base_url}/api/control/backups/create", json={"tenant_id": "tenant-1"}
        )
        assert created_backup.status_code == 200
        created_item = created_backup.json()
        assert created_item["ok"] is True
        assert created_item["tenant_id"] == "tenant-1"
        assert created_item["product_code"] == "teknik_servis"

        mute = session.post(
            f"{base_url}/api/admin/companies/tenant-2", json={"muted": True}
        )
        assert mute.status_code == 200
        assert mute.json()["muted"] == 1
        muted_login = requests.Session().post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-2"},
        )
        assert muted_login.status_code == 403
        assert muted_login.json()["code"] == "LICENSE_REQUIRED"
        unmute = session.post(
            f"{base_url}/api/admin/companies/tenant-2", json={"muted": False}
        )
        assert unmute.status_code == 200
        assert unmute.json()["muted"] == 0
        restored_login = requests.Session().post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-2"},
        )
        assert restored_login.status_code == 200

        customer_360 = session.get(
            f"{base_url}/api/admin/customer-360/tenant-1"
        )
        assert customer_360.status_code == 200
        assert customer_360.json()["company"]["id"] == "tenant-1"

        backup_list = session.get(f"{base_url}/api/admin/backups/tenant-1")
        assert backup_list.status_code == 200
        item = next(
            item
            for item in backup_list.json()["backups"]
            if item.get("backup_id") == created_item["backup_id"]
        )
        assert item["source"] == "control-center"

        restore = session.post(
            f"{base_url}/api/admin/backups/tenant-1/restore",
            json={"backup_index": item["index"], "backup_id": item["backup_id"]},
        )
        assert restore.status_code == 200
        assert restore.json()["ok"] is True

        deploy = session.post(
            f"{base_url}/api/admin/updates/deploy",
            json={
                "version": "2.0.6",
                "targets": ["tenant-1"],
                "changelog": "HTTP route smoke test",
                "channel": "pilot",
            },
        )
        assert deploy.status_code == 200
        assert deploy.json()["targets"] == ["tenant-1"]

        with web_main.registry_connect() as registry:
            commands = registry.execute(
                "SELECT command_type,status,payload_json FROM desktop_commands "
                "WHERE tenant_id=? ORDER BY id DESC LIMIT 2",
                ("tenant-1",),
            ).fetchall()
        assert {row[0] for row in commands} == {"restore_backup", "deploy_update"}
        assert all(row[1] == "pending" for row in commands)
        assert any(json.loads(row[2]).get("version") == "2.0.6" for row in commands)

        monkeypatch.setattr(web_main, "ROOT", tmp_path / "http-application-root")
        deleted = session.post(f"{base_url}/api/admin/companies/tenant-2/delete", json={})
        assert deleted.status_code == 200
        assert deleted.json()["ok"] is True
        archive = web_main.ROOT / "deleted_tenants" / deleted.json()["archive"]
        assert archive.is_file()
        with web_main.registry_connect() as registry:
            assert registry.execute("SELECT 1 FROM tenants WHERE id='tenant-2'").fetchone() is None
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_tax_currency_routes_enforce_admin_and_write_to_authenticated_tenant(
    monkeypatch, tmp_path
):
    _, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as tenant:
        tenant.execute(
            "INSERT INTO users(username,password,email,phone,role,active) "
            "VALUES(?,?,?,?,?,1)",
            (
                "settings-personnel",
                web_main.password_hash("personnel-pass"),
                "personnel@example.com",
                "",
                "Personel",
            ),
        )
        tenant.commit()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.Session()
        assert (
            anonymous.post(
                f"{base_url}/api/desktop/tax-currency/vat",
                json={"percent": 8.5},
            ).status_code
            == 401
        )

        personnel = requests.Session()
        personnel_login = personnel.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": "personnel@example.com",
                "password": "personnel-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert personnel_login.status_code == 200
        assert (
            personnel.post(
                f"{base_url}/api/desktop/exchange-rates/manual",
                json={"rates": {"USD": 40}},
            ).status_code
            == 403
        )

        admin = requests.Session()
        admin_login = admin.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert admin_login.status_code == 200
        assert admin_login.json()["user"]["role"] == "Admin"
        vat = admin.post(
            f"{base_url}/api/desktop/tax-currency/vat",
            json={"percent": 8.5},
        )
        assert vat.status_code == 200, vat.text
        assert vat.json() == {"ok": True, "percent": 8.5}
        rates = admin.post(
            f"{base_url}/api/desktop/exchange-rates/manual",
            json={"rates": {"USD": 45.5, "EUR": 49.25, "GBP": 58.75}},
        )
        assert rates.status_code == 200
        assert rates.json()["saved"] == {
            "USD": 45.5,
            "EUR": 49.25,
            "GBP": 58.75,
        }

        with sqlite3.connect(tenant_path) as tenant:
            settings = dict(
                tenant.execute(
                    "SELECT key,value FROM settings WHERE key IN "
                    "('default_vat_percent','vat_default_rate')"
                ).fetchall()
            )
            stored_rates = dict(
                tenant.execute(
                    "SELECT currency,selling_rate FROM exchange_rates "
                    "WHERE source='MANUAL'"
                ).fetchall()
            )
        assert settings == {
            "default_vat_percent": "8.5",
            "vat_default_rate": "8.5",
        }
        assert stored_rates == {"USD": 45.5, "EUR": 49.25, "GBP": 58.75}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
