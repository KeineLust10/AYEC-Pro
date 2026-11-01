import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_status_assistant_loads_complete_table_catalogs():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("async function ayecStatusAssistantLoad()")
    end = app.index("\n}", start)
    block = app[start:end]

    assert "endpoints.map(table => loadAllDesktopTableData(table))" in block
    assert "?limit=500" not in block


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
    assert 'body[data-page="service-status"] .page-head .actions {\n    display: grid;' in parity
    assert 'body[data-page="service-status"] .page-head .actions > .status-wall-action-hint {\n    grid-column: 1 / -1;' in parity


def test_status_search_and_critical_filter_match_desktop_columns_and_tokens():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "service_status_page.py").read_text(encoding="utf-8")

    assert "row.entry_date, row.estimated_date, row.urgency, row.delivered_at, row.exit_date" in app
    assert r"const critical = /par\u00e7a|bekliyor|acil/.test" in app
    start = desktop.index("def _apply_status_filters(self):")
    end = desktop.index("def _", start + 5)
    native_filter = desktop[start:end]
    assert 'for token in ("PARCA", "BEKLIYOR", "ACIL")' in native_filter
    assert "kritik" not in native_filter.casefold()


def test_status_wall_renders_assistant_technician_and_camera_panels():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "AYEC Servis Asistani" in app
    assert 'class="status-wall-side"' in app
    assert 'id="statusAssistantPersonnel"' in app
    assert "status-wall-camera" in app
    assert "status-wall-assistant" in app
    assert 'class="status-wall-flow"' in app
    assert 'id="statusWallFlowChart"' in app
    assert "function ayecStatusFlowRender(rows)" in app


def test_status_wall_desktop_spacing_matches_reference_geometry():
    styles = (WEB / "desktop-parity.css").read_text(encoding="utf-8")
    reference_styles = (WEB / "service-status-reference.css").read_text(encoding="utf-8")

    assert '--sidebar: 250px;' not in reference_styles
    assert 'body[data-page="service-status"] .content {\n  padding: 35px 0 45px 12px;' in styles
    assert 'body[data-page="service-status"] .page-head {\n  display: grid;' in styles
    assert 'min-height: 82px;' in styles
    assert 'background: var(--bg);' in styles
    assert 'body[data-page="service-status"] .status-wall-metrics > article {\n  position: relative;\n  display: flex;\n  height: 106px;' in styles
    assert 'grid-template-columns: minmax(0, 1fr) 260px' in styles
    assert 'gap: 12px;' in styles
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
    assert 'window.ayecStatusWallDisplayMode ? 5000 : 1000' in app
    assert 'setInterval(' not in script
    assert 'if(titles[requested]||genericModules[requested]' in app
    assert 'return canAccessControlCenter()?requested:"dashboard"' in app
    assert 'body[data-page="service-status"][data-status-display="wall"] .app-shell > .sidebar' in styles
    assert 'service-status-reference.js' in index
    assert 'service-status-reference.js?v=20261027-status-export-search-parity-1' in index
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
    assert "if (!marquee) return;" in handler
    assert "!db.settings.doubleClick" not in handler
    assert 'event.target.closest("#statusWallHost tbody tr")' not in handler
    assert 'openGenericDialog(genericModules["service-status"]' not in handler

def test_status_wall_capacity_percentage_matches_desktop_rounding():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("function ayecRoundHalfEven")
    end = app.index("function ayecStatusMetrics", start)
    rounding = app[start:end]
    values = [100 * count / 8 for count in (1, 3, 5, 7)]
    script = (
        rounding
        + "\nprocess.stdout.write(JSON.stringify("
        + json.dumps(values)
        + ".map(ayecRoundHalfEven)));"
    )
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)

    assert json.loads(result.stdout) == [round(value) for value in values]
    assert "ayecRoundHalfEven(metrics.occupying * 100 / metrics.capacity)" in app


