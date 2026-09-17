import pytest

from src.database import Database
from src.utils.currency_helper import CurrencyHelper


def _new_database(tmp_path, name):
    return Database(str(tmp_path / name))


def _add_customer(db):
    return db.add_customer(
        {
            "name": "Atomic Customer",
            "phone": "05550000000",
            "email": "atomic@example.com",
        }
    )


def test_payment_allocation_retry_is_idempotent(tmp_path):
    db = _new_database(tmp_path, "payment-idempotency.db")
    customer_id = _add_customer(db)

    assert db.add_currency_transaction(
        customer_id=customer_id,
        amount=100,
        currency="TRY",
        transaction_type="DEBIT",
        exchange_rate=1,
        description="Service debt",
    )
    debt_id = db.get_last_currency_transaction_id()

    assert db.add_currency_transaction(
        customer_id=customer_id,
        amount=40,
        currency="TRY",
        transaction_type="CREDIT",
        exchange_rate=1,
        description="Partial payment",
    )
    payment_id = db.get_last_currency_transaction_id()

    first = db.apply_payment_to_debts(
        customer_id,
        40,
        "TRY",
        payment_transaction_id=payment_id,
        selected_debt_ids=[debt_id],
    )
    second = db.apply_payment_to_debts(
        customer_id,
        40,
        "TRY",
        payment_transaction_id=payment_id,
        selected_debt_ids=[debt_id],
    )

    assert first["ok"] is True
    assert first["allocated"] == pytest.approx(40)
    assert second["ok"] is True
    assert second["allocated"] == pytest.approx(0)
    assert db.cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM payment_debt_links "
        "WHERE payment_txn_id=?",
        (payment_id,),
    ).fetchone()[0] == pytest.approx(40)
    assert db.cursor.execute(
        "SELECT current_balance FROM currency_transactions WHERE id=?",
        (debt_id,),
    ).fetchone()[0] == pytest.approx(-60)
    assert db.get_customer_currency_balance(customer_id, "TRY") == pytest.approx(-60)
    db.close()


def test_use_part_rolls_back_stock_when_detail_insert_fails(tmp_path):
    db = _new_database(tmp_path, "part-rollback.db")
    part_id = db.add_part(
        "Rollback Part",
        "Computer",
        5,
        100,
        purchase_price=60,
        currency="TRY",
        code="ROLLBACK-PART",
    )
    initial_movement_count = db.cursor.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE part_id=?",
        (part_id,),
    ).fetchone()[0]
    db.cursor.execute("DROP TABLE used_parts")
    db.conn.commit()

    assert db.use_part(part_id, 2, "ROLLBACK-SERVICE") is False
    assert db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?",
        (part_id,),
    ).fetchone()[0] == pytest.approx(5)
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE part_id=?",
        (part_id,),
    ).fetchone()[0] == initial_movement_count
    db.close()


def test_unit_product_preflight_preserves_stock_and_finance(tmp_path):
    db = _new_database(tmp_path, "unit-product-preflight.db")
    project_id = db.add_project(
        {
            "name": "Atomic Project",
            "budget": 0,
            "currency": "TRY",
            "exchange_rate": 1,
        }
    )
    unit_id = db.add_project_unit(
        {
            "project_id": project_id,
            "block_name": "A",
            "unit_no": "A-1",
        }
    )
    part_id = db.add_part(
        "Limited Part",
        "Security",
        1,
        100,
        purchase_price=50,
        currency="TRY",
        code="LIMITED-PART",
    )

    result = db.add_unit_product(
        {
            "unit_id": unit_id,
            "project_id": project_id,
            "part_id": part_id,
            "part_name": "Limited Part",
            "quantity": 2,
        }
    )

    assert result is None
    assert db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?",
        (part_id,),
    ).fetchone()[0] == pytest.approx(1)
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM project_unit_products WHERE unit_id=?",
        (unit_id,),
    ).fetchone()[0] == 0
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM project_transactions WHERE project_id=?",
        (project_id,),
    ).fetchone()[0] == 0
    db.close()


def test_project_insert_rolls_back_when_finance_insert_fails(tmp_path, monkeypatch):
    db = _new_database(tmp_path, "project-rollback.db")
    monkeypatch.setattr(
        db,
        "add_project_transaction",
        lambda *_args, **_kwargs: False,
    )

    result = db.add_project(
        {
            "name": "Rejected Project",
            "budget": 1000,
            "currency": "TRY",
            "exchange_rate": 1,
        }
    )

    assert result is None
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM projects WHERE name='Rejected Project'"
    ).fetchone()[0] == 0
    db.close()


def test_accounting_and_bank_balance_commit_together(tmp_path):
    db = _new_database(tmp_path, "accounting-bank-atomicity.db")
    db.create_bank_accounts_table()
    db.cursor.execute(
        """
        INSERT INTO bank_accounts
        (bank_name, account_holder, current_balance, currency, created_at)
        VALUES ('Atomic Bank', 'Owner', 100, 'TRY', CURRENT_TIMESTAMP)
        """
    )
    bank_id = db.cursor.lastrowid
    db.conn.commit()

    transaction_id = db.add_transaction(
        t_type="Gelir",
        category="Tahsilat",
        amount=50,
        description="Atomic payment",
        bank_account_id=bank_id,
        payment_method="Banka",
    )

    assert transaction_id
    assert db.cursor.execute(
        "SELECT amount FROM accounting WHERE id=?",
        (transaction_id,),
    ).fetchone()[0] == pytest.approx(50)
    assert db.cursor.execute(
        "SELECT current_balance FROM bank_accounts WHERE id=?",
        (bank_id,),
    ).fetchone()[0] == pytest.approx(150)
    db.close()


