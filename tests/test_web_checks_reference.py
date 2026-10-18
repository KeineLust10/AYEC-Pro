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
    assert '/api/desktop/table/${meta.table}?limit=500&q=' in code
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
    assert 'return `${pageHead(title' in source
    assert "checks-reference-controls .control" in styles


def test_checks_route_uses_the_reference_renderer_expected_by_its_loader():
    source = APP.read_text(encoding="utf-8")
    marker = "const genericShellBeforeChecks = genericShell;"
    active = source[source.rfind(marker):source.index("let ayecSettingsUsers = [];", source.rfind(marker))]

    assert "return renderChecksReference();" in active
    assert 'return loadChecksReference(meta, query)' in active
    assert '"#checksRows"' not in active
    assert 'document.addEventListener("click", event => {' not in active
