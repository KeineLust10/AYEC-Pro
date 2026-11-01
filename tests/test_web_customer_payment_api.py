from contextlib import closing
from http.server import ThreadingHTTPServer
import shutil
import sqlite3
import threading

import requests

import Web_Arayuzu.Main as web_main
from src.database import Database
from tests.test_vendor_management_center import _setup_tenant


def _seed_payment_debt(path, customer_id, name, amount):
    with closing(sqlite3.connect(path)) as conn:
        conn.execute(
            "INSERT INTO customers(id,name,is_deleted) VALUES(?,?,0)",
            (customer_id, name),
        )
        conn.execute(
            "INSERT INTO customer_currency_balances "
            "(customer_id,currency,balance,last_updated) VALUES(?,?,?,?)",
            (customer_id, "TRY", -amount, "2026-10-24"),
        )
        cursor = conn.execute(
            "INSERT INTO currency_transactions "
            "(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,"
            "description,tracking_no,created_at,current_balance,is_invoiced) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                customer_id,
                "DEBIT",
                amount,
                "TRY",
                1,
                amount,
                "QA invoice debt",
                f"QA-{customer_id}",
                "2026-10-24 10:00:00",
                -amount,
                0,
            ),
        )
        conn.commit()
        return int(cursor.lastrowid)


def _post_payment(session, url, customer_id, amount, debt_id):
    return session.post(
        url,
        json={
            "customer_id": customer_id,
            "customer_name": f"QA Customer {customer_id}",
            "amount": amount,
            "currency": "TRY",
            "description": "QA tenant-scoped payment",
            "payment_method": "Banka",
            "reference": f"QA-{customer_id}",
            "date": "2026-10-24",
            "selected_debt_ids": [debt_id],
            "exchange_rate": 1,
        },
    )


