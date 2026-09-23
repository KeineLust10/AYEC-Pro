import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.services.offer_acceptance_service import (
    OfferAcceptanceError,
    OfferAcceptanceService,
)
from src.ui.dialogs.customer_360_dialog import Customer360Dialog
from src.ui.pages.new_transaction_v2_page import NewTransactionV2Page

def _app():
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app


def _create_customer(db):
    db.cursor.execute(
        """
        INSERT INTO customers (name, phone, email, type)
        VALUES (?, ?, ?, ?)
        """,
        ("Test Customer", "5550000000", "test@example.com", "Individual"),
    )
    db.conn.commit()
    return int(db.cursor.lastrowid)


def _create_part(db):
    db.cursor.execute(
        """
        INSERT INTO parts (
            name, part_name, stock, price, purchase_price, currency, code
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        ("Test Part", "Test Part", 10, 5000, 3000, "TRY", "PART-1"),
    )
    db.conn.commit()
    return int(db.cursor.lastrowid)


def _create_offer(db, customer_id, part_id):
    return db.save_offer_record(
        {
            "offer_no": "PRF-TEST-1",
            "customer_id": customer_id,
            "customer_name": "Test Customer",
            "company_name": "Test Company",
            "contact_name": "Test Customer",
            "project_name": "Test Project",
            "template_type": "modern",
            "currency_code": "TRY",
            "currency_symbol": "TL",
            "exchange_rate": 1,
            "totals": {
                "subtotal": 40000,
                "discount": 0,
                "vat_rate": 0,
                "vat_amount": 0,
                "total": 40000,
            },
            "totals_try": {
                "subtotal": 40000,
                "discount": 0,
                "vat_amount": 0,
                "total": 40000,
            },
            "status": "created",
            "source": "sales_hub",
            "items": [
                {
                    "item_id": part_id,
                    "type": "part",
                    "service": "Test Part",
                    "description": "Stock item",
                    "qty": 2,
                    "price": 5000,
                },
                {
                    "item_id": None,
                    "type": "service",
                    "service": "Labor",
                    "description": "Installation",
                    "qty": 1,
                    "price": 30000,
                },
            ],
        }
    )


def test_offer_acceptance_records_down_payment_balance_and_stock_once():
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    offer_id = _create_offer(db, customer_id, part_id)

    result = OfferAcceptanceService(db).accept(
        offer_id,
        payment_amount=10000,
        payment_method="Nakit",
        accepted_by="tester",
    )

    assert result["total"] == 40000
    assert result["payment"] == 10000
    assert result["remaining"] == 30000
    assert db.get_customer_currency_balance(customer_id, "TRY") == -30000

    offer = db.get_offer_record(offer_id)
    assert offer["status"] == "accepted"
    assert offer["accepted_by"] == "tester"
    assert offer["accepted_payment"] == 10000
    assert offer["remaining_amount"] == 30000
    assert offer["payment_method"] == "Nakit"

    transactions = db.cursor.execute(
        """
        SELECT transaction_type, amount, tracking_no
        FROM currency_transactions
        WHERE customer_id=?
        ORDER BY id
        """,
        (customer_id,),
    ).fetchall()
    assert [(row[0], row[1]) for row in transactions] == [
        ("DEBIT", 40000),
        ("CREDIT", 10000),
    ]
    assert transactions[0][2] == transactions[1][2]
    assert transactions[0][2] == offer["processed_tracking_no"]

    stock = db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?",
        (part_id,),
    ).fetchone()[0]
    assert stock == 8

    accounting = db.cursor.execute(
        """
        SELECT type, category, amount, selected_services
        FROM accounting
        WHERE tracking_no=?
        ORDER BY id
        """,
        (offer["processed_tracking_no"],),
    ).fetchall()
    assert [(row[0], row[1], row[2]) for row in accounting] == [
        ("Gelir", "Satis", 40000),
        ("Gider", "Satilan Malin Maliyeti", 6000),
    ]
    sale_items = json.loads(accounting[0][3])
    assert [item["service"] for item in sale_items] == ["Test Part", "Labor"]

    with pytest.raises(OfferAcceptanceError, match="already processed"):
        OfferAcceptanceService(db).accept(offer_id, payment_amount=10000)

    stock_after_retry = db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?",
        (part_id,),
    ).fetchone()[0]
    assert stock_after_retry == 8


def test_accepted_offer_cannot_be_overwritten_by_edit_save():
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    offer_id = _create_offer(db, customer_id, part_id)
    OfferAcceptanceService(db).accept(offer_id, payment_amount=0)

    with pytest.raises(ValueError, match="cannot be edited"):
        db.save_offer_record(
            {
                "offer_id": offer_id,
                "offer_no": "PRF-TEST-1",
                "customer_id": customer_id,
                "currency_code": "TRY",
                "totals": {"total": 1},
                "totals_try": {"total": 1},
                "items": [],
            }
        )


def test_localized_processed_offer_cannot_be_overwritten_by_edit_save():
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    offer_id = _create_offer(db, customer_id, part_id)
    db.cursor.execute("UPDATE offers SET status=? WHERE id=?", ("\u0130\u015flendi", offer_id))
    db.conn.commit()

    with pytest.raises(ValueError, match="cannot be edited"):
        db.save_offer_record(
            {
                "offer_id": offer_id,
                "offer_no": "PRF-TEST-1",
                "customer_id": customer_id,
                "currency_code": "TRY",
                "totals": {"total": 1},
                "totals_try": {"total": 1},
                "items": [],
            }
        )


def test_processed_offer_can_be_reversed_for_revision_with_stock_and_audit_trace():
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    offer_id = _create_offer(db, customer_id, part_id)
    result = OfferAcceptanceService(db).accept(offer_id, payment_amount=0)

    reversal = OfferAcceptanceService(db).reverse_for_revision(
        offer_id, "Musteri urun miktarini degistirdi", reversed_by="tester"
    )
    assert reversal["stock_entries"] == 1
    assert reversal["currency_entries"] >= 1
    assert reversal["accounting_entries"] >= 1
    assert db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?", (part_id,)
    ).fetchone()[0] == 10
    assert db.cursor.execute(
        "SELECT status FROM offers WHERE id=?", (offer_id,)
    ).fetchone()[0] == "revision_pending"
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE description LIKE 'Offer reversal:%'"
    ).fetchone()[0] == 1
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM audit_logs WHERE action='REVERSE_FOR_REVISION'"
    ).fetchone()[0] == 1


def test_reversal_restores_net_currency_balance_after_partial_collection():
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    offer_id = _create_offer(db, customer_id, part_id)
    OfferAcceptanceService(db).accept(offer_id, payment_amount=10000)
    assert db.get_customer_currency_balance(customer_id, "TRY") == -30000

    OfferAcceptanceService(db).reverse_for_revision(
        offer_id, "Revizyon icin tahsilat ve borc geri alindi", reversed_by="tester"
    )
    assert db.get_customer_currency_balance(customer_id, "TRY") == 0


def test_customer_360_offer_actions_have_live_qt_connections():
    app = _app()
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    _create_offer(db, customer_id, part_id)

    dialog = Customer360Dialog(db, customer_id, "Test Customer")
    app.processEvents()

    assert dialog.table_offers.topLevelItemCount() == 1
    assert dialog.btn_open_offer.receivers(dialog.btn_open_offer.clicked) > 0
    assert dialog.btn_edit_offer.receivers(dialog.btn_edit_offer.clicked) > 0
    assert dialog.btn_process_offer.receivers(dialog.btn_process_offer.clicked) > 0
    assert (
        dialog.table_offers.receivers(dialog.table_offers.itemDoubleClicked) > 0
    )

    dialog.close()
    dialog.deleteLater()
    app.processEvents()
    db.close()


def test_offer_edit_loads_sales_cart_without_deducting_stock(monkeypatch):
    app = _app()
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    offer_id = _create_offer(db, customer_id, part_id)
    stock_before = db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?",
        (part_id,),
    ).fetchone()[0]

    page = NewTransactionV2Page(db)
    monkeypatch.setattr(page, "notify", lambda *_args, **_kwargs: None)
    page.load_offer_for_edit(offer_id)
    app.processEvents()

    assert page._editing_offer_id == offer_id
    assert page._editing_offer_no == "PRF-TEST-1"
    assert page._editing_offer_project == "Test Project"
    assert page._editing_offer_template == "modern"
    assert len(page.cart_items) == 2
    assert page.cart_items[0]["item_id"] == part_id
    assert page.cart_items[0]["qty"] == 2
    assert page.cmb_vat.currentText() == "%0"
    stock_after = db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?",
        (part_id,),
    ).fetchone()[0]
    assert stock_after == stock_before

    page.close()
    page.deleteLater()


def test_offer_edit_restores_pdf_approval_preference(monkeypatch):
    app = _app()
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    offer_id = _create_offer(db, customer_id, part_id)
    payload = json.loads(
        db.cursor.execute(
            "SELECT payload_json FROM offers WHERE id=?",
            (offer_id,),
        ).fetchone()[0]
    )
    payload["include_approval"] = False
    db.cursor.execute(
        "UPDATE offers SET payload_json=? WHERE id=?",
        (json.dumps(payload), offer_id),
    )
    db.conn.commit()

    page = NewTransactionV2Page(db)
    monkeypatch.setattr(page, "notify", lambda *_args, **_kwargs: None)
    page.load_offer_for_edit(offer_id)
    app.processEvents()

    assert page.toggle_offer_approval.isChecked() is False
    page.clear_cart()
    assert page.toggle_offer_approval.isChecked() is True

    page.close()
    page.deleteLater()
    app.processEvents()
    db.close()


def test_legacy_percent_offer_is_normalized_before_edit():
    app = _app()
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    offer_id = _create_offer(db, customer_id, part_id)
    db.cursor.execute(
        """
        UPDATE offers
        SET vat_rate=20, vat_amount=800000, total=840000,
            vat_amount_try=800000, total_try=840000
        WHERE id=?
        """,
        (offer_id,),
    )
    db.conn.commit()

    db.create_offer_tables()
    repaired = db.get_offer_record(offer_id)
    assert float(repaired["vat_rate"]) == pytest.approx(0.20)
    assert float(repaired["vat_amount"]) == pytest.approx(8000)
    assert float(repaired["total"]) == pytest.approx(48000)

    page = NewTransactionV2Page(db)
    page.notify = lambda *_args, **_kwargs: None
    page.load_offer_for_edit(offer_id)
    app.processEvents()
    assert page.cmb_vat.currentText() == "%20"
    assert page.update_totals()[3] == pytest.approx(48000)

    page.close()
    page.deleteLater()
    db.close()
    app.processEvents()
    db.close()


def test_offer_acceptance_rolls_back_partial_financial_and_stock_changes(
    monkeypatch,
):
    db = Database(":memory:")
    customer_id = _create_customer(db)
    part_id = _create_part(db)
    offer_id = _create_offer(db, customer_id, part_id)
    original_add_transaction = db.add_transaction
    call_count = {"value": 0}

    def fail_on_cost_transaction(*args, **kwargs):
        call_count["value"] += 1
        if call_count["value"] == 2:
            raise RuntimeError("Injected accounting failure")
        return original_add_transaction(*args, **kwargs)

    monkeypatch.setattr(db, "add_transaction", fail_on_cost_transaction)
    with pytest.raises(OfferAcceptanceError, match="Injected accounting failure"):
        OfferAcceptanceService(db).accept(offer_id, payment_amount=10000)

    assert db.cursor.execute(
        "SELECT COUNT(*) FROM currency_transactions WHERE tracking_no LIKE 'OFFER-%'"
    ).fetchone()[0] == 0
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM accounting WHERE tracking_no LIKE 'OFFER-%'"
    ).fetchone()[0] == 0
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM used_parts WHERE tracking_no LIKE 'OFFER-%'"
    ).fetchone()[0] == 0
    assert db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?",
        (part_id,),
    ).fetchone()[0] == 10
    assert db.get_customer_currency_balance(customer_id, "TRY") == 0
    assert db.get_offer_record(offer_id)["status"] == "processing_error"
