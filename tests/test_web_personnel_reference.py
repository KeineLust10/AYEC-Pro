from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
CSS = ROOT / "Web_Arayuzu" / "web" / "midnight-reference.css"


def test_personnel_reference_reads_only_recorded_staff_and_payroll_fields():
    source = APP.read_text(encoding="utf-8")
    assert 'if (page !== "personnel" || meta?.table !== "personnel")' in source
    assert '/api/desktop/table/personnel?limit=500&q=' in source
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
