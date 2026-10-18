import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_personnel_table_can_include_archived_rows(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute("ALTER TABLE personnel ADD COLUMN is_deleted INTEGER DEFAULT 0")
        conn.execute(
            "INSERT INTO personnel(name, role, is_deleted) VALUES(?,?,?)",
            ("Active worker", "Teknisyen", 0),
        )
        conn.execute(
            "INSERT INTO personnel(name, role, is_deleted) VALUES(?,?,?)",
            ("Archived worker", "Teknisyen", 1),
        )

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200, login.text

        default = session.get(f"{base_url}/api/desktop/table/personnel?limit=100")
        assert default.status_code == 200, default.text
        assert {row["name"] for row in default.json()["rows"]} == {"Active worker"}

        inclusive = session.get(f"{base_url}/api/desktop/table/personnel?limit=100&include_deleted=1")
        assert inclusive.status_code == 200, inclusive.text
        assert {row["name"] for row in inclusive.json()["rows"]} == {"Active worker", "Archived worker"}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
