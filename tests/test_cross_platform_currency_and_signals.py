import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.database import Database
from Web_Arayuzu import Main as web_main


def _sales_database(path):
    db = Database(str(path))
    customer_id = db.add_customer(
        {
            "name": "Currency Test Customer",
            "phone": "05550000001",
            "email": "currency@example.com",
        }
    )
    part_ids = [
        db.add_part(
            "TRY Part", "General", 10, 100,
            purchase_price=50, currency="TRY", code="TRY-1",
        ),
        db.add_part(
            "USD Part", "General", 10, 10,
            purchase_price=5, currency="USD", code="USD-1",
        ),
        db.add_part(
            "EUR Part", "General", 10, 20,
            purchase_price=10, currency="EUR", code="EUR-1",
        ),
    ]
    db.close()
    return customer_id, part_ids


def _configure_web_database(monkeypatch, path):
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", path)
    rates = {"TRY": 1.0, "USD": 40.0, "EUR": 50.0}
    monkeypatch.setattr(
        web_main,
        "resolve_exchange_rate",
        lambda _conn, currency, supplied=None: float(
            supplied or rates[str(currency).upper()]
        ),
    )


def test_unlinked_customer_payment_auto_allocation_rebuilds_currency_balance(tmp_path):
    db = Database(str(tmp_path / "auto-allocation-balance.db"))
    customer_id = db.add_customer({"name": "Auto Allocation Customer"})
    assert db.add_currency_transaction(
        customer_id, 100, "TRY", "DEBIT", exchange_rate=1.0,
        description="Service debt", tracking_no="AUTO-ALLOC-1",
    )
    assert db.add_currency_transaction(
        customer_id, 60, "TRY", "CREDIT", exchange_rate=1.0,
        description="Unlinked payment",
    )

    allocated = db.auto_allocate_unlinked_customer_payments(customer_id, "TRY")

    assert allocated == 1
    linked_amount = db.cursor.execute(
        "SELECT SUM(amount) FROM payment_debt_links"
    ).fetchone()[0]
    balance = db.cursor.execute(
        "SELECT balance FROM customer_currency_balances "
        "WHERE customer_id=? AND currency='TRY'",
        (customer_id,),
    ).fetchone()[0]
    assert float(linked_amount) == pytest.approx(60)
    assert float(balance) == pytest.approx(-40)
    db.close()


@pytest.mark.parametrize("device_type", ["Device", "Vehicle"])
def test_mixed_currency_offer_converts_without_reducing_stock(
    tmp_path, monkeypatch, device_type
):
    path = tmp_path / f"offer-{device_type}.db"
    customer_id, part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)

    base = {
        "mode": "proforma",
        "customer_id": customer_id,
        "customer_name": "Currency Test Customer",
        "rates": {"TRY": 1, "USD": 40, "EUR": 50},
        "lines": [{"product_id": part_id, "qty": 1} for part_id in part_ids],
        "device_type": device_type,
        "vat_rate": 20,
    }
    result_try = web_main.commit_sales_hub(
        {**base, "currency": "TRY", "exchange_rate": 1, "offer_no": "MIX-TRY"}
    )
    result_eur = web_main.commit_sales_hub(
        {**base, "currency": "EUR", "exchange_rate": 50, "offer_no": "MIX-EUR"}
    )

    assert result_try["subtotal"] == pytest.approx(1500)
    assert result_try["total"] == pytest.approx(1800)
    assert result_eur["subtotal"] == pytest.approx(30)
    assert result_eur["total"] == pytest.approx(36)

    db = Database(str(path))
    stocks = [
        float(row[0])
        for row in db.cursor.execute(
            "SELECT stock FROM parts WHERE id IN (?,?,?) ORDER BY id", part_ids
        ).fetchall()
    ]
    assert stocks == [10.0, 10.0, 10.0]
    items = db.cursor.execute(
        "SELECT unit_price,line_total FROM offer_items "
        "WHERE offer_id=? ORDER BY id",
        (result_eur["offer_id"],),
    ).fetchall()
    assert [float(row[0]) for row in items] == pytest.approx([2, 8, 20])
    db.close()


