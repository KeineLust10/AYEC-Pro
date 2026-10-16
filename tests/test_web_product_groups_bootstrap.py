import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_product_group_page_bootstrap_seeds_device_types_in_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute("DROP TABLE IF EXISTS product_groups")
        conn.execute("DELETE FROM device_brands")
        conn.execute("INSERT INTO device_brands (device_type,brand,is_active) VALUES (?,?,1)", ("Tablet Audit", "Brand A"))
        conn.execute("CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY, device_type TEXT)")
        conn.execute("DELETE FROM devices")
        conn.execute("INSERT INTO devices (device_type) VALUES (?)", ("Workshop IoT",))

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    bootstrap_url = f"{base_url}/api/desktop/product-groups/bootstrap"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(bootstrap_url).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200

        seeded = session.get(bootstrap_url)
        assert seeded.status_code == 200
        assert seeded.json()["seeded"] == 2
        rows = session.get(f"{base_url}/api/desktop/table/product_groups?limit=1000").json()["rows"]
        assert {row["name"] for row in rows} == {"Tablet Audit", "Workshop IoT"}
        assert all(row["is_active"] == 1 for row in rows)
        assert session.get(bootstrap_url).json()["seeded"] == 0

        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM product_groups").fetchone()[0] == 2
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
