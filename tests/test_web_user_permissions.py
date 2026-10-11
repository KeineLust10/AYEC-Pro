from pathlib import Path
import json
import subprocess
from src.utils.user_permission_catalog import USER_PERMISSION_SECTIONS


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"


def test_web_permission_catalog_matches_desktop_catalog():
    source = APP.read_text(encoding="utf-8")
    start = source.index("const ayecUserPermissionSections")
    end = source.index("\nfunction normalizeUserPermissions(", start)
    script = source[start:end] + "\nprocess.stdout.write(JSON.stringify(ayecUserPermissionSections));"
    result = subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True, encoding="utf-8")
    expected = [[section, [[page_id, title] for page_id, title in items]] for section, items in USER_PERMISSION_SECTIONS]
    assert json.loads(result.stdout) == expected


def test_permission_normalizer_handles_invalid_values():
    source = APP.read_text(encoding="utf-8")
    start = source.index("function normalizeUserPermissions(")
    end = source.index("function userAdminRole(", start)
    function = source[start:end]
    script = function + """
const cases = [
  ["{\\\"pages\\\":[21]}", {pages: [21]}],
  ["null", null],
  ["[]", null],
  ["not-json", null]
];
for (const [value, expected] of cases) {
  const actual = normalizeUserPermissions(value);
  if (JSON.stringify(actual) !== JSON.stringify(expected)) process.exit(1);
}
"""
    subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)


def test_permission_parser_matches_desktop_saved_formats_and_role_defaults():
    source = APP.read_text(encoding="utf-8")
    catalog_start = source.index("const ayecUserPermissionSections")
    catalog_end = source.index("\nfunction renderUserPermissionMatrix(", catalog_start)
    catalog = source[catalog_start:catalog_end]
    script = catalog + """
const allIds = ayecUserPermissionSections.flatMap(([, items]) => items.map(([id]) => id));
const cases = [
  ["{\\\"mode\\\":\\\"all\\\"}", "user", allIds],
  ["{\\\"pages\\\":[21,999]}", "user", [21]],
  ["[21,50]", "user", [21,50]],
  ["{\\\"logs\\\":true}", "user", [135]],
  ["{\\\"logs\\\":false}", "user", []],
  ["{\\\"pages\\\":[21]}", "admin", allIds],
  ["null", "technician", [40,41,60,61,30,150,21,50,70]],
  ["null", "accounting", [40,21,101,135,130]],
  ["null", "admin", allIds],
  ["null", "root", [40,41,21,50]],
  ["{\\\"pages\\\":[21]}", "Firma Y\\u00f6neticisi", allIds]
];
for (const [value, role, expected] of cases) {
  const actual = [...userPermissionPages(value, role)].sort((a,b) => a-b);
  if (JSON.stringify(actual) !== JSON.stringify([...expected].sort((a,b) => a-b))) process.exit(1);
}
"""
    subprocess.run(["node", "-e", script], check=True, capture_output=True, text=True)
