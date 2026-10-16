from datetime import date
from pathlib import Path

import pytest

from src.database import Database
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_project_transaction_form_matches_desktop_fields_and_categories():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function openProjectTransactionDialog(")
    end = app.index("\nfunction openProjectTransactionDetailDialog", start)
    flow = app[start:end]

    assert 'name="category"' in flow
    assert 'name="amount" type="number"' in flow
    assert 'name="bank_account_id"' in flow
    assert 'name="date" type="date"' in flow
    assert 'name="description"' in flow
    assert r"\u0130\u015f\u00e7ilik" in flow
    assert "\u00d6dendi" not in flow
    assert '"/api/desktop/projects/transactions"' in flow


def test_project_transaction_save_posts_paid_project_and_accounting_records(monkeypatch, tmp_path):
    database_path = tmp_path / "project-transaction.db"
    database = Database(str(database_path))
    project_id = database.add_project(
        {"name": "Web Project Transaction", "currency": "TRY", "exchange_rate": 1}
    )
    assert database.add_bank_account(
        "Fixture Bank", "Main", "Project Account", "987654", "", 0, "TRY"
    )
    bank_columns = {row[1] for row in database.conn.execute("PRAGMA table_info(bank_accounts)")}
    account_column = "account_number" if "account_number" in bank_columns else "account_no"
    bank_account_id = database.conn.execute(
        f"SELECT id FROM bank_accounts WHERE {account_column}='987654'"
    ).fetchone()[0]
    database.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    result = web_main.desktop_save_project_transaction(
        {
            "project_id": project_id,
            "type": "Gider",
            "category": "Ta\u015feron \u00d6demesi",
            "amount": 275.5,
            "bank_account_id": bank_account_id,
            "date": date.today().isoformat(),
            "description": "Web project transaction",
        }
    )

    assert result["ok"] is True
    assert result["currency"] == "TRY"
    assert result["amount_try"] == pytest.approx(275.5)
    database = Database(str(database_path), init_mode="connection_only")
    try:
        transaction = database.conn.execute(
            "SELECT type,category,amount,payment_method,status,description "
            "FROM project_transactions WHERE id=?",
            (result["id"],),
        ).fetchone()
        assert tuple(transaction) == (
            "Gider", "Ta\u015feron \u00d6demesi", 275.5, "Banka", "\u00d6dendi", "Web project transaction"
        )
        accounting_rows = database.conn.execute(
            "SELECT COUNT(*) FROM accounting WHERE project_id=? AND amount=275.5",
            (project_id,),
        ).fetchone()[0]
        assert accounting_rows == 1
    finally:
        database.close()


def test_project_transaction_save_rejects_missing_project_and_unavailable_bank(monkeypatch, tmp_path):
    database_path = tmp_path / "project-transaction-validation.db"
    database = Database(str(database_path))
    project_id = database.add_project({"name": "Project Transaction Validation"})
    database.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)
    common = {
        "type": "Gelir",
        "category": "Di\u011fer",
        "amount": 10,
        "date": date.today().isoformat(),
    }

    with pytest.raises(LookupError, match="Project was not found"):
        web_main.desktop_save_project_transaction({**common, "project_id": project_id + 500})
    with pytest.raises(LookupError, match="selected bank account"):
        web_main.desktop_save_project_transaction(
            {**common, "project_id": project_id, "bank_account_id": 9001}
        )


