from contextlib import closing
from http.server import ThreadingHTTPServer
import sqlite3
import threading

import requests

from src.database import Database
from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_technician_service_collection_http_flow_persists_payment_and_bank(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    database = Database(str(tenant_path))
    customer_id = database.add_customer(
        {"name": "Payment API Customer", "phone": "05550000000", "email": "payment@example.com"}
    )
    device_id = database.add_device(
        {
            "tracking_no": "WEB-PAY-API-1",
            "customer_id": customer_id,
            "customer_name": "Payment API Customer",
            "device_type": "Computer",
            "device_brand": "Test Brand",
            "device_model": "Test Model",
            "serial_no": "WEB-PAY-SERIAL-1",
            "fault_description": "No power",
            "status": "Waiting",
            "payment_status": "Beklemede",
            "labor_cost": 250,
        }
    )
    unpaid_device_id = database.add_device(
        {
            "tracking_no": "WEB-PAY-API-2",
            "customer_id": customer_id,
            "customer_name": "Payment API Customer",
            "device_type": "Computer",
            "device_brand": "Test Brand",
            "device_model": "Test Model",
            "serial_no": "WEB-PAY-SERIAL-2",
            "fault_description": "No display",
            "status": "Waiting",
            "payment_status": "Beklemede",
            "labor_cost": 100,
        }
    )
    part_id = database.add_part(
        "QA Service Part",
        "Computer",
        5,
        10,
        purchase_price=6,
        currency="TRY",
        code="QA-SERVICE-PART-1",
    )
    invalid_bank_device_id = database.add_device(
        {
            "tracking_no": "WEB-PAY-API-3",
            "customer_id": customer_id,
            "customer_name": "Payment API Customer",
            "device_type": "Computer",
            "device_brand": "Test Brand",
            "device_model": "Test Model",
            "serial_no": "WEB-PAY-SERIAL-3",
            "fault_description": "No sound",
            "status": "Waiting",
            "payment_status": "Beklemede",
            "labor_cost": 50,
        }
    )
    assert database.add_bank_account("Payment Bank", "Main", "Operations", "PAY-001", "", 0)
    bank_account_id = database.conn.execute(
        "SELECT id FROM bank_accounts ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    assert database.add_bank_account("Inactive Bank", "Main", "Disabled", "PAY-002", "", 0)
    inactive_bank_id = database.conn.execute(
        "SELECT id FROM bank_accounts ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    database.conn.execute(
        "UPDATE bank_accounts SET is_active=0 WHERE id=?",
        (inactive_bank_id,),
    )
    database.conn.commit()
    database.close()
    other_path = tenant_path.parent / "Other Company.db"
    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active) "
            "VALUES(?,?,?,?,1)",
            ("tenant-2", "Other Company", other_path.name, "2026-01-02T00:00:00"),
        )
    other_database = Database(str(other_path))
    other_customer_id = other_database.add_customer(
        {"name": "Other Tenant Customer", "phone": "05550000001", "email": "other@example.com"}
    )
    other_device_id = other_database.add_device(
        {
            "tracking_no": "WEB-PAY-API-1",
            "customer_id": other_customer_id,
            "customer_name": "Other Tenant Customer",
            "device_type": "Computer",
            "device_brand": "Other Brand",
            "device_model": "Other Model",
            "serial_no": "OTHER-WEB-PAY-SERIAL-1",
            "fault_description": "Other tenant fixture",
            "status": "Waiting",
            "payment_status": "Beklemede",
            "labor_cost": 250,
        }
    )
    other_part_id = other_database.add_part(
        "Other Tenant Part",
        "Computer",
        11,
        10,
        purchase_price=6,
        currency="TRY",
        code="OTHER-SERVICE-PART-1",
    )
    assert other_part_id == part_id
    other_database.close()
    monkeypatch.setattr(web_main, "exchange_rates", lambda refresh=False: {"TRY": 1.0})
    monkeypatch.setattr(
        web_main,
        "resolve_exchange_rate",
        lambda _conn, currency, preferred=None: 40.0 if currency == "USD" else 1.0,
    )

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.post(
            f"{base_url}/api/desktop/technician/update",
            json={"device_id": device_id, "tracking_no": "WEB-PAY-API-1"},
            timeout=10,
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
            timeout=10,
        )
        assert login.status_code == 200
        response = session.post(
            f"{base_url}/api/desktop/technician/update",
            json={
                "device_id": device_id,
                "tracking_no": "WEB-PAY-API-1",
                "status": "Teslim Edildi",
                "labor_cost": 250,
                "cargo_fee": 7,
                "collect_payment": True,
                "payment_amount": 100,
                "payment_currency": "TRY",
                "payment_method": "Havale/EFT",
                "bank_account_id": bank_account_id,
                "part_id": part_id,
                "part_quantity": 2,
                "manual_used_parts": [{"name": "Manual Bench Labor", "price": 30}],
            },
            timeout=10,
        )
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["finance_id"]
        assert result["payment_status"] == "K\u0131smi \u00d6dendi"
        assert result["service_charge_try"] == 307
        with closing(sqlite3.connect(tenant_path)) as conn:
            delivery_dates = conn.execute(
                "SELECT exit_date,delivered_at FROM devices WHERE id=?",
                (device_id,),
            ).fetchone()
        assert all(delivery_dates)

        unpaid_response = session.post(
            f"{base_url}/api/desktop/technician/update",
            json={
                "device_id": unpaid_device_id,
                "tracking_no": "WEB-PAY-API-2",
                "status": "Teslim Edildi",
                "labor_cost": 100,
                "collect_payment": False,
                "payment_currency": "TRY",
            },
            timeout=10,
        )
        assert unpaid_response.status_code == 200, unpaid_response.text
        unpaid_result = unpaid_response.json()
        assert unpaid_result["finance_id"] is None
        assert unpaid_result["payment_status"] == "\u00d6denmedi"
        assert unpaid_result["pending_finance_id"]
        unpaid_repeat = session.post(
            f"{base_url}/api/desktop/technician/update",
            json={
                "device_id": unpaid_device_id,
                "tracking_no": "WEB-PAY-API-2",
                "status": "Teslim Edildi",
                "labor_cost": 100,
                "collect_payment": False,
                "payment_currency": "TRY",
            },
            timeout=10,
        )
        assert unpaid_repeat.status_code == 200, unpaid_repeat.text
        assert unpaid_repeat.json()["pending_finance_id"] == unpaid_result["pending_finance_id"]

        rejected_bank = session.post(
            f"{base_url}/api/desktop/technician/update",
            json={
                "device_id": invalid_bank_device_id,
                "tracking_no": "WEB-PAY-API-3",
                "status": "Teslim Edildi",
                "labor_cost": 50,
                "collect_payment": True,
                "payment_amount": 20,
                "payment_currency": "TRY",
                "payment_method": "Havale/EFT",
                "bank_account_id": inactive_bank_id,
                "part_id": part_id,
                "part_quantity": 1,
            },
            timeout=10,
        )
        assert rejected_bank.status_code == 400
        assert "unavailable" in rejected_bank.json()["error"]

        rejected_currency = session.post(
            f"{base_url}/api/desktop/technician/update",
            json={
                "device_id": invalid_bank_device_id,
                "tracking_no": "WEB-PAY-API-3",
                "status": "Teslim Edildi",
                "labor_cost": 50,
                "collect_payment": True,
                "payment_amount": 2,
                "payment_currency": "USD",
                "exchange_rate": 40,
            },
            timeout=10,
        )
        assert rejected_currency.status_code == 400

        reopened_service = session.post(
            f"{base_url}/api/desktop/technician/update",
            json={
                "device_id": device_id,
                "tracking_no": "WEB-PAY-API-1",
                "status": "Tamirde",
                "labor_cost": 250,
                "cargo_fee": 7,
                "collect_payment": False,
                "payment_currency": "TRY",
            },
            timeout=10,
        )
        assert reopened_service.status_code == 200, reopened_service.text

        with closing(sqlite3.connect(tenant_path)) as conn:
            conn.row_factory = sqlite3.Row
            payment = conn.execute(
                "SELECT type,category,amount,payment_method,bank_account_id,tracking_no "
                "FROM accounting WHERE id=?",
                (result["finance_id"],),
            ).fetchone()
            status = conn.execute(
                "SELECT status,exit_date,delivered_at,payment_status FROM devices WHERE id=?",
                (device_id,),
            ).fetchone()
            unpaid_status = conn.execute(
                "SELECT payment_status FROM devices WHERE id=?",
                (unpaid_device_id,),
            ).fetchone()[0]
            unpaid_income_count = conn.execute(
                "SELECT COUNT(*) FROM accounting WHERE tracking_no=?",
                ("WEB-PAY-API-2",),
            ).fetchone()[0]
            unpaid_income = conn.execute(
                "SELECT type,category,amount,payment_method FROM accounting WHERE tracking_no=?",
                ("WEB-PAY-API-2",),
            ).fetchone()
            rejected_state = conn.execute(
                "SELECT status,payment_status FROM devices WHERE id=?",
                (invalid_bank_device_id,),
            ).fetchone()
            rejected_income_count = conn.execute(
                "SELECT COUNT(*) FROM accounting WHERE tracking_no=?",
                ("WEB-PAY-API-3",),
            ).fetchone()[0]
            stock = conn.execute(
                "SELECT stock FROM parts WHERE id=?",
                (part_id,),
            ).fetchone()[0]
            used_parts = conn.execute(
                "SELECT quantity,price FROM used_parts WHERE tracking_no=?",
                ("WEB-PAY-API-1",),
            ).fetchall()
            rejected_used_part_count = conn.execute(
                "SELECT COUNT(*) FROM used_parts WHERE tracking_no=?",
                ("WEB-PAY-API-3",),
            ).fetchone()[0]
            movement_count = conn.execute(
                "SELECT COUNT(*) FROM stock_movements WHERE part_id=? AND description LIKE ?",
                (part_id, "%WEB-PAY-API-1%"),
            ).fetchone()[0]
            balance = conn.execute(
                "SELECT balance FROM customer_currency_balances "
                "WHERE customer_id=? AND currency='TRY'",
                (customer_id,),
            ).fetchone()[0]
            bank_balance = conn.execute(
                "SELECT current_balance FROM bank_accounts WHERE id=?",
                (bank_account_id,),
            ).fetchone()[0]
        assert tuple(payment) == (
            "Gelir", "Tahsilat", 100, "Havale/EFT", bank_account_id, "WEB-PAY-API-1"
        )
        assert tuple(status) == ("Tamirde", None, None, "K\u0131smi \u00d6dendi")
        assert unpaid_status == "\u00d6denmedi"
        assert unpaid_income_count == 1
        assert tuple(unpaid_income) == ("Gelir", "Servis Hizmeti", 100, "\u00d6denmedi")
        assert tuple(rejected_state) == ("Waiting", "Beklemede")
        assert rejected_income_count == 0
        assert stock == 3
        assert [tuple(row) for row in used_parts] == [(2, 10), (1, 30)]
        assert rejected_used_part_count == 0
        assert movement_count == 1
        assert balance == -307
        assert bank_balance == 100
        assert result["bank_account_balance"] == 100
        with closing(sqlite3.connect(other_path)) as conn:
            other_state = conn.execute(
                "SELECT status,payment_status FROM devices WHERE id=?",
                (other_device_id,),
            ).fetchone()
            other_income_count = conn.execute(
                "SELECT COUNT(*) FROM accounting WHERE tracking_no=?",
                ("WEB-PAY-API-1",),
            ).fetchone()[0]
            other_stock = conn.execute(
                "SELECT stock FROM parts WHERE id=?",
                (other_part_id,),
            ).fetchone()[0]
            other_used_parts = conn.execute(
                "SELECT COUNT(*) FROM used_parts WHERE tracking_no=?",
                ("WEB-PAY-API-1",),
            ).fetchone()[0]
        assert other_state == ("Waiting", "Beklemede")
        assert other_income_count == 0
        assert other_stock == 11
        assert other_used_parts == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
