import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_knowledge_articles_create_search_update_delete_in_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    table_url = f"{base_url}/api/desktop/table/kb_articles"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(table_url).status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        added = session.post(table_url, json={"title": "Repair guide", "content": "Inspect the sensor connector", "tags": "sensor, engine"})
        assert added.status_code == 200
        article_id = added.json()["id"]
        result = session.get(f"{table_url}?q=sensor").json()
        assert [row["id"] for row in result["rows"]] == [article_id]
        changed = session.post(table_url, json={"id": article_id, "_action": "update", "title": "Repair guide v2"})
        assert changed.status_code == 200
        assert session.get(f"{table_url}?q=v2").json()["rows"][0]["title"] == "Repair guide v2"
        removed = session.post(table_url, json={"id": article_id, "_action": "delete"})
        assert removed.status_code == 200
        assert session.get(table_url).json()["rows"] == []
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM kb_articles").fetchone()[0] == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
