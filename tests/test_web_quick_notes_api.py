import json
import sqlite3
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import Web_Arayuzu.Main as web


def test_authenticated_tenant_api_round_trips_fast_note_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(web, "DB_PATH", tmp_path / "registry.sqlite")
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    monkeypatch.setattr(web, "TENANT_ROOT", tenant_root)
    tenant = web.create_tenant("Quick Notes API Test", email="qa@example.invalid")

    with sqlite3.connect(web._tenant_path(tenant)) as conn:
        conn.execute(
            "INSERT INTO users(username, password, email, role, active, full_name) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (
                "qa",
                web.password_hash("test-password"),
                "qa@example.invalid",
                "Admin",
                "QA User",
            ),
        )

    token, _ = web.create_session(
        1, False, "Quick Notes API Test", "127.0.0.1", tenant["id"]
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.AYECRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    headers = {
        "Cookie": f"{web.SESSION_COOKIE}={token}",
        "Content-Type": "application/json",
    }

    def request(path, payload=None):
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        req = urllib.request.Request(
            base_url + path,
            data=body,
            headers=headers,
            method="POST" if payload is not None else "GET",
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read())

    try:
        status, inserted = request(
            "/api/desktop/table/fast_notes",
            {
                "category": "Ariza Notu",
                "label": "Check scope",
                "is_active": 1,
                "display_order": 4,
                "display_category": "Clinic",
                "title": "Repair macro",
            },
        )
        assert status == 200
        assert inserted["action"] == "insert"

        status, listing = request("/api/desktop/table/fast_notes?limit=200")
        assert status == 200
        row = listing["rows"][0]
        assert row["display_category"] == "Clinic"
        assert row["title"] == "Repair macro"

        status, updated = request(
            "/api/desktop/table/fast_notes",
            {
                "id": row["id"],
                "_action": "update",
                "category": "Ariza Notu",
                "label": "Updated content",
                "is_active": 0,
                "display_order": 7,
                "display_category": "Custom Clinic",
                "title": "Updated title",
            },
        )
        assert status == 200
        assert updated["action"] == "update"

        _, listing = request("/api/desktop/table/fast_notes?limit=200")
        row = listing["rows"][0]
        assert row["display_category"] == "Custom Clinic"
        assert row["title"] == "Updated title"
        assert row["label"] == "Updated content"
        assert row["display_order"] == 7
        assert row["is_active"] == 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        web.delete_session(token)
