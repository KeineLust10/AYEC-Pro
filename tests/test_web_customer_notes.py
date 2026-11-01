import sqlite3
import shutil
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_customer_note_offscreen_delete_audit_checks_cancel_before_write():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "customerNotesDeleteWorkflow.cancelNoWrite" in route_smoke
    assert "customerNotesDeleteWorkflow.deleteFailureRetained" in route_smoke
    assert 'QA customer note delete unavailable' in route_smoke
    assert "customerNotesDeleteWorkflow.deleteAttempts!==2" in route_smoke


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


def test_customer_note_date_insert_uses_the_local_calendar_date():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = source.index("function openCustomerNotes(")
    end = source.index("\nfunction ", start + 10)
    editor = source[start:end]
    assert '$("[data-cnote-date]",bodyNode).addEventListener("mousedown",rememberNoteRange)' in editor
    assert 'if(!restoreNoteRange())editor.focus();document.execCommand("insertText",false,today());value.value=editor.innerHTML' in editor
    assert 'textContent="Kaydedilmedi"' in editor
    assert 'new Date().toISOString().slice(0,10)' not in editor
    assert "const today = () => ayecLocalDateKey(new Date());" in source


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


def test_customer_note_create_update_delete_roundtrip_uses_returned_row_id(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active,product_code) VALUES(?,?,?,?,1,?)",
            ("tenant-2", "Second Company", "Second Company.db", "2026-01-02T00:00:00", "teknik_servis"),
        )
    tenant_two_path = web_main.TENANT_ROOT / "Second Company.db"
    shutil.copy2(tenant_path, tenant_two_path)
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
        other_session = requests.Session()
        other_session.headers["Origin"] = base_url
        other_login = other_session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-2"},
        )
        assert other_login.status_code == 200

        created = session.post(
            f"{base_url}/api/desktop/table/customer_notes",
            json={"customer_id": 11, "type": "SMS", "note_type": "SMS", "title": "Follow up", "content": "First body"},
        )
        assert created.status_code == 200
        note_id = created.json()["id"]
        assert isinstance(note_id, int) and note_id > 0
        other_rows = other_session.get(f"{base_url}/api/desktop/table/customer_notes?limit=1000")
        assert other_rows.status_code == 200
        assert all(row["id"] != note_id for row in other_rows.json()["rows"])

        updated = session.post(
            f"{base_url}/api/desktop/table/customer_notes",
            json={"id": note_id, "_action": "update", "customer_id": 11, "type": "SMS", "note_type": "SMS", "title": "Updated follow up", "content": "Revised body"},
        )
        assert updated.status_code == 200
        assert updated.json()["id"] == note_id

        listed = session.get(f"{base_url}/api/desktop/table/customer_notes?limit=1000")
        assert listed.status_code == 200
        row = next(item for item in listed.json()["rows"] if item["id"] == note_id)
        assert (row["customer_id"], row["title"], row["content"]) == (11, "Updated follow up", "Revised body")

        deleted = session.post(
            f"{base_url}/api/desktop/table/customer_notes",
            json={"id": note_id, "_action": "delete"},
        )
        assert deleted.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM customer_notes WHERE id=?", (note_id,)).fetchone()[0] == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