def test_sales_offer_accepts_explicit_line_price_and_description(tmp_path, monkeypatch):
    path = tmp_path / "custom-priced-offer.db"
    customer_id, part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)

    result = web_main.commit_sales_hub(
        {
            "mode": "proforma",
            "customer_id": customer_id,
            "customer_name": "Currency Test Customer",
            "currency": "USD",
            "exchange_rate": 40,
            "rates": {"TRY": 1, "USD": 40, "EUR": 50},
            "lines": [{"product_id": part_ids[0], "qty": 2, "unit_price": 3.5,
                       "description": "Screen replacement labor"}],
            "vat_rate": 0,
            "offer_no": "CUSTOM-PRICE-1",
        }
    )

    db = Database(str(path))
    item = db.cursor.execute(
        "SELECT unit_price,line_total,description,payload_json FROM offer_items WHERE offer_id=?",
        (result["offer_id"],),
    ).fetchone()
    db.close()

    assert result["subtotal"] == pytest.approx(7)
    assert float(item[0]) == pytest.approx(3.5)
    assert float(item[1]) == pytest.approx(7)
    assert item[2] == "Screen replacement labor"
    assert json.loads(item[3])["price_overridden"] is True


@pytest.mark.parametrize("unit_price", [-1, float("nan"), 1_000_000_001])
def test_sales_offer_rejects_invalid_explicit_line_price(tmp_path, monkeypatch, unit_price):
    path = tmp_path / f"invalid-price-{str(unit_price).replace('.', '-')}.db"
    customer_id, part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)

    with pytest.raises(ValueError):
        web_main.commit_sales_hub(
            {
                "mode": "proforma", "customer_id": customer_id,
                "customer_name": "Currency Test Customer", "currency": "TRY",
                "exchange_rate": 1, "rates": {"TRY": 1, "USD": 40, "EUR": 50},
                "lines": [{"product_id": part_ids[0], "qty": 1, "unit_price": unit_price}],
                "vat_rate": 0,
            }
        )


def test_mixed_currency_paid_sale_updates_stock_income_and_cost(
    tmp_path, monkeypatch
):
    path = tmp_path / "paid-sale.db"
    customer_id, part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)

    result = web_main.commit_sales_hub(
        {
            "mode": "payment",
            "customer_id": customer_id,
            "customer_name": "Currency Test Customer",
            "currency": "USD",
            "exchange_rate": 40,
            "rates": {"TRY": 1, "USD": 40, "EUR": 50},
            "lines": [{"product_id": part_id, "qty": 1} for part_id in part_ids],
            "vat_rate": 0,
            "reference": "MIX-SALE-1",
        }
    )

    assert result["subtotal"] == pytest.approx(37.5)
    assert result["total_try"] == pytest.approx(1500)
    db = Database(str(path))
    stocks = [
        float(row[0])
        for row in db.cursor.execute(
            "SELECT stock FROM parts WHERE id IN (?,?,?) ORDER BY id", part_ids
        ).fetchall()
    ]
    assert stocks == [9.0, 9.0, 9.0]
    income = db.cursor.execute(
        "SELECT amount,original_amount,try_equivalent,currency,exchange_rate "
        "FROM accounting WHERE id=?",
        (result["income_id"],),
    ).fetchone()
    cost = db.cursor.execute(
        "SELECT amount,try_equivalent,currency FROM accounting WHERE id=?",
        (result["cost_id"],),
    ).fetchone()
    assert tuple(income[:3]) == pytest.approx((1500, 37.5, 1500))
    assert income[3] == "USD"
    assert float(income[4]) == pytest.approx(40)
    assert tuple(cost[:2]) == pytest.approx((750, 750))
    assert cost[2] == "TRY"
    db.close()


def test_paid_sale_uses_explicit_line_price_and_keeps_line_description(tmp_path, monkeypatch):
    path = tmp_path / "custom-priced-sale.db"
    customer_id, part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)

    result = web_main.commit_sales_hub(
        {
            "mode": "payment", "customer_id": customer_id,
            "customer_name": "Currency Test Customer", "currency": "EUR",
            "exchange_rate": 50, "rates": {"TRY": 1, "USD": 40, "EUR": 50},
            "lines": [{"product_id": part_ids[0], "qty": 2, "unit_price": 4.5,
                       "description": "Screen replacement labor"}],
            "vat_rate": 0, "reference": "CUSTOM-SALE-1",
        }
    )

    db = Database(str(path))
    stock = db.cursor.execute("SELECT stock FROM parts WHERE id=?", (part_ids[0],)).fetchone()[0]
    income = db.cursor.execute(
        "SELECT amount,original_amount,currency FROM accounting WHERE id=?",
        (result["income_id"],),
    ).fetchone()
    movement = db.cursor.execute(
        "SELECT description FROM stock_movements WHERE id=?", (result["movement_ids"][0],)
    ).fetchone()[0]
    db.close()

    assert result["subtotal"] == pytest.approx(9)
    assert float(stock) == pytest.approx(8)
    assert float(income[0]) == pytest.approx(450)
    assert float(income[1]) == pytest.approx(9)
    assert income[2] == "EUR"
    assert "Screen replacement labor" in movement