def test_project_transaction_detail_uses_desktop_double_click_fields():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openProjectTransactionDetailDialog(")
    end = app.index("const p9GenericShellBefore", start)
    flow = app[start:end]

    assert r'"\u0130\u015flem Detay\u0131"' in flow
    assert '"Tarih:"' in flow
    assert '"Kategori:"' in flow
    assert r'"A\u00e7\u0131klama:"' in flow
    assert '"Durum:"' in flow
    assert '"Takip No:"' in flow
    assert '"Kapat"' in flow
    assert 'document.addEventListener("dblclick"' in flow


def test_project_finance_category_and_payment_filters_use_saved_transactions():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function renderPart9Projects()")
    end = app.index("function openProjectTransactionDialog(", start)
    flow = app[start:end]

    assert 'new Set(transactions.map(item => String(item.category || "").trim())' in flow
    assert 'new Set(transactions.map(item => String(item.payment_method || "").trim())' in flow
    assert 'id="p9FinanceCategory"' in flow
    assert 'id="p9FinanceChannel"' in flow
    assert '"Banka Transferi"' not in flow
    assert '"Kredi Kart' not in flow

def test_project_finance_has_pending_reconciliation_segment():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function renderPart9Projects()")
    end = app.index("function openProjectTransactionDialog(", start)
    flow = app[start:end]

    assert '["pending", "Bekleyen Mutabakatlar"]' in flow
    assert 'p9FinanceView.segment === "pending"' in flow
    assert '! ["odendi", "tahsil edildi"]' not in flow
    assert '["odendi", "tahsil edildi"].includes(key(item.status))' in flow

def test_subcontractor_payment_transaction_is_linked_to_its_project(monkeypatch, tmp_path):
    database_path = tmp_path / "subcontractor-payment.db"
    database = Database(str(database_path))
    project_id = database.add_project({"name": "Subcontractor Payment Project", "currency": "TRY"})
    other_project_id = database.add_project({"name": "Other Subcontractor Project", "currency": "TRY"})
    subcontractor_id = database.add_subcontractor(
        {"project_id": project_id, "name": "Fixture Contractor", "job_type": "Electrical", "total_contract_amount": 1000}
    )
    assert subcontractor_id
    database.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    with pytest.raises(LookupError, match="subcontractor was not found in this project"):
        web_main.desktop_save_project_transaction(
            {
                "project_id": other_project_id,
                "type": "Gider",
                "category": "Ta\u015feron \u00d6demesi",
                "amount": 25,
                "date": date.today().isoformat(),
                "ref_table": "subcontractors",
                "ref_id": subcontractor_id,
            }
        )

    result = web_main.desktop_save_project_transaction(
        {
            "project_id": project_id,
            "type": "Gider",
            "category": "Ta\u015feron \u00d6demesi",
            "amount": 275.5,
            "date": date.today().isoformat(),
            "description": "Fixture contractor payment",
            "ref_table": "subcontractors",
            "ref_id": subcontractor_id,
        }
    )

    database = Database(str(database_path), init_mode="connection_only")
    try:
        transaction = database.conn.execute(
            "SELECT ref_table, ref_id, category, status FROM project_transactions WHERE id=?",
            (result["id"],),
        ).fetchone()
        assert tuple(transaction) == ("subcontractors", subcontractor_id, "Ta\u015feron \u00d6demesi", "\u00d6dendi")
        assert database.get_subcontractor_balance(subcontractor_id) == pytest.approx(724.5)
    finally:
        database.close()


def test_subcontractor_payment_form_is_locked_to_payment_category():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function openProjectTransactionDialog(")
    end = app.index("\nfunction openProjectTransactionDetailDialog", start)
    flow = app[start:end]

    assert "paymentFor = null" in flow
    assert 'data-p9-team-pay="${esc(item.id)}"' in app
    assert 'category: paymentFor ? "Ta\\u015feron \\u00d6demesi"' in flow
    assert 'ref_table: paymentFor ? "subcontractors" : null' in flow
    assert 'ref_id: paymentFor ? Number(paymentFor.id) : null' in flow
    assert 'await openProjectTransactionDialog(project, "Gider", member)' in app


def test_project_unit_bulk_status_uses_desktop_status_choices_and_root_units():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("if (unitBulk || unitEdit)")
    end = app.index("if (unitQr)", start)
    flow = app[start:end]

    assert '"Bekliyor", "Devam Ediyor", "Tamamland\\u0131"' in flow
    assert '(!item.parent_unit_id || Number(item.parent_unit_id) === 0)' in flow
    assert 'openDialog(unitEdit ? "Durumu De\\u011fi\\u015ftir" : "Toplu Durum G\\u00fcncelle"' in flow
    assert 'id: Number(item.id), status: nextStatus, _action: "update"' in flow
    assert 'document.querySelector("#dialogCancel")' not in flow