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


def test_service_debt_creation_includes_existing_unlinked_payments(tmp_path):
    database_path = tmp_path / "service-debt-existing-payment.db"
    tracking_no = "TECH-OLD-PAYMENT-1"
    customer_id, device_id, _part_id = _prepare_service_database(
        database_path, tracking_no=tracking_no, labor_cost=100
    )
    db = _open_database(database_path)
    db.cursor.execute(
        "UPDATE devices SET status='Tamirde' WHERE id=?", (device_id,)
    )
    db.cursor.execute(
        """
        INSERT INTO currency_transactions
            (customer_id, transaction_type, amount, currency, exchange_rate,
             try_equivalent, description, tracking_no, created_at, current_balance)
        VALUES (?, 'CREDIT', 25, 'TRY', 1, 25, 'Legacy service payment', ?,
                '2026-10-11 00:00:00', 25)
        """,
        (customer_id, tracking_no),
    )
    db.conn.commit()

    assert db._sync_service_debt_from_tracking(tracking_no, create_if_missing=True)

    balance = db.cursor.execute(
        "SELECT current_balance FROM currency_transactions "
        "WHERE customer_id=? AND tracking_no=? AND transaction_type='DEBIT'",
        (customer_id, tracking_no),
    ).fetchone()[0]
    assert float(balance) == -75.0
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
            "fault_description": "Intermittent startup failure",
            "accessories": "Power adapter, case",
            "checklist_status": "POWER,DISPLAY",
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
    wizard_fields = db.cursor.execute(
        "SELECT fault_description,accessories,checklist_status FROM devices WHERE id=?",
        (device_id,),
    ).fetchone()
    assert float(stock) == 3.0
    assert tuple(used) == (2, "USD", 40.0, 400.0)
    assert tuple(map(float, debit)) == (900.0, 900.0)
    assert float(balance) == -900.0
    assert status == "\u00d6denmedi"
    assert tuple(wizard_fields) == (
        "Intermittent startup failure",
        "Power adapter, case",
        "POWER,DISPLAY",
    )
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


def test_technician_manual_used_product_adds_service_debt_without_stock_movement(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "technical-manual-used-part.db"
    customer_id, device_id, part_id = _prepare_service_database(
        database_path, tracking_no="TECH-MANUAL-1"
    )
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    db = _open_database(database_path)
    movements_before = db.cursor.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE part_id=?", (part_id,)
    ).fetchone()[0]
    db.close()

    result = web_main.update_technician_job(
        {
            "device_id": device_id,
            "tracking_no": "TECH-MANUAL-1",
            "manual_used_parts": [{"name": "Screen cleaning", "price": 75}],
        }
    )

    assert result["service_charge_try"] == 75.0
    db = _open_database(database_path)
    used = db.cursor.execute(
        "SELECT part_id,part_name,price,quantity,currency,exchange_rate,price_try "
        "FROM used_parts WHERE tracking_no=? ORDER BY id DESC LIMIT 1",
        ("TECH-MANUAL-1",),
    ).fetchone()
    stock = db.cursor.execute("SELECT stock FROM parts WHERE id=?", (part_id,)).fetchone()[0]
    movements = db.cursor.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE part_id=?", (part_id,)
    ).fetchone()[0]
    debit = db.cursor.execute(
        "SELECT amount FROM currency_transactions WHERE customer_id=? AND tracking_no=? "
        "AND transaction_type='DEBIT'",
        (customer_id, "TECH-MANUAL-1"),
    ).fetchone()[0]
    assert tuple(used) == (None, "Screen cleaning", 75.0, 1, "TRY", 1.0, 75.0)
    assert float(stock) == 5.0
    assert movements == movements_before
    assert float(debit) == 75.0
    db.close()



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


def test_technician_service_collection_keeps_selected_bank_account(tmp_path, monkeypatch):
    database_path = tmp_path / "technical-bank-payment.db"
    tracking_no = "TECH-BANK-1"
    _customer_id, device_id, _part_id = _prepare_service_database(
        database_path, tracking_no=tracking_no
    )
    db = Database(str(database_path))
    assert db.add_bank_account("QA Bank", "QA Branch", "QA Account", "QA-001", "", 0)
    bank_account_id = db.conn.execute(
        "SELECT id FROM bank_accounts ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]
    db.close()
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)

    result = web_main.update_technician_job(
        {
            "device_id": device_id,
            "tracking_no": tracking_no,
            "status": "Delivered",
            "labor_cost": 250,
            "collect_payment": True,
            "payment_amount": 250,
            "payment_currency": "TRY",
            "payment_method": "Havale/EFT",
            "bank_account_id": bank_account_id,
        }
    )

    assert result["finance_id"] is not None
    with web_main.closing(web_main.db_connect()) as conn:
        saved = conn.execute(
            "SELECT bank_account_id,payment_method FROM accounting WHERE id=?",
            (result["finance_id"],),
        ).fetchone()
    assert saved["bank_account_id"] == bank_account_id
    assert saved["payment_method"] == "Havale/EFT"
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

    assert '$$(".c360-pay").forEach' in sources
    assert 'setTimeout(()=>paymentDialog(c),0)' in sources
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


