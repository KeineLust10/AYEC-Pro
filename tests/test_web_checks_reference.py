from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "styles.css"


def test_checks_reference_uses_persisted_portfolio_fields_and_safe_filters():
    source = APP.read_text(encoding="utf-8")
    start = source.index("async function loadChecksReference(")
    end = source.index("const ayecRenderBeforeChecksReference", start)
    code = source[start:end]
    assert 'const host=$("#genericHost");if(!host)return;' in source
    assert 'meta?.table === "checks_notes"' in source
    assert 'loadAllDesktopTableData(meta.table,{q})' in code
    for field in ("direction", "type", "status", "due_date", "issuer", "bank_name", "check_no", "amount"):
        assert f"row.{field}" in code
    assert "function checkMoney(value,currency)" in source
    assert "function resetChecksReferenceFilters(meta)" in source
    assert '$("#checkStatusFilter").value = "";' in source
    assert '$("#checkDateStart").value = dateValue(first);' in source
    assert '$("#checkDateEnd").value = dateValue(nextYear);' in source


def test_checks_reference_has_working_filters_and_mobile_table_behavior():
    source = APP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'data-check-tab="${key}"' in source
    assert 'id="checkStatusFilter"' in source
    assert 'id="checkDateStart"' in source
    assert 'id="checkDateEnd"' in source
    assert 'data-check-clear' in source
    assert 'data-check-export' in source
    assert 'body[data-page="checks"] .checks-reference-metrics' in css
    assert 'body[data-page="checks"] .checks-page-head{align-items:center;margin-bottom:29px}' in css
    assert 'body[data-page="checks"] .checks-page-head .actions{flex:0 0 auto;flex-wrap:nowrap}' in css
    assert 'body[data-page="checks"] .checks-page-head [data-check-add]{background:#4bd49d' in css
    assert '@media(max-width:1100px){body[data-page="checks"] .checks-page-head' in css
    assert '@media(max-width:760px){body[data-page="checks"]' in css
    assert 'body[data-page="checks"] .checks-reference-table table{min-width:1120px}' in css


def test_checks_route_loads_data_into_the_rendered_reference_workspace():
    source = APP.read_text(encoding="utf-8")
    marker = "const genericShellBeforeChecks = genericShell;"
    active = source[source.rfind(marker):source.index("let ayecSettingsUsers = [];", source.rfind(marker))]
    styles = (ROOT / "Web_Arayuzu" / "web" / "styles.css").read_text(encoding="utf-8")

    assert "return renderChecksReference();" in active
    assert 'return loadChecksReference(meta, query)' in active
    assert '"#checksRows"' not in active
    start = source.index("function renderChecksReference(){")
    end = source.index("\nfunction ", start + 10)
    header = source[start:end]
    assert 'class="page-head checks-page-head"' in header
    assert "checks-reference-badge" not in header
    assert 'data-check-add>+ Yeni \\u00c7ek / Senet Giri\\u015fi' in header
    assert "checks-reference-controls .control" in styles


def test_checks_route_uses_the_reference_renderer_expected_by_its_loader():
    source = APP.read_text(encoding="utf-8")
    marker = "const genericShellBeforeChecks = genericShell;"
    active = source[source.rfind(marker):source.index("let ayecSettingsUsers = [];", source.rfind(marker))]

    assert "return renderChecksReference();" in active
    assert 'return loadChecksReference(meta, query)' in active
    assert '"#checksRows"' not in active
    assert 'document.addEventListener("click", event => {' not in active


def test_offscreen_route_audit_covers_selected_check_bulk_endorsement():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.checkBulkEndorsementWorkflow" in route_smoke
    assert "workflow.updatedCount !== 2" in route_smoke
    assert 'workflow.updatedIds.join(",") !== "8841,8842"' in route_smoke
    assert 'row.id === "8843"' in route_smoke
    assert "workflow.portfolioPreserved" in route_smoke
    assert 'workflow.individualStatus !== "Tahsil Edildi"' in route_smoke
    assert 'workflow.individualBankId !== "9905"' in route_smoke
    assert "workflow.bankDialogFound" in route_smoke
    assert "workflow.returnButtonFound" in route_smoke
    assert "workflow.returnStatus" in route_smoke
    assert "workflow.invalidAmountRejected" in route_smoke
    assert "workflow.missingPartyRejected" in route_smoke
    assert "workflow.createPayloadCount !== 1" in route_smoke
    assert "workflow.createdRowFound" in route_smoke
    assert "workflow.exportContainsCreatedNote" in route_smoke
    assert "workflow.exportContainsReturnedStatus" in route_smoke
    assert "workflow.detailDialogFound" in route_smoke
    assert "workflow.detailDialogClosed" in route_smoke
    assert "result.checkPortfolioVisualFixture" in route_smoke
    assert 'renderedIds.filter(Boolean).join(",") !== "8841,8842,8843"' in route_smoke
    assert "headerHeight > 48" in route_smoke
    assert "headerGap < 28" in route_smoke
    assert 'addButtonColor !== "rgb(75, 212, 157)"' in route_smoke
    assert "allActionsSameTop" in route_smoke
    assert route_smoke.index("result.checkPortfolioVisualFixture") < route_smoke.index("const routeCaptureState = await evaluate(")
    assert "Mobile check portfolio table is not horizontally contained" in route_smoke
    assert 'workflow.endorsedFilteredIds.join(",") !== "8841"' in route_smoke
    assert "mobileResult.checkHeader" in route_smoke
    assert "Mobile check portfolio actions are not fully visible" in route_smoke
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert '[data-check-bulk]")?.addEventListener("click"' not in app
