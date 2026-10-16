import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_voice_price_increase_requires_preview_and_is_tenant_scoped(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as connection:
        connection.executemany(
            "INSERT INTO parts(name,category,price,currency,stock,is_deleted) VALUES(?,?,?,?,?,?)",
            [
                ("Keyboard", "Computer", 100, "TRY", 2, 0),
                ("Mouse", "Computer", 15, "TRY", 3, 0),
                ("Cable", "Other", 10, "TRY", 4, 0),
                ("Deleted keyboard", "Computer", 20, "TRY", 1, 1),
            ],
        )
        connection.commit()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    session = requests.Session()
    session.headers["Origin"] = base_url
    try:
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200

        request = {"action": "preview", "percentage": 10, "category": "Computer"}
        preview = session.post(f"{base_url}/api/desktop/stock/price-increase", json=request)
        assert preview.status_code == 200
        assert preview.json()["affected_count"] == 2

        applied = session.post(
            f"{base_url}/api/desktop/stock/price-increase",
            json={**request, "action": "apply", "expected_count": 2},
        )
        assert applied.status_code == 200
        assert applied.json()["affected_count"] == 2

        with sqlite3.connect(tenant_path) as connection:
            prices = dict(connection.execute("SELECT name,price FROM parts"))
            audit_count = connection.execute(
                "SELECT COUNT(*) FROM audit_logs WHERE action='STOCK_PRICE_BULK_UPDATE'"
            ).fetchone()[0]
        assert prices == {
            "Keyboard": 110,
            "Mouse": 16.5,
            "Cable": 10,
            "Deleted keyboard": 20,
        }
        assert audit_count == 1

        all_stock = session.post(
            f"{base_url}/api/desktop/stock/price-increase",
            json={"action": "preview", "percentage": 5},
        )
        assert all_stock.status_code == 200
        assert all_stock.json()["affected_count"] == 3
        with sqlite3.connect(tenant_path) as connection:
            connection.execute(
                "INSERT INTO parts(name,category,price,currency,stock,is_deleted) VALUES(?,?,?,?,?,0)",
                ("New item", "Other", 8, "TRY", 1),
            )
            connection.commit()
        stale = session.post(
            f"{base_url}/api/desktop/stock/price-increase",
            json={"action": "apply", "percentage": 5, "expected_count": 3},
        )
        assert stale.status_code == 409
        assert stale.json()["ok"] is False

        invalid = session.post(
            f"{base_url}/api/desktop/stock/price-increase",
            json={"action": "preview", "percentage": 101},
        )
        assert invalid.status_code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
