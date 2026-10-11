from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js"

def test_generic_controls_are_optional_for_custom_route_views():
    source = APP.read_text(encoding="utf-8")
    assert 'const genericSearch=$("#genericSearch"),genericRefresh=$("[data-generic-refresh]"),genericAdd=$("[data-generic-add]")' in source
    assert 'if(genericRefresh)genericRefresh.onclick=' in source
    assert 'if(genericAdd)genericAdd.onclick=' in source
