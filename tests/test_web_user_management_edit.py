import sqlite3
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def _edit_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, email TEXT, phone TEXT, role TEXT, full_name TEXT, personnel_id INTEGER, active INTEGER, permissions TEXT, interface_edit_access INTEGER, auto_login INTEGER, password_updated_at TEXT, secret_question TEXT, secret_answer_hash TEXT);"
        "CREATE TABLE personnel (id INTEGER PRIMARY KEY, name TEXT);"
        "CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT);"
        "INSERT INTO users VALUES (1,'admin','hash','admin@example.test',NULL,'Admin','Admin',NULL,1,'{}',1,0,NULL,NULL,NULL);"
        "INSERT INTO users VALUES (2,'operator','oldhash','operator@example.test',NULL,'Teknisyen','Operator',NULL,1,'{}',0,0,NULL,NULL,NULL);"
        "INSERT INTO users VALUES (3,'other','oldhash','other@example.test',NULL,'Teknisyen','Other',NULL,1,'{}',0,0,NULL,NULL,NULL);"
        "INSERT INTO personnel VALUES (9,'Operator Personel');"
    )
    return conn


def test_managed_user_edit_updates_desktop_fields_and_hashes_secrets():
    conn = _edit_db()
    result = web_main.desktop_update_managed_user(
        conn,
        {"id": 1, "role": "Admin"},
        {
            "user_id": 2,
            "username": "operator.new",
            "full_name": "Operator New",
            "email": "operator.new@example.test",
            "phone": "+90 555 123 45 67",
            "role": "Teknisyen",
            "personnel_id": 9,
            "active": 0,
            "auto_login": 1,
            "interface_edit_access": 1,
            "permissions": {"pages": [40, 50]},
            "password": "EditStrongPass42",
            "secret_question": "First school?",
            "secret_answer": "Example Answer",
        },
    )
    row = conn.execute("SELECT * FROM users WHERE id=2").fetchone()
    assert result["ok"] is True
    assert (row["username"], row["full_name"], row["role"], row["personnel_id"]) == (
        "operator.new",
        "Operator New",
        "Teknisyen",
        9,
    )
    assert (row["active"], row["auto_login"], row["interface_edit_access"]) == (0, 1, 1)
    assert row["permissions"] == '{"pages":[40,50]}'
    assert web_main.password_matches("EditStrongPass42", row["password"])
    assert row["password_updated_at"]
    assert row["secret_question"] == "First school?"
    assert row["secret_answer_hash"] == web_main.hashlib.sha256(b"example answer").hexdigest()
    assert conn.execute("SELECT action FROM audit_logs").fetchone()[0] == "USER_UPDATED"


def test_managed_user_edit_rejects_invalid_fields_and_rolls_back_audit_failure():
    conn = _edit_db()
    base = {"user_id": 2, "username": "operator", "role": "Teknisyen"}
    with pytest.raises(ValueError, match="already in use"):
        web_main.desktop_update_managed_user(
            conn, {"id": 1, "role": "Admin"}, {**base, "username": "other"}
        )
    with pytest.raises(ValueError, match="provided together"):
        web_main.desktop_update_managed_user(
            conn, {"id": 1, "role": "Admin"}, {**base, "secret_question": "Question"}
        )
    with pytest.raises(ValueError, match="personnel record"):
        web_main.desktop_update_managed_user(
            conn, {"id": 1, "role": "Admin"}, {**base, "personnel_id": 999}
        )
    conn.execute(
        "CREATE TRIGGER reject_audit BEFORE INSERT ON audit_logs BEGIN SELECT RAISE(ABORT, 'audit failed'); END;"
    )
    with pytest.raises(sqlite3.IntegrityError, match="audit failed"):
        web_main.desktop_update_managed_user(
            conn,
            {"id": 1, "role": "Admin"},
            {**base, "username": "changed.name"},
        )
    assert conn.execute("SELECT username FROM users WHERE id=2").fetchone()[0] == "operator"


def test_managed_user_edit_requires_admin_and_immutable_builtin_name():
    conn = _edit_db()
    with pytest.raises(PermissionError, match="Administrator"):
        web_main.desktop_update_managed_user(
            conn, {"id": 1, "role": "Teknisyen"}, {"user_id": 2, "username": "operator"}
        )
    with pytest.raises(PermissionError, match="built-in account name"):
        web_main.desktop_update_managed_user(
            conn,
            {"id": 1, "role": "Admin"},
            {"user_id": 1, "username": "renamed.admin", "role": "Admin"},
        )


def test_http_managed_user_edit_is_authenticated_and_tenant_scoped(monkeypatch, tmp_path):
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
        created = session.post(
            f"{base_url}/api/desktop/users",
            json={
                "full_name": "Edit Target",
                "username": "edit.target",
                "password": "StrongPass123",
                "role": "Teknisyen",
                "active": 1,
                "permissions": {"pages": [40]},
            },
        )
        assert created.status_code == 201
        target_id = created.json()["user_id"]
        response = session.post(
            f"{base_url}/api/desktop/users/update",
            json={
                "user_id": target_id,
                "username": "edit.target.new",
                "full_name": "Edited Target",
                "email": "edited.target@example.test",
                "phone": "+90 555 123 45 67",
                "role": "Teknisyen",
                "active": 0,
                "auto_login": 1,
                "permissions": {"pages": [40, 50]},
            },
        )
        assert response.status_code == 200
        assert response.json()["username"] == "edit.target.new"
        anonymous = requests.post(
            f"{base_url}/api/desktop/users/update",
            json={"user_id": target_id, "username": "edit.target"},
            headers={"Origin": base_url},
        )
        assert anonymous.status_code == 401
        with sqlite3.connect(tenant_path) as conn:
            row = conn.execute(
                "SELECT username,full_name,email,phone,active,auto_login,permissions FROM users WHERE id=?",
                (target_id,),
            ).fetchone()
            assert row == (
                "edit.target.new",
                "Edited Target",
                "edited.target@example.test",
                "+90 555 123 45 67",
                0,
                1,
                '{"pages":[40,50]}',
            )
            assert conn.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE action='USER_UPDATED'"
            ).fetchone()[0] == 1
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
