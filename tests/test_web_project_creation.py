from datetime import date, timedelta
import base64
from pathlib import Path

import pytest

from src.database import Database
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def _payload(**overrides):
    today = date.today()
    return {
        "name": "Web Project Creation",
        "start_date": today.isoformat(),
        "end_date": (today + timedelta(days=365)).isoformat(),
        "budget": 1200,
        "cost": 500,
        "currency": "TRY",
        "exchange_rate": 1,
        "payment_method": "Pe\u015fin",
        "description": "Created from web form",
        "customer_id": None,
        **overrides,
    }


def test_project_creation_uses_desktop_core_financial_side_effects(monkeypatch, tmp_path):
    database_path = tmp_path / "project-create.db"
    database = Database(str(database_path))
    customer_id = database.add_customer({"name": "Project Fixture Customer", "phone": "5550100100"})
    assert customer_id
    database.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    result = web_main.desktop_create_project(_payload(customer_id=customer_id))
    database = Database(str(database_path), init_mode="connection_only")
    try:
        project = database.conn.execute(
            "SELECT name,start_date,end_date,budget,cost,currency,exchange_rate,payment_method,status,description "
            "FROM projects WHERE id=?",
            (result["project_id"],),
        ).fetchone()
        assert tuple(project) == (
            "Web Project Creation", _payload()["start_date"], _payload()["end_date"],
            1200, 500, "TRY", 1, "Pe\u015fin", "Devam Ediyor", "Created from web form",
        )
        transactions = database.conn.execute(
            "SELECT type,category,amount,status FROM project_transactions WHERE project_id=? ORDER BY id",
            (result["project_id"],),
        ).fetchall()
        assert [tuple(row) for row in transactions] == [
            ("Gelir", "Proje B\u00fct\u00e7esi", 1200, "\u00d6denmedi"),
            ("Gider", "Proje Maliyeti", 500, "\u00d6denmedi"),
        ]
        assert database.conn.execute(
            "SELECT COUNT(*) FROM currency_transactions WHERE customer_id=?",
            (customer_id,),
        ).fetchone()[0] == 1
    finally:
        database.close()


def test_project_creation_validates_customer_dates_currency_and_amounts(monkeypatch, tmp_path):
    database_path = tmp_path / "project-create-validation.db"
    Database(str(database_path)).close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    with pytest.raises(LookupError, match="selected customer was not found"):
        web_main.desktop_create_project(_payload(customer_id=404))
    with pytest.raises(ValueError, match="end date cannot be before"):
        web_main.desktop_create_project(_payload(end_date="2000-01-01"))
    with pytest.raises(ValueError, match="currency is not supported"):
        web_main.desktop_create_project(_payload(currency="XYZ"))
    with pytest.raises(ValueError, match="budget and cost must be between"):
        web_main.desktop_create_project(_payload(cost=-1))


def test_new_project_form_exposes_desktop_fields_and_core_endpoint():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("async function openNewProjectDialog(")
    end = app.index("function openProjectLifecycleDialog(", start)
    flow = app[start:end]

    for field in ("name", "customer_id", "start_date", "end_date", "currency", "exchange_rate", "budget", "cost", "payment_method", "description", "contract_file"):
        assert f'name="{field}"' in flow
    assert '/api/desktop/table/customers?limit=1000' in flow
    assert '/api/desktop/projects/create' in flow
    assert 'data: ' not in flow


def test_project_creation_stores_tenant_scoped_pdf_contract(monkeypatch, tmp_path):
    database_path = tmp_path / "project-contract.db"
    Database(str(database_path)).close()
    contract_root = tmp_path / "contract_docs" / "tenant-a"
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)
    monkeypatch.setattr(web_main, "_contract_attachment_root", lambda create=False: (contract_root.mkdir(parents=True, exist_ok=True) or contract_root))
    pdf = b"%PDF-fixture"
    payload = _payload(contract_pdf={"filename": "signed-contract.pdf", "data_base64": base64.b64encode(pdf).decode("ascii")})

    result = web_main.desktop_create_project(payload)
    database = Database(str(database_path), init_mode="connection_only")
    try:
        row = database.conn.execute("SELECT contract_path FROM projects WHERE id=?", (result["project_id"],)).fetchone()
        stored = Path(row["contract_path"])
        assert stored.parent == contract_root
        assert stored.read_bytes() == pdf
        download, filename = web_main.desktop_project_contract_download(result["project_id"])
        assert download == pdf
        assert filename == f"project-contract-{result['project_id']}.pdf"
        listed = web_main.desktop_documents_center_rows(database.conn)
        contract_row = next(item for item in listed if item["key"] == f"project:{result['project_id']}")
        assert contract_row["available"] is True
        assert contract_row["url"].endswith(f"/{result['project_id']}/contract/download")
    finally:
        database.close()

    monkeypatch.setattr(web_main, "_contract_attachment_root", lambda create=False: tmp_path / "contract_docs" / "tenant-b")
    with pytest.raises(LookupError, match="unavailable"):
        web_main.desktop_project_contract_download(result["project_id"])
