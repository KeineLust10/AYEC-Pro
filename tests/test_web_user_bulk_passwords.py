import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def _account_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, role TEXT, password TEXT, "
        "password_updated_at TEXT, must_change_password INTEGER, remember_token TEXT, auto_login INTEGER);"
        "INSERT INTO users VALUES (1,'Admin','admin-hash',NULL,0,'admin-token',1);"
        "INSERT INTO users VALUES (2,'Teknisyen','old-hash',NULL,1,'old-token',1);"
        "INSERT INTO users VALUES (3,'Muhasebe','old-hash',NULL,1,'old-token',1);"
        "INSERT INTO users VALUES (4,'Master','master-hash',NULL,0,'master-token',1);"
    )
    return conn


def test_bulk_password_update_uses_password_codec_and_clears_remembered_login():
    conn = _account_db()
    result = web_main.desktop_bulk_change_user_passwords(
        conn,
        {"id": 1, "role": "Admin"},
        {"changes": [
            {"user_id": 2, "password": "TechnicianPass42"},
            {"user_id": 3, "password": "AccountingPass42"},
        ]},
    )
    assert result == {"ok": True, "changed": 2}
    for user_id, password in ((2, "TechnicianPass42"), (3, "AccountingPass42")):
        row = conn.execute(
            "SELECT password,password_updated_at,must_change_password,remember_token,auto_login "
            "FROM users WHERE id=?", (user_id,),
        ).fetchone()
        assert web_main.password_matches(password, row["password"])
        assert row["password"] != password
        assert row["password_updated_at"]
        assert row["must_change_password"] == 0
        assert row["remember_token"] is None
        assert row["auto_login"] == 0


def test_bulk_password_update_rejects_privileged_accounts_and_invalid_passwords():
    conn = _account_db()
    actor = {"id": 1, "role": "Admin"}
    with pytest.raises(PermissionError):
        web_main.desktop_bulk_change_user_passwords(
            conn, {"id": 2, "role": "Teknisyen"},
            {"changes": [{"user_id": 3, "password": "AccountingPass42"}]},
        )
    for changes in (
        [{"user_id": 1, "password": "AdminPassword42"}],
        [{"user_id": 4, "password": "MasterPassword42"}],
        [{"user_id": 2, "password": "short"}],
        [{"user_id": 2, "password": "RepeatPassword42"},
         {"user_id": 3, "password": "RepeatPassword42"}],
    ):
        with pytest.raises((PermissionError, ValueError)):
            web_main.desktop_bulk_change_user_passwords(conn, actor, {"changes": changes})
    assert conn.execute("SELECT password FROM users WHERE id=2").fetchone()[0] == "old-hash"


def test_bulk_password_api_requires_admin_and_changes_only_active_tenant_users(monkeypatch, tmp_path):
    _setup_tenant(monkeypatch, tmp_path)
    tenant_path = web_main.TENANT_ROOT / "Test Company.db"
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO users(username,password,email,phone,role,active,remember_token,auto_login) "
            "VALUES(?,?,?,?,?,1,?,1)",
            ("bulk-tech", web_main.password_hash("InitialPass42"), "", "", "Teknisyen", "saved-token"),
        )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.post(
            f"{base_url}/api/desktop/users/bulk-passwords",
            json={"changes": [{"user_id": 3, "password": "NewTechnicianPass42"}]},
        )
        assert anonymous.status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        response = session.post(
            f"{base_url}/api/desktop/users/bulk-passwords",
            json={"changes": [{"user_id": 3, "password": "NewTechnicianPass42"}]},
        )
        assert response.status_code == 200, response.text
        assert response.json() == {"ok": True, "changed": 1}
        with sqlite3.connect(tenant_path) as conn:
            stored, remembered, auto_login = conn.execute(
                "SELECT password,remember_token,auto_login FROM users WHERE id=3"
            ).fetchone()
        assert web_main.password_matches("NewTechnicianPass42", stored)
        assert remembered is None
        assert auto_login == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)


def test_web_user_management_exposes_bulk_password_dialog():
    source = (Path(web_main.__file__).parent / "web" / "user-management-reference.js").read_text(encoding="utf-8")
    assert 'function ayecBulkPasswordsDialog()' in source
    assert 'data-managed-user-bulk-password' in source
    assert 'apiFetch("/api/desktop/users/bulk-passwords"' in source
    assert 'data-bulk-password-select' in source


def test_user_security_report_opens_existing_audit_view_in_a_wide_dialog():
    web_dir = Path(web_main.__file__).parent / "web"
    source = (web_dir / "user-management-reference.js").read_text(encoding="utf-8")
    audit = (web_dir / "audit-reference.js").read_text(encoding="utf-8")
    css = (web_dir / "audit-reference.css").read_text(encoding="utf-8")
    desktop = (Path(web_main.__file__).parents[1] / "src" / "ui" / "pages" / "settings_widgets" / "user_management.py").read_text(encoding="utf-8")
    assert 'self.security_report_button = security_report' in desktop
    assert 'function ayecOpenUserSecurityReport()' in source
    assert 'data-managed-user-security-report' in source
    assert 'renderAuditReference()' in source
    assert 'bindAuditReference();loadAuditReference()' in source
    assert '#appDialog.audit-report-dialog' in css
    assert 'auditReferenceState.paused' in audit


def test_user_list_filters_active_state_and_orders_newest_first():
    app = (Path(web_main.__file__).parent / "web" / "app.js").read_text(encoding="utf-8")
    reference = (Path(web_main.__file__).parent / "web" / "user-management-reference.js").read_text(encoding="utf-8")
    css = (Path(web_main.__file__).parent / "web" / "midnight-reference.css").read_text(encoding="utf-8")
    assert 'id="settingsUsersStatus"' in app
    assert 'id="settingsUsersSort"' in app
    assert 'selectedStatus === "active"' in app
    assert 'selectedStatus === "inactive"' in app
    assert 'selectedSort === "DESC" ? -1 : 1' in app
    assert 'const totalPages = Math.max(1, Math.ceil(visible.length / 6))' in app
    assert 'settingsUsersPrevious' in app and 'settingsUsersNext' in app
    assert 'settingsUsersView' in app and 'settings-user-cards' in app
    assert 'renderSettings=function(){document.body.dataset.settingsSection=settingsSection;' in reference
    assert 'grid-template-columns:repeat(2,minmax(0,1fr))' in css