def test_status_wall_critical_filter_matches_desktop_tokens():
    source = (WEB / "service-status-reference.js").read_text(encoding="utf-8")
    start = source.index("function ayecStatusNormalizeText")
    end = source.index("(function()", start)
    helper = source[start:end]
    cases = [
        {"status": "Kritik", "urgency": "Normal"},
        {"status": "Par\u00e7a bekliyor", "urgency": "Normal"},
        {"status": "Tamirde", "urgency": "Acil"},
        {"status": "Bekl\u0131yor", "urgency": "Normal"},
    ]
    category_cases = [
        ["Yedek par\u00e7a", "parts"],
        ["Malzeme bekliyor", "parts"],
        ["Malzeme bekliyor", "open"],
        ["Par\u00e7a teslim edildi", "parts"],
        ["Par\u00e7a teslim edildi", "done"],
        ["Teslime haz\u0131r", "open"],
    ]
    script = (
        helper
        + "\nprocess.stdout.write(JSON.stringify({critical:"
        + json.dumps(cases)
        + ".map(row=>ayecStatusCriticalMatch(row.status,row.urgency)),categories:"
        + json.dumps(category_cases)
        + ".map(([status,category])=>ayecStatusCategoryMatch(status,category))}));"
    )
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)

    assert json.loads(result.stdout) == {
        "critical": [False, True, True, True],
        "categories": [True, False, True, True, True, True],
    }


def test_status_wall_sort_matches_desktop_newest_and_oldest_options():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("function ayecStatusSortRows")
    end = app.index("function ayecStatusMetrics", start)
    helper = app[start:end]
    rows = [
        {"tracking_no": "SRV-OLD", "entry_date": "2026-10-20"},
        {"tracking_no": "SRV-NEW", "entry_date": "2026-10-21"},
    ]
    script = (
        helper
        + "\nconst rows="
        + json.dumps(rows)
        + ";process.stdout.write(JSON.stringify({newest:ayecStatusSortRows([...rows],\"newest\").map(row=>row.tracking_no),oldest:ayecStatusSortRows([...rows],\"oldest\").map(row=>row.tracking_no)}));"
    )
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)
    app_html = app[app.index('id="statusWallSort"'):app.index('</select>', app.index('id="statusWallSort"'))]

    assert json.loads(result.stdout) == {"newest": ["SRV-NEW", "SRV-OLD"], "oldest": ["SRV-OLD", "SRV-NEW"]}
    assert 'value="newest"' in app_html
    assert 'value="oldest"' in app_html


def test_status_wall_export_search_matches_visible_serial_number():
    source = (WEB / "service-status-reference.js").read_text(encoding="utf-8")
    start = source.index("function ayecStatusSearchMatch")
    end = source.index("\n(function()", start)
    helper = source[start:end]
    row = {
        "tracking_no": "SRV-100",
        "customer_name": "Ada",
        "device_brand": "Acme",
        "device_model": "Phone",
        "status": "Tamirde",
        "entry_date": "2026-10-10",
        "estimated_date": "2026-10-12",
        "urgency": "Acil",
        "delivered_at": "2026-10-11",
        "serial_no": "SN-204",
    }
    queries = ["2026-10-10", "2026-10-12", "acil", "2026-10-11", "SN-204"]
    script = (
        helper
        + "\nconst row="
        + json.dumps(row)
        + ";process.stdout.write(JSON.stringify("
        + json.dumps(queries)
        + ".map(query=>ayecStatusSearchMatch(row,query))));"
    )
    result = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True)

    assert json.loads(result.stdout) == [True, True, True, True, True]
    assert "return ayecStatusSearchMatch(row, query)" in source


def test_status_wall_cells_use_desktop_fallbacks_and_uppercase_values():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    line = next(line for line in app.splitlines() if "status-wall-table-wrap" in line)

    assert 'esc(row.tracking_no || "-")' in line
    assert 'esc([row.device_brand, row.device_model].filter(Boolean).join(" "))' in line
    assert 'row.device_type || "-"' not in line
    assert 'esc((row.status || "Bekliyor").toLocaleUpperCase("tr-TR"))' in line
    assert 'esc((row.urgency || "Normal").toLocaleUpperCase("tr-TR"))' in line


def test_generic_service_cells_keep_full_desktop_tooltips_for_clipped_values():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'function genericCell(value,key){return `<span title="${esc(value===null||value===undefined?"":value)}">${genericValue(value,key)}</span>`}' in app
    assert 'columns.map(c=>`<td>${genericCell(row[c],c)}</td>`)' in app


def test_status_wall_broadcast_matches_desktop_latest_twenty_limit():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "service_status_page.py").read_text(encoding="utf-8")

    assert "ORDER BY id DESC LIMIT 20" in desktop
    assert '.sort((left,right)=>Number(right.id||0)-Number(left.id||0)).slice(0,20)' in app
