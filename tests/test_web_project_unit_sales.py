import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.database import Database
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_project_unit_sale_form_matches_desktop_tabs_and_save_actions():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    server = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    start = app.index("async function p9OpenProjectUnitSale(")
    end = app.index("async function openProjectTransactionDialog(", start)
    flow = app[start:end]

    for field in ("buyer_name", "buyer_tc", "buyer_phone", "buyer_email", "buyer_address", "list_price", "sale_price", "down_payment_rate", "down_payment_amount", "remaining_balance", "delivery_date", "sales_rep", "notes"):
        assert f'name="{field}"' in flow
    assert 'data-p9-sale-panel="plan"' in flow
    assert 'data-p9-sale-panel="docs"' in flow
    assert 'data-p9-sale-panel="map"' in flow
    assert 'data-p9-sale-plan-add' in flow
    assert 'data-p9-sale-doc-input' in flow
    assert 'data-p9-sale-map-search' in flow
    assert '"/api/desktop/projects/unit-sales"' in flow
    assert 'data-p9-sale-submit="print"' in flow
    assert 'data-p9-sale-submit="proforma"' in flow
    assert 'p9OpenProjectUnitSale(Number(button.dataset.p9UnitSale))' in app
    route = server[server.index('if path == "/api/desktop/projects/unit-sales":'):]
    assert 'if not self.current_user()' in route[:180]
    assert 'desktop_create_project_unit_sale(self.read_json())' in route[:300]


def _fixture(tmp_path, monkeypatch):
    database_path = tmp_path / "project-unit-sale.db"
    database = Database(str(database_path))
    project_id = database.add_project({"name": "Unit Sale Fixture", "currency": "TRY", "exchange_rate": 1})
    unit_id = database.add_project_unit({"project_id": project_id, "block_name": "A", "unit_no": "A-12", "status": "Sat\u0131l\u0131k", "price": 180000})
    database.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)
    return database_path, project_id, unit_id


def _payload(project_id, unit_id):
    delivery = datetime.now() + timedelta(days=30)
    installment = datetime.now() + timedelta(days=45)
    return {
        "project_id": project_id,
        "unit_id": unit_id,
        "buyer_name": "Unit Sale Buyer",
        "buyer_tc": "10000000146",
        "buyer_phone": "5551234567",
        "buyer_email": "buyer@example.test",
        "buyer_address": "Example Street 1",
        "delivery_date": delivery.strftime("%Y-%m-%dT%H:%M"),
        "sales_rep": "Fixture Rep",
        "notes": "Sale notes",
        "list_price": 220000,
        "sale_price": 200000,
        "down_payment_rate": 10,
        "down_payment_amount": 20000,
        "payment_plan": [{"date": installment.strftime("%Y-%m-%dT%H:%M"), "amount": 180000, "status": "Bekliyor"}],
        "documents": ["purchase-agreement.pdf"],
    }


def test_project_unit_sale_is_saved_atomically_with_unit_and_income_updates(tmp_path, monkeypatch):
    database_path, project_id, unit_id = _fixture(tmp_path, monkeypatch)
    result = web_main.desktop_create_project_unit_sale(_payload(project_id, unit_id))

    assert result["ok"] is True
    assert result["unit_status"] == "Sat\u0131ld\u0131"
    assert result["remaining_balance"] == 180000
    database = Database(str(database_path), init_mode="connection_only")
    sale = database.conn.execute("SELECT * FROM project_unit_sales WHERE id=?", (result["sale_id"],)).fetchone()
    unit = database.conn.execute("SELECT status, price FROM project_units WHERE id=?", (unit_id,)).fetchone()
    project_transactions = database.conn.execute("SELECT type, category, amount, ref_table, ref_id FROM project_transactions WHERE id=?", (result["project_transaction_id"],)).fetchone()
    accounting = database.conn.execute("SELECT type, category, amount, customer_name, project_id FROM accounting WHERE id=?", (result["accounting_id"],)).fetchone()
    database.close()

    assert sale["buyer_tc"] == "10000000146"
    assert json.loads(sale["payment_plan"])[0]["amount"] == 180000
    assert json.loads(sale["documents"]) == ["purchase-agreement.pdf"]
    assert tuple(unit) == ("Sat\u0131ld\u0131", 200000)
    assert tuple(project_transactions) == ("Gelir", "Konut Sat\u0131\u015f\u0131", 200000, "project_units", unit_id)
    assert tuple(accounting) == ("Gelir", "Konut Sat\u0131\u015f\u0131", 200000, "Unit Sale Buyer", project_id)


