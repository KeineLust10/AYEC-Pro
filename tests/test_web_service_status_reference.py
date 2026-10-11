from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_service_status_reference_has_a_distinct_menu_and_full_width_status_wall():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    styles = (WEB / "midnight-reference.css").read_text(encoding="utf-8")

    assert '"service-status"' in app
    assert 'label:"Durum Paneli"' in app
    assert 'meta?.table !== "devices"' in app
    assert 'id="statusWallHost"' in app
    assert 'data-status-filter="parts"' in app
    assert 'class="active" data-status-filter="all"' in app
    assert 'id="statusWallCritical"' in app
    assert "@media(max-width:760px){.status-wall-metrics" in styles
    assert '@media print{body[data-page="service-status"]' in styles
    parity = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    assert 'status-wall-list>header nav button:not(.active)' in parity


def test_status_wall_omits_technician_and_camera_panels():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "AYEC Servis Asistan\u0131" not in app
    assert 'class="status-wall-side"' not in app
    assert 'id="statusWallTechnicians"' not in app
    assert 'class="status-wall-camera"' not in app
    assert 'class="status-wall-chart"' not in app
    assert 'id="statusWallChart"' not in app


def test_status_wall_desktop_spacing_matches_reference_geometry():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="service-status"] .content {\n  padding: 35px 0 45px 12px;' in styles
    assert 'body[data-page="service-status"] .page-head {\n  min-height: 98px;' in styles
    assert 'body[data-page="service-status"] .status-wall-metrics > article {\n  position: relative;\n  display: flex;\n  height: 106px;' in styles
    assert 'grid-template-columns: minmax(0, 3fr) minmax(390px, 1fr)' in styles
    assert '@media (max-width: 760px)' in styles
