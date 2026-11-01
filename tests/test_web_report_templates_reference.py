from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_report_template_editor_consumes_shared_dialog_form_data():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")
    app_source = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")

    assert "form=>saveTemplate(form,row)" in source
    assert "function saveTemplate(formData,row){const values=Object.fromEntries(formData);" in source
    assert "await onSubmit?.(new FormData(form))" in app_source


def test_report_template_manager_loads_all_paged_templates():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")

    assert 'loadAllDesktopTableRows("fast_notes")' in source
    assert 'apiFetch("/api/desktop/table/fast_notes?limit=1000")' not in source


def test_report_template_delete_uses_shared_confirmation_dialog():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")
    start = source.index("async function runTemplateAction(")
    end = source.index("\n  function parseCSV", start)
    block = source[start:end]

    assert "window.confirm" not in block
    assert 'openDialog("Kal\\u0131b\\u0131 Sil","SILME ONAYI"' in block
    assert '"Evet, Sil"' in block
    assert 'textContent="Hay\\u0131r"' in block
    assert 'JSON.stringify({id:row.id,_action:"delete"})' in block


def test_report_template_transfer_uses_desktop_menu_actions():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")

    assert 'aria-haspopup="menu"' in source
    assert 'data-template-transfer="import"' in source
    assert 'data-template-transfer="export"' in source
    assert 'CSV\\u2019den \\u0130\\u00e7e Aktar' in source
    assert 'CSV\\u2019ye D\\u0131\\u015fa Aktar' in source
    assert 'document.getElementById("templateCsv").click()' in source
    assert 'download("rapor-cumle-kaliplari.csv",csv(templates))' in source


def test_report_template_csv_import_matches_export_separator_and_multiline_fields():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")

    assert "function parseCSV(text)" in source
    assert "semicolonCount>commaCount?\";\":\",\"" in source
    assert "(char===\"\\n\"||char===\"\\r\")&&quoted" in source
    assert "parseCSV(await file.text())" in source


def test_report_template_rows_expose_desktop_context_edit_and_delete_actions():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")

    assert 'row.oncontextmenu=event=>openTemplateContextMenu(event,row)' in source
    assert 'data-template-context="edit"' in source
    assert 'data-template-context="delete"' in source
    assert 'runTemplateAction(button.dataset.templateContext,selectedId)' in source
    assert 'ayecContextMenuEnabled("report-templates")' in source


def test_report_template_rows_support_desktop_double_click_and_keyboard_context_menu():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")

    assert 'tabindex="0"' in source
    assert 'row.ondblclick=event=>{event.preventDefault();runTemplateAction("edit",row.dataset.templateRow)' in source
    assert 'event.key!=="ContextMenu"&&!(event.key==="F10"&&event.shiftKey)' in source


def test_report_template_transfer_menu_supports_desktop_keyboard_navigation():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")

    assert 'menu.querySelector("[data-template-transfer]")?.focus()' in source
    assert '["ArrowDown","ArrowUp","Home","End"].includes(action.key)' in source
    assert 'action.key==="Escape"' in source
    assert 'trigger?.focus()' in source
    assert 'items[next]?.focus()' in source


def test_report_template_preview_splits_nested_title_and_detail_like_desktop():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")

    assert 'function templatePreviewTitle(text)' in source
    assert 'function templatePreviewType(category)' in source
    assert 'labels[name]||name.toUpperCase()' in source
    assert 'function templatePreviewId(id)' in source
    assert r'template-preview-meta"><span>${esc(templatePreviewType(selected.category))}</span><small>Se\u00e7ili \u015eablon #${esc(templatePreviewId(selected.id))}</small></div>' in source
    assert 'const nested=detail.indexOf(") (")' in source
    assert r'template-preview-text">\u00bb  ${esc(templatePreviewTitle(selected.label))}' in source
