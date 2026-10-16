import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests
from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def test_desktop_audit_page_filters_search_severity_module_and_offset():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE audit_logs (id INTEGER, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT)"
    )
    records = [
        (1, "alice", "auth_sessions", "login", '{"severity":"SECURITY"}', "2026-10-13 10:00:00"),
        (2, "bob", "stock_movements", "insert", '{"severity":"INFO"}', "2026-10-13 09:00:00"),
        (3, "cara", "service_jobs", "update", '{"severity":"WARN"}', "2026-10-13 08:00:00"),
        (4, "dave", "bank_accounts", "delete", '{"severity":"CRITICAL"}', "2026-10-13 07:00:00"),
        (5, "erin", "company_settings", "update", '{}', "2026-10-13 06:00:00"),
    ]
    conn.executemany("INSERT INTO audit_logs VALUES (?, ?, ?, ?, ?, ?)", records)

    users, count, limit, offset = web_main.desktop_audit_page(
        conn, limit=2, offset=1, query="", hours="all", severity="Tumu", module=""
    )
    assert count == 5
    assert (limit, offset) == (2, 1)
    assert [row["id"] for row in users] == [2, 3]

    filtered, filtered_count, _, _ = web_main.desktop_audit_page(
        conn, limit=25, offset=0, query="bob", hours="all", severity="INFO", module="Stok Hareketi"
    )
    assert filtered_count == 1
    assert filtered[0]["id"] == 2

    security, security_count, _, _ = web_main.desktop_audit_page(
        conn, limit=25, offset=0, query="", hours="all", severity="SECURITY", module="Kullan\u0131c\u0131 Giri\u015fi"
    )
    assert security_count == 1
    assert security[0]["id"] == 1


def test_audit_account_suspension_is_admin_only_not_self_and_is_audited():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, active INTEGER);"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT);"
        "INSERT INTO users VALUES (1, 'admin', 1);"
        "INSERT INTO users VALUES (2, 'operator', 1);"
    )

    result = web_main.desktop_suspend_audit_account(
        conn, {"id": 1, "role": "Admin"}, 2
    )
    assert result == {"ok": True, "user_id": 2, "username": "operator", "active": False}
    assert conn.execute("SELECT active FROM users WHERE id=2").fetchone()[0] == 0
    audit = conn.execute("SELECT user_id, action, details FROM audit_logs").fetchone()
    assert audit[0] == "1"
    assert audit[1] == "ACCOUNT_SUSPENDED"
    assert '"target_user_id":2' in audit[2]

    import pytest

    with pytest.raises(PermissionError, match="own account"):
        web_main.desktop_suspend_audit_account(conn, {"id": 1, "role": "Admin"}, 1)
    with pytest.raises(PermissionError, match="Administrator"):
        web_main.desktop_suspend_audit_account(conn, {"id": 3, "role": "Manager"}, 1)


def test_http_audit_account_suspension_keeps_tenant_session_and_blocks_self(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200
        response = session.post(
            f"{base_url}/api/desktop/audit/suspend-user", json={"user_id": 1}
        )
        assert response.status_code == 200
        assert response.json()["active"] is False
        self_suspend = session.post(
            f"{base_url}/api/desktop/audit/suspend-user", json={"user_id": 2}
        )
        assert self_suspend.status_code == 403
        assert "own account" in self_suspend.json()["error"]
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT active FROM users WHERE id=1").fetchone()[0] == 0
            assert conn.execute(
                "SELECT action FROM audit_logs WHERE table_name='users' ORDER BY id DESC LIMIT 1"
            ).fetchone()[0] == "ACCOUNT_SUSPENDED"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_http_audit_event_pdf_uses_authenticated_tenant_record(monkeypatch, tmp_path):
    from src.utils import audit_export

    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO audit_logs(user_id,table_name,action,details,created_at) VALUES(?,?,?,?,?)",
            ("2", "stock_movements", "UPDATE", "recorded payload", "2026-10-14 10:00:00"),
        )
        event_id = conn.execute("SELECT id FROM audit_logs ORDER BY id DESC LIMIT 1").fetchone()[0]

    exported = {}

    def write_pdf(path, record):
        exported["record"] = tuple(record)
        path.write_bytes(b"%PDF-1.4\nverified test report\n%%EOF")

    monkeypatch.setattr(audit_export, "export_audit_event_pdf", write_pdf)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.get(f"{base_url}/api/desktop/audit/event-pdf?id={event_id}")
        assert anonymous.status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200
        response = session.get(f"{base_url}/api/desktop/audit/event-pdf?id={event_id}")
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/pdf"
        assert response.headers["Content-Disposition"] == f'attachment; filename="audit_event_{event_id}.pdf"'
        assert response.content.startswith(b"%PDF-")
        assert exported["record"][0] == event_id
        assert exported["record"][2:] == (
            "stock_movements",
            "UPDATE",
            "recorded payload",
            "2026-10-14 10:00:00",
        )
        missing = session.get(f"{base_url}/api/desktop/audit/event-pdf?id=999999")
        assert missing.status_code == 404
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_audit_page_uses_desktop_workflow_controls_and_server_filters():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    app = (root / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    page = (root / "Web_Arayuzu" / "web" / "audit-reference.js").read_text(encoding="utf-8")
    index = (root / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")

    assert "audit:renderAuditReference" in app
    assert "bindAuditReference();loadAuditReference()" in app
    assert "audit_logs?${params}" in page
    assert "data-audit-severity" in page
    assert "data-audit-live" in page
    assert "data-audit-prev" in page and "data-audit-next" in page
    assert "auditReferenceInspector" in page
    assert "auditReferenceExport" in page
    assert "/api/desktop/audit/suspend-user" in page
    assert "/api/desktop/audit/event-pdf?id=" in page
    assert "window.print()" not in page
    assert "auditReferencePrint" in page
    assert "desktop_suspend_audit_account" in (root / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    assert "audit-reference.js" in index
    assert "audit-reference.css" in index
