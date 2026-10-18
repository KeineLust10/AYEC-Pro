from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_stock_context_menu_has_authenticated_photo_action():
    source = (WEB / "stock-context-parity.js").read_text(encoding="utf-8")
    style = (WEB / "stock-context-parity.css").read_text(encoding="utf-8")
    page = (WEB / "index.html").read_text(encoding="utf-8")

    assert '["\\uD83D\\uDCF7 Foto\\u011fraf\\u0131 G\\u00f6r\\u00fcnt\\u00fcle", "stock-photo"]' in source
    assert '"/api/desktop/stock/photo/"' in source
    assert '"\\uD83D\\uDCC4 PDF Olarak Kaydet", "stock-pdf"' in source
    assert '"/api/desktop/stock/export/pdf"' in source
    assert 'if (kind === "stock" && action === "stock-pdf")' in source
    assert 'if (kind === "stock" && action === "stock-print")' in source
    assert '["stock-pdf", "stock-print"].includes(action)' not in source
    assert '"\\uD83D\\uDCCA Excel\'e Aktar", "stock-excel"' in source
    assert '"/api/desktop/stock/export/xlsx"' in source
    assert '"/api/desktop/stock/delete"' in source
    assert 'name="password" type="password"' in source
    assert '"\\uD83D\\uDCE6 Stok Ekle/\\u00c7\\u0131kar", "movement"' in source
    assert source.index('"movement"') < source.index('"edit-product"')
    assert 'kind !== "stock"' in source
    assert "stock-context-parity.js" in page
    assert "stock-context-parity.css" in page
    assert ".stock-photo-preview img" in style


def test_stock_movement_history_context_menu_matches_desktop_actions():
    web = (WEB / "stock-movements-page.js").read_text(encoding="utf-8")
    delete_flow = (WEB / "stock-history-delete-confirm.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "_stock_context_menus.py").read_text(encoding="utf-8")
    page = (WEB / "index.html").read_text(encoding="utf-8")
    start = web.index('document.addEventListener("contextmenu", function (event) {')
    end = web.index("}, true);", start)
    web_menu = web[start:end]
    desktop_start = desktop.index("def show_history_context_menu")
    desktop_end = desktop.index("def delete_history_context", desktop_start)
    desktop_menu = desktop[desktop_start:desktop_end]
    expected = ["movement-export", "movement-pdf", "movement-print", "movement-delete"]
    positions = []
    cursor = 0
    for action in expected:
        position = web_menu.index(f'"{action}"', cursor)
        positions.append(position)
        cursor = position + len(action) + 2

    assert positions == sorted(positions)
    assert "page_id=50" in desktop_menu
    assert "export_history_to_excel" in desktop_menu
    assert "export_history_to_pdf" in desktop_menu
    assert "print_history_table" in desktop_menu
    assert "delete_history_context(row)" in desktop_menu
    assert 'ayecContextMenuEnabled("stock")' in web_menu
    assert 'window.print();' in web
    assert 'if (kind === "movement" && action === "movement-pdf")' in web
    assert 'if (kind === "movement" && action === "movement-print")' in web
    assert '"/api/desktop/stock/movements/export/pdf?"' in web
    assert '(action === "movement-pdf" || action === "movement-print")' not in web
    assert 'apiFetch("/api/desktop/stock/movements/delete"' in delete_flow
    assert 'stock-movements-page.js' in page
    assert 'stock-history-delete-confirm.js' in page


def test_stock_delete_requires_the_current_password_in_the_web_dialog():
    web = (WEB / "app.js").read_text(encoding="utf-8")
    start = web.index("deleteProduct=function(product)")
    end = web.index("\n};", start)
    flow = web[start:end]
    assert 'name="password" type="password" autocomplete="current-password" required' in flow
    assert 'password:String(form.get("password")||"")' in flow
    assert '"/api/desktop/stock/delete"' in flow


def test_service_delete_action_uses_the_desktop_confirmation_and_soft_delete_endpoint():
    web = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'data-action="service-delete"' in web
    assert 'if(action==="service-delete")return deleteServiceFromWeb(id)' in web
    assert 'function deleteServiceFromWeb(trackingNo)' in web
    assert '"/api/desktop/table/devices"' in web
    assert '_action:"delete"' in web
    assert 'Bu i\\u015flem geri al\\u0131namaz.' in web


def test_quick_close_confirmation_continues_to_the_technician_panel():
    web = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'data-action="service-quick-close"' in web
    assert 'if(action==="service-quick-close")return quickCloseServiceFromWeb(id)' in web
    assert 'function quickCloseServiceFromWeb(trackingNo)' in web
    assert 'void technicianDialog(customer,service)' in web
    assert 'Teslim ve tahsilat ad\\u0131mlar\\u0131 teknisyen panelinde tamamlan\\u0131r.' in web


def test_stock_context_adjustment_uses_the_tenant_stock_adjust_api():
    web = (WEB / "app.js").read_text(encoding="utf-8")
    start = web.index("movementDialog=function(product)")
    end = web.index("\n", start)
    flow = web[start:end]
    assert 'name="type"' in flow and 'name="qty"' in flow and 'name="ref"' in flow
    assert '"/api/desktop/stock/adjust"' in flow
    assert 'delta:values.type==="Giri\\u015f"?quantity:-quantity' in flow
