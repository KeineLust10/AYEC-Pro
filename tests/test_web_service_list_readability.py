from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_service_list_and_accept_form_use_readable_text_sizes():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    stylesheet = (WEB / "service-list-reference.css").read_text(encoding="utf-8")

    assert re.search(r'service-list-reference\.css\?v=[^" ]+', html)
    assert ".service-list-table{font-size:12px}" in stylesheet
    assert ".service-list-table td{height:70px;" in stylesheet
    assert ".service-list-table td small{font-size:11px}" in stylesheet
    assert '.service-list-status{display:inline-block;box-sizing:border-box;max-width:100%;height:30px;' in stylesheet
    assert 'font:800 8px/1.1 Inter,"Segoe UI",sans-serif;text-align:center;white-space:pre-line' in stylesheet
    assert '.service-list-ticket{color:#cfe0ff;font:700 11px "JetBrains Mono",monospace}' in stylesheet
    assert '.service-list-table td:nth-child(5),.service-list-table td:nth-child(6){font:11px "JetBrains Mono",monospace;white-space:nowrap}' in stylesheet
    assert '.service-list-price{color:#34d399;text-align:right;font:700 11px "JetBrains Mono",monospace}' in stylesheet
    assert '.service-list-priority{display:inline-flex;min-height:18px;box-sizing:border-box;align-items:center;padding:0 4px;border-radius:3px;background:transparent;color:#aab6c8;font:800 8px/1 Inter,"Segoe UI",sans-serif;text-align:center}' in stylesheet
    assert '.service-list-priority.priority-high{background:#713f12;color:#fcd34d}' in stylesheet
    assert ".service-list-status{font-size:8px}.service-list-priority{font-size:8px}" in stylesheet
    assert ".service-list-table td small{font-size:11px}.service-list-priority{font-size:8px}" in stylesheet
    assert "#dialogBody:has(select[name=\"customerId\"]) .field label{font-size:12px}" in stylesheet
    assert "#dialogBody:has(select[name=\"customerId\"]) input:not([type=checkbox]),#dialogBody:has(select[name=\"customerId\"]) select,#dialogBody:has(select[name=\"customerId\"]) textarea{min-height:38px;font-size:13px}" in stylesheet
    assert '#appDialog:has(#dialogBody select[name="customerId"]){width:min(1440px,calc(100vw - 32px))' in stylesheet
    assert "@media(max-width:760px){.service-list-table td::before{font-size:11px}.service-list-table td{font-size:12px}" in stylesheet


def test_service_status_dialog_uses_sector_specific_repair_status():
    source = (WEB / "service-list-reference.js").read_text(encoding="utf-8")
    dialog = source.split("function openServiceStatusDialog(customer, service) {", 1)[1].split("\n}", 1)[0]

    assert 'currentSector === "otomotiv"' in dialog
    assert '["Bekliyor", "Serviste", "Par\\u00e7a Bekliyor"' in dialog
    assert '["Bekliyor", "Tamirde", "Par\\u00e7a Bekliyor"' in dialog


def test_service_status_filter_uses_sector_specific_repair_label():
    source = (WEB / "service-list-reference.js").read_text(encoding="utf-8")

    assert '["repair",currentSector === "otomotiv" ? "Serviste" : "Tamirde"]' in source


def test_service_list_desktop_table_keeps_native_columns_and_all_row_actions():
    stylesheet = (WEB / "service-list-reference.css").read_text(encoding="utf-8")
    source = (WEB / "service-list-reference.js").read_text(encoding="utf-8")

    assert "@media(min-width:761px){\n.service-list-table{min-width:1000px}" in stylesheet
    assert ".service-list-table th:nth-child(1),.service-list-table td:nth-child(1){width:3.9293%}" in stylesheet
    assert ".service-list-table th:nth-child(9),.service-list-table td:nth-child(9){width:6.9745%}" in stylesheet
    assert ".service-list-table th:last-child,.service-list-table td:last-child{width:24.558%;min-width:0}" in stylesheet
    action_markup = source.split('<div class="service-list-actions">', 1)[1].split("</div>", 1)[0]
    assert action_markup.count("<button type=\"button\"") == 8
    assert "@media(max-width:760px){.service-list-table{min-width:0}" in stylesheet


def test_service_list_uses_shared_theme_and_mobile_width_rules():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    parity = (WEB / "desktop-parity.css").read_text(encoding="utf-8")

    assert re.search(r'href="desktop-parity\.css\?v=[^"]+"', html)
    assert 'grid-template-columns: repeat(5, minmax(39px, 1fr))' in parity
    assert 'flex: 0 0 100%' in parity
    assert '--sl-panel: var(--surface)' in parity
    assert '.content .service-list-ref .service-list-tabs {\n  display: flex !important' in parity
    assert '@media (max-width: 760px)' in parity
    assert '.service-list-metrics {\n    grid-template-columns: repeat(2, minmax(0, 1fr))' in parity
    assert '.service-list-table-wrap {\n    max-width: 100%;\n    overflow-x: auto' in parity
    assert '#content .service-list-table-wrap .service-list-table thead tr {\n    height: 42px !important;' in parity
    assert '#content .service-list-table-wrap .service-list-table thead input[type="checkbox"] {\n    width: 16px;' in parity