@pytest.mark.parametrize("change", [
    {"buyer_tc": "10000000145"},
    {"buyer_email": ""},
    {"sale_price": -1},
    {"down_payment_rate": 10, "down_payment_amount": 1000},
    {"payment_plan": [{"date": "not-a-date", "amount": 10, "status": "Bekliyor"}]},
    {"documents": ["bad\nname.pdf"]},
])
def test_project_unit_sale_rejects_invalid_payload_without_writes(tmp_path, monkeypatch, change):
    database_path, project_id, unit_id = _fixture(tmp_path, monkeypatch)
    payload = {**_payload(project_id, unit_id), **change}

    with pytest.raises(ValueError):
        web_main.desktop_create_project_unit_sale(payload)

    database = Database(str(database_path), init_mode="connection_only")
    assert database.conn.execute("SELECT COUNT(*) FROM project_unit_sales").fetchone()[0] == 0
    assert database.conn.execute("SELECT status FROM project_units WHERE id=?", (unit_id,)).fetchone()[0] == "Sat\u0131l\u0131k"
    database.close()


def test_project_unit_sale_rejects_cross_project_unit_and_duplicate_sale(tmp_path, monkeypatch):
    database_path, project_id, unit_id = _fixture(tmp_path, monkeypatch)
    database = Database(str(database_path), init_mode="connection_only")
    other_project_id = database.add_project({"name": "Other Project", "currency": "TRY", "exchange_rate": 1})
    database.close()

    with pytest.raises(LookupError):
        web_main.desktop_create_project_unit_sale({**_payload(other_project_id, unit_id)})
    web_main.desktop_create_project_unit_sale(_payload(project_id, unit_id))
    with pytest.raises(ValueError):
        web_main.desktop_create_project_unit_sale(_payload(project_id, unit_id))

    database = Database(str(database_path), init_mode="connection_only")
    assert database.conn.execute("SELECT COUNT(*) FROM project_unit_sales WHERE unit_id=?", (unit_id,)).fetchone()[0] == 1
    database.close()


def test_project_unit_sale_rolls_back_all_rows_when_accounting_insert_fails(tmp_path, monkeypatch):
    database_path, project_id, unit_id = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(Database, "add_transaction", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="accounting income"):
        web_main.desktop_create_project_unit_sale(_payload(project_id, unit_id))

    database = Database(str(database_path), init_mode="connection_only")
    assert database.conn.execute("SELECT COUNT(*) FROM project_unit_sales").fetchone()[0] == 0
    assert database.conn.execute("SELECT status FROM project_units WHERE id=?", (unit_id,)).fetchone()[0] == "Sat\u0131l\u0131k"
    assert database.conn.execute("SELECT COUNT(*) FROM project_transactions").fetchone()[0] == 0
    assert database.conn.execute("SELECT COUNT(*) FROM accounting").fetchone()[0] == 0
    database.close()


def test_project_unit_sale_only_changes_the_active_tenant_database(tmp_path, monkeypatch):
    active_path, project_id, unit_id = _fixture(tmp_path, monkeypatch)
    other_path = tmp_path / "other-tenant.db"
    other = Database(str(other_path))
    other_project = other.add_project({"name": "Unit Sale Fixture", "currency": "TRY", "exchange_rate": 1})
    other_unit = other.add_project_unit({"project_id": other_project, "block_name": "A", "unit_no": "A-12", "status": "Sat\u0131l\u0131k", "price": 180000})
    other.close()

    web_main.desktop_create_project_unit_sale(_payload(project_id, unit_id))

    other = Database(str(other_path), init_mode="connection_only")
    assert other.conn.execute("SELECT status FROM project_units WHERE id=?", (other_unit,)).fetchone()[0] == "Sat\u0131l\u0131k"
    assert other.conn.execute("SELECT COUNT(*) FROM project_unit_sales").fetchone()[0] == 0
    other.close()
    assert active_path.exists()
