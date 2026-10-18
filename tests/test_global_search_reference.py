from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_global_search_reference_is_loaded_after_app_and_exposes_desktop_targets():
    index = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "global-search-reference.js").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    assert index.index('src="app.js') < index.index('src="global-search-reference.js')
    assert 'id="globalSearchResults"' in script
    assert 'id="globalSearchDialog"' in script
    assert 'palette.showModal()' in script
    assert 'Gitmek istedi\\u011finiz yer' in script
    assert 'searchAnchor.before(wrapper)' in script
    assert 'palette.addEventListener("close"' in script
    assert 'palette.querySelector(".global-search-dialog-body").append(wrapper)' in script
    assert 'route:"dashboard"' in script
    assert 'route:"services"' in script
    assert 'route:"customers"' in script
    assert 'route:"stock"' in script
    assert 'route:"finance"' in script
    assert 'route:"settings"' in script
    assert 'route:"announcements"' in script
    assert 'route:"field-service"' in script
    assert 'document.querySelectorAll("#nav [data-page]")' in script
    assert 'button.querySelector(".nav-label")' in script
    assert 'button.children[1]?.textContent' in script
    assert 'data-search-route="${esc(item.route||"")}"' in script
    assert 'return visible.length?visible:fallbackPageItems' in script
    assert 'item.kind==="customer"?"customerSearch":"stockSearch"' in script
    assert 'fold(customer.name).includes(folded)||fold(customer.phone).includes(folded)' in script
    assert 'if(item.kind==="service")' in script
    assert 'service.serial_no' in script
    assert 'window.ayecAdvancedServiceFilter={customer:"",tracking:item.query' in script
    assert 'event.key==="ArrowDown"' in script
    assert 'event.key==="ArrowUp"' in script
    assert 'event.key==="Escape"' in script
    assert 'event.ctrlKey||event.metaKey' in script
    assert 'dispatchEvent(new Event("input",{bubbles:true}))' in app
    assert '$("#globalSearch").onkeydown=' not in app
