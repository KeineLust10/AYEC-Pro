from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_midnight_reference_styles_are_loaded_after_page_styles():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    stylesheet = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert "midnight-reference.css?v=20261011-05" in html
    assert html.index("service-list-reference.css") < html.index("midnight-reference.css")
    assert "color-scheme: dark" in stylesheet
    assert "--bg: #080d16" in stylesheet
    assert "--surface: #0e1726" in stylesheet
    assert ".topbar" in stylesheet
    assert ".nav-button.active" in stylesheet
    assert ".form-grid" in stylesheet
    assert ".table-wrap" in stylesheet
    assert "max-width: 760px" in stylesheet
    assert "max-width: 420px" in stylesheet
    assert "overflow-x:auto" in stylesheet
    assert "touch-action:pan-x" in stylesheet
    assert "flex-wrap:nowrap" in stylesheet
    assert "calc(100vw - 70px - 28vw)" in stylesheet
    assert "100dvh" in stylesheet


def test_midnight_controls_use_active_theme_surface_tokens():
    stylesheet = (WEB / "midnight-reference.css").read_text(encoding="utf-8")
    assert "background: var(--surface-2);" in stylesheet
    assert "background: var(--input-bg, var(--surface));" in stylesheet
    assert "background: #0c1727;" not in stylesheet
    assert "background-color:var(--surface)" in stylesheet
    assert "background-color:#0b1320" not in stylesheet


def test_web_shell_keeps_cache_versions_for_updated_ui_assets():
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert re.search(r'href="styles\.css\?v=[^"]+"', html)
    assert re.search(r'src="app\.js\?v=[^"]+"', html)


def test_forest_theme_uses_desktop_midnight_enterprise_slate_palette():
    stylesheet = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    forest = stylesheet.split('html[data-theme="forest"] {', 1)[1].split("}", 1)[0]
    assert "--bg: #0a1410" in forest
    assert "--surface: #122019" in forest
    assert "--sidebar-bg: #0a1410" in forest
    assert "--brand: #10b981" in forest


def test_sales_product_cards_stay_compact_and_reflow_on_mobile():
    stylesheet = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'body[data-page="sales"] .product-picker{display:grid;grid-template-columns:repeat(3,minmax(0,1fr))' in stylesheet
    assert 'body[data-page="sales"] .product-tile{display:flex;align-items:center' in stylesheet
    assert 'max-height:min(66vh,720px)' in stylesheet
    assert '@media(max-width:760px){body[data-page="sales"] .grid-2{grid-template-columns:minmax(0,1fr)}' in stylesheet
    assert '@media(max-width:420px){body[data-page="sales"] .product-picker{grid-template-columns:minmax(0,1fr)' in stylesheet


def test_finance_dashboard_matches_part_one_composition_and_mobile_layout():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'class="finance-ref-metrics"' in app
    assert 'class="finance-weekly card"' in app
    assert 'data-action="collect-finance"' in app
    assert "grid-template-columns:repeat(5,minmax(0,1fr))" in styles
    assert "@media(max-width:760px)" in styles
    assert ".finance-layout{grid-template-columns:1fr}" in styles


def test_income_expense_metrics_follow_selected_period_and_reflow_on_mobile():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "styles.css").read_text(encoding="utf-8")

    assert 'startsWith(ayecIncomeExpenseMonth||currentMonth)' in app
    assert "@media(max-width:700px){.ie-page" in styles
    assert ".ie-metrics{grid-template-columns:repeat(2,minmax(0,1fr))}" in styles
    assert ".ie-columns aside{grid-template-columns:1fr}" in styles


def test_service_operations_board_has_five_stages_and_bound_filters():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'id="serviceBoardSearch"' in app
    assert 'data-service-board-filter="urgent"' in app
    assert 'data-service-board-filter="today"' in app
    assert '["bekliyor","BEK\\u0130YOR"' in app
    assert '["tamirde","TAM\\u0130RDE"' in app
    assert '["parca","PAR\\u00c7A BEKL\\u0130YOR"' in app
    assert '"test","TEST / ONAY"' in app
    assert '["teslim","TESL\\u0130M"' in app
    assert "grid-template-columns:repeat(5,minmax(0,1fr))" in styles
    assert "grid-template-columns:repeat(5,minmax(245px,1fr))" in styles


def test_appointments_follow_part_two_calendar_composition_and_mobile_layout():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    app = (WEB / "appointments-reference.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'appointments-reference.js?v=20261007-2' in html
    assert "data-appointment-view=\"'+id+'\"" in app
    assert 'data-appointment-shift="-1"' in app
    assert 'data-appointment-today' in app
    assert 'ayecAppointmentView==="month"?month' in app
    assert 'ayecAppointmentView==="day"?[new Date()]' in app
    assert 'data-kind="appointment"' in app
    assert 'appointment-ref-metrics' in app
    assert 'appointment-ref-layout' in app
    assert '.appointment-ref-calendar{display:grid;grid-template-columns:52px repeat(var(--appointment-days,7),minmax(95px,1fr))' in styles
    assert '@media(max-width:760px){.appointment-ref-toolbar' in styles
    assert '.appointment-ref-calendar{grid-template-columns:42px repeat(var(--appointment-days,7),minmax(135px,1fr))' in styles
    assert '.appointment-ref-month-head,.appointment-ref-month-grid{display:grid;grid-template-columns:repeat(7,minmax(100px,1fr))' in styles


def test_finance_dashboard_uses_data_backed_currency_balances_and_periods():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert "usdRate>0?money(value/usdRate,\"USD\"):money(value,\"TRY\")" in app
    assert "Math.max(0,-moneyNumber(balance))*rateForCode(currency)" in app
    assert 'Array.isArray(db.bankAccounts)' in app
    assert "finance-weekly-chart" in app
    assert "data-finance-period=\"week\"" in app
    assert "ayecFinancePeriod=button.dataset.financePeriod" in app
    assert ".finance-weekly-chart polyline" in styles






