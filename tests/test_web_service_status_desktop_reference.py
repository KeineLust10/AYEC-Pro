from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_status_wall_renders_desktop_assistant_personnel_and_camera_panels():
    source = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "Web_Arayuzu/web/desktop-parity.css").read_text(encoding="utf-8")
    assert 'id="statusWallHost"' in source
    assert 'data-status-filter="all"' in source
    assert 'status-wall-technicians' in source
    assert 'status-wall-camera' in source
    assert 'class="status-wall-side" tabindex="0"' in source
    assert 'status-wall-assistant' in source
    assert 'body[data-page="service-status"] .status-wall-layout' in styles
    assert 'body[data-page="service-status"] .status-wall-side{grid-template-rows:160px 168px 150px;overflow-y:auto' in styles
    assert 'body[data-page="service-status"] .status-wall-camera>div{min-height:112px;flex:none}' in styles
    assert 'body[data-page="service-status"] .status-wall-side:focus-visible{outline:2px solid var(--brand)' in styles
    assert 'body[data-page="service-status"] .status-wall-side{grid-template-rows:160px 168px 150px' in styles


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


def test_status_wall_filter_buttons_render_live_category_counts():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")

    assert 'const counts = { all: 0, done: 0, parts: 0, open: 0 }' in source
    assert 'const labels = { all: "T\\u00fcm\\u00fc", done: "Teslim", parts: "Par\\u00e7a Bekleyen", open: "\\u0130\\u015flemde" }' in source
    assert 'counts[kind] = (counts[kind] || 0) + 1' in source
    assert 'button.textContent = `${labels[button.dataset.statusFilter] || ""} (${counts[button.dataset.statusFilter] || 0})`' in source
