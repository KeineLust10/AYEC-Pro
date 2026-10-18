import json
import os
import sqlite3
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import Web_Arayuzu.Main as web


def test_authenticated_technician_permissions_filter_both_sector_sidebars(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(web, "DB_PATH", tmp_path / "registry.sqlite")
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    monkeypatch.setattr(web, "TENANT_ROOT", tenant_root)
    tenant = web.create_tenant("Sidebar Permission Tenant", email="sidebar@example.invalid")
    tenant_path = web._tenant_path(tenant)
    permissions = json.dumps({"pages": [40, 41, 21]}, separators=(",", ":"))
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO users(username,password,email,role,active,full_name,permissions) "
            "VALUES(?,?,?,?,1,?,?)",
            (
                "tech-audit",
                web.password_hash("TechAuditPass123"),
                "tech-audit@example.invalid",
                "Teknisyen",
                "Sidebar Technician",
                permissions,
            ),
        )

    server = ThreadingHTTPServer(("127.0.0.1", 0), web.AYECRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/"
    env = os.environ.copy()
    env["AYEC_ROLE_LOGIN_USER"] = "tech-audit"
    env["AYEC_ROLE_LOGIN_PASSWORD"] = "TechAuditPass123"
    env["AYEC_ROLE_LOGIN_TENANT"] = tenant["id"]
    try:
        audit = subprocess.run(
            ["node", "tools/quality/sidebar_authenticated_role_offscreen.cjs", base_url],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        assert audit.returncode == 0, audit.stderr or audit.stdout
        result = json.loads(audit.stdout.strip().splitlines()[-1])
        assert result["signedIn"]["role"] == "Teknisyen"
        assert result["signedIn"]["pages"] == [40, 41, 21]
        assert result["authStatus"]["isControlAdmin"] is False
        assert result["technical"]["allowed"] == [True, True, True]
        assert result["technical"]["denied"] == [False, False, False]
        assert result["automotive"]["allowed"] == [True, False, True]
        assert result["automotive"]["denied"] == [False, False, False, False]
        assert result["browserExceptions"] == 0
        with sqlite3.connect(tenant_path) as conn:
            persisted = conn.execute(
                "SELECT role,permissions FROM users WHERE username='tech-audit'"
            ).fetchone()
        assert persisted == ("Teknisyen", permissions)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_sidebar_version_and_logout_controls_match_native_footer():
    root = Path(__file__).resolve().parents[1]
    styles = (root / "Web_Arayuzu" / "web" / "styles.css").read_text(encoding="utf-8")
    parity = (root / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")
    desktop = (root / "src" / "ui" / "widgets" / "side_menu.py").read_text(encoding="utf-8")
    theme = (root / "src" / "themes" / "dark_blue_theme.json").read_text(encoding="utf-8")

    assert 'self.version_label.setFixedSize(122, 32)' in desktop
    assert '"font-size: 10px; font-weight: 800;' in desktop
    assert 'font-size: 13px;' in desktop
    assert '.sidebar-license{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:7px 4px;color:var(--ink);font-size:10px;font-weight:800}' in styles
    assert '.sidebar-license strong{font-size:10px;font-weight:800}' in styles
    assert '.sidebar-license span{padding:0 6px;border:1px solid var(--finance-outline,var(--line));border-radius:6px;background:var(--finance-surface-alt,var(--surface-2));color:var(--accent);' in styles
    assert '.sidebar-bottom .user-logout{width:100%;height:44px;margin:0;padding:0 14px;border:1px solid var(--danger);border-radius:8px;background:var(--surface);color:var(--danger);font-size:13px;font-weight:600;text-align:center}' in styles
    assert '"danger": "#FFB2B7"' in theme
    assert 'html[data-theme="midnight"] .sidebar .sidebar-bottom .sidebar-license span{border-color:#1b2a42}' in parity
    assert 'html[data-theme="midnight"] .sidebar .sidebar-bottom .user-logout{border-color:#ffb2b7;color:#ffb2b7}' in parity