def test_technician_payment_selects_and_persists_a_bank_account():
    web_root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    app = (web_root / "app.js").read_text(encoding="utf-8")
    technician = app[
        app.index("technicianDialog=async function(customer,service)"):
        app.index("const technicianDialogWithoutLock=technicianDialog")
    ]

    assert 'apiFetch("/api/desktop/table/bank_accounts?limit=500")' in technician
    assert 'name="bank_account_id"' in technician
    assert "Havale/EFT" in technician
    assert "bank_account_id:Number(values.bank_account_id)||0" in technician
    assert '"bank_account_id": bank_account_id or None' in Path(
        __file__
    ).resolve().parents[1].joinpath("Web_Arayuzu", "Main.py").read_text(encoding="utf-8")


def test_technician_service_tests_replace_saved_results_and_validate_tenant_record(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "technician-tests.db"
    _customer_id, _device_id, _part_id = _prepare_service_database(
        database_path, tracking_no="TECH-TEST-1"
    )
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    saved = web_main.technician_service_tests(
        "TECH-TEST-1",
        [
            {"name": "Display", "result": "Ge\u00e7ti", "note": "Touch works"},
            {"name": "Battery", "result": "Kald\u0131"},
        ],
        "Test Technician",
    )
    assert saved["saved"] == 2
    loaded = web_main.technician_service_tests("TECH-TEST-1")
    assert {item["name"]: item["result"] for item in loaded["tests"]} == {
        "Display": "Ge\u00e7ti", "Battery": "Kald\u0131"
    }
    web_main.technician_service_tests(
        "TECH-TEST-1", [{"name": "Display", "result": "Test Edilmedi"}], "Test Technician"
    )
    assert [item["name"] for item in web_main.technician_service_tests("TECH-TEST-1")["tests"]] == ["Display"]
    with pytest.raises(ValueError):
        web_main.technician_service_tests(
            "TECH-TEST-1", [{"name": "Display", "result": "Forged"}], "Test Technician"
        )
    with pytest.raises(LookupError):
        web_main.technician_service_tests("UNKNOWN-1")


def test_technician_history_reads_tenant_logs_and_used_parts(tmp_path, monkeypatch):
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    database_path = tenant_root / "tenant-a.db"
    _customer_id, _device_id, part_id = _prepare_service_database(
        database_path, tracking_no="TECH-HISTORY-1"
    )
    web_main.clear_tenant_context()
    admin_path = tmp_path / "admin.db"
    _prepare_service_database(admin_path, tracking_no="TECH-HISTORY-1")
    monkeypatch.setattr(web_main, "DB_PATH", admin_path)
    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    admin_conn = sqlite3.connect(admin_path)
    admin_conn.execute(
        "INSERT INTO logs(tracking_no,log_type,message,created_at,user) VALUES(?,?,?,?,?)",
        ("TECH-HISTORY-1", "Admin", "Wrong tenant event", "2026-10-18 13:00:00", "Admin User"),
    )
    admin_conn.commit()
    admin_conn.close()
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, tracking_no TEXT, log_type TEXT, message TEXT, created_at TEXT, user TEXT)"
    )
    conn.execute(
        "INSERT INTO logs(tracking_no,log_type,message,created_at,user) VALUES(?,?,?,?,?)",
        ("TECH-HISTORY-1", "Technician", "Diagnosis saved", "2026-10-18 12:00:00", "Tech A"),
    )
    part_columns = {row[1] for row in conn.execute('PRAGMA table_info("used_parts")')}
    part_values = {
        "tracking_no": "TECH-HISTORY-1", "part_id": part_id, "part_name": "Screen", "quantity": 2,
        "price": 125, "currency": "TRY", "created_at": "2026-10-18 12:30:00",
        "is_deleted": 0, "is_archived": 0,
    }
    selected = {key: value for key, value in part_values.items() if key in part_columns}
    conn.execute(
        f'INSERT INTO used_parts ({",".join(selected)}) VALUES ({",".join("?" for _ in selected)})',
        tuple(selected.values()),
    )
    conn.commit()
    conn.close()

    web_main.set_tenant_context({"id": "tenant-a", "db_filename": "tenant-a.db"})
    try:
        result = web_main.technician_service_history("TECH-HISTORY-1")
        assert [item["entry_type"] for item in result["events"]] == ["Part", "Technician"]
        assert "Screen x 2" in result["events"][0]["message"]
        assert result["events"][1]["user"] == "Tech A"
        assert "Wrong tenant event" not in str(result["events"])
        with pytest.raises(LookupError):
            web_main.technician_service_history("UNKNOWN-HISTORY")
    finally:
        web_main.clear_tenant_context()


