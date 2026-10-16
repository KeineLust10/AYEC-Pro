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


def test_field_map_queue_has_search_status_and_narrow_layout_rules():
    source = APP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'id="genericSearch"' in source
    assert 'id="fieldMapStatus"' in source
    assert 'id="fieldMapRows"' in source
    assert "field-map-layout" in css
    assert "@media(max-width:1000px){.field-map-layout" in css
    assert "@media print" in css


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
    assert '"draw-route", "Yeni Rota Ciz"' in script
    assert '"manual-location", "Manuel Koordinat Gir"' in script
    assert '"whatsapp-paste", "WhatsApp Konumu Yapistir"' in script
    assert '"assign-location", "Secili Konumu Personele Ata"' in script
    assert "navigator.clipboard.readText()" in script
    assert '"/api/desktop/field-service/assign"' in script
    assert 'fieldMap.on("click"' in script
    assert "finishFieldRouteDrawing" in script
