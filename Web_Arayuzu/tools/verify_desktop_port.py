"""Static and live coverage audit for the AYEC Pro desktop-to-web port."""

from __future__ import annotations

import ast
import json
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT.parent / "Masaustu"
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")


def literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


page_names = literal_assignment(DESKTOP / "src" / "utils" / "page_config.py", "PAGE_NAMES")
missing_pages = [label for label in page_names.values() if label not in APP]

manifest = json.loads((DESKTOP / "web_interface" / "static" / "dialogs.generated.json").read_text(encoding="utf-8"))
dialog_keys = [dialog["key"] for dialog in manifest["dialogs"]]
direct_dialogs = [
    "add_customer_dialog", "add_stock_dialog", "payment_dialog", "tahsilat_dialog",
    "new_service_dialog", "customer_360_dialog", "stock_smart_import_dialog", "technician_panel",
]
missing_direct = [key for key in direct_dialogs if key not in APP]

with urllib.request.urlopen("http://127.0.0.1:8501/api/desktop/health", timeout=3) as response:
    health = json.load(response)
with urllib.request.urlopen("http://127.0.0.1:8501/api/desktop/dialogs", timeout=3) as response:
    live_manifest = json.load(response)

report = {
    "ok": not missing_pages and not missing_direct and health.get("ok") is True,
    "desktop_pages": len(page_names),
    "web_page_labels_found": len(page_names) - len(missing_pages),
    "missing_page_labels": missing_pages,
    "desktop_dialogs": len(dialog_keys),
    "live_dialogs": live_manifest.get("summary", {}).get("dialog_count", 0),
    "desktop_signals": manifest.get("summary", {}).get("connection_count", 0),
    "critical_direct_dialogs": len(direct_dialogs) - len(missing_direct),
    "missing_critical_direct_dialogs": missing_direct,
    "database_tables": health.get("tables"),
}
print(json.dumps(report, ensure_ascii=False, indent=2))
raise SystemExit(0 if report["ok"] else 1)