def test_technician_test_catalog_uses_active_profile_and_sector_notes(tmp_path, monkeypatch):
    database_path = tmp_path / "technician-test-catalog.db"
    _customer_id, device_id, _part_id = _prepare_service_database(
        database_path, tracking_no="TECH-CATALOG-1"
    )
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    conn = sqlite3.connect(database_path)
    conn.execute("UPDATE devices SET device_type=? WHERE id=?", ("Cep Telefonu", device_id))
    conn.execute(
        "INSERT INTO internal_settings(key,value) VALUES('current_sector','teknik_servis') "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
    )
    phone_category = "Teknik Servis::Cep Telefonu::Cihaz Testi"
    conn.execute("DELETE FROM fast_notes WHERE category IN (?,?)", (phone_category, "Otomotiv Kontrol Listesi"))
    conn.executemany(
        "INSERT INTO fast_notes(category,label,is_active,display_order) VALUES(?,?,?,?)",
        [
            (phone_category, "Display check", 1, 0),
            (phone_category, "Hidden check", 0, 1),
            ("Otomotiv Kontrol Listesi", "Vehicle check", 1, 0),
        ],
    )
    conn.commit()
    conn.close()

    phone = web_main.technician_service_test_catalog("TECH-CATALOG-1")
    assert phone["category"] == phone_category
    assert phone["tests"] == [
        {"name": "Display check", "active": True},
        {"name": "Hidden check", "active": False},
    ]

    conn = sqlite3.connect(database_path)
    conn.execute(
        "INSERT INTO internal_settings(key,value) VALUES('current_sector','otomotiv') "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value"
    )
    conn.commit()
    conn.close()
    vehicle = web_main.technician_service_test_catalog("TECH-CATALOG-1")
    assert vehicle["category"] == "Otomotiv Kontrol Listesi"
    assert vehicle["tests"] == [{"name": "Vehicle check", "active": True}]

    with pytest.raises(LookupError):
        web_main.technician_service_test_catalog("UNKNOWN-CATALOG")


def test_technician_checklist_update_changes_only_the_active_service_checklist(tmp_path, monkeypatch):
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    database_path = tenant_root / "tenant-checklist.db"
    _customer_id, device_id, _part_id = _prepare_service_database(
        database_path, tracking_no="TECH-CHECKLIST-1", labor_cost=390
    )
    web_main.clear_tenant_context()
    admin_path = tmp_path / "admin.db"
    _customer_id, admin_device_id, _part_id = _prepare_service_database(
        admin_path, tracking_no="TECH-CHECKLIST-1", labor_cost=800
    )
    monkeypatch.setattr(web_main, "DB_PATH", admin_path)
    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    conn = sqlite3.connect(database_path)
    conn.execute("UPDATE devices SET technician=?,status=? WHERE id=?", ("Tech A", "Tamirde", device_id))
    conn.commit()
    conn.close()

    web_main.set_tenant_context({"id": "tenant-checklist", "db_filename": "tenant-checklist.db"})
    try:
        saved = web_main.update_technician_checklist(
            "TECH-CHECKLIST-1", ["LCD Check", "Battery", "LCD Check", ""]
        )
        assert saved["checklist_status"] == "LCD Check,Battery"
        conn = sqlite3.connect(database_path)
        device = conn.execute(
            "SELECT checklist_status,labor_cost,technician,status FROM devices WHERE id=?", (device_id,)
        ).fetchone()
        conn.close()
        assert device == ("LCD Check,Battery", 390, "Tech A", "Tamirde")
        conn = sqlite3.connect(admin_path)
        admin_device = conn.execute(
            "SELECT checklist_status,labor_cost FROM devices WHERE id=?", (admin_device_id,)
        ).fetchone()
        conn.close()
        assert admin_device == (None, 800)
        with pytest.raises(ValueError):
            web_main.update_technician_checklist("TECH-CHECKLIST-1", "LCD Check")
        with pytest.raises(ValueError):
            web_main.update_technician_checklist("TECH-CHECKLIST-1", ["X" * 161])
        with pytest.raises(LookupError):
            web_main.update_technician_checklist("UNKNOWN-CHECKLIST", [])
    finally:
        web_main.clear_tenant_context()


def test_desktop_label_api_reads_updates_and_resets_tenant_labels(tmp_path, monkeypatch):
    database_path = tmp_path / "tenant-labels.db"
    db = Database(str(database_path))
    db.cursor.execute(
        "INSERT INTO app_labels(key_name,default_value,current_value,category,description) VALUES(?,?,?,?,?)",
        ("audit_label", "Default text", None, "Audit", "Fixture label"),
    )
    db.conn.commit()
    db.close()
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)
    assert web_main.desktop_label_entries("Audit")[0]["key"] == "audit_label"
    assert web_main.update_desktop_label("audit_label", "Custom text")["ok"]
    assert web_main.desktop_label_entries(search="Custom")[0]["current"] == "Custom text"
    assert web_main.update_desktop_label("audit_label", reset=True)["reset"]
    assert web_main.desktop_label_entries("Audit")[0]["current"] is None
    with pytest.raises(LookupError):
        web_main.update_desktop_label("unknown_label", "No")
