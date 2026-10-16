import json
import sqlite3
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import Web_Arayuzu.Main as web


def test_pc_builder_stock_deduction_is_atomic_for_authenticated_tenant(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(web, "DB_PATH", tmp_path / "registry.sqlite")
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    monkeypatch.setattr(web, "TENANT_ROOT", tenant_root)
    tenant = web.create_tenant("PC Builder API Test", email="qa@example.invalid")
    tenant_db = web._tenant_path(tenant)

    with sqlite3.connect(tenant_db) as conn:
        conn.execute(
            "INSERT INTO users(username, password, email, role, active, full_name) "
            "VALUES (?, ?, ?, ?, 1, ?)",
            (
                "qa",
                web.password_hash("test-password"),
                "qa@example.invalid",
                "Admin",
                "QA User",
            ),
        )
        part_ids = []
        for index, stock in enumerate((5, 3), start=1):
            cursor = conn.execute(
                "INSERT INTO parts "
                "(name, part_name, code, category, currency, stock, purchase_price, price) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    f"PC Component {index}",
                    f"PC Component {index}",
                    f"PC-QA-{index}",
                    "PC Parts",
                    "TRY",
                    stock,
                    10,
                    20,
                ),
            )
            part_ids.append(cursor.lastrowid)

    token, _ = web.create_session(
        1, False, "PC Builder API Test", "127.0.0.1", tenant["id"]
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web.AYECRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    headers = {
        "Cookie": f"{web.SESSION_COOKIE}={token}",
        "Content-Type": "application/json",
    }

    def post(payload):
        request = urllib.request.Request(
            base_url + "/api/desktop/pc-builder/deduct-stock",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.loads(response.read())
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read())

    try:
        status, result = post(
            {
                "reference": "PC-QA-ORDER",
                "items": [
                    {"part_id": part_ids[0], "quantity": 2},
                    {"part_id": part_ids[1], "quantity": 1},
                ],
            }
        )
        assert status == 200
        assert [item["stock"] for item in result["items"]] == [3, 2]
        with sqlite3.connect(tenant_db) as conn:
            before_failure = conn.execute(
                "SELECT id, stock FROM parts WHERE id IN (?, ?) ORDER BY id",
                part_ids,
            ).fetchall()
            movements_before = conn.execute(
                "SELECT COUNT(*) FROM stock_movements WHERE part_id IN (?, ?)",
                part_ids,
            ).fetchone()[0]
        assert before_failure == [(part_ids[0], 3), (part_ids[1], 2)]
        assert movements_before == 2

        status, error = post(
            {
                "reference": "PC-QA-FAIL",
                "items": [
                    {"part_id": part_ids[0], "quantity": 1},
                    {"part_id": part_ids[1], "quantity": 9},
                ],
            }
        )
        assert status == 400
        assert "Insufficient stock" in error["error"]
        with sqlite3.connect(tenant_db) as conn:
            after_failure = conn.execute(
                "SELECT id, stock FROM parts WHERE id IN (?, ?) ORDER BY id",
                part_ids,
            ).fetchall()
            movements_after = conn.execute(
                "SELECT COUNT(*) FROM stock_movements WHERE part_id IN (?, ?)",
                part_ids,
            ).fetchone()[0]
        assert after_failure == before_failure
        assert movements_after == movements_before
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        web.delete_session(token)
