import sqlite3
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_manual_stock_adjustment_matches_desktop_movement_and_accounting(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main._TENANT_LOCAL, "db_path", tenant_path, raising=False)
    with sqlite3.connect(tenant_path) as connection:
        connection.execute(
            "INSERT INTO parts(id,name,stock,purchase_price,currency,is_deleted) "
            "VALUES(92001,'Adjustment Part',4,3,'TRY',0)"
        )

    added = web_main.desktop_adjust_stock(92001, 2, "PO-42")
    assert added["stock"] == 6
    assert added["delta"] == 2
    assert added["expense"] == 6
    assert added["finance_description"] == "Stok Ekleme (K\u0131sayol): 2 x Adjustment Part"

    removed = web_main.desktop_adjust_stock(92001, -1, "Waste")
    assert removed["stock"] == 5
    assert removed["expense"] == 3
    assert removed["finance_description"] == "Stok D\u00fc\u015f\u00fcm\u00fc (Manuel): 1 x Adjustment Part"

    with sqlite3.connect(tenant_path) as connection:
        movement_rows = connection.execute(
            "SELECT movement_type,amount,new_stock,description FROM stock_movements "
            "WHERE part_id=92001 ORDER BY id"
        ).fetchall()
        assert movement_rows == [
            ("Giri\u015f", 2, 6, "Manuel G\u00fcncelleme - Adjustment Part | Ref: PO-42"),
            ("\u00c7\u0131k\u0131\u015f", 1, 5, "Manuel G\u00fcncelleme - Adjustment Part | Ref: Waste"),
        ]
        finance_rows = connection.execute(
            "SELECT type,category,amount,description FROM accounting "
            "WHERE product_service_id=92001 ORDER BY id"
        ).fetchall()
        assert finance_rows == [
            ("Gider", "Stok Al\u0131m\u0131", 6, "Stok Ekleme (K\u0131sayol): 2 x Adjustment Part"),
            ("Gider", "Stok D\u00fc\u015f\u00fcm\u00fc / Fire", 3, "Stok D\u00fc\u015f\u00fcm\u00fc (Manuel): 1 x Adjustment Part"),
        ]

    with pytest.raises(ValueError, match="Insufficient stock"):
        web_main.desktop_adjust_stock(92001, -6)
    with sqlite3.connect(tenant_path) as connection:
        assert connection.execute("SELECT stock FROM parts WHERE id=92001").fetchone()[0] == 5


def test_manual_stock_adjustment_route_requires_authentication(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as connection:
        connection.execute(
            "INSERT INTO parts(id,name,stock,purchase_price,currency,is_deleted) "
            "VALUES(92002,'Route Part',3,2,'TRY',0)"
        )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.post(
            base_url + "/api/desktop/stock/adjust",
            json={"id": 92002, "delta": 1},
            headers={"Origin": base_url},
        )
        assert anonymous.status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            base_url + "/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200
        response = session.post(
            base_url + "/api/desktop/stock/adjust",
            json={"id": 92002, "delta": 1},
        )
        assert response.status_code == 200, response.text
        assert response.json()["stock"] == 4
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
