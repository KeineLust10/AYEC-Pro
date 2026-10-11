from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "midnight-reference.css"


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


def test_checks_reference_has_working_filters_and_mobile_table_behavior():
    source = APP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'data-check-filter="incoming-check"' in source
    assert 'id="checksStatusFilter"' in source
    assert 'id="checksDueStart"' in source
    assert 'id="checksDueEnd"' in source
    assert 'data-check-clear' in source
    assert 'data-check-export' in source
    assert 'body[data-page="checks"] .checks-ref-metrics' in css
    assert '@media(max-width:700px){body[data-page="checks"]' in css
    assert 'body[data-page="checks"] .checks-ref-table tbody>tr{display:grid' in css
    assert '@media print{body[data-page="checks"]' in css


def test_checks_route_loads_data_into_the_rendered_reference_workspace():
    source = APP.read_text(encoding="utf-8")
    start = source.index("const ayecLoadChecksReferenceBeforeLegacy = loadGenericModule;")
    end = source.index('document.addEventListener("click", event => {', start)
    active_loader = source[start:end]
    parity = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'return loadChecksReference(meta, query)' in active_loader
    assert '$("#checksRows")' not in active_loader
    assert "height: 172px;" in parity
    assert "checks-reference-controls .control" in parity
