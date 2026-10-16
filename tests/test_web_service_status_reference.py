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


def test_status_wall_renders_assistant_technician_and_camera_panels():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "AYEC Servis Asistani" in app
    assert 'class="status-wall-side"' in app
    assert 'id="statusAssistantPersonnel"' in app
    assert "status-wall-camera" in app
    assert "status-wall-assistant" in app
    assert 'class="status-wall-chart"' not in app
    assert 'id="statusWallChart"' not in app


def test_status_wall_desktop_spacing_matches_reference_geometry():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert 'body[data-page="service-status"] .content {\n  padding: 35px 0 45px 12px;' in styles
    assert 'body[data-page="service-status"] .page-head {\n  min-height: 98px;' in styles
    assert 'body[data-page="service-status"] .status-wall-metrics > article {\n  position: relative;\n  display: flex;\n  height: 106px;' in styles
    assert 'grid-template-columns: minmax(0, 3fr) minmax(390px, 1fr)' in styles
    assert '@media (max-width: 760px)' in styles


def test_status_wall_tv_mode_shares_display_link_and_exports_filtered_rows():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    script = (WEB / "service-status-reference.js").read_text(encoding="utf-8")
    styles = (WEB / "service-status-reference.css").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")

    assert 'params.get("display") === "status-wall"' in script
    assert 'url.searchParams.set("display", "status-wall")' in script
    assert 'const records = filteredRows().map' in script
    assert '"Tamam"' in script and r'ayn\u0131 \u015firket hesab\u0131yla' in script
    assert 'toggle.id = "statusWallTargetToggle"' in script
    assert 'row?.delivered_at || row?.exit_date || "-"' in script
    assert 'row.estimated_date || "-"' in script
    assert 'window.ayecStatusWallDisplayMode ? 20' in app
    assert 'if(titles[requested]||genericModules[requested]' in app
    assert 'return canAccessControlCenter()?requested:"dashboard"' in app
    assert 'body[data-status-display="wall"] .app-shell > .sidebar' in styles
    assert 'service-status-reference.js' in index
    assert 'service-status-reference.css' in index


def test_service_status_double_click_only_edits_the_desktop_marquee_target():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "service_status_page.py").read_text(encoding="utf-8")
    marker = app.index("function ayecStatusMarqueeRender")
    start = app.index('document.addEventListener("dblclick", event => {', marker)
    end = app.index("const ayecStatusRenderBeforeActionParity", start)
    handler = app[start:end]

    assert "def mouseDoubleClickEvent(self, event):" in desktop
    assert 'event.target.closest("[data-status-marquee]")' in handler
    assert "!db.settings.doubleClick" in handler
    assert 'event.target.closest("#statusWallHost tbody tr")' not in handler
    assert 'openGenericDialog(genericModules["service-status"]' not in handler
