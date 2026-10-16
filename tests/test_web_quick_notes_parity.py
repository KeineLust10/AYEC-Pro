from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
DESKTOP = ROOT / "src" / "ui" / "pages" / "quick_notes_settings_widget.py"


def test_quick_notes_row_supports_desktop_double_click_and_context_actions():
    app = APP.read_text(encoding="utf-8")
    desktop = DESKTOP.read_text(encoding="utf-8")

    assert "self.table.doubleClicked.connect(self.open_edit_dialog)" in desktop
    assert "menu.addAction(\"\u270f\ufe0f D\u00fczenle\", self.open_edit_dialog)" in desktop
    assert 'menu.addAction("\U0001f5d1\ufe0f Sil", self.delete_note)' in desktop
    assert 'data-kind="quick-note"' in app
    assert "tr.ondblclick=event=>{if(db.settings.doubleClick&&!event.target.closest('button,input'))quickNoteDialog(note)}" in app
    assert 'data-quick-note-action="edit"' in app
    assert 'data-quick-note-action="delete"' in app
    assert '&#x270f;&#xfe0f; D\\u00fczenle' in app
    assert '&#x1f5d1;&#xfe0f; Sil' in app
    assert "button.onclick=event=>{event.stopPropagation();deleteQuickNote(rows[+button.dataset.index])}" in app


def test_quick_notes_delete_requires_confirmation_before_write():
    app = APP.read_text(encoding="utf-8")
    start = app.index("function deleteQuickNote(note)")
    end = app.index("function quickNoteDialog", start)
    delete = app[start:end]

    assert 'openDialog("Notu Sil"' in delete
    assert 'desktopWrite("fast_notes",{id:note.id,_action:"delete"})' in delete
    assert delete.index("openDialog(") < delete.index("desktopWrite(")
