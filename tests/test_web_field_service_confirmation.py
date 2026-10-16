from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_field_duty_completion_uses_shared_confirmation_dialog():
    source = (ROOT / "Web_Arayuzu" / "web" / "field-service-parity.js").read_text(encoding="utf-8")
    start = source.index("async function finishDuty(id)")
    end = source.index("\n  const genericLoadBeforeFieldPersonnel", start)
    block = source[start:end]

    assert "window.confirm" not in block and "!confirm(" not in block
    assert 'openDialog("G\\u00f6revi Tamamla"' in block
    assert '"Evet, Tamamla"' in block
    assert 'textContent = "Hay\\u0131r"' in block
    assert '"/api/desktop/field-service/finish"' in block



def test_field_personnel_context_action_matches_desktop_and_respects_menu_preference():
    desktop = (ROOT / "src" / "ui" / "pages" / "field_service_components.py").read_text(encoding="utf-8")
    source = (ROOT / "Web_Arayuzu" / "web" / "field-service-parity.js").read_text(encoding="utf-8")
    desktop_card = desktop[desktop.index("class PersonnelCard"):desktop.index("class ModernConfirmDialog")]
    context_start = source.index("const showContextBeforeFieldPersonnel")
    context_end = source.index("const contextActionBeforeFieldPersonnel", context_start)
    context_menu = source[context_start:context_end]

    assert 'menu.addAction("Gorevi Tamamla / Bosa Cikar")' in desktop_card
    assert 'if (kind !== "field-personnel") return showContextBeforeFieldPersonnel(event, kind, id);' in context_menu
    assert 'if (!ayecContextMenuEnabled()) return;' in context_menu
    assert 'event.preventDefault();' in context_menu
    assert 'data-context-action="field-personnel-finish">G\\u00f6revi Tamamla / Bo\\u015fa \\u00c7\\u0131kar</button>' in context_menu
    assert 'if (kind === "field-personnel" && action === "field-personnel-finish") return finishDuty(id);' in source