def test_missing_bank_rolls_back_accounting_row(tmp_path):
    db = _new_database(tmp_path, "missing-bank-rollback.db")
    initial_count = db.cursor.execute(
        "SELECT COUNT(*) FROM accounting"
    ).fetchone()[0]

    with pytest.raises(RuntimeError):
        db.add_transaction(
            t_type="Gelir",
            category="Tahsilat",
            amount=50,
            description="Rejected payment",
            bank_account_id=999999,
            payment_method="Banka",
        )

    assert db.cursor.execute(
        "SELECT COUNT(*) FROM accounting"
    ).fetchone()[0] == initial_count
    db.close()


def test_missing_foreign_rate_rejects_accounting_row(tmp_path, monkeypatch):
    db = _new_database(tmp_path, "missing-rate-rejection.db")
    monkeypatch.setattr(
        CurrencyHelper,
        "_get_rate",
        staticmethod(lambda _db, _code: 0.0),
    )
    initial_count = db.cursor.execute(
        "SELECT COUNT(*) FROM accounting"
    ).fetchone()[0]

    with pytest.raises(ValueError):
        db.add_transaction(
            t_type="Gider",
            category="Stok",
            amount=10,
            description="No rate",
            currency="USD",
            original_amount=10,
        )

    assert db.cursor.execute(
        "SELECT COUNT(*) FROM accounting"
    ).fetchone()[0] == initial_count
    db.close()


def test_service_like_failure_rolls_back_debt_accounting_and_stock(tmp_path):
    db = _new_database(tmp_path, "service-workflow-rollback.db")
    customer_id = _add_customer(db)
    part_id = db.add_part(
        "Atomic Service Part",
        "Computer",
        3,
        75,
        purchase_price=40,
        currency="TRY",
        code="ATOMIC-SERVICE-PART",
    )
    db.cursor.execute(
        """
        CREATE TRIGGER fail_atomic_used_part
        BEFORE INSERT ON used_parts
        BEGIN
            SELECT RAISE(ABORT, 'forced used part failure');
        END
        """
    )
    db.conn.commit()
    initial_accounting = db.cursor.execute(
        "SELECT COUNT(*) FROM accounting"
    ).fetchone()[0]
    initial_movements = db.cursor.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE part_id=?",
        (part_id,),
    ).fetchone()[0]

    assert db.add_currency_transaction(
        customer_id=customer_id,
        amount=75,
        currency="TRY",
        transaction_type="DEBIT",
        exchange_rate=1,
        description="Atomic service debt",
        tracking_no="ATOMIC-SERVICE",
        commit=False,
    )
    assert db.add_transaction(
        t_type="Gelir",
        category="Satis",
        amount=75,
        description="Atomic service sale",
        customer_id=customer_id,
        tracking_no="ATOMIC-SERVICE",
        currency="TRY",
        commit=False,
    )
    assert db.use_part(
        part_id,
        1,
        "ATOMIC-SERVICE",
        commit=False,
    ) is False

    db.conn.rollback()

    assert db.cursor.execute(
        "SELECT COUNT(*) FROM currency_transactions "
        "WHERE tracking_no='ATOMIC-SERVICE'"
    ).fetchone()[0] == 0
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM accounting"
    ).fetchone()[0] == initial_accounting
    assert db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?",
        (part_id,),
    ).fetchone()[0] == pytest.approx(3)
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM stock_movements WHERE part_id=?",
        (part_id,),
    ).fetchone()[0] == initial_movements
    db.close()


def test_new_stock_card_can_roll_back_with_finance_failure(tmp_path):
    db = _new_database(tmp_path, "new-stock-finance-rollback.db")

    part_id = db.add_part(
        "Rejected Stock Card",
        "Computer",
        2,
        100,
        purchase_price=60,
        currency="TRY",
        code="REJECTED-STOCK",
        commit=False,
    )
    assert part_id
    with pytest.raises(RuntimeError):
        db.add_transaction(
            t_type="Gider",
            category="Stok Alimi",
            amount=120,
            description="Rejected stock finance",
            bank_account_id=999999,
            payment_method="Banka",
            commit=False,
        )
    db.conn.rollback()

    assert db.cursor.execute(
        "SELECT COUNT(*) FROM parts WHERE code='REJECTED-STOCK'"
    ).fetchone()[0] == 0
    db.close()


def test_stock_update_finance_failure_rolls_back_quantity(tmp_path):
    db = _new_database(tmp_path, "stock-update-finance-rollback.db")
    part_id = db.add_part(
        "Rollback Update Part",
        "Computer",
        2,
        100,
        purchase_price=60,
        currency="TRY",
        code="ROLLBACK-UPDATE",
    )

    assert db.update_part(
        part_id,
        "Rollback Update Part",
        "Computer",
        5,
        100,
        "",
        1,
        "ROLLBACK-UPDATE",
        "",
        purchase_price=60,
        currency="TRY",
        bank_account_id=999999,
        payment_method="Banka",
    ) is False

    assert db.cursor.execute(
        "SELECT stock FROM parts WHERE id=?",
        (part_id,),
    ).fetchone()[0] == pytest.approx(2)
    db.close()
