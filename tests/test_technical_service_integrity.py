import re
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import Database
from Web_Arayuzu import Main as web_main


def _prepare_service_database(database_path, *, tracking_no, labor_cost=0):
    db = Database(str(database_path))
    customer_id = db.add_customer(
        {
            "name": "Technical Service Customer",
            "phone": "05550000000",
            "email": "technical@example.com",
        }
    )
    device_id = db.add_device(
        {
            "tracking_no": tracking_no,
            "customer_id": customer_id,
            "customer_name": "Technical Service Customer",
            "device_type": "Computer",
            "device_brand": "Test Brand",
            "device_model": "Test Model",
            "serial_no": "TECH-SERIAL-1",
            "fault_description": "No power",
            "status": "Waiting",
            "payment_status": "Beklemede",
            "labor_cost": labor_cost,
        }
    )
    part_id = db.add_part(
        "USD Technical Part",
        "Computer",
        5,
        10,
        purchase_price=6,
        currency="USD",
        code="TECH-USD-1",
    )
    db.close()
    return customer_id, device_id, part_id


def _open_database(database_path):
    return Database(str(database_path))


def test_web_schema_migrates_legacy_used_part_currency_values():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE used_parts (
            id INTEGER PRIMARY KEY,
            tracking_no TEXT,
            price REAL,
            quantity REAL,
            currency TEXT
        );
        CREATE TABLE exchange_rates (
            id INTEGER PRIMARY KEY,
            currency TEXT,
            buying_rate REAL,
            selling_rate REAL,
            effective_date TEXT,
            source TEXT,
            created_at TEXT
        );
        INSERT INTO exchange_rates
            (currency,buying_rate,selling_rate,effective_date,source,created_at)
        VALUES ('USD',39,40,'2026-01-01','TEST','2026-01-01');
        INSERT INTO used_parts
            (tracking_no,price,quantity,currency)
        VALUES ('LEGACY-1',10,2,'USD');
        """
    )

    web_main.ensure_web_schema(conn)

    row = conn.execute(
        "SELECT exchange_rate,price_try FROM used_parts WHERE tracking_no='LEGACY-1'"
    ).fetchone()
    assert tuple(map(float, row)) == (40.0, 400.0)
    assert web_main._service_used_parts_total_try(conn, "LEGACY-1") == 800.0
    conn.close()


def test_desktop_technical_service_uses_part_and_updates_debt(
    tmp_path, monkeypatch
):
    from src.utils.currency_helper import CurrencyHelper

    monkeypatch.setattr(
        CurrencyHelper,
        "_get_rate",
        staticmethod(lambda _db, code: 40.0 if code == "USD" else 1.0),
    )
    database_path = tmp_path / "desktop-technical-service.db"
    tracking_no = "TECH-DESKTOP-1"
    customer_id, _device_id, part_id = _prepare_service_database(
        database_path, tracking_no=tracking_no, labor_cost=100
    )
    db = _open_database(database_path)
    db.cursor.execute(
        "UPDATE devices SET status='Tamirde' WHERE tracking_no=?", (tracking_no,)
    )
    db.conn.commit()

    assert db.use_part(part_id, 2, tracking_no)
    stock = db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?", (part_id,)
    ).fetchone()[0]
    debit = db.cursor.execute(
        "SELECT amount,currency FROM currency_transactions "
        "WHERE customer_id=? AND tracking_no=? AND transaction_type='DEBIT'",
        (customer_id, tracking_no),
    ).fetchone()
    assert float(stock) == 3.0
    assert tuple(debit) == (900.0, "TRY")
    db.close()


def test_technical_service_part_stock_debt_and_repeat_update(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "technical-service.db"
    tracking_no = "TECH-WEB-1"
    customer_id, device_id, part_id = _prepare_service_database(
        database_path, tracking_no=tracking_no
    )
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    monkeypatch.setattr(
        web_main,
        "resolve_exchange_rate",
        lambda _conn, currency, preferred=None: 40.0 if currency == "USD" else 1.0,
    )

    first = web_main.update_technician_job(
        {
            "device_id": device_id,
            "tracking_no": tracking_no,
            "status": "In progress",
            "labor_cost": 100,
            "cargo_fee": 0,
            "part_id": part_id,
            "part_quantity": 2,
            "payment_status": "\u00d6dendi",
        }
    )

    assert first["service_charge_try"] == 900.0
    assert first["payment_status"] == "\u00d6denmedi"
    db = _open_database(database_path)
    stock = db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?", (part_id,)
    ).fetchone()[0]
    used = db.cursor.execute(
        "SELECT quantity,currency,exchange_rate,price_try FROM used_parts "
        "WHERE tracking_no=? ORDER BY id DESC LIMIT 1",
        (tracking_no,),
    ).fetchone()
    debit = db.cursor.execute(
        "SELECT amount,try_equivalent FROM currency_transactions "
        "WHERE tracking_no=? AND transaction_type='DEBIT'",
        (tracking_no,),
    ).fetchone()
    balance = db.cursor.execute(
        "SELECT balance FROM customer_currency_balances "
        "WHERE customer_id=? AND currency='TRY'",
        (customer_id,),
    ).fetchone()[0]
    status = db.cursor.execute(
        "SELECT payment_status FROM devices WHERE id=?", (device_id,)
    ).fetchone()[0]
    assert float(stock) == 3.0
    assert tuple(used) == (2, "USD", 40.0, 400.0)
    assert tuple(map(float, debit)) == (900.0, 900.0)
    assert float(balance) == -900.0
    assert status == "\u00d6denmedi"
    db.close()

    second = web_main.update_technician_job(
        {
            "device_id": device_id,
            "tracking_no": tracking_no,
            "status": "Testing",
            "labor_cost": 150,
            "cargo_fee": 0,
        }
    )
    assert second["service_charge_try"] == 950.0
    db = _open_database(database_path)
    debit_rows = db.cursor.execute(
        "SELECT amount FROM currency_transactions "
        "WHERE tracking_no=? AND transaction_type='DEBIT'",
        (tracking_no,),
    ).fetchall()
    balance = db.cursor.execute(
        "SELECT balance FROM customer_currency_balances "
        "WHERE customer_id=? AND currency='TRY'",
        (customer_id,),
    ).fetchone()[0]
    assert len(debit_rows) == 1
    assert float(debit_rows[0][0]) == 950.0
    assert float(balance) == -950.0
    db.close()
    web_main.clear_tenant_context()


def test_web_bootstrap_reconciles_legacy_service_debit(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "technical-reconcile.db"
    tracking_no = "TECH-RECONCILE-1"
    customer_id, device_id, part_id = _prepare_service_database(
        database_path, tracking_no=tracking_no
    )
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    monkeypatch.setattr(
        web_main,
        "resolve_exchange_rate",
        lambda _conn, currency, preferred=None: 40.0 if currency == "USD" else 1.0,
    )
    web_main.update_technician_job(
        {
            "device_id": device_id,
            "tracking_no": tracking_no,
            "labor_cost": 100,
            "part_id": part_id,
            "part_quantity": 2,
        }
    )
    db = _open_database(database_path)
    db.cursor.execute(
        "UPDATE currency_transactions SET amount=120,try_equivalent=120 "
        "WHERE tracking_no=? AND transaction_type='DEBIT'",
        (tracking_no,),
    )
    db.cursor.execute(
        "UPDATE customer_currency_balances SET balance=-120 "
        "WHERE customer_id=? AND currency='TRY'",
        (customer_id,),
    )
    db.conn.commit()
    db.close()

    source = web_main.desktop_bootstrap()

    db = _open_database(database_path)
    debit = db.cursor.execute(
        "SELECT amount FROM currency_transactions "
        "WHERE tracking_no=? AND transaction_type='DEBIT'",
        (tracking_no,),
    ).fetchone()[0]
    balance = db.cursor.execute(
        "SELECT balance FROM customer_currency_balances "
        "WHERE customer_id=? AND currency='TRY'",
        (customer_id,),
    ).fetchone()[0]
    db.close()
    service = next(
        item
        for customer in source["customers"]
        for item in customer["services"]
        if item["no"] == tracking_no
    )
    assert float(debit) == 900.0
    assert float(balance) == -900.0
    assert float(service["amount"]) == 900.0
    web_main.clear_tenant_context()


def test_technical_service_partial_and_customer_payment_refresh_status(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "technical-payment.db"
    tracking_no = "TECH-PAY-1"
    customer_id, device_id, _part_id = _prepare_service_database(
        database_path, tracking_no=tracking_no
    )
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)

    partial = web_main.update_technician_job(
        {
            "device_id": device_id,
            "tracking_no": tracking_no,
            "status": "Ready",
            "labor_cost": 500,
            "collect_payment": True,
            "payment_amount": 200,
            "payment_currency": "TRY",
            "payment_method": "Cash",
        }
    )
    assert partial["payment_status"] == "K\u0131smi \u00d6dendi"

    paid = web_main.record_customer_payment(
        {
            "customer_id": customer_id,
            "currency": "TRY",
            "amount": 300,
            "reference": tracking_no,
            "description": "Remaining service payment",
            "payment_method": "Card",
        }
    )
    assert paid["open_debt_after"] == 0
    assert paid["payment_status"] == "\u00d6dendi"

    db = _open_database(database_path)
    status = db.cursor.execute(
        "SELECT payment_status FROM devices WHERE id=?", (device_id,)
    ).fetchone()[0]
    balance = db.cursor.execute(
        "SELECT balance FROM customer_currency_balances "
        "WHERE customer_id=? AND currency='TRY'",
        (customer_id,),
    ).fetchone()[0]
    accounting_count = db.cursor.execute(
        "SELECT COUNT(*) FROM accounting WHERE tracking_no=? AND type='Gelir'",
        (tracking_no,),
    ).fetchone()[0]
    assert status == "\u00d6dendi"
    assert float(balance) == 0.0
    assert int(accounting_count) == 2
    db.close()
    web_main.clear_tenant_context()


def test_technical_service_rejects_overpayment_without_extra_records(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "technical-overpayment.db"
    tracking_no = "TECH-PAY-2"
    customer_id, device_id, _part_id = _prepare_service_database(
        database_path, tracking_no=tracking_no
    )
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    web_main.update_technician_job(
        {
            "device_id": device_id,
            "tracking_no": tracking_no,
            "labor_cost": 100,
        }
    )

    with pytest.raises(ValueError, match="en fazla"):
        web_main.record_customer_payment(
            {
                "customer_id": customer_id,
                "currency": "TRY",
                "amount": 101,
                "reference": tracking_no,
            }
        )

    db = _open_database(database_path)
    credits = db.cursor.execute(
        "SELECT COUNT(*) FROM currency_transactions "
        "WHERE tracking_no=? AND transaction_type='CREDIT'",
        (tracking_no,),
    ).fetchone()[0]
    assert int(credits) == 0
    db.close()
    web_main.clear_tenant_context()


def test_technical_service_web_and_mobile_signals_are_connected():
    web_root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    app_text = (web_root / "app.js").read_text(encoding="utf-8")
    parity_text = (web_root / "automotive-parity.js").read_text(
        encoding="utf-8"
    )
    sources = app_text + "\n" + parity_text

    required_actions = {
        "add-customer": "saveCustomer",
        "new-service": "serviceDialog",
        "service-detail": "serviceDetailDialog",
        "technician-open": "technicianDialog",
        "add-appointment": "appointmentDialog",
        "add-product": "productForm",
    }
    for action, handler in required_actions.items():
        assert re.search(rf'data-action=["\']{re.escape(action)}["\']', sources)
        assert handler in sources

    assert 'data-modal-action="payment"' in sources
    assert "paymentDialog" in sources

    assert 'await apiFetch("/api/desktop/table/customers"' in parity_text
    assert 'await apiFetch("/api/desktop/table/devices"' in parity_text
    assert 'await apiFetch("/api/desktop/table/appointments"' in parity_text
    assert 'apiFetch("/api/desktop/technician/update"' in sources
    assert 'apiFetch("/api/desktop/customer/payment"' in sources
    assert 'apiFetch("/api/desktop/stock/save"' in sources
    assert "ondblclick" in sources
    assert "contextmenu" in sources


def test_technical_service_currency_and_payment_status_ui_guards():
    parity_text = (
        Path(__file__).resolve().parents[1]
        / "Web_Arayuzu"
        / "web"
        / "automotive-parity.js"
    ).read_text(encoding="utf-8")

    assert "baseServiceDetailDialog=serviceDetailDialog" in parity_text
    assert "totals.set(currency" in parity_text
    assert "money(total,currency)" in parity_text
    assert "paymentStatus.disabled=true" in parity_text