def test_sales_hub_applies_discount_before_vat_and_persists_summary(
    tmp_path, monkeypatch
):
    path = tmp_path / "discounted-offer.db"
    customer_id, part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)

    result = web_main.commit_sales_hub(
        {
            "mode": "proforma",
            "customer_id": customer_id,
            "customer_name": "Currency Test Customer",
            "currency": "TRY",
            "exchange_rate": 1,
            "rates": {"TRY": 1, "USD": 40, "EUR": 50},
            "lines": [{"product_id": part_ids[0], "qty": 1}],
            "vat_rate": 20,
            "discount_percent": 5,
            "offer_no": "DISC-1",
        }
    )

    db = Database(str(path))
    row = db.cursor.execute(
        "SELECT payload_json FROM offers WHERE id=?", (result["offer_id"],)
    ).fetchone()
    db.close()
    payload = json.loads(row[0])

    assert result["subtotal"] == pytest.approx(100)
    assert result["discount"] == pytest.approx(5)
    assert result["vat_amount"] == pytest.approx(19)
    assert result["total"] == pytest.approx(114)
    assert payload["discount_percent"] == pytest.approx(5)
    assert payload["discount_try"] == pytest.approx(5)


def test_web_offer_update_replaces_items_without_creating_duplicate(
    tmp_path, monkeypatch
):
    path = tmp_path / "offer-update.db"
    customer_id, part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)
    payload = {
        "mode": "proforma",
        "customer_id": customer_id,
        "customer_name": "Currency Test Customer",
        "currency": "USD",
        "exchange_rate": 40,
        "rates": {"TRY": 1, "USD": 40, "EUR": 50},
        "lines": [{"product_id": part_ids[0], "qty": 1}],
        "vat_rate": 0,
        "offer_no": "EDIT-1",
    }
    created = web_main.commit_sales_hub(payload)
    updated = web_main.commit_sales_hub(
        {
            **payload,
            "offer_id": created["offer_id"],
            "lines": [{"product_id": part_ids[1], "qty": 2,
                       "description": "Install and configure device"}],
        }
    )

    db = Database(str(path))
    offer_count = db.cursor.execute(
        "SELECT COUNT(*) FROM offers WHERE offer_no='EDIT-1'"
    ).fetchone()[0]
    items = db.cursor.execute(
        "SELECT item_id,qty FROM offer_items WHERE offer_id=?",
        (created["offer_id"],),
    ).fetchall()
    db.close()

    assert updated["updated"] is True
    assert offer_count == 1
    assert [tuple(row) for row in items] == [(part_ids[1], 2)]


def test_web_service_commit_persists_device_and_customer_debt(
    tmp_path, monkeypatch
):
    path = tmp_path / "service-save.db"
    customer_id, part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)

    result = web_main.commit_sales_hub(
        {
            "mode": "service",
            "customer_id": customer_id,
            "customer_name": "Currency Test Customer",
            "currency": "USD",
            "exchange_rate": 40,
            "rates": {"TRY": 1, "USD": 40, "EUR": 50},
            "lines": [{"product_id": part_ids[1], "qty": 2,
                       "description": "Install and configure device"}],
            "vat_rate": 0,
            "reference": "WEB-SERVICE-1",
        }
    )

    db = Database(str(path))
    device = db.cursor.execute(
        "SELECT customer_id,tracking_no,service_source,repair_details FROM devices WHERE id=?",
        (result["device_id"],),
    ).fetchone()
    balance = db.cursor.execute(
        "SELECT balance FROM customer_currency_balances "
        "WHERE customer_id=? AND currency='USD'",
        (customer_id,),
    ).fetchone()
    assert tuple(device[:3]) == (customer_id, "WEB-SERVICE-1", "Web Sales Hub")
    assert "Install and configure device" in device[3]
    assert float(balance[0]) == pytest.approx(-20)
    income_count = db.cursor.execute(
        "SELECT COUNT(*) FROM accounting WHERE tracking_no='WEB-SERVICE-1' "
        "AND type='Gelir'"
    ).fetchone()[0]
    assert int(income_count) == 0


