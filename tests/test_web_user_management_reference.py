from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "midnight-reference.css"


def test_user_management_view_uses_existing_user_and_permission_fields():
    source = APP.read_text(encoding="utf-8")
    start = source.index("let ayecSettingsUsers =")
    code = source[start:]
    assert '/api/desktop/table/users?limit=1000' in code
    for field in ("username", "full_name", "email", "role", "active", "last_login", "interface_edit_access"):
        assert f"selected.{field}" in code or f"user.{field}" in code
    assert "userPermissionPages(selected?.permissions, selected?.role)" in code
    assert 'settingsUserDialog(user)' in code
    assert 'id="settingsUsersHost"' not in code


def test_user_management_reference_has_search_profile_and_responsive_layout():
    source = APP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'id="settingsUsersSearch"' in source
    assert 'id="settingsUsersRole"' in source
    assert 'settings-users-profile' in source
    assert 'settings-users-metrics' in css
    assert 'settings-user-permission-group' in source
    assert 'settings-user-permission-group' in css
    assert 'data-user-permission' in source
    assert 'settings-user-edit-matrix' in source
    assert 'settings-user-edit-matrix' in css
    assert 'saved?.mode==="all"' in source
    assert 'JSON.stringify({mode:"all"})' in source
    assert 'JSON.stringify({pages:selected})' in source
    assert 'user.role].filter(Boolean)' in source
    assert 'roleChoices.map(r=>' in source
    assert 'userPermissionPages(value,role)' in source
    assert 'ayecUserPermissionSections' in source
    assert 'max-height:72vh;overflow:auto' in css
    assert '@media(max-width:700px){body[data-page="settings"]' in css
    assert '@media print{body[data-page="settings"]' in css


def test_user_table_rows_expose_the_desktop_edit_delete_context_menu():
    source = APP.read_text(encoding="utf-8")
    assert 'data-kind="settings-user" data-id="${esc(user.id)}"' in source
    assert 'if(kind==="settings-user")items=[[' in source
    assert '"settings-user-edit"' in source
    assert '"settings-user-delete"' in source
    assert 'apiFetch("/api/desktop/users/delete"' in source
