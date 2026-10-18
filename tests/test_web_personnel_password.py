import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from src.utils.password_security import hash_password, verify_password
from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_personnel_editor_never_exposes_hash_and_supports_policy_checked_password_reset(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        web_main.desktop_personnel_daily_wages(conn, "2026", "2")
        columns = set(web_main.table_columns(conn, "personnel"))
        if "password_hash" not in columns:
            conn.execute("ALTER TABLE personnel ADD COLUMN password_hash TEXT")
        conn.execute(
            "INSERT INTO personnel(name,role,password_hash) VALUES(?,?,?)",
            ("Staff One", "Technician", hash_password("OldPassword123!")),
        )
        person_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    path = f"{base_url}/api/desktop/table/personnel"
    session = requests.Session()
    session.headers["Origin"] = base_url
    try:
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200

        fetched = session.get(f"{path}?limit=1000&include_deleted=1")
        assert fetched.status_code == 200
        assert "password_hash" not in fetched.json()["columns"]
        record = next(row for row in fetched.json()["rows"] if row["id"] == person_id)
        assert "password_hash" not in record

        direct_hash_write = session.post(path, json={"id": person_id, "_action": "update", "name": "Staff Two", "password_hash": "attacker-value"})
        assert direct_hash_write.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            stored = conn.execute("SELECT password_hash FROM personnel WHERE id=?", (person_id,)).fetchone()[0]
        assert verify_password("OldPassword123!", stored)[0]

        invalid_reset = session.post(path, json={"id": person_id, "_action": "update", "new_password": "weak"})
        assert invalid_reset.status_code == 400
        valid_reset = session.post(path, json={"id": person_id, "_action": "update", "new_password": "NewPassword123!"})
        assert valid_reset.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            stored = conn.execute("SELECT password_hash FROM personnel WHERE id=?", (person_id,)).fetchone()[0]
        assert verify_password("NewPassword123!", stored)[0]
        assert not verify_password("OldPassword123!", stored)[0]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_personnel_generic_editor_uses_a_separate_password_input():
    app = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
    start = app.index("function openGenericDialog(")
    end = app.index("\n}", start) + 2
    editor = app[start:end]
    assert "password_hash" in editor
    assert 'name="new_password" type="password"' in editor
    assert "autocomplete=\"new-password\"" in editor


def test_user_table_api_never_returns_authentication_secrets(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        columns = set(web_main.table_columns(conn, "users"))
        for column in ("remember_token", "secret_answer", "secret_answer_hash"):
            if column not in columns:
                conn.execute(f'ALTER TABLE users ADD COLUMN "{column}" TEXT')
        conn.execute(
            "UPDATE users SET remember_token=?,secret_answer=?,secret_answer_hash=? WHERE id=1",
            ("remember-secret", "answer-secret", "answer-hash-secret"),
        )

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    session = requests.Session()
    session.headers["Origin"] = base_url
    try:
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        fetched = session.get(f"{base_url}/api/desktop/table/users?limit=1000")
        assert fetched.status_code == 200
        result = fetched.json()
        private = {
            "password", "remember_token", "secret_answer", "secret_answer_hash",
            "security_answer_hash", "reset_token", "reset_token_expires",
        }
        assert not private.intersection(result["columns"])
        assert all(not private.intersection(row) for row in result["rows"])
        assert "remember-secret" not in fetched.text
        assert "answer-hash-secret" not in fetched.text
        direct_secret_write = session.post(
            f"{base_url}/api/desktop/table/users",
            json={
                "id": 1,
                "_action": "update",
                "active": 1,
                "password": "attacker-password",
                "remember_token": "attacker-token",
                "secret_answer_hash": "attacker-answer-hash",
            },
        )
        assert direct_secret_write.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            stored = conn.execute(
                "SELECT password,remember_token,secret_answer_hash FROM users WHERE id=1"
            ).fetchone()
        assert web_main.password_matches("oldpass123", stored[0])
        assert stored[1:] == ("remember-secret", "answer-hash-secret")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
