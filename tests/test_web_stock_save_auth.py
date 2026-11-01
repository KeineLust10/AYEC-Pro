from contextlib import closing
from http.server import ThreadingHTTPServer
import sqlite3
import threading

import requests

from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def test_stock_save_requires_auth_same_origin_and_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(
        web_main,
        "exchange_rates",
        lambda *args, **kwargs: {"TRY": 1.0, "USD": 35.0, "EUR": 38.0},
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    payload = {
        "code": "QA-AUTH-001",
        "name": "Auth Protected Stock",
        "stock": 1,
        "purchase_price": 2,
        "price": 3,
        "currency": "TRY",
    }
    try:
        anonymous = requests.post(
            f"{base_url}/api/desktop/stock/save",
            json=payload,
            headers={"Origin": base_url},
            timeout=5,
        )
        assert anonymous.status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
            timeout=5,
        )
        assert login.status_code == 200

        cross_origin = requests.post(
            f"{base_url}/api/desktop/stock/save",
            json=payload,
            cookies=session.cookies,
            headers={"Origin": "http://attacker.invalid"},
            timeout=5,
        )
        assert cross_origin.status_code == 403

        saved = session.post(
            f"{base_url}/api/desktop/stock/save", json=payload, timeout=5
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["ok"] is True

        with closing(sqlite3.connect(tenant_path)) as tenant:
            row = tenant.execute(
                "SELECT code,name FROM parts WHERE code=?", (payload["code"],)
            ).fetchone()
        assert row == (payload["code"], payload["name"])
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
