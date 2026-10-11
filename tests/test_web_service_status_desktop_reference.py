from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_status_wall_does_not_render_unconfigured_personnel_or_camera_panels():
    source = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
    styles = (ROOT / "Web_Arayuzu/web/desktop-parity.css").read_text(encoding="utf-8")
    assert 'id="statusWallHost"' in source
    assert 'data-status-filter="all"' in source
    assert 'status-wall-technicians' not in source
    assert 'status-wall-camera' not in source
    assert 'statusWallSideOpen' not in source
    assert 'body[data-page="service-status"] .status-wall-layout' in styles


def test_status_wall_keeps_desktop_toolbar_actions_and_critical_filter_behavior():
    source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    styles = (ROOT / "Web_Arayuzu" / "web" / "desktop-parity.css").read_text(encoding="utf-8")

    for control in ("statusWallRefreshCount", "data-status-share", "data-status-critical", "data-status-export", "data-status-help"):
        assert control in source
    assert "(!ayecStatusCriticalOnly || critical)" in source
    assert 'body[data-page="service-status"] .status-wall-refresh-count' in styles
    assert 'body[data-page="service-status"] .page-head .actions' in styles
