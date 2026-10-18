import json
import os
import sqlite3
import subprocess
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import Web_Arayuzu.Main as web


def test_status_board_device_reads_are_authenticated_and_tenant_scoped(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(web, "DB_PATH", tmp_path / "registry.sqlite")
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    monkeypatch.setattr(web, "TENANT_ROOT", tenant_root)
    first_tenant = web.create_tenant("Status Tenant A", email="a@example.invalid")
    second_tenant = web.create_tenant("Status Tenant B", email="b@example.invalid")

    for tenant, tracking_no, customer_name in (
        (first_tenant, "TV-A-001", "Tenant A Customer"),
        (second_tenant, "TV-B-001", "Tenant B Customer"),
    ):
        with sqlite3.connect(web._tenant_path(tenant)) as conn:
            if tenant["id"] == first_tenant["id"]:
                conn.execute(
                    "INSERT INTO users(username, password, email, role, active, full_name) "
                    "VALUES (?, ?, ?, ?, 1, ?)",
                    (
                        "qa",
                        web.password_hash("test-password"),
                        "a@example.invalid",
                        "Admin",
                        "QA User",
                    ),
                )
            conn.execute(
                "INSERT INTO devices "
                "(tracking_no, customer_name, device_brand, device_model, status, entry_date) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (tracking_no, customer_name, "TestBrand", "Model X", "Tamirde", "2026-10-14"),
            )

    token, _ = web.create_session(
        1, False, "Status Board API Test", "127.0.0.1", first_tenant["id"]
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.AYECRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/api/desktop/table/devices?limit=20"

    try:
        req = urllib.request.Request(
            url,
            headers={"Cookie": f"{web.SESSION_COOKIE}={token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            assert response.status == 200
            rows = json.loads(response.read())["rows"]
        rows_by_tracking = {row["tracking_no"]: row for row in rows}
        assert "TV-A-001" in rows_by_tracking
        assert "TV-B-001" not in rows_by_tracking
        assert rows_by_tracking["TV-A-001"]["customer_name"] == "Tenant A Customer"

        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                raise AssertionError(
                    f"Anonymous request unexpectedly returned {response.status}"
                )
        except urllib.error.HTTPError as error:
            assert error.code == 401
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        web.delete_session(token)


def test_hidden_browser_tv_refresh_renders_live_tenant_changes_on_next_poll(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(web, "DB_PATH", tmp_path / "registry.sqlite")
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    monkeypatch.setattr(web, "TENANT_ROOT", tenant_root)
    tenant = web.create_tenant("TV Browser Tenant", email="tv@example.invalid")
    tenant_path = web._tenant_path(tenant)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO users(username, password, email, role, active, full_name) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            ("qa", web.password_hash("test-password"), "tv@example.invalid", "Admin", "QA User"),
        )
        conn.execute(
            "INSERT INTO devices "
            "(tracking_no, customer_name, device_brand, device_model, status, entry_date) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("TV-A-001", "Tenant TV Customer", "TestBrand", "Model X", "Tamirde", "2026-10-14"),
        )
    token, _session = web.create_session(1, False, "Status Board Browser Test", "127.0.0.1", tenant["id"])
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.AYECRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/"
    env = os.environ.copy()
    env["AYEC_STATUS_TV_SESSION_COOKIE"] = token
    try:
        audit = subprocess.run(
            ["node", "tools/quality/service_status_tv_refresh_offscreen.cjs", base_url],
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
        assert result["readCount"] >= 2
        assert result["intervalMs"] == 5000
        assert 4500 <= result["refreshDelayMs"] <= 8000
        assert result["rowVisible"] is True
        assert result["updatedStatusVisible"] is True
        assert result["browserExceptions"] == 0
        with sqlite3.connect(tenant_path) as conn:
            status = conn.execute(
                "SELECT status FROM devices WHERE tracking_no='TV-A-001'"
            ).fetchone()[0]
        assert status == "Teslim Edildi"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        web.delete_session(token)
