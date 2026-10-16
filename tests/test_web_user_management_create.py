import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests
import pytest

from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def _create_payload(**overrides):
    payload = {
        "full_name": "Taylor Example",
        "username": "taylor.example",
        "password": "StrongPass123",
        "email": "taylor@example.test",
        "phone": "+90 555 123 45 67",
        "department": "Teknik Servis",
        "role": "Teknisyen",
        "active": 1,
        "permissions": {"pages": [40, 41, 50]},
    }
    payload.update(overrides)
    return payload


def test_managed_user_creation_adds_personnel_user_permission_and_audit_atomically():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, email TEXT, phone TEXT, role TEXT, created_at TEXT, full_name TEXT, personnel_id INTEGER, active INTEGER, permissions TEXT, interface_edit_access INTEGER);"
        "CREATE TABLE personnel (id INTEGER PRIMARY KEY, name TEXT, role TEXT, phone TEXT, email TEXT, department TEXT, active INTEGER, created_at TEXT);"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT);"
        "INSERT INTO users (username,password,role,active) VALUES ('admin','hash','Admin',1);"
    )
    result = web_main.desktop_create_managed_user(
        conn, {"id": 1, "role": "Admin"}, _create_payload()
    )
    assert result["ok"] is True
    user = conn.execute("SELECT * FROM users WHERE id=?", (result["user_id"],)).fetchone()
    staff = conn.execute("SELECT * FROM personnel WHERE id=?", (user["personnel_id"],)).fetchone()
    assert web_main.password_matches("StrongPass123", user["password"])
    assert user["role"] == "Teknisyen"
    assert user["permissions"] == '{"pages":[40,41,50]}'
    assert (staff["name"], staff["department"], staff["active"]) == (
        "Taylor Example",
        "Teknik Servis",
        1,
    )
    assert conn.execute("SELECT action FROM audit_logs").fetchone()[0] == "USER_CREATED"
    assert "StrongPass123" not in user["password"]


def test_managed_user_creation_rejects_non_admin_duplicate_and_weak_password():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, email TEXT, role TEXT, active INTEGER);"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT);"
        "INSERT INTO users VALUES (1,'admin','hash','admin@example.test','Admin',1);"
    )
    with pytest.raises(PermissionError):
        web_main.desktop_create_managed_user(
            conn, {"id": 1, "role": "Manager"}, _create_payload()
        )
    with pytest.raises(ValueError, match="already in use"):
        web_main.desktop_create_managed_user(
            conn,
            {"id": 1, "role": "Admin"},
            _create_payload(username="admin"),
        )
    with pytest.raises(ValueError, match="10 characters"):
        web_main.desktop_create_managed_user(
            conn,
            {"id": 1, "role": "Admin"},
            _create_payload(password="weak"),
        )
    with pytest.raises(ValueError, match="supported desktop role"):
        web_main.desktop_create_managed_user(
            conn,
            {"id": 1, "role": "Admin"},
            _create_payload(role="manager"),
        )


def test_managed_user_creation_rolls_back_personnel_when_audit_insert_fails():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, email TEXT, role TEXT, active INTEGER, personnel_id INTEGER);"
        "CREATE TABLE personnel (id INTEGER PRIMARY KEY, name TEXT, role TEXT, active INTEGER);"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT);"
        "CREATE TRIGGER reject_audit BEFORE INSERT ON audit_logs BEGIN SELECT RAISE(ABORT, 'audit failed'); END;"
        "INSERT INTO users VALUES (1,'admin','hash','admin@example.test','Admin',1,NULL);"
    )
    with pytest.raises(sqlite3.IntegrityError, match="audit failed"):
        web_main.desktop_create_managed_user(
            conn, {"id": 1, "role": "Admin"}, _create_payload()
        )
    assert conn.execute("SELECT COUNT(*) FROM users WHERE username='taylor.example'").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM personnel WHERE name='Taylor Example'").fetchone()[0] == 0


def test_http_managed_user_creation_is_authenticated_and_tenant_scoped(monkeypatch, tmp_path):
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
        response = session.post(f"{base_url}/api/desktop/users", json=_create_payload())
        assert response.status_code == 201
        created = response.json()
        assert created["username"] == "taylor.example"
        assert created["role"] == "Teknisyen"
        users = session.get(f"{base_url}/api/desktop/table/users?limit=200")
        assert users.status_code == 200
        assert any(item["username"] == "taylor.example" for item in users.json()["rows"])
        assert all("password" not in item for item in users.json()["rows"])
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM users WHERE username='taylor.example'"
            ).fetchone()[0] == 1
            assert conn.execute(
                "SELECT COUNT(*) FROM personnel WHERE name='Taylor Example'"
            ).fetchone()[0] == 1
            assert conn.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE action='USER_CREATED'"
            ).fetchone()[0] == 1
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_user_settings_has_admin_only_create_control():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    source = (root / "Web_Arayuzu" / "web" / "user-management-reference.js").read_text(
        encoding="utf-8"
    )
    index = (root / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")
    assert 'userAdminRole(currentAuthUser?.role)' in source
    assert 'apiFetch("/api/desktop/users"' in source
    assert "renderUserPermissionMatrix" in source
    assert "user-management-reference.js" in index
