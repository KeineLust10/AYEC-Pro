from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_user_rows_have_desktop_edit_and_delete_context_actions():
    desktop = (ROOT / "src/ui/pages/settings_widgets/user_management.py").read_text(
        encoding="utf-8"
    )
    web = (ROOT / "Web_Arayuzu/web/user-management-reference.js").read_text(
        encoding="utf-8"
    )
    app = (ROOT / "Web_Arayuzu/web/app.js").read_text(encoding="utf-8")

    assert "action_edit = menu.addAction" in desktop
    assert "action_delete = menu.addAction" in desktop
    assert "\u270f\ufe0f D\u00fczenle" in desktop
    assert "\U0001f5d1\ufe0f Sil" in desktop
    assert 'data-kind="settings-user"' in app
    assert '"managed-user-edit"' in web
    assert '"managed-user-delete"' in web
    assert '\\u270f\\ufe0f D\\u00fczenle' in web
    assert '\\u{1f5d1}\\ufe0f Sil' in web
    assert 'settingsUserDialog(user)' in web
    assert 'ayecDeleteManagedUser(user.id)' in web
