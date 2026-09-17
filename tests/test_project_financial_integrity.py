from pathlib import Path

import pytest

from src.database import Database
from src.utils.currency_helper import CurrencyHelper


def _new_database(tmp_path):
    return Database(str(tmp_path / "project-integrity.db"))


def test_project_budget_opens_debt_without_implicit_payment(tmp_path):
    db = _new_database(tmp_path)
    customer_id = db.add_customer(
        {
            "name": "Project Customer",
            "phone": "05550000000",
            "email": "project@example.com",
        }
    )

    project_id = db.add_project(
        {
            "name": "USD Project",
            "customer_id": customer_id,
            "customer_name": "Project Customer",
            "budget": 100,
            "currency": "USD",
            "exchange_rate": 40,
            "payment_method": "Cash",
        }
    )

    assert project_id
    transactions = db.cursor.execute(
        "SELECT transaction_type,amount,currency,exchange_rate,"
        "try_equivalent,tracking_no FROM currency_transactions "
        "WHERE customer_id=? ORDER BY id",
        (customer_id,),
    ).fetchall()
    assert len(transactions) == 1
    assert transactions[0][0] == "DEBIT"
    assert float(transactions[0][1]) == pytest.approx(100)
    assert transactions[0][2] == "USD"
    assert float(transactions[0][3]) == pytest.approx(40)
    assert float(transactions[0][4]) == pytest.approx(4000)
    assert transactions[0][5]

    balance = db.cursor.execute(
        "SELECT balance FROM customer_currency_balances "
        "WHERE customer_id=? AND currency='USD'",
        (customer_id,),
    ).fetchone()
    assert float(balance[0]) == pytest.approx(-100)

    project_income = db.cursor.execute(
        "SELECT amount,status FROM project_transactions "
        "WHERE project_id=? AND type='Gelir'",
        (project_id,),
    ).fetchone()
    assert float(project_income[0]) == pytest.approx(4000)
    assert project_income[1] == "\u00d6denmedi"
    db.close()


def test_foreign_part_cost_and_note_update_are_financially_stable(
    tmp_path, monkeypatch
):
    db = _new_database(tmp_path)
    monkeypatch.setattr(
        CurrencyHelper,
        "_get_rate",
        staticmethod(lambda _db, code: {"USD": 40.0, "EUR": 50.0}.get(code, 1.0)),
    )
    project_id = db.add_project(
        {
            "name": "Installation",
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
        "USD Device",
        "Security",
        5,
        15,
        purchase_price=10,
        currency="USD",
        code="USD-DEVICE",
    )

    entry_id = db.add_unit_product(
        {
            "unit_id": unit_id,
            "project_id": project_id,
            "part_id": part_id,
            "part_name": "USD Device",
            "part_code": "USD-DEVICE",
            "quantity": 2,
            "notes": "Initial note",
        }
    )
    assert entry_id
    assert float(
        db.cursor.execute("SELECT stock FROM parts WHERE id=?", (part_id,)).fetchone()[0]
    ) == pytest.approx(3)

    expense = db.cursor.execute(
        "SELECT amount,original_amount,original_currency,exchange_rate,description "
        "FROM project_transactions WHERE ref_table='project_unit_products' "
        "AND ref_id=?",
        (entry_id,),
    ).fetchone()
    assert float(expense[0]) == pytest.approx(800)
    assert float(expense[1]) == pytest.approx(20)
    assert expense[2] == "USD"
    assert float(expense[3]) == pytest.approx(40)
    original_description = expense[4]

    assert db.update_unit_product_note(entry_id, "Updated technical note")
    saved_note = db.cursor.execute(
        "SELECT notes FROM project_unit_products WHERE id=?", (entry_id,)
    ).fetchone()
    saved_description = db.cursor.execute(
        "SELECT description FROM project_transactions "
        "WHERE ref_table='project_unit_products' AND ref_id=?",
        (entry_id,),
    ).fetchone()
    assert saved_note[0] == "Updated technical note"
    assert saved_description[0] == original_description

    assert db.remove_unit_product(entry_id)
    assert float(
        db.cursor.execute("SELECT stock FROM parts WHERE id=?", (part_id,)).fetchone()[0]
    ) == pytest.approx(5)
    assert (
        db.cursor.execute(
            "SELECT COUNT(*) FROM project_transactions "
            "WHERE ref_table='project_unit_products' AND ref_id=?",
            (entry_id,),
        ).fetchone()[0]
        == 0
    )
    db.close()


def test_paid_project_transaction_has_one_central_finance_entry(tmp_path):
    db = _new_database(tmp_path)
    project_id = db.add_project(
        {
            "name": "Finance Integrity",
            "budget": 0,
            "currency": "TRY",
            "exchange_rate": 1,
        }
    )

    transaction_id = db.add_project_transaction(
        {
            "project_id": project_id,
            "type": "Gider",
            "category": "Ta\u015feron \u00d6demesi",
            "amount": 2500,
            "payment_method": "Nakit",
            "date": "2026-08-01",
            "description": "Subcontractor payment",
            "status": "\u00d6dendi",
            "ref_table": "subcontractors",
            "ref_id": 1,
        }
    )

    assert transaction_id
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM project_transactions WHERE project_id=?",
        (project_id,),
    ).fetchone()[0] == 1
    assert db.cursor.execute(
        "SELECT COUNT(*) FROM accounting WHERE project_id=? AND amount=2500",
        (project_id,),
    ).fetchone()[0] == 1
    legacy_table = db.cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='transactions'"
    ).fetchone()
    if legacy_table:
        assert db.cursor.execute(
            "SELECT COUNT(*) FROM transactions WHERE amount=2500"
        ).fetchone()[0] == 0
    db.close()


def test_project_note_double_click_uses_a_bounded_dialog():
    source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "ui"
        / "pages"
        / "project_management"
        / "project_detail_components.py"
    ).read_text(encoding="utf-8")
    handler = source.split("def _on_cell_double_clicked", 1)[1].split(
        "def save_notes", 1
    )[0]
    assert "QInputDialog.getMultiLineText" in handler
    assert "update_unit_product_note" in handler
    assert "editItem(" not in handler
