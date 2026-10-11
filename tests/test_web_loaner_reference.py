from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_loaner_workspace_matches_reference_and_supports_mobile_layout():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'meta?.table !== "loaner_devices"' in app
    assert 'let ayecLoanerDevices = [];' in app
    assert 'data-loaner-view="depot"' in app
    assert 'data-loaner-view="overdue"' in app
    assert 'loaner_transactions?limit=500' in app
    assert 'id="loanerMetricAvailable"' in app
    assert 'id="loanerSmsEnabled"' in app
    assert "const buttons = $$('.loaner-ref-tabs [data-loaner-view]')" in app
    assert "$$('.loaner-ref-tabs [data-loaner-view]').forEach" in app
    assert "loaner-ref-tabs" in styles
    assert "loaner-ref-table" in styles
    assert "loaner-ref-category-layout" in styles
    assert '@media print{body[data-page="loaners"]' in styles
    assert 'data-loaner-row-action="return"' in app
    assert 'class="loaner-ref-actions"' in app
    assert ".loaner-ref-actions{display:flex" in styles
    assert 'data-loaner-page="1"' in app
    assert "@media(max-width:600px){.loaner-ref-metrics" in styles
    assert "@media(max-width:420px){.loaner-ref-metrics" in styles


def test_loaner_desktop_metrics_and_full_width_workspace_match_desktop_density():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="loaners"] .loaner-ref-metrics article' in styles
    assert "height: 84px;" in styles
    assert "min-height: 438px;" in styles
    assert "grid-template-columns: minmax(0, 1fr) 370px 125px;" in styles
    assert 'body[data-page="loaners"] .loaner-ref-category-filter button.active' in styles
    assert "@media (max-width: 760px)" in styles


def test_logistics_workspace_uses_real_tracking_fields_and_mobile_cards():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert 'meta?.table !== "logistics"' in app
    assert 'id="logisticsMetricTotal"' in app
    assert 'id="logisticsStatus"' in app
    assert 'id="logisticsCarrier"' in app
    assert 'id="genericHost" hidden' in app
    assert 'row.cargo_firm' in app
    assert 'row.tracking_no' in app
    assert "@media(max-width:760px){.logistics-ref-table" in styles
    assert '@media print{body[data-page="logistics"]' in styles


def test_logistics_month_filter_accepts_iso_and_localized_dates():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "function ayecLogisticsMonthMatches(dateValue, month)" in app
    assert 'value.match(/^(\\d{4})-(\\d{2})/)' in app
    assert 'value.match(/^(\\d{1,2})[./-](\\d{1,2})[./-](\\d{4})/)' in app
    assert "ayecLogisticsMonthMatches(row.date, month)" in app


def test_loaner_actions_and_category_filters_are_wired():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'data-loaner-action="return-selected"' in app
    assert 'data-loaner-type="Switch"' in app
    assert 'data-loaner-select-all' in app
    assert 'loanerMetricOverdueDetail' in app
