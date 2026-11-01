from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "midnight-reference.css"


def test_field_map_uses_source_appointments_without_faking_gps():
    source = APP.read_text(encoding="utf-8")
    assert 'page !== "field-service"' in source
    assert 'apiFetch("/api/desktop/table/appointments?limit=1")' in source
    assert "GPS BA\\u011eLI DE\\u011e\\u0130L" in source
    assert "Koordinat kayd\\u0131 olmadan konum g\\u00f6sterilmez." in source
    assert 'data-page="settings"' in source


def test_field_map_initial_and_reset_zoom_match_native_tile_scale():
    field_map = (ROOT / "Web_Arayuzu" / "web" / "field-service-parity.js").read_text(encoding="utf-8")
    desktop_map = (ROOT / "src" / "ui" / "widgets" / "field_radar_canvas.py").read_text(encoding="utf-8")
    marker_update_start = field_map.index("function drawPersonnelMarkers(L)")
    marker_update_end = field_map.index("function distanceKm(first, second)", marker_update_start)
    marker_update = field_map[marker_update_start:marker_update_end]

    assert "TILE_ZOOM = 12" in desktop_map
    assert "self.zoom = 2 ** 5" in desktop_map
    assert "self.TILE_ZOOM + math.log2(self.zoom)" in desktop_map
    assert field_map.count("setView([fieldMapCenter.lat, fieldMapCenter.lng], 17)") == 2
    assert "fieldMap.setView([fieldMapCenter.lat, fieldMapCenter.lng], 17)" in marker_update
    assert "fieldMap.fitBounds" not in marker_update


def test_field_map_queue_has_search_status_and_narrow_layout_rules():
    source = APP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'id="genericSearch"' in source
    assert 'id="fieldMapStatus"' in source
    assert 'id="fieldMapRows"' in source
    assert "field-map-layout" in css
    assert "@media(max-width:1000px){.field-map-layout" in css
    assert "@media print" in css


def test_field_export_serializes_filtered_visible_fields_as_csv():
    source = APP.read_text(encoding="utf-8")

    assert "function ayecFieldFilteredRows()" in source
    assert "function ayecFieldExportCsv(rows)" in source
    assert 'download("saha-gorevleri-" + today() + ".csv", ayecFieldExportCsv(ayecFieldFilteredRows()))' in source
    export = source[source.index("function ayecFieldExportCsv(rows)"):source.index("function ayecFieldRender()")]
    assert '"Telefon": row.phone || ""' in export
    assert '"gps_latitude"' not in export
    assert '"internal_notes"' not in export


def test_field_panel_restores_desktop_modes_and_team_filters():
    script = (ROOT / "Web_Arayuzu" / "web" / "field-service-parity.js").read_text(encoding="utf-8")
    css = (ROOT / "Web_Arayuzu" / "web" / "field-service-parity.css").read_text(encoding="utf-8")
    assert '"customer", "M\\u00fc\\u015fteri & WhatsApp"' in script
    assert '"teams", "Ekipler"' in script
    assert '"jobs", "\\u0130\\u015f Emirleri"' in script
    assert "data-field-radar-category" in script
    assert 'fieldRadarCategory === "warnings" && !point' in script
    assert ".field-mode-tabs" in css
    assert ".field-radar-filters" in css


def test_field_location_tools_cover_desktop_actions_and_assignment_contract():
    script = (ROOT / "Web_Arayuzu" / "web" / "field-service-parity.js").read_text(encoding="utf-8")
    assert 'drawRoute.dataset.fieldMapAction = "draw-route"' in script
    assert 'drawRoute.textContent = "Rota Ciz"' in script
    assert 'finish.disabled = routePoints.length < 2' in script
    assert '"manual-location", "Manuel Koordinat Gir"' in script
    assert '"whatsapp-paste", "WhatsApp Konumu Yapistir"' in script
    assert '"assign-location", "Secili Konumu Personele Ata"' in script
    assert "navigator.clipboard.readText()" in script
    assert '"/api/desktop/field-service/assign"' in script
    assert 'fieldMap.on("click"' in script
    assert "finishFieldRouteDrawing" in script
