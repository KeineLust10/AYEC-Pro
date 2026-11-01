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
    assert 'loadAllDesktopTableData("personnel", { include_deleted: 1 })' in source
    assert 'loadAllDesktopTableData("reminders", { q: query || "" })' in source


def test_reminder_delete_rejection_keeps_confirmation_open_for_retry():
    source = (ROOT / "Web_Arayuzu" / "web" / "reminders-reference.js").read_text(encoding="utf-8")
    start = source.index("async function deleteSelectedReminder()")
    block = source[start:source.index("\n  }", start)]
    assert 'await apiFetch("/api/desktop/table/reminders"' in block
    assert 'toast("Silinemedi: " + (error.message || ""), "error")' in block
    assert "return false" in block


def test_reminder_reload_clears_selection_before_fetching_rows():
    source = (ROOT / "Web_Arayuzu" / "web" / "reminders-reference.js").read_text(encoding="utf-8")
    start = source.index("loadGenericModule = async function (meta, query)")
    end = source.index('document.addEventListener("click"', start)
    block = source[start:end]
    assert block.index("selectedReminderId = null;") < block.index('loadAllDesktopTableData("reminders"')
    assert block.index("updateDeleteButton();") < block.index('loadAllDesktopTableData("reminders"')
    audit = (ROOT / "tools" / "quality" / "reminders_offscreen_audit.cjs").read_text(encoding="utf-8")
    assert "refreshFailureRetained" in audit
    assert "staleDeletePrevented" in audit
    assert 'limit=1000&offset=0&include_deleted=1' in audit


def test_reminder_tabs_use_roving_keyboard_navigation():
    source = (ROOT / "Web_Arayuzu" / "web" / "reminders-reference.js").read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "reminders_offscreen_audit.cjs").read_text(encoding="utf-8")

    assert 'aria-selected="true" tabindex="0" data-reminder-tab="add"' in source
    assert 'aria-selected="false" tabindex="-1" data-reminder-tab="list"' in source
    assert 'event.key === "ArrowRight"' in source
    assert 'event.key === "ArrowLeft"' in source
    assert 'event.key === "Home"' in source
    assert 'event.key === "End"' in source
    assert "setReminderTab(tabs[next].dataset.reminderTab, true)" in source
    assert "result.reminderTabKeyboard.rightWrap" in audit
    assert "result.reminderTabKeyboard.leftWrap" in audit


def test_offscreen_route_audit_covers_reminder_create_and_confirmed_delete():
    source = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert "result.reminderCrudWorkflow" in source
    assert 'workflow.title !== "QA Follow-up"' in source
    assert "workflow.deleteDialogOpen" in source
    assert "workflow.deleteCancelPreserved" in source
    assert "workflow.deleteAttempts !== 2" in source
    assert "workflow.deleteFailureRetained" in source
    assert "QA reminder delete unavailable" in source
    assert "workflow.deletedId" in source
