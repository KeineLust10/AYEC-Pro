from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_report_template_delete_uses_shared_confirmation_dialog():
    source = (ROOT / "Web_Arayuzu" / "web" / "report-templates.js").read_text(encoding="utf-8")
    start = source.index("async function runTemplateAction(")
    end = source.index("\n  function parseCSVLine", start)
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
