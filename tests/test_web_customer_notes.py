import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_customer_note_editor_has_a_confirmed_delete_action():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = source.index("function openCustomerNotes(")
    end = source.index("\nfunction ", start + 10)
    editor = source[start:end]
    assert 'id="customerNoteDelete"' in editor
    assert '"/api/desktop/table/customer_notes"' in editor
    assert '_action:"delete"' in editor
    assert "confirmation.addEventListener(\"close\"" in editor
    assert "classList.add(\"danger\")" in editor


def test_customer_note_delete_uses_the_authenticated_tenant_table(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        web_main._partner_notes_table(conn)
        conn.execute(
            "INSERT INTO customer_notes (id,customer_id,type,title,content,created_at) VALUES (?,?,?,?,?,?)",
            (701, 11, "General Note", "Audit note", "Delete this note", "2026-01-01T00:00:00"),
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
        assert login.status_code == 200

        response = session.post(
            f"{base_url}/api/desktop/table/customer_notes",
            json={"id": 701, "_action": "delete"},
        )
        assert response.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM customer_notes WHERE id=701").fetchone()[0] == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
