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
