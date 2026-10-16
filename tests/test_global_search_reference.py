from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_global_search_reference_is_loaded_after_app_and_exposes_desktop_targets():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "global-search-reference.js").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert index.index('src="app.js') < index.index('src="global-search-reference.js')
    assert 'id="globalSearchResults"' in script
    assert 'route:"dashboard"' in script
    assert 'route:"services"' in script
    assert 'route:"customers"' in script
    assert 'route:"stock"' in script
    assert 'route:"finance"' in script
    assert 'route:"settings"' in script
    assert 'route:"announcements"' in script
    assert 'route:"field-service"' in script
    assert 'item.kind==="customer"?"customerSearch":"stockSearch"' in script
    assert 'event.key==="ArrowDown"' in script
    assert 'event.key==="ArrowUp"' in script
    assert 'event.key==="Escape"' in script
    assert 'event.ctrlKey||event.metaKey' in script
    assert 'dispatchEvent(new Event("input",{bubbles:true}))' in app
