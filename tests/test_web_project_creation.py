from datetime import date, timedelta
import base64
from pathlib import Path

import pytest

from src.database import Database
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_project_detail_tabs_support_accessible_keyboard_navigation():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function renderPart9Projects()")
    end = app.index("function loadPart9Projects(", start)
    markup = app[start:end]
    for text in (
        'role="tablist" aria-label="Proje ayrintilari"',
        'role="tab" id="p9ProjectTab-${id}"',
        'aria-controls="p9ProjectBody"',
        'role="tabpanel" tabindex="0"',
        'aria-labelledby="p9ProjectTab-${p9ProjectState.tab}"',
        'aria-pressed="${p9ProjectState.tab === id}"',
    ):
        assert text in markup
    assert 'event.target.closest(".p9-project-tabs button[data-p9-project-tab]")' in app
    for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
        assert f'event.key === "{key}"' in app
    assert 'document.querySelector(`.p9-project-tabs [data-p9-project-tab="${p9ProjectState.tab}"]`)?.focus()' in app


def test_project_management_list_precedes_detail_and_matches_desktop_actions():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function renderPart9ProjectList()")
    end = app.index("function renderPart9Projects()", start)
    listing = app[start:end]
    for text in (
        'class="p9-project-list"',
        'id="p9ProjectSearch"',
        'const pageSize = 30;',
        'data-p9-project-open="${id}"',
        'data-p9-project-action="complete"',
        'archived ? "restore" : "archive"',
        'data-p9-project-action="delete"',
        'data-p9-project-page="prev"',
        'data-p9-project-page="next"',
    ):
        assert text in listing
    assert 'p9ProjectState.view !== "detail" || !project' in app
    assert 'event.target.closest("[data-p9-project-open]")' in app
    assert 'event.target.id !== "p9ProjectSearch"' in app
    assert 'p9ProjectState.selectedId = null;' in app[app.index("async function openNewProjectDialog("):]


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
    assert 'loadAllDesktopTableRows("customers")' in flow
    assert 'id="p9ProjectCustomerPick"' in flow
    assert 'customerSelect(customer =>' in flow
    assert 'state.contract_file = activeForm.elements.namedItem("contract_file")?.files?.[0]' in flow
    assert 'openNewProjectDialog(state)' in flow
    assert '/api/desktop/projects/create' in flow
    assert 'data: ' not in flow


def test_project_page_resolves_desktop_label_catalog_entries():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function p9ProjectLabel(")
    end = app.index("function renderPart9Projects(", start)
    labels = app[start:end]
    project_render = app[end:app.index("function ", end + 1)]

    assert 'apiFetch("/api/desktop/labels?search=prj_")' in labels
    assert 'p9ProjectLabels[item.key] = String(item.current || item.default || "")' in labels
    assert 'item.key || "").startsWith("prj_")' in labels
    assert 'p9ProjectLabels[item.key] = String(item.value || "")' in labels
    assert 'p9ProjectLabel("prj_page_title", "Proje Y\\u00f6netimi")' in project_render
    assert 'p9ProjectLabel("prj_btn_new", "\\u2795 Yeni Proje Ekle")' in project_render


def test_offscreen_route_audit_covers_customer_linked_foreign_currency_creation():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "auditProjectCreation" in audit
    assert 'const customerPickerWorkflow={pickerOpened,pickerRowCount,pickerContextMenuReady,projectFormRestored,projectDraftPreserved}' in audit
    assert 'if (!project.customerPickerWorkflow?.pickerOpened || project.customerPickerWorkflow?.pickerRowCount !== 1 || !project.customerPickerWorkflow?.pickerContextMenuReady || !project.customerPickerWorkflow?.projectFormRestored || !project.customerPickerWorkflow?.projectDraftPreserved)' in audit
    assert 'project.payload.currency !== "USD"' in audit
    assert 'Number(project.payload.customer_id) !== 940030' in audit
    assert 'Number(project.selectedId) !== 940031' in audit
    assert 'project.unitPayload.naming !== "custom"' in audit
    assert 'project.preview.includes("North: 2 daire")' in audit
    assert 'JSON.stringify(project.lifecycleActions) !== JSON.stringify(["archive","restore"])' in audit
    assert 'project.transactions[0].type !== "Gelir"' in audit
    assert 'project.transactions[1].type !== "Gider"' in audit
    assert 'project.member.payment_model !== "daily"' in audit
    assert 'project.transactions[2].ref_table !== "subcontractors"' in audit


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
    database = Database(str(database_path), init_mode="connection_only")
    try:
        contract_row = next(item for item in web_main.desktop_documents_center_rows(database.conn) if item["key"] == f"project:{result['project_id']}")
        assert contract_row["available"] is False
        assert contract_row["url"] == ""
    finally:
        database.close()
    with pytest.raises(LookupError, match="unavailable"):
        web_main.desktop_project_contract_download(result["project_id"])


def test_offscreen_project_switch_filters_units_to_selected_project():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert 'name:"QA Second Project"' in audit
    assert 'unit_no:"QA-SECOND-UNIT"' in audit
    assert 'projectSwitch.selectedId !== "940099"' in audit
    assert 'projectSwitch.primaryUnitHidden' in audit