def test_sales_commit_accepts_service_lines_without_stock_movements(
    tmp_path, monkeypatch
):
    path = tmp_path / "service-line-offer.db"
    customer_id, part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)

    result = web_main.commit_sales_hub(
        {
            "mode": "proforma",
            "customer_id": customer_id,
            "customer_name": "Currency Test Customer",
            "currency": "TRY",
            "exchange_rate": 1,
            "rates": {"TRY": 1, "USD": 40, "EUR": 50},
            "lines": [{
                "line_type": "service",
                "service_id": 45,
                "service_name": "Installation",
                "service_description": "On-site setup",
                "unit_price": 750,
                "qty": 2,
            }],
            "offer_no": "SERVICE-OFFER-1",
        }
    )

    db = Database(str(path))
    item = db.cursor.execute(
        "SELECT item_id,item_type,service,qty,unit_price,line_total "
        "FROM offer_items WHERE offer_id=?",
        (result["offer_id"],),
    ).fetchone()
    stock = db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?", (part_ids[0],)
    ).fetchone()[0]
    assert tuple(item) == (None, "service", "Installation", 2.0, 750.0, 1500.0)
    assert float(stock) == 10.0
    db.close()


def test_accounting_normalizer_recomputes_try_value_on_currency_change():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE exchange_rates ("
        "id INTEGER PRIMARY KEY, currency TEXT, selling_rate REAL, created_at TEXT)"
    )
    conn.execute(
        "INSERT INTO exchange_rates(currency,selling_rate,created_at) "
        "VALUES ('EUR',50,'2026-07-23')"
    )
    result = web_main.normalize_accounting_payload(
        conn,
        {"currency": "EUR", "amount": 12},
        {"currency": "USD", "amount": 12, "exchange_rate": 40},
    )
    assert result["currency"] == "EUR"
    assert result["exchange_rate"] == 50
    assert result["amount"] == 600
    assert result["original_amount"] == 12
    assert result["try_equivalent"] == 600


def test_legacy_stock_expense_uses_explicit_line_currency(monkeypatch):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE accounting ("
        "id INTEGER PRIMARY KEY,currency TEXT,exchange_rate REAL,amount REAL,"
        "original_amount REAL,try_equivalent REAL,selected_services TEXT,"
        "is_deleted INTEGER DEFAULT 0)"
    )
    conn.execute(
        "INSERT INTO accounting(currency,exchange_rate,amount,original_amount,"
        "try_equivalent,selected_services) VALUES ('TRY',1,30,30,30,?)",
        ('[{"kind":"stock_purchase","quantity":3,"unit_price":10,'
         '"currency":"USD","line_total":30}]',),
    )
    monkeypatch.setattr(
        web_main,
        "resolve_exchange_rate",
        lambda _conn, currency, supplied=None: 40.0,
    )

    repaired = web_main.repair_explicit_stock_accounting_currency(conn)
    result = conn.execute(
        "SELECT amount,original_amount,currency,exchange_rate,try_equivalent "
        "FROM accounting WHERE id=1"
    ).fetchone()

    assert repaired == 1
    assert tuple(result[:2]) == pytest.approx((30, 30))
    assert result[2] == "USD"
    assert tuple(result[3:]) == pytest.approx((40, 1200))


@pytest.mark.parametrize(
    ("currency", "debt", "payment", "rate", "expected_try"),
    [("USD", 10, 4, 40, 160), ("EUR", 8, 3, 50, 150)],
)
def test_customer_payment_preserves_currency_rate_and_open_debt(
    tmp_path, monkeypatch, currency, debt, payment, rate, expected_try
):
    path = tmp_path / f"payment-{currency}.db"
    customer_id, _part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO customer_currency_balances "
            "(customer_id,currency,balance,last_updated) VALUES (?,?,?,?)",
            (customer_id, currency, -debt, "2026-07-23"),
        )

    result = web_main.record_customer_payment(
        {
            "customer_id": customer_id,
            "currency": currency,
            "amount": payment,
            "exchange_rate": rate,
            "reference": f"PAY-{currency}",
            "description": "Cross-platform payment",
            "payment_method": "Bank",
            "date": "2026-10-01",
        }
    )

    assert result["open_debt_before"] == pytest.approx(debt)
    assert result["open_debt_after"] == pytest.approx(debt - payment)
    assert result["exchange_rate"] == pytest.approx(rate)
    assert result["try_equivalent"] == pytest.approx(expected_try)
    with sqlite3.connect(path) as conn:
        accounting = conn.execute(
            "SELECT amount,original_amount,currency,exchange_rate,try_equivalent,date "
            "FROM accounting WHERE id=?",
            (result["finance_id"],),
        ).fetchone()
        transaction = conn.execute(
            "SELECT amount,currency,exchange_rate,try_equivalent,current_balance,created_at "
            "FROM currency_transactions WHERE id=?",
            (result["currency_transaction_id"],),
        ).fetchone()
    assert float(accounting[0]) == pytest.approx(expected_try)
    assert float(accounting[1]) == pytest.approx(payment)
    assert accounting[2] == currency
    assert tuple(map(float, accounting[3:5])) == pytest.approx((rate, expected_try))
    assert accounting[5] == "2026-10-01"
    assert float(transaction[0]) == pytest.approx(payment)
    assert transaction[1] == currency
    assert tuple(map(float, transaction[2:5])) == pytest.approx(
        (rate, expected_try, payment - debt)
    )
    assert transaction[5].startswith("2026-10-01 ")


