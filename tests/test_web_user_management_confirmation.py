from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_user_management_mutations_use_in_app_confirmation():
    source = (ROOT / "Web_Arayuzu" / "web" / "user-management-reference.js").read_text(encoding="utf-8")
    assert "window.confirm" not in source

    bulk_start = source.index("function ayecBulkPasswordsDialog()")
    bulk_end = source.index("function ayecAttachBulkPasswordAction()", bulk_start)
    bulk = source[bulk_start:bulk_end]
    assert "data-bulk-password-confirm" in bulk
    assert "dialogBody.append(prompt)" in bulk
    assert "event.target.matches(\"[data-bulk-password-user], [data-bulk-password-field]\")" in bulk
    assert 'if(!confirmation.checked)throw Error(' in bulk
    assert bulk.index("if(!confirmation.checked)") < bulk.index('apiFetch("/api/desktop/users/bulk-passwords"')

    delete_start = source.index("async function ayecDeleteManagedUser(userId)")
    delete_end = source.index("function ayecAttachUserDeleteAction()", delete_start)
    delete = source[delete_start:delete_end]
    assert "userAdminRole(currentAuthUser?.role)" in delete
    assert 'String(target.id)===String(currentAuthUser?.id)' in delete
    assert 'openDialog("Kullan\\u0131c\\u0131y\\u0131 Sil"' in delete
    assert '"/api/desktop/users/delete"' in delete