def test_dashboard_service_context_menu_keeps_desktop_actions_and_order():
    source = (WEB / "service-list-reference.js").read_text(encoding="utf-8")
    parity = (WEB / "service-list-reference.css").read_text(encoding="utf-8")

    assert '["technician", panelLabel], ["form", formLabel], ["edit", "D\\u00fczenle"]' in source
    assert 'const updateActions=permissions.canUpdate?' in source
    assert 'buttonMarkup(["close",closeLabel])' in source
    assert source.index('const updateActions=') < source.index('const customerActions=')
    assert 'if (action === "technician") return technicianDialog(customer, service);' in source
    assert 'event.target.closest(".service-list-table tbody tr[data-kind=service]")' in source
    assert 'aria-selected="${current}" class="${[selected ? "is-selected" : "", current ? "is-current" : ""].filter(Boolean).join(" ")}' in source
    assert 'if(page==="service-list"&&serviceRow)' in source
    assert "menu.querySelector('button[role=\"menuitem\"]')?.focus()" in source
    assert 'event.target.closest(".service-list-table tbody tr[data-kind=service]")' in source
    assert 'if(page==="service-list")' in source
    assert 'item.classList.toggle("is-current", current)' in source
    assert ' .service-list-table tbody tr.is-current td'.strip() in parity
    assert 'return technicianDialog(customer,service);' in source
    assert 'if (action === "form" || action === "edit") return dashboardServiceEditDialog(customer, service);' in source
    assert '["print-detailed", "Detayli Fis Yazdir"], ["invoice", "E-Fatura Kes"], ["print-menu", "Fi\\u015f / Yazd\\u0131r"]' in source
    assert 'data-service-submenu-trigger="status"' in source
    assert 'data-service-submenu-trigger="print"' in source
    assert 'statusPanel.innerHTML=statuses.map' in source
    assert 'printPanel.innerHTML=printChoices.map' in source
    assert 'runServicePrintChoice(customer, service, choice)' in source
    assert 'menu.offsetWidth - 8' in source
    assert 'panelHeight-8' in source
    assert '.service-list-context-menu button[hidden]{display:none!important}' in parity
    assert '"Cihaz Etiketi A"' in source and '"Cihaz Etiketi B"' in source
    assert 'D\\u00fczenle / Teknisyen Paneli' not in source
    assert 'openDialog("Servis Kayd\\u0131n\\u0131 Sil","S\\u0130LME ONAYI"' in source
    assert '"Evet, Sil");document.querySelector("#dialogCancel").textContent="Hay\\u0131r"' in source
    assert 'openDialog("Servis \\u0130\\u015flemini Kapat", "TEKN\\u0130SYEN PANEL\\u0130"' in source
    assert '"Evet, A\\u00e7"); document.querySelector("#dialogCancel").textContent = "Hay\\u0131r"' in source
    assert 'openDialog("Servis Kayd\\u0131n\\u0131 Sil"' in source
    assert 'openDialog("Servis Foto\\u011fraf\\u0131n\\u0131 Sil"' in source
    assert 'querySelectorAll(".service-list-context-menu:not(.service-list-context-submenu-panel)")' in source
    assert 'window.confirm(' not in source


def test_service_list_date_defaults_and_today_chip_match_desktop():
    source = (WEB / "service-list-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "service_list_page.py").read_text(encoding="utf-8")

    assert 'tab: "all", query: "", status: "all", date: "last_30", priority: "all"' in source
    assert 'if (key === "today") return ayecServiceListDateMatches(item, "today");' in source
    assert 'item.id, item.customer, item.brand, item.model' in source
    assert 'self.combo_date.setCurrentIndex(self.combo_date.findData("last_30"))' in desktop
    assert 'entry = str(rec.get("entry_date") or "")' in desktop
    assert 'if not entry.startswith(today_str):' in desktop


def test_service_list_page_size_choices_match_desktop():
    source = (WEB / "service-list-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "service_list_page.py").read_text(encoding="utf-8")

    assert "for size in [8, 15, 25, 50, 100]:" in desktop
    assert "[8,15,25,50,100].map(size=>" in source


def test_service_invoice_tabs_follow_desktop_invoice_flag():
    source = (WEB / "service-list-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "service_list_page.py").read_text(encoding="utf-8")

    assert 'function ayecServiceListIsInvoiced(item)' in source
    assert 'if (key === "invoiced") return ayecServiceListIsInvoiced(item);' in source
    assert 'if (key === "uninvoiced") return !ayecServiceListIsInvoiced(item);' in source
    assert 'str(record.get("is_invoiced") or "0").strip().lower() in {"1", "true"}' in desktop


def test_service_cargo_tab_uses_desktop_delivery_fields_and_statuses():
    source = (WEB / "service-list-reference.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "service_list_page.py").read_text(encoding="utf-8")

    assert 'const shipment = `${item.delivery_type || ""} ${item.service_source || ""}`' in source
    assert '["kargo bekliyor", "kargoya verildi"].includes(status)' in source
    assert 'elif cat == "cargo_waiting":' in desktop
    assert 'str(rec.get("delivery_type") or "") + " " + str(rec.get("service_source") or "")' in desktop























