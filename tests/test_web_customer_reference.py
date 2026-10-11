from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_customer_header_actions_match_reference_hierarchy_and_mobile_widths():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    start = app.index("function renderCustomers()")
    end = app.index("function customerTable", start)
    template = app[start:end]

    assert template.index("customer-page-head") < template.index("customer-head-actions")
    assert template.index("customer-head-actions") < template.index("customer-management")
    assert template.index("customer-export-actions") < template.index("customer-add")
    assert ".customer-head-actions{display:grid" in styles
    assert "@media(max-width:760px){.customer-page-head" in styles
    assert "@media(max-width:420px){.customer-export-actions" in styles
    assert ".customer-export-actions .mini{min-height:38px;padding:8px;font-size:12px}" in styles
    assert ".customer-filterbar{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;padding:12px}" in styles
    assert "@media(max-width:420px){.customer-filterbar{grid-template-columns:minmax(0,1fr)}" in styles


def test_customer_desktop_filter_rows_and_main_content_spacing_match_reference():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="customers"] .customer-filterbar' in styles
    assert "grid-template-columns: 285px 240px 225px max-content;" in styles
    assert "min-height: 132px;" in styles
    assert "grid-column: 1 / -1;" in styles
    assert "width: 560px;" in styles





def test_customer_reference_table_and_metrics_fit_viewport():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="customers"] #customerTable { height: 285px; min-height: 285px; flex: none; }' in styles
    assert 'body[data-page="customers"] #customerTable { height: auto; min-height: 0; flex: none; }' in styles


def test_customer_metrics_and_hover_use_midnight_enterprise_surfaces():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'body[data-page="customers"] .customer-metrics {\n  background: transparent;' in styles
    assert 'body[data-page="customers"] .customer-metrics .metric {\n  background: var(--surface);' in styles
    assert 'body[data-page="customers"] .customer-filterbar {\n  background: var(--surface);' in styles
    assert 'body[data-page="customers"] .customer-data-table tbody tr:hover td {\n  background: var(--surface-2);' in styles
