import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def _actor():
    return {"id": 1, "role": "Admin"}


def _delete_db(schema):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(schema)
    return conn


def test_managed_user_delete_prefers_deleted_flag_and_sets_inactive():
    conn = _delete_db(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, active INTEGER, is_deleted INTEGER);"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT);"
        "INSERT INTO users VALUES (1,'admin',1,0);"
        "INSERT INTO users VALUES (2,'operator',1,0);"
    )
    result = web_main.desktop_delete_managed_user(conn, _actor(), 2)
    row = conn.execute("SELECT active,is_deleted FROM users WHERE id=2").fetchone()
    assert result["mode"] == "is_deleted"
    assert tuple(row) == (0, 1)
    assert conn.execute("SELECT action FROM audit_logs").fetchone()[0] == "USER_DELETED"


def test_managed_user_delete_uses_legacy_soft_delete_and_hard_delete_fallback():
    active_conn = _delete_db(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, is_active INTEGER, deleted_at TEXT);"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT);"
        "INSERT INTO users VALUES (1,'admin',1,NULL);"
        "INSERT INTO users VALUES (2,'operator',1,NULL);"
    )
    active_result = web_main.desktop_delete_managed_user(active_conn, _actor(), 2)
    active_row = active_conn.execute("SELECT is_active,deleted_at FROM users WHERE id=2").fetchone()
    assert active_result["mode"] == "is_active"
    assert active_row[0] == 0 and active_row[1]

    hard_conn = _delete_db(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT);"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT);"
        "INSERT INTO users VALUES (1,'admin');"
        "INSERT INTO users VALUES (2,'operator');"
    )
    hard_result = web_main.desktop_delete_managed_user(hard_conn, _actor(), 2)
    assert hard_result["mode"] == "hard_delete"
    assert hard_conn.execute("SELECT COUNT(*) FROM users WHERE id=2").fetchone()[0] == 0
    assert hard_conn.execute("SELECT action FROM audit_logs").fetchone()[0] == "USER_DELETED"


def test_managed_user_delete_is_admin_only_self_protected_and_atomic():
    conn = _delete_db(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, active INTEGER);"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT);"
        "CREATE TRIGGER reject_delete_audit BEFORE INSERT ON audit_logs BEGIN SELECT RAISE(ABORT, 'audit failed'); END;"
        "INSERT INTO users VALUES (1,'admin',1);"
        "INSERT INTO users VALUES (2,'operator',1);"
    )
    with pytest.raises(PermissionError, match="own account"):
        web_main.desktop_delete_managed_user(conn, _actor(), 1)
    with pytest.raises(PermissionError, match="Administrator"):
        web_main.desktop_delete_managed_user(conn, {"id": 3, "role": "Manager"}, 2)
    with pytest.raises(sqlite3.IntegrityError, match="audit failed"):
        web_main.desktop_delete_managed_user(conn, _actor(), 2)
    assert conn.execute("SELECT active FROM users WHERE id=2").fetchone()[0] == 1


def test_http_managed_user_delete_uses_active_tenant_and_blocks_self(monkeypatch, tmp_path):
    _actor_fixture, tenant_path = _setup_tenant(monkeypatch, tmp_path)
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
            f"{base_url}/api/desktop/users/delete", json={"user_id": 1}
        )
        assert response.status_code == 200
        assert response.json()["user_id"] == 1
        self_delete = session.post(
            f"{base_url}/api/desktop/users/delete", json={"user_id": 2}
        )
        assert self_delete.status_code == 403
        assert "own account" in self_delete.json()["error"]
        with sqlite3.connect(tenant_path) as conn:
            columns = {row[1] for row in conn.execute('PRAGMA table_info("users")')}
            if "is_deleted" in columns:
                assert conn.execute("SELECT is_deleted FROM users WHERE id=1").fetchone()[0] == 1
            elif "is_archived" in columns:
                assert conn.execute("SELECT is_archived FROM users WHERE id=1").fetchone()[0] == 1
            elif "active" in columns:
                assert conn.execute("SELECT active FROM users WHERE id=1").fetchone()[0] == 0
            assert conn.execute(
                "SELECT action FROM audit_logs WHERE table_name='users' ORDER BY id DESC LIMIT 1"
            ).fetchone()[0] == "USER_DELETED"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_settings_profile_offers_admin_only_delete_action():
    root = Path(__file__).resolve().parents[1]
    source = (root / "Web_Arayuzu" / "web" / "user-management-reference.js").read_text(
        encoding="utf-8"
    )
    assert "data-managed-user-delete" in source
    assert 'apiFetch("/api/desktop/users/delete"' in source
    assert 'String(target.id)===String(currentAuthUser?.id)' in source
    assert 'userAdminRole(currentAuthUser?.role)' in source