def test_customer_payment_allocates_to_selected_invoice_debt(
    tmp_path, monkeypatch
):
    path = tmp_path / "selected-payment-debt.db"
    customer_id, _part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO customer_currency_balances "
            "(customer_id,currency,balance,last_updated) VALUES (?,?,?,?)",
            (customer_id, "TRY", -100, "2026-10-07"),
        )
        conn.execute(
            "INSERT INTO currency_transactions "
            "(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,"
            "description,tracking_no,created_at,current_balance,is_invoiced) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (customer_id, "DEBIT", 100, "TRY", 1, 100, "Invoice debt", "INV-42", "2026-10-07", -100, 0),
        )
        debt_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    result = web_main.record_customer_payment(
        {
            "customer_id": customer_id,
            "currency": "TRY",
            "amount": 35,
            "exchange_rate": 1,
            "debt_transaction_id": debt_id,
            "reference": "INV-42",
            "description": "Selected invoice payment",
            "payment_method": "Bank",
        }
    )

    assert result["allocated_debt_id"] == debt_id
    assert result["allocated_debt_remaining"] == pytest.approx(65)
    assert result["reference"] == "INV-42"
    with sqlite3.connect(path) as conn:
        allocation = conn.execute(
            "SELECT payment_txn_id,debt_txn_id,amount FROM payment_debt_links"
        ).fetchone()
    assert allocation[0] == result["currency_transaction_id"]
    assert allocation[1] == debt_id
    assert allocation[2] == pytest.approx(35)
    assert web_main.customer_open_debt_items(customer_id, "TRY")[0]["remaining"] == pytest.approx(65)


def test_customer_payment_cannot_overpay_one_selected_invoice(
    tmp_path, monkeypatch
):
    path = tmp_path / "selected-payment-limit.db"
    customer_id, _part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO customer_currency_balances "
            "(customer_id,currency,balance,last_updated) VALUES (?,?,?,?)",
            (customer_id, "TRY", -200, "2026-10-07"),
        )
        for reference in ("INV-1", "INV-2"):
            conn.execute(
                "INSERT INTO currency_transactions "
                "(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,"
                "description,tracking_no,created_at,current_balance,is_invoiced) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (customer_id, "DEBIT", 100, "TRY", 1, 100, "Invoice debt", reference, "2026-10-07", -100, 0),
            )
        first_debt_id = conn.execute(
            "SELECT id FROM currency_transactions WHERE tracking_no='INV-1'"
        ).fetchone()[0]

    with pytest.raises(ValueError, match="a\\u015famaz"):
        web_main.record_customer_payment(
            {
                "customer_id": customer_id,
                "currency": "TRY",
                "amount": 150,
                "exchange_rate": 1,
                "debt_transaction_id": first_debt_id,
                "description": "Overpayment attempt",
            }
        )

    with sqlite3.connect(path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM currency_transactions WHERE transaction_type='CREDIT'"
        ).fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM payment_debt_links").fetchone()[0] == 0


