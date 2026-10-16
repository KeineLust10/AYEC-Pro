from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_status_wall_renders_desktop_assistant_personnel_and_camera_panels():
    source = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "Web_Arayuzu/web/desktop-parity.css").read_text(encoding="utf-8")
    assert 'id="statusWallHost"' in source
    assert 'data-status-filter="all"' in source
    assert 'status-wall-technicians' in source
    assert 'status-wall-camera' in source
    assert 'status-wall-assistant' in source
    assert 'body[data-page="service-status"] .status-wall-layout' in styles


def test_status_wall_keeps_desktop_toolbar_actions_and_critical_filter_behavior():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")

    for control in ("statusWallRefreshCount", "data-status-share", "data-status-critical", "data-status-export", "data-status-help"):
        assert control in source
    assert "(!ayecStatusCriticalOnly || critical)" in source
    assert 'body[data-page="service-status"] .status-wall-refresh-count' in styles
    assert 'body[data-page="service-status"] .page-head .actions' in styles


def test_status_rows_keep_desktop_detail_print_and_sms_actions():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")

    assert 'data-status-edit' in source
    assert 'data-status-print' in source
    assert 'data-status-sms' in source
    assert 'function ayecStatusPrintChoices(row)' in source
    assert 'apiFetch("/api/desktop/service-sms/status?tracking_no="' in source
