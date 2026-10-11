from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_service_list_and_accept_form_use_readable_text_sizes():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    stylesheet = (WEB / "service-list-reference.css").read_text(encoding="utf-8")

    assert "service-list-reference.css?v=20261008-1" in html
    assert ".service-list-table{font-size:12px}" in stylesheet
    assert ".service-list-table td small{font-size:11px}" in stylesheet
    assert ".service-list-status,.service-list-priority{font-size:11px}" in stylesheet
    assert "#dialogBody:has(select[name=\"customerId\"]) .field label{font-size:12px}" in stylesheet
    assert "#dialogBody:has(select[name=\"customerId\"]) input:not([type=checkbox]),#dialogBody:has(select[name=\"customerId\"]) select,#dialogBody:has(select[name=\"customerId\"]) textarea{min-height:38px;font-size:13px}" in stylesheet
    assert '#appDialog:has(#dialogBody select[name="customerId"]){width:min(1440px,calc(100vw - 32px))' in stylesheet
    assert "@media(max-width:760px){.service-list-table td::before{font-size:11px}.service-list-table td{font-size:12px}" in stylesheet


def test_service_list_uses_shared_theme_and_mobile_width_rules():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    parity = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert re.search(r'href="desktop-parity\.css\?v=[^"]+"', html)
    assert 'grid-template-columns: repeat(5, minmax(39px, 1fr))' in parity
    assert 'flex: 0 0 100%' in parity
    assert '.top-actions .primary[data-action="quick-add"]' in parity
    assert '--sl-panel: var(--surface)' in parity
    assert '.content .service-list-ref .service-list-tabs {\n  display: flex !important' in parity
    assert '@media (max-width: 760px)' in parity
    assert '.service-list-metrics {\n    grid-template-columns: repeat(2, minmax(0, 1fr))' in parity
    assert '.service-list-table-wrap {\n    max-width: 100%;\n    overflow-x: auto' in parity
    assert '#content .service-list-table-wrap .service-list-table thead tr {\n    height: 42px !important;' in parity
    assert '#content .service-list-table-wrap .service-list-table thead input[type="checkbox"] {\n    width: 16px;' in parity