def test_customer_payment_allocates_across_selected_invoices_in_desktop_order(
    tmp_path, monkeypatch
):
    path = tmp_path / "selected-multi-payment.db"
    customer_id, _part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO customer_currency_balances "
            "(customer_id,currency,balance,last_updated) VALUES (?,?,?,?)",
            (customer_id, "TRY", -120, "2026-10-07"),
        )
        for reference, amount in (("INV-1", 50), ("INV-2", 70)):
            conn.execute(
                "INSERT INTO currency_transactions "
                "(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,"
                "description,tracking_no,created_at,current_balance,is_invoiced) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (customer_id, "DEBIT", amount, "TRY", 1, amount, "Invoice debt", reference, "2026-10-07", -amount, 0),
            )
        debt_ids = [row[0] for row in conn.execute(
            "SELECT id FROM currency_transactions WHERE tracking_no IN ('INV-1','INV-2') ORDER BY id"
        )]

    result = web_main.record_customer_payment(
        {
            "customer_id": customer_id,
            "currency": "TRY",
            "amount": 75,
            "exchange_rate": 1,
            "selected_debt_ids": debt_ids,
            "description": "Selected invoices payment",
        }
    )

    assert result["selected_debt_ids"] == debt_ids
    assert [(item["debt_id"], item["amount"]) for item in result["allocations"]] == [
        (debt_ids[0], 50), (debt_ids[1], 25)
    ]
    with sqlite3.connect(path) as conn:
        linked = conn.execute(
            "SELECT debt_txn_id,amount FROM payment_debt_links ORDER BY debt_txn_id"
        ).fetchall()
    assert linked == [(debt_ids[0], 50), (debt_ids[1], 25)]

    automatic = web_main.record_customer_payment(
        {
            "customer_id": customer_id,
            "currency": "TRY",
            "amount": 45,
            "exchange_rate": 1,
            "description": "Automatic FIFO payment",
        }
    )
    assert automatic["allocations"] == [
        {"debt_id": debt_ids[1], "amount": 45.0, "remaining_after": 0.0}
    ]


def test_web_open_debt_items_show_partial_and_unpaid_service_remainders(
    tmp_path, monkeypatch
):
    path = tmp_path / "open-debt-items.db"
    customer_id, _part_ids = _sales_database(path)
    _configure_web_database(monkeypatch, path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO currency_transactions "
            "(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,"
            "description,tracking_no,created_at,current_balance) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (customer_id, "DEBIT", 100, "USD", 40, 4000, "Service invoice", "SRV-001", "2026-10-01", -100),
        )
        conn.execute(
            "INSERT INTO currency_transactions "
            "(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,"
            "description,tracking_no,created_at,current_balance) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (customer_id, "CREDIT", 25, "USD", 40, 1000, "Partial payment", "SRV-001", "2026-10-02", -75),
        )
        conn.execute(
            "INSERT INTO currency_transactions "
            "(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,"
            "description,tracking_no,created_at,current_balance) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (customer_id, "DEBIT", 50, "USD", 40, 2000, "Second service invoice", "SRV-002", "2026-10-03", -50),
        )

    items = web_main.customer_open_debt_items(customer_id, "USD")

    assert [(item["tracking_no"], item["remaining"]) for item in items] == [
        ("SRV-002", 50),
        ("SRV-001", 75),
    ]


def test_web_finance_mobile_contract_and_action_bindings():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    css = (ROOT / "Web_Arayuzu" / "web" / "styles.css").read_text(
        encoding="utf-8"
    )

    assert 'input name="exchange_rate"' in app
    assert 'addEventListener("change",syncRate)' in app
    assert 'class="table-wrap finance-table"' in app
    assert 'data-label="TRY"' in app
    assert "financeTryValue(item)" in app
    assert "ayecFinanceExportRows" in app
    assert "ayecStockExportRows" in app
    assert '"Para Birimi"' in app
    assert '"TRY Kar\\u015f\\u0131l\\u0131\\u011f\\u0131"' in app
    assert ".finance-table .finance-action" in css
    assert "content:attr(data-label)" in css

    actions = set(re.findall(r'data-action=["\']([^"\']+)', app))
    missing = [name for name in sorted(actions) if len(re.findall(re.escape(name), app)) < 2]
    assert not missing, f"Actions without a matching handler reference: {missing}"

    parity = (ROOT / "Web_Arayuzu" / "web" / "automotive-parity.js").read_text(
        encoding="utf-8"
    )
    assert 'input name="exchange_rate"' in parity
    assert "amount*rate" in parity
    assert "/api/desktop/customer/payment" in app


def test_desktop_web_gap_audit_uses_current_layout():
    result = subprocess.run(
        [sys.executable, str(ROOT / "Web_Arayuzu" / "tools" / "desktop_web_gap_audit.py")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"sector"' in result.stdout
