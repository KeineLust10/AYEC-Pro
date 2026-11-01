from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "midnight-reference.css"


def test_user_management_view_uses_existing_user_and_permission_fields():
    source = APP.read_text(encoding="utf-8")
    start = source.index("let ayecSettingsUsers =")
    code = source[start:]
    assert 'loadAllDesktopTableRows("users")' in code
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


def test_user_management_role_filter_normalizes_desktop_role_aliases():
    source = APP.read_text(encoding="utf-8")
    assert 'userManagementRoleLabel(user.role)' in source
    assert 'yonetici:"Admin"' in source
    assert 'teknisyen:"Teknisyen"' in source
    assert 'sales:"Sat\\u0131\\u015f"' in source


def test_user_search_exposes_and_matches_assigned_personnel_name():
    source = APP.read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    assert 'item["personnel_name"] = personnel_names.get(str(item.get("personnel_id")), "")' in backend
    assert '[user.username, user.full_name, user.email, user.personnel_name, user.role].join(" ")' in source


def test_user_profile_supports_desktop_personnel_detail_and_access_toggle():
    source = APP.read_text(encoding="utf-8")
    assert 'data-settings-user-toggle-active="${esc(selected.id)}"' in source
    assert 'Atanan personel</dt><dd>${esc(selected.personnel_name || "Atanmad' in source
    assert 'active: Number(user.active ?? 1) !== 0 ? 0 : 1' in source
    assert 'self.detail_active_button.clicked.connect(self._toggle_selected_user_active)' in (ROOT / "src" / "ui" / "pages" / "settings_widgets" / "user_management.py").read_text(encoding="utf-8")


def test_managed_user_personnel_picker_loads_every_table_page():
    source = (ROOT / "Web_Arayuzu" / "web" / "user-management-reference.js").read_text(encoding="utf-8")
    assert "async function loadAllManagedTableRows(table)" in source
    assert 'personnel=await loadAllManagedTableRows("personnel")' in source
    assert "offset<Number(first.count||0)" in source



def test_user_metrics_match_desktop_telemetry_contract():
    source = APP.read_text(encoding="utf-8")
    start = source.index("  const metrics = `<section class=\"settings-users-metrics\">")
    end = source.index("`;", start)
    metrics = source[start:end]
    assert "TOPLAM KULLANICI" in metrics
    assert "ROL DA\\u011eILIMI" in metrics
    assert "CANLI OTURUMLAR" in metrics
    assert "G\\u00dcVENL\\u0130K SKORU" in metrics
    assert "<strong>-</strong>" in metrics
    desktop = (ROOT / "src" / "ui" / "pages" / "settings_widgets" / "user_management.py").read_text(encoding="utf-8")
    assert "Oturum telemetrisi yok" in desktop
    assert "Guvenlik olcumu yok" in desktop



def test_user_table_matches_desktop_columns_and_normalized_roles():
    source = APP.read_text(encoding="utf-8")
    assert "<th>KULLANICI</th><th>ROL</th><th>PERSONEL</th><th>DURUM</th><th></th>" in source
    assert 'esc(userManagementRoleLabel(user.role) || "Personel")' in source
    assert 'esc(userManagementRoleLabel(selected.role) || "Personel")' in source
    assert 'esc(user.personnel_name || "-")' in source
    assert 'esc(selected.personnel_name || "Atanmad' in source
    desktop = (ROOT / "src" / "ui" / "pages" / "settings_widgets" / "user_management.py").read_text(encoding="utf-8")
    assert "self.table.setColumnCount(9)" in desktop
    assert "normalize_role(user[2] or \"Personel\")" in desktop
    assert "for hidden_column in (0, 4, 6, 7, 8)" in desktop
