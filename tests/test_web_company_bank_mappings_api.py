import sqlite3
import threading
from contextlib import closing
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_company_bank_mapping_lifecycle_is_authenticated_and_admin_only(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with closing(sqlite3.connect(tenant_path)) as conn:
        conn.execute("DELETE FROM product_bank_mappings")
        cursor = conn.execute(
            "INSERT INTO product_bank_mappings "
            "(item_type,item_id,bank_account_id,default_kdv_rate,default_category) "
            "VALUES(?,?,?,?,?)",
            ("service", 8802, 9101, 20, "Service"),
        )
        mapping_id = cursor.lastrowid
        conn.execute(
            "INSERT INTO users(username,password,email,phone,role,active) "
            "VALUES(?,?,?,?,?,1)",
            ("tech", web_main.password_hash("tech-test-pass"), "tech@example.com", "", "Technician"),
        )
        conn.commit()

    other_path = tenant_path.parent / "Other Company.db"
    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active) "
            "VALUES(?,?,?,?,1)",
            ("tenant-2", "Other Company", other_path.name, "2026-01-02T00:00:00"),
        )
    with closing(sqlite3.connect(other_path)) as conn:
        web_main.ensure_operational_schema(conn)
        web_main.ensure_web_schema(conn)
        conn.execute(
            "INSERT INTO product_bank_mappings "
            "(id,item_type,item_id,bank_account_id,default_kdv_rate,default_category) "
            "VALUES(1,?,?,?,?,?)",
            ("service", 8802, 9102, 77, "Private"),
        )
        conn.commit()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        admin = requests.Session()
        admin.headers["Origin"] = base_url
        login = admin.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200

        created = admin.post(
            f"{base_url}/api/desktop/table/product_bank_mappings",
            json={
                "item_type": "product",
                "item_id": 8801,
                "bank_account_id": 9101,
                "default_kdv_rate": 18.5,
                "default_category": "Service",
            },
        )
        assert created.status_code == 200
        created_id = created.json()["id"]
        with closing(sqlite3.connect(tenant_path)) as conn:
            created_row = conn.execute(
                "SELECT item_type,item_id,bank_account_id,default_kdv_rate,default_category "
                "FROM product_bank_mappings WHERE id=?",
                (created_id,),
            ).fetchone()
        assert created_row == ("product", 8801, 9101, 18.5, "Service")
        listed = admin.get(f"{base_url}/api/desktop/table/product_bank_mappings?limit=1000")
        assert listed.status_code == 200
        assert {row["item_id"] for row in listed.json()["rows"]} == {8801, 8802}

        updated = admin.post(
            f"{base_url}/api/desktop/table/product_bank_mappings",
            json={"id": mapping_id, "_action": "update", "default_kdv_rate": 16.25},
        )
        assert updated.status_code == 200
        with closing(sqlite3.connect(tenant_path)) as conn:
            updated_rate = conn.execute(
                "SELECT default_kdv_rate FROM product_bank_mappings WHERE id=?",
                (mapping_id,),
            ).fetchone()[0]
        assert updated_rate == 16.25
        with closing(sqlite3.connect(other_path)) as conn:
            other_rate = conn.execute(
                "SELECT default_kdv_rate FROM product_bank_mappings WHERE id=?",
                (mapping_id,),
            ).fetchone()[0]
        assert other_rate == 77

        technician = requests.Session()
        technician.headers["Origin"] = base_url
        tech_login = technician.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "tech", "password": "tech-test-pass", "tenant_id": "tenant-1"},
        )
        assert tech_login.status_code == 200
        denied = technician.post(
            f"{base_url}/api/desktop/table/product_bank_mappings",
            json={"id": mapping_id, "_action": "update", "default_kdv_rate": 99},
        )
        assert denied.status_code == 403

        deleted = admin.post(
            f"{base_url}/api/desktop/table/product_bank_mappings",
            json={"id": created_id, "_action": "delete"},
        )
        assert deleted.status_code == 200
        with closing(sqlite3.connect(tenant_path)) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM product_bank_mappings WHERE id=?",
                (created_id,),
            ).fetchone()[0] == 0
            assert conn.execute(
                "SELECT default_kdv_rate FROM product_bank_mappings WHERE id=?",
                (mapping_id,),
            ).fetchone()[0] == 16.25
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
