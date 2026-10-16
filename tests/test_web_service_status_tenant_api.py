import json
import sqlite3
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

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
