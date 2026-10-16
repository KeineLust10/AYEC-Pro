import json
import sqlite3
import threading
import urllib.request
from http.server import ThreadingHTTPServer

import Web_Arayuzu.Main as web


def test_customer_note_fields_migrate_without_losing_legacy_data(tmp_path):
    db_path = tmp_path / "legacy_customer_notes.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE customer_notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, type TEXT, "
        "content TEXT, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO customer_notes(customer_id, type, content, created_at) "
        "VALUES(?, ?, ?, ?)",
        (7, "Call", "Existing note", "2026-10-14T10:00:00"),
    )
    web._ensure_path_schema(conn, db_path)

    columns = {row[1] for row in conn.execute('PRAGMA table_info("customer_notes")')}
    assert {"note_type", "title"}.issubset(columns)
    assert conn.execute(
        "SELECT customer_id, type, content, created_at FROM customer_notes"
    ).fetchone() == (7, "Call", "Existing note", "2026-10-14T10:00:00")
    conn.close()


def test_pc_builder_quote_note_and_finance_persist_in_authenticated_tenant(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(web, "DB_PATH", tmp_path / "registry.sqlite")
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    monkeypatch.setattr(web, "TENANT_ROOT", tenant_root)
    tenant = web.create_tenant("PC Builder Persistence Test", email="qa@example.invalid")
    tenant_db = web._tenant_path(tenant)

    with sqlite3.connect(tenant_db) as conn:
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
        customer_id = conn.execute(
            "INSERT INTO customers(name, email, type) VALUES (?, ?, ?)",
            ("QA Customer", "customer@example.invalid", "Bireysel"),
        ).lastrowid

    token, _ = web.create_session(
        1, False, "PC Builder Persistence Test", "127.0.0.1", tenant["id"]
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
        status, saved_note = request(
            "/api/desktop/table/customer_notes",
            {
                "customer_id": customer_id,
                "note_type": "PC Teklif",
                "type": "PC Teklif",
                "title": "PC Teklif #PC-QA-1",
                "content": "Build quote detail",
                "created_at": "2026-10-14T10:00:00",
            },
        )
        assert status == 200
        assert saved_note["action"] == "insert"
        _, notes = request("/api/desktop/table/customer_notes?limit=100")
        note = next(row for row in notes["rows"] if row["id"] == saved_note["id"])
        assert note["customer_id"] == customer_id
        assert note["note_type"] == "PC Teklif"
        assert note["type"] == "PC Teklif"
        assert note["title"] == "PC Teklif #PC-QA-1"
        assert note["content"] == "Build quote detail"

        status, saved_finance = request(
            "/api/desktop/table/accounting",
            {
                "type": "Gelir",
                "category": "Sat\u0131\u015f",
                "amount": 1200,
                "description": "Bilgisayar Topla / Teklif #PC-QA-1",
                "customer_name": "QA Customer",
                "customer_id": customer_id,
                "payment_method": "Nakit",
                "currency": "TRY",
                "date": "2026-10-14T10:00:00",
            },
        )
        assert status == 200
        assert saved_finance["action"] == "insert"
        _, finance_rows = request("/api/desktop/table/accounting?limit=100")
        finance = next(
            row for row in finance_rows["rows"] if row["id"] == saved_finance["id"]
        )
        assert finance["type"] == "Gelir"
        assert finance["category"] == "Sat\u0131\u015f"
        assert finance["amount"] == 1200
        assert finance["customer_id"] == customer_id
        assert finance["description"] == "Bilgisayar Topla / Teklif #PC-QA-1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        web.delete_session(token)
