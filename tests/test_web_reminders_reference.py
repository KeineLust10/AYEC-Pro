from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_reminder_delete_uses_shared_confirmation_dialog():
    source = (ROOT / "Web_Arayuzu" / "web" / "reminders-reference.js").read_text(encoding="utf-8")
    start = source.index("async function deleteSelectedReminder()")
    end = source.index("\n  }", start)
    block = source[start:end]

    assert "window.confirm" not in block
    assert 'openDialog("Hat\\u0131rlat\\u0131c\\u0131y\\u0131 Sil", "SILME ONAYI"' in block
    assert '"Evet, Sil"' in block
    assert 'textContent = "Hay\\u0131r"' in block
    assert 'JSON.stringify({ id: Number(selectedReminderId), _action: "delete" })' in block
    assert "return false;" in block
    assert 'data-reminder-delete disabled' not in source


def test_reminder_creation_preserves_selected_personnel_id_and_name():
    source = (ROOT / "Web_Arayuzu" / "web" / "reminders-reference.js").read_text(encoding="utf-8")
    start = source.index('var body = {', source.index('event.target.id !== "reminderCreateForm"'))
    end = source.index("};", start)
    body = source[start:end]

    assert 'personnel: personnelName(values.personnel) || ""' in body
    assert 'personnel_id: values.personnel ? Number(values.personnel) : null' in body


def test_reminder_personnel_options_include_archived_directory_entries():
    source = (ROOT / "Web_Arayuzu" / "web" / "reminders-reference.js").read_text(encoding="utf-8")
    assert 'apiFetch("/api/desktop/table/personnel?limit=500&include_deleted=1")' in source
