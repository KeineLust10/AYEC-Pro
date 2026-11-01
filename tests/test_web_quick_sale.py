import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from src.database import Database
from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_quick_sale_api_is_authenticated_and_persists_to_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    database = Database(str(tenant_path))
    part_id = database.add_part(
        "Quick sale item",
        "General",
        5,
        12,
        purchase_price=3,
        currency="TRY",
        code="QS-API-1",
    )
    customer_id = database.add_customer({"name": "Quick Sale Customer", "is_deleted": 0})
    assert customer_id
    database.close()
    monkeypatch.setattr(web_main, "exchange_rates", lambda refresh=True: None)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        payload = {
            "lines": [{"product_id": part_id, "qty": 2}],
            "discount": 5,
            "payment_method": "Nakit",
            "reference": "QS-API-1",
            "customer_id": customer_id,
        }
        anonymous = requests.post(
            f"{base_url}/api/desktop/sales/quick-commit",
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
        assert login.status_code == 200, login.text
        invalid_customer = session.post(
            f"{base_url}/api/desktop/sales/quick-commit",
            json={**payload, "customer_id": customer_id + 100000},
            timeout=5,
        )
        assert invalid_customer.status_code == 404
        invalid_customer_type = session.post(
            f"{base_url}/api/desktop/sales/quick-commit",
            json={**payload, "customer_id": 1.5},
            timeout=5,
        )
        assert invalid_customer_type.status_code == 400
        response = session.post(
            f"{base_url}/api/desktop/sales/quick-commit",
            json=payload,
            timeout=5,
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["total"] == 19
        assert result["currency"] == "TRY"

        with web_main._raw_connect(tenant_path) as conn:
            stock = conn.execute(
                "SELECT stock FROM parts WHERE id=?", (part_id,)
            ).fetchone()[0]
            income = conn.execute(
                "SELECT amount,customer_id,customer_name FROM accounting WHERE tracking_no=?",
                ("QS-API-1",),
            ).fetchone()
            cost = conn.execute(
                "SELECT customer_id,customer_name FROM accounting WHERE tracking_no=? AND type='Gider'",
                ("QS-API-1",),
            ).fetchone()
            movement = conn.execute(
                "SELECT amount,new_stock FROM stock_movements WHERE part_id=? ORDER BY id DESC LIMIT 1",
                (part_id,),
            ).fetchone()
            ledger = conn.execute(
                "SELECT transaction_type,amount,current_balance FROM currency_transactions "
                "WHERE customer_id=? ORDER BY id",
                (customer_id,),
            ).fetchall()
            customer_balance = conn.execute(
                "SELECT balance FROM customer_currency_balances WHERE customer_id=? AND currency='TRY'",
                (customer_id,),
            ).fetchone()[0]
        assert stock == 3
        assert income["amount"] == 19
        assert income["customer_id"] == customer_id
        assert income["customer_name"] == "Quick Sale Customer"
        assert cost["customer_id"] == customer_id
        assert cost["customer_name"] == "Quick Sale Customer"
        assert movement["amount"] == 2
        assert movement["new_stock"] == 3
        assert [(row["transaction_type"], row["amount"]) for row in ledger] == [
            ("DEBIT", 19), ("CREDIT", 19),
        ]
        assert ledger[-1]["current_balance"] == 0
        assert customer_balance == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_quick_sale_keyboard_shortcuts_are_cache_busted():
    web_root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    index = (web_root / "index.html").read_text(encoding="utf-8")
    script = (web_root / "quick-sale-reference.js").read_text(encoding="utf-8")
    assert 'quick-sale-reference.css?v=20261026-quick-sale-customer-parity-1' in index
    assert 'quick-sale-reference.js?v=20261028-quick-sale-stale-customer-reconcile-1' in index
    assert 'id="quickSaleCustomer"' in script
    assert 'customer_id: selectedCustomerId || null' in script
    assert 'event.key === "F1" || event.key === "F2"' in script
    assert 'event.key !== "Delete"' in script
    assert 'event.target?.closest?.("input,textarea,select,[contenteditable=true]")' in script


def test_customer_picker_deletion_clears_the_quick_sale_customer_and_saved_draft():
    web_root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    script = (web_root / "quick-sale-reference.js").read_text(encoding="utf-8")
    route_smoke = (Path(__file__).resolve().parents[1] / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert 'result !== "ok"' in script
    assert "nextCustomers.some(item => String(item.id) === String(selectedCustomerId))" in script
    assert 'selectedCustomerId = ""' in script
    assert "saveDraft();" in script
    assert "quickSaleCustomerRemovalWorkflow" in route_smoke
