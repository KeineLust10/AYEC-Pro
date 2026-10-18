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


def test_quick_note_search_includes_original_and_display_categories():
    app = APP.read_text(encoding="utf-8")
    desktop = DESKTOP.read_text(encoding="utf-8")
    loader_start = app.index("async function loadQuickNotes")
    loader_end = app.index("\n", loader_start)
    loader = app[loader_start:loader_end]
    desktop_filter_start = desktop.index("haystack = ", desktop.index("def load_notes(self):"))
    desktop_filter = desktop[desktop_filter_start:desktop.index("\n", desktop_filter_start)]

    assert '" ".join((str(n_cat), display_category, title, str(n_label))).lower()' in desktop_filter
    assert 'const text=`${n.category||\"\"} ${n.display_category||\"\"} ${n.title||\"\"} ${n.label||\"\"}`' in loader


def test_quick_notes_delete_requires_confirmation_before_write():
    app = APP.read_text(encoding="utf-8")
    start = app.index("function deleteQuickNote(note)")
    end = app.index("function quickNoteDialog", start)
    delete = app[start:end]

    assert 'openDialog("Notu Sil"' in delete
    assert 'desktopWrite("fast_notes",{id:note.id,_action:"delete"})' in delete
    assert delete.index("openDialog(") < delete.index("desktopWrite(")


def test_quick_note_editor_matches_desktop_single_line_and_toggle_controls():
    app = APP.read_text(encoding="utf-8")
    desktop = DESKTOP.read_text(encoding="utf-8")
    start = app.index("function quickNoteDialog")
    end = app.index("\n", start)
    editor = app[start:end]
    desktop_editor = desktop[desktop.index("class QuickNoteDialog"):]

    assert "self.inp_label = QLineEdit()" in desktop_editor
    assert "self.toggle_active = AnimatedToggle()" in desktop_editor
    assert 'self.cmb_cat.addItems(["Ar\\u0131za Notu", "\\u0130\\u015flem Detay\\u0131", "Gizli Not"])' in desktop_editor
    assert 'super().__init__("H\\u0131zl\\u0131 Not Detay\\u0131"' in desktop_editor
    assert 'QLabel("H\\u0131zl\\u0131 Not\\u0131 D\\u00fczenle / Ekle")' in desktop_editor
    assert 'self.add_button("Kaydet"' in desktop_editor
    assert 'openDialog("H\\u0131zl\\u0131 Not Detay\\u0131",""' in editor
    assert 'class="quick-note-editor"' in editor
    assert 'dialog.classList.add("quick-note-editor-dialog")' in editor
    assert '<input name="label" value="${esc(row.label||\"\")}"' in editor
    assert '<textarea name="label"' not in editor
    assert 'list="quickNoteCategories"' in editor
    assert 'placeholder="\\u015eablon ba\\u015fl\\u0131\\u011f\\u0131..."' in editor
    assert 'name="is_active" type="checkbox"' in editor
    assert 'payload.is_active=fd.has("is_active")?1:0' in editor
    assert 'name="category" list="quickNoteCategories" required' not in editor
    assert 'name="title" required' not in editor
    assert 'name="label" required' not in editor
    assert 'name="display_order" type="number" min="0"' not in editor


def test_quick_note_filter_categories_are_derived_from_loaded_rows():
    app = APP.read_text(encoding="utf-8")
    loader_start = app.index("async function loadQuickNotes")
    loader_end = app.index("\n", loader_start)
    loader = app[loader_start:loader_end]

    assert 'const categories=[...new Set(data.rows.map(n=>String(n.display_category||n.category||"Genel")))]' in loader
    assert 'filter.innerHTML=`<option value="">T\\u00fcm Kategoriler</option>${categories.map(category=>`<option value="${esc(category)}">${esc(category)}</option>`).join("")}`' in loader
    assert 'filter.value=categories.includes(priorCategory)?priorCategory:""' in loader


def test_quick_notes_table_saves_inline_order_and_label_edits():
    app = APP.read_text(encoding="utf-8")
    loader = app[app.index("async function loadQuickNotes"):app.index("\n", app.index("async function loadQuickNotes"))]
    saver_start = app.index("async function saveQuickNoteInline")
    saver = app[saver_start:app.index("\nfunction showQuickNoteContext", saver_start)]
    css = (ROOT / "Web_Arayuzu" / "web" / "styles.css").read_text(encoding="utf-8")

    assert 'class="quick-note-inline-label"' in loader
    assert 'class="quick-note-inline-order"' in loader
    assert 'input.onchange=()=>saveQuickNoteInline(rows[+input.dataset.index],"label",input.value,input)' in loader
    assert 'input.onchange=()=>saveQuickNoteInline(rows[+input.dataset.index],"display_order",input.value,input)' in loader
    assert 'Number.parseInt(value,10)' in saver
    assert 'String(value).trim()' in saver
    assert 'await desktopWrite("fast_notes",{id:note.id,[field]:next,_action:"update"})' in saver
    assert '#quickNotesHost .quick-note-inline-label:focus' in css