def test_customer_payment_requires_auth_and_is_tenant_scoped(monkeypatch, tmp_path):
    _actor, tenant_one_path = _setup_tenant(monkeypatch, tmp_path)
    Database(str(tenant_one_path)).close()
    tenant_one_debt_id = _seed_payment_debt(tenant_one_path, 71, "QA Customer 71", 100)

    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active,product_code) "
            "VALUES(?,?,?,?,1,?)",
            ("tenant-2", "Second Company", "Second Company.db", "2026-01-02T00:00:00", "teknik_servis"),
        )
        registry.commit()
    tenant_two_path = web_main._tenant_path(web_main.tenant_by_id("tenant-2"))
    tenant_two_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tenant_one_path, tenant_two_path)
    with closing(sqlite3.connect(tenant_two_path)) as tenant:
        tenant.execute("UPDATE users SET email='operator2@example.com' WHERE id=2")
        tenant.execute(
            "UPDATE customer_currency_balances SET balance=-200 WHERE customer_id=71 AND currency='TRY'"
        )
        tenant.execute(
            "UPDATE currency_transactions SET amount=200,try_equivalent=200,current_balance=-200 "
            "WHERE customer_id=71 AND transaction_type='DEBIT'"
        )
        tenant.commit()

    web_main.clear_tenant_context()
    with closing(web_main.db_connect()) as registry_db:
        registry_db.execute("INSERT INTO customers(id,name,is_deleted) VALUES(72,'QA Anonymous Customer',0)")
        registry_db.execute(
            "INSERT INTO customer_currency_balances "
            "(customer_id,currency,balance,last_updated) VALUES(72,'TRY',-100,'2026-10-24')"
        )
        registry_db.execute(
            "INSERT INTO currency_transactions "
            "(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,"
            "description,tracking_no,created_at,current_balance,is_invoiced) "
            "VALUES(72,'DEBIT',100,'TRY',1,100,'QA debt','QA-72','2026-10-24 10:00:00',-100,0)"
        )
        registry_db.commit()

    monkeypatch.setattr(web_main, "exchange_rates", lambda refresh=False: {"TRY": 1, "USD": 1, "EUR": 1})
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    payment_url = f"{base_url}/api/desktop/customer/payment"

    def login(identifier, tenant_id):
        session = requests.Session()
        session.headers["Origin"] = base_url
        response = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": identifier,
                "password": "operator-test-pass",
                "tenant_id": tenant_id,
            },
        )
        assert response.status_code == 200, response.text
        return session

    try:
        anonymous = requests.post(
            payment_url,
            json={
                "customer_id": 72,
                "amount": 25,
                "currency": "TRY",
                "selected_debt_ids": [],
            },
        )
        assert anonymous.status_code == 401

        tenant_one = login(web_main.VENDOR_EMAIL, "tenant-1")
        tenant_two = login("operator2@example.com", "tenant-2")
        debts_url = f"{base_url}/api/desktop/customer/open-debts?customer_id=71&currency=TRY"
        assert tenant_one.get(debts_url).json()["items"][0]["remaining"] == 100
        assert tenant_two.get(debts_url).json()["items"][0]["remaining"] == 200
        paid = _post_payment(tenant_one, payment_url, 71, 40, tenant_one_debt_id)
        assert paid.status_code == 200, paid.text
        assert paid.json()["open_debt_before"] == 100
        assert paid.json()["open_debt_after"] == 60
        assert paid.json()["allocated_debt_remaining"] == 60
        assert tenant_one.get(debts_url).json()["items"][0]["remaining"] == 60
        assert tenant_two.get(debts_url).json()["items"][0]["remaining"] == 200

        with closing(sqlite3.connect(tenant_one_path)) as tenant_one_db:
            assert tenant_one_db.execute(
                "SELECT balance FROM customer_currency_balances WHERE customer_id=71 AND currency='TRY'"
            ).fetchone()[0] == -60
            assert tenant_one_db.execute(
                "SELECT COUNT(*) FROM currency_transactions WHERE customer_id=71 AND transaction_type='CREDIT'"
            ).fetchone()[0] == 1
        with closing(sqlite3.connect(tenant_two_path)) as tenant_two_db:
            assert tenant_two_db.execute(
                "SELECT balance FROM customer_currency_balances WHERE customer_id=71 AND currency='TRY'"
            ).fetchone()[0] == -200
            assert tenant_two_db.execute(
                "SELECT COUNT(*) FROM currency_transactions WHERE customer_id=71 AND transaction_type='CREDIT'"
            ).fetchone()[0] == 0

        cross_origin = requests.Session()
        cross_origin.headers["Origin"] = "https://attacker.example"
        cross_origin.cookies.update(tenant_one.cookies)
        rejected_origin = _post_payment(cross_origin, payment_url, 71, 10, tenant_one_debt_id)
        assert rejected_origin.status_code == 403

        overpayment = _post_payment(tenant_one, payment_url, 71, 61, tenant_one_debt_id)
        assert overpayment.status_code == 400
        with closing(sqlite3.connect(tenant_one_path)) as tenant_one_db:
            assert tenant_one_db.execute(
                "SELECT COUNT(*) FROM currency_transactions WHERE customer_id=71 AND transaction_type='CREDIT'"
            ).fetchone()[0] == 1
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_new_web_tenant_has_customer_payment_allocation_schema(monkeypatch, tmp_path):
    previous_ready_paths = set(web_main._SCHEMA_READY_PATHS)
    monkeypatch.setattr(web_main, "DB_PATH", tmp_path / "registry.db")
    monkeypatch.setattr(web_main, "TENANT_ROOT", tmp_path / "tenants")
    monkeypatch.setattr(web_main, "DEMO_TEMPLATE_PATH", tmp_path / "missing-template.db")
    web_main._SCHEMA_READY_PATHS.clear()
    try:
        tenant = web_main.create_tenant(
            "QA Fresh Tenant",
            installation_lat=40.0,
            installation_lng=28.0,
        )
        tenant_path = web_main._tenant_path(tenant)
        with closing(sqlite3.connect(tenant_path)) as connection:
            available_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            assert web_main.REQUIRED_OPERATIONAL_TABLES.issubset(available_tables)
            assert connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='payment_debt_links'"
            ).fetchone()
            part_columns = {
                row[1]: row
                for row in connection.execute('PRAGMA table_info("parts")')
            }
            assert part_columns["min_stock"][2] == "REAL"
            assert part_columns["min_stock"][4] == "5"
            for table, required_columns in web_main.REQUIRED_OPERATIONAL_COLUMNS.items():
                available = {
                    row[1] for row in connection.execute(f'PRAGMA table_info("{table}")')
                }
                assert set(required_columns).issubset(available), table
            connection.execute("DROP TABLE payment_debt_links")
            connection.execute("DROP TABLE product_groups")
            connection.execute("DROP TABLE stock_locations")
            connection.execute("DROP TABLE offer_reversals")
            connection.execute("DROP TABLE appointment_plan_items")
            connection.execute('ALTER TABLE "fast_notes" DROP COLUMN "display_category"')
            connection.execute('ALTER TABLE "fast_notes" DROP COLUMN "title"')
            connection.execute('ALTER TABLE "services" DROP COLUMN "duration_minutes"')
            connection.execute('ALTER TABLE "offers" DROP COLUMN "payment_method"')
            connection.execute('ALTER TABLE "appointments" DROP COLUMN "workflow"')
            connection.execute('ALTER TABLE "parts" DROP COLUMN "updated_at"')
            connection.execute('ALTER TABLE "used_parts" DROP COLUMN "stock_location_id"')
            connection.execute('ALTER TABLE "customers" DROP COLUMN "updated_at"')
            connection.commit()
            assert not web_main.operational_schema_ready(connection)
        web_main.set_tenant_context(tenant)
        try:
            with closing(web_main.db_connect()) as connection:
                assert connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='payment_debt_links'"
                ).fetchone()
                available_tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                assert web_main.REQUIRED_OPERATIONAL_TABLES.issubset(available_tables)
                for table, required_columns in web_main.REQUIRED_OPERATIONAL_COLUMNS.items():
                    column_info = {
                        row[1]: row
                        for row in connection.execute(f'PRAGMA table_info("{table}")')
                    }
                    available = set(column_info)
                    assert set(required_columns).issubset(available), table
                fast_note_columns = {
                    row[1]: row
                    for row in connection.execute('PRAGMA table_info("fast_notes")')
                }
                assert fast_note_columns["display_category"][4] == "''"
                assert fast_note_columns["title"][4] == "''"
                used_part_columns = {
                    row[1]: row
                    for row in connection.execute('PRAGMA table_info("used_parts")')
                }
                assert used_part_columns["exchange_rate"][4] == "1"
                assert used_part_columns["stock_location_id"][2] == "INTEGER"
            debt_id = _seed_payment_debt(tenant_path, 87, "QA Fresh Tenant Customer", 100)
            with closing(web_main.db_connect()) as connection:
                connection.execute(
                    "INSERT INTO users(username,password,email,phone,role,active) "
                    "VALUES(?,?,?,?,?,1)",
                    (
                        "fresh-admin",
                        web_main.password_hash("fresh-admin-pass"),
                        "fresh-admin@example.test",
                        "",
                        "Admin",
                    ),
                )
                connection.commit()
        finally:
            web_main.clear_tenant_context()
        monkeypatch.setattr(
            web_main,
            "exchange_rates",
            lambda refresh=False: {"TRY": 1, "USD": 1, "EUR": 1},
        )
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
                    "identifier": "fresh-admin@example.test",
                    "password": "fresh-admin-pass",
                    "tenant_id": tenant["id"],
                },
            )
            assert login.status_code == 200, login.text
            payment = session.post(
                f"{base_url}/api/desktop/customer/payment",
                json={
                    "customer_id": 87,
                    "amount": 25,
                    "currency": "TRY",
                    "description": "QA fresh-tenant payment",
                    "selected_debt_ids": [debt_id],
                    "exchange_rate": 1,
                    "date": "2026-10-24",
                },
            )
            assert payment.status_code == 200, payment.text
            assert payment.json()["open_debt_before"] == 100
            assert payment.json()["open_debt_after"] == 75
            assert payment.json()["allocated_debt_remaining"] == 75
            group_bootstrap = session.get(
                f"{base_url}/api/desktop/product-groups/bootstrap"
            )
            assert group_bootstrap.status_code == 200, group_bootstrap.text
            group_create = session.post(
                f"{base_url}/api/desktop/table/product_groups",
                json={"name": "QA Fresh Tenant Group", "is_active": 1},
            )
            assert group_create.status_code == 200, group_create.text
            groups = session.get(
                f"{base_url}/api/desktop/table/product_groups?limit=1000"
            )
            assert groups.status_code == 200, groups.text
            assert any(
                row["name"] == "QA Fresh Tenant Group"
                for row in groups.json().get("rows", [])
            )
            location_create = session.post(
                f"{base_url}/api/desktop/stock/location-management",
                json={
                    "action": "create-location",
                    "name": "QA Fresh Tenant Warehouse",
                    "location_type": "warehouse",
                },
            )
            assert location_create.status_code == 200, location_create.text
            warehouse_id = location_create.json().get("location_id")
            assert warehouse_id
            with closing(sqlite3.connect(tenant_path)) as connection:
                cursor = connection.execute(
                    "INSERT INTO parts(name,part_name,stock,price,currency,is_deleted) "
                    "VALUES(?,?,?,?,?,0)",
                    ("QA Fresh Tenant Part", "QA Fresh Tenant Part", 10, 5, "TRY"),
                )
                part_id = int(cursor.lastrowid)
                main_location_id = int(
                    connection.execute(
                        "SELECT id FROM stock_locations WHERE location_type='main' LIMIT 1"
                    ).fetchone()[0]
                )
                connection.commit()
            transfer = session.post(
                f"{base_url}/api/desktop/stock/location-management",
                json={
                    "action": "transfer-stock",
                    "source_location_id": main_location_id,
                    "target_location_id": warehouse_id,
                    "lines": [{"part_id": part_id, "quantity": 3, "unit": "Adet"}],
                },
            )
            assert transfer.status_code == 200, transfer.text
            assert transfer.json().get("transfer_id")
            with closing(sqlite3.connect(tenant_path)) as connection:
                balances = dict(
                    connection.execute(
                        "SELECT location_id,quantity FROM stock_location_balances "
                        "WHERE part_id=?",
                        (part_id,),
                    )
                )
                assert balances[main_location_id] == 7
                assert balances[warehouse_id] == 3
            rejected_transfer = session.post(
                f"{base_url}/api/desktop/stock/location-management",
                json={
                    "action": "transfer-stock",
                    "source_location_id": main_location_id,
                    "target_location_id": warehouse_id,
                    "lines": [{"part_id": part_id, "quantity": 8, "unit": "Adet"}],
                },
            )
            assert rejected_transfer.status_code == 400
            with closing(sqlite3.connect(tenant_path)) as connection:
                balances = dict(
                    connection.execute(
                        "SELECT location_id,quantity FROM stock_location_balances "
                        "WHERE part_id=?",
                        (part_id,),
                    )
                )
                transfer_count = connection.execute(
                    "SELECT COUNT(*) FROM stock_transfers"
                ).fetchone()[0]
                assert balances[main_location_id] == 7
                assert balances[warehouse_id] == 3
                assert transfer_count == 1
            stock_count = session.post(
                f"{base_url}/api/desktop/stock/location-management",
                json={
                    "action": "save-count",
                    "location_id": warehouse_id,
                    "lines": [{"part_id": part_id, "counted_quantity": 2}],
                    "note": "QA fresh schema count",
                },
            )
            assert stock_count.status_code == 200, stock_count.text
            assert stock_count.json().get("count_id")
            with closing(sqlite3.connect(tenant_path)) as connection:
                count_line = connection.execute(
                    "SELECT expected_quantity,counted_quantity,difference "
                    "FROM stock_count_lines WHERE count_id=?",
                    (stock_count.json()["count_id"],),
                ).fetchone()
                assert count_line == (3, 2, -1)
                warehouse_quantity = connection.execute(
                    "SELECT quantity FROM stock_location_balances "
                    "WHERE part_id=? AND location_id=?",
                    (part_id, warehouse_id),
                ).fetchone()[0]
                total_stock = connection.execute(
                    "SELECT stock FROM parts WHERE id=?", (part_id,)
                ).fetchone()[0]
                assert warehouse_quantity == 2
                assert total_stock == 9
            stock_kit = session.post(
                f"{base_url}/api/desktop/stock/location-management",
                json={
                    "action": "save-kit",
                    "name": "QA Fresh Tenant Kit",
                    "lines": [{"part_id": part_id, "quantity": 1}],
                },
            )
            assert stock_kit.status_code == 200, stock_kit.text
            assert stock_kit.json().get("kit_id")
            with closing(sqlite3.connect(tenant_path)) as connection:
                kit_line = connection.execute(
                    "SELECT part_id,quantity FROM stock_kit_lines WHERE kit_id=?",
                    (stock_kit.json()["kit_id"],),
                ).fetchone()
                assert kit_line == (part_id, 1)
            vehicle_create = session.post(
                f"{base_url}/api/desktop/stock/location-management",
                json={
                    "action": "create-location",
                    "name": "QA Fresh Tenant Vehicle",
                    "location_type": "vehicle",
                    "vehicle_plate": "QA-1",
                },
            )
            assert vehicle_create.status_code == 200, vehicle_create.text
            vehicle_id = vehicle_create.json()["location_id"]
            vehicle_transfer = session.post(
                f"{base_url}/api/desktop/stock/location-management",
                json={
                    "action": "transfer-stock",
                    "source_location_id": warehouse_id,
                    "target_location_id": vehicle_id,
                    "lines": [{"part_id": part_id, "quantity": 1, "unit": "Adet"}],
                },
            )
            assert vehicle_transfer.status_code == 200, vehicle_transfer.text
            with closing(sqlite3.connect(tenant_path)) as connection:
                connection.execute(
                    "INSERT INTO appointment_plan_items "
                    "(appointment_id,part_id,item_role,name,loaded_qty,used_qty,returned_qty,"
                    "source_location_id,vehicle_location_id,status,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        99401,
                        part_id,
                        "material",
                        "QA Fresh Tenant Part",
                        1,
                        0,
                        0,
                        warehouse_id,
                        vehicle_id,
                        "loaded",
                        "2026-10-24 10:00:00",
                        "2026-10-24 10:00:00",
                    ),
                )
                connection.commit()
            vehicle_count = session.post(
                f"{base_url}/api/desktop/stock/location-management",
                json={
                    "action": "save-count",
                    "location_id": vehicle_id,
                    "lines": [{"part_id": part_id, "counted_quantity": 0}],
                    "note": "QA vehicle stock reconciliation",
                },
            )
            assert vehicle_count.status_code == 200, vehicle_count.text
            with closing(sqlite3.connect(tenant_path)) as connection:
                plan_item = connection.execute(
                    "SELECT returned_qty,status FROM appointment_plan_items WHERE appointment_id=?",
                    (99401,),
                ).fetchone()
                assert plan_item == (1, "completed")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)
    finally:
        web_main._SCHEMA_READY_PATHS.clear()
        web_main._SCHEMA_READY_PATHS.update(previous_ready_paths)
