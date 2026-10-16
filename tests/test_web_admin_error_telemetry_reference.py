from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "Web_Arayuzu/web/control-center.css").read_text(encoding="utf-8")
CAPTURE = (ROOT / "tools/quality/admin_web_offscreen_capture.py").read_text(encoding="utf-8")


def test_error_telemetry_uses_real_admin_api_and_bound_fields():
    assert '/api/control/telemetry/errors' in APP
    assert 'id="adminTelemetryTotal"' in APP
    assert 'id="adminTelemetryStackCount"' in APP
    assert 'id="adminTelemetryTenantCount"' in APP
    assert 'log.error_message' in APP
    assert 'log.stack_trace' in APP
    assert 'log.os_info' in APP
    assert 'log.created_at' in APP
    assert 'id="adminTelemetryCompany"' in APP
    assert 'id="adminTelemetrySearch"' in APP
    assert 'data-telemetry-filter="warning"' in APP
    assert 'Kritik Hatalar (Crash)' in APP
    assert 'Yakalanan \\u0130stisnalar (Handled)' in APP
    assert 'disabled title="Hata cozme API' in APP
    assert 'disabled title="Destek bildirimi API' in APP


def test_error_telemetry_has_full_width_and_mobile_layout_rules():
    assert '#adminTabContent .admin-error-page' in CSS
    assert '#adminTabContent .admin-error-metrics { display: grid; grid-template-columns: repeat(4,minmax(0,1fr))' in CSS
    assert '@media(max-width:1023px) { #adminTabContent .admin-error-metrics { grid-template-columns: repeat(2,minmax(0,1fr)); } }' in CSS
    assert '#adminTabContent .admin-error-metrics { grid-template-columns: repeat(2,minmax(0,1fr))' in CSS
    assert '#adminTabContent .admin-error-toolbar { align-items: stretch; flex-direction: column' in CSS
    assert '#adminTabContent .admin-error-table-wrap tbody tr { height: 36px; cursor: pointer; }' in CSS
    assert '#adminTabContent .admin-error-table-wrap table { width: 100%; min-width: 0; table-layout: fixed;' in CSS
    assert '@media(max-width:1100px) { #adminTabContent .admin-error-table-wrap { overflow-x: auto; }' in CSS
    assert 'checks["error_table_fits_desktop"]' in CAPTURE
    assert '#adminTabContent .admin-error-metrics article:last-child strong { font-size: 24px; }' in CSS
    assert '@media (min-width: 1280px) {\n  #adminTabContent #adminTelemetryState { display: none; }' in CSS
    assert '#adminTabContent .admin-error-metrics article { min-height: 148px; }' in CSS
    assert '#adminTabContent #adminTelemetryRefresh { grid-column: 1; grid-row: 2;' in CSS

