from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "midnight-reference.css"
CONTEXT = ROOT / "Web_Arayuzu" / "web" / "personnel-context-parity.js"


def test_personnel_reference_reads_only_recorded_staff_and_payroll_fields():
    source = APP.read_text(encoding="utf-8")
    assert 'if (page !== "personnel" || meta?.table !== "personnel")' in source
    assert 'apiFetch("/api/desktop/table/personnel?limit=1000&include_deleted=1")' in source
    assert 'Number(row.salary)' in source
    assert 'Number(row.commission)' in source
    assert 'GPS' not in source[source.index('let ayecPersonnelSelectedId'):]
    assert 'data-generic-add' in source[source.index('let ayecPersonnelSelectedId'):]


def test_personnel_reference_has_search_role_filter_profile_and_mobile_layout():
    source = APP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    assert 'id="genericSearch"' in source[source.index('let ayecPersonnelSelectedId'):]
    assert 'id="personnelRoleFilter"' in source
    assert 'id="personnelProfile"' in source
    assert 'personnel-ref-layout' in css
    assert '@media(max-width:700px){body[data-page="personnel"]' in css
    assert '@media print{body[data-page="personnel"]' in css


def test_personnel_desktop_context_actions_require_password_and_delete_linked_payroll():
    source = CONTEXT.read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    assert '["&#x1F4DD; D\\u00fczenle", "edit"]' in source
    assert '["&#x1F5D1;&#xFE0F; Personel \\u00c7\\u0131kar", "remove"]' in source
    assert '<hr class="context-menu-separator" role="separator">' in source
    assert 'type="password"' in source
    assert '"/api/desktop/personnel/delete"' in source
    route = backend[backend.index('if path == "/api/desktop/personnel/delete":'):]
    route = route[:route.index('if path == "/api/desktop/personnel/daily-wages/delete":')]
    assert 'password_matches(password, stored_password)' in route
    assert 'DELETE FROM personnel_daily_wages WHERE personnel_id=?' in route
    assert 'DELETE FROM accounting WHERE id IN' in route
    assert 'DELETE FROM personnel WHERE id=?' in route


def test_personnel_reference_covers_desktop_table_rail_and_field_expansion():
    source = APP.read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    personnel = source[source.index("let ayecPersonnelSelectedId"):]
    for token in (
        'id="personnelFieldsToggle"',
        'personnel-ref-ranking',
        'id="personnelProfile"',
        'data-personnel-open-payroll',
        'data-personnel-payroll-open',
        'G\\u00d6REV DURUMU',
        'COZULEN IS',
        'KAYITLI PRIM',
        'Birim Ucret',
        'const personnelFormatMoney = value =>',
    ):
        assert token in personnel
    assert 'personnel-ref-footer' in personnel
    assert 'personnel-ref-table.expanded .personnel-extra' in css
    assert 'personnel-ref-list .table-wrap{height:560px' in css


def test_personnel_table_column_order_matches_desktop():
    source = APP.read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "personnel_page.py").read_text(encoding="utf-8")
    assert '"TC No", "\\u00dccret Tipi", "Birim \\u00dccret",' in desktop
    assert '"KAYITLI PRIM", "G\\u00d6REV DURUMU", "COZULEN IS", "AKSIYON"' in desktop
    assert '<th class="personnel-extra">Ucret Tipi</th><th>Birim Ucret</th><th>KAYITLI PRIM</th><th>G\\u00d6REV DURUMU</th><th>COZULEN IS</th>' in source
    row_start = source.index('host.innerHTML = visible.map', source.index('const genericShellBeforePersonnel'))
    row_end = source.index('}).join("")', row_start)
    row_template = source[row_start:row_end]
    assert row_template.index('class="personnel-money"') < row_template.index('${task}') < row_template.index('<td>-</td>')


def test_personnel_fields_toggle_has_only_one_click_state_transition():
    source = APP.read_text(encoding="utf-8")
    assert 'document.addEventListener("click", event => {\n  const toggle = event.target.closest("#personnelFieldsToggle")' in source
    assert '$("#personnelFieldsToggle")?.addEventListener("click"' not in source


def test_personnel_search_and_role_filters_match_desktop_normalization():
    source = APP.read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "personnel_page.py").read_text(encoding="utf-8")
    assert 'const personnelFilterText = value => String(value ?? "").toLocaleLowerCase("tr-TR").normalize("NFKD")' in source
    assert 'apiFetch("/api/desktop/table/personnel?limit=1000&include_deleted=1")' in source
    assert 'const roles = ["Teknisyen", "Muhendis", "Idare"]' in source
    assert 'personnelFilterText(Object.values(row).join(" "))' in source
    assert 'query = normalize(self.personnel_search.text().strip())' in desktop
    assert 'visible = visible and normalize(role) in haystack' in desktop


def test_personnel_table_can_include_archived_rows_without_changing_other_tables():
    source = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    route = source[source.index('if path.startswith("/api/desktop/table/")'):]
    route = route[:route.index("if path.startswith(", 1)]
    assert 'include_deleted = table == "personnel" and query.get("include_deleted", ["0"])[0] == "1"' in route
    assert 'if "is_deleted" in columns and not include_deleted:' in route
