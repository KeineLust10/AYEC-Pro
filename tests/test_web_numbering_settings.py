from pathlib import Path
import json
import subprocess


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"


def test_numbering_settings_use_desktop_keys_and_export_controls():
    source = APP.read_text(encoding="utf-8")
    body_start = source.index("function numberingSettingsBody(){")
    body_end = source.index("\nfunction settingBody", body_start)
    body = source[body_start:body_end]

    assert 'settingsSection==="numbering"' in source
    assert 'data-setting-scope="settings"' in body
    for key in (
        "job_number_prefix",
        "job_number_next",
        "service_number_prefix",
        "service_number_next",
        "project_number_prefix",
        "project_number_next",
        "reference_number_prefix",
        "reference_number_next",
        "payment_number_prefix",
        "payment_number_next",
    ):
        assert key in body
    for action in ("copy", "csv", "excel", "print"):
        assert f'data-numbering-action="{action}"' in body
    assert 'id="setModuleValue"' not in body


def test_numbering_settings_render_five_prefix_and_sequence_pairs():
    source = APP.read_text(encoding="utf-8")
    start = source.index("function numberingSettingsBody(){")
    end = source.index("\nfunction settingBody", start)
    body = source[start:end]
    node_code = f"""
const vm = require('node:vm');
const exactSettingsField = (field, scope) => '<input class=\"exact-setting\" data-setting-scope=\"' + scope + '\" data-setting-key=\"' + field[0] + '\" value=\"' + field[3] + '\">';
const context = {{ exactSettingsField, desktopSettings: {{}}, esc: value => String(value) }};
vm.createContext(context);
vm.runInContext({json.dumps(body)}, context);
const html = context.numberingSettingsBody();
for (const key of ['job_number_prefix','job_number_next','service_number_prefix','service_number_next','project_number_prefix','project_number_next','reference_number_prefix','reference_number_next','payment_number_prefix','payment_number_next']) {{
  if (!html.includes('data-setting-key=\"' + key + '\"')) throw Error('missing setting field ' + key);
}}
for (const action of ['copy','csv','excel','print']) if (!html.includes('data-numbering-action=\"' + action + '\"')) throw Error('missing action ' + action);
"""
    subprocess.run(["node", "-e", node_code], check=True, capture_output=True, text=True)


def test_numbering_export_actions_escape_spreadsheet_formulas_and_validate_numbers():
    source = APP.read_text(encoding="utf-8")

    assert "function numberingSettingsSafeCell(value)" in source
    assert "return /^\\s*[=+\\-@]/.test(text)?\"'\"+text:text" in source
    assert "application/vnd.ms-excel;charset=utf-8" in source
    assert "if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(text)" in source
    assert "control.checkValidity()" in source
    assert "invalid.reportValidity()" in source


def test_numbering_export_helpers_build_safe_csv_and_excel_rows():
    source = APP.read_text(encoding="utf-8")
    start = source.index("function numberingSettingsRows(){")
    end = source.index('\ndocument.addEventListener("click",async event=>{', start)
    helpers = source[start:end]
    node_code = f"""
const vm = require('node:vm');
const values = {{ job_number_prefix: '=1+1', job_number_next: '7', service_number_prefix: 'SRV', service_number_next: '8', project_number_prefix: 'PRJ', project_number_next: '9', reference_number_prefix: 'REF', reference_number_next: '10', payment_number_prefix: 'PAY', payment_number_next: '11' }};
const document = {{ querySelector(selector) {{ const key = selector.match(/data-setting-key=\"([^\"]+)/)?.[1]; return key ? {{ value: values[key] }} : null; }} }};
const esc = value => String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('\"', '&quot;');
const context = {{ document, esc }};
vm.createContext(context);
vm.runInContext({json.dumps(helpers)}, context);
const rows = context.numberingSettingsRows();
const csv = context.numberingSettingsCsv(rows);
const excel = context.numberingSettingsExcel(rows);
if (rows.length !== 5 || rows[0][2] !== '7') throw Error('numbering rows mismatch');
if (!csv.startsWith('\\ufeff') || !csv.includes(\"\\\"'=1+1\\\"\")) throw Error('safe CSV content mismatch');
if (!excel.includes(\"'=1+1\") || !excel.includes('Sonraki Numara')) throw Error('Excel content mismatch');
"""
    subprocess.run(["node", "-e", node_code], check=True, capture_output=True, text=True)
