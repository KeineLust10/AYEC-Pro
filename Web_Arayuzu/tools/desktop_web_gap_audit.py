"""AYEC Pro masaüstü ile web portu arasındaki statik kapsam farklarını raporlar."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT.parent
WEB_TEXT = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in (ROOT / "web").glob("*.*"))


def literal_assignment(path: Path, name: str):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


page_names = literal_assignment(DESKTOP / "src" / "utils" / "page_config.py", "PAGE_NAMES")
manifest = json.loads((ROOT / "web" / "dialogs.generated.json").read_text(encoding="utf-8"))

settings_files = list((DESKTOP / "src" / "ui" / "pages" / "settings_widgets").glob("*.py"))
settings_files += [DESKTOP / "src" / "ui" / "pages" / "security_settings_widget.py"]
setting_pattern = re.compile(r"(?:get|set)_(?:internal_)?setting\(\s*[fr]?['\"]([^'\"]+)")
desktop_setting_keys = set()
for path in settings_files:
    desktop_setting_keys.update(setting_pattern.findall(path.read_text(encoding="utf-8", errors="ignore")))
web_setting_keys = {key for key in desktop_setting_keys if key in WEB_TEXT}
runtime_only_setting_keys = {"last_login_user"}

page_files = list((DESKTOP / "src" / "ui" / "pages").rglob("*.py"))
desktop_connects = 0
desktop_context_files = []
desktop_double_files = []
for path in page_files:
    text = path.read_text(encoding="utf-8", errors="ignore")
    desktop_connects += len(re.findall(r"\.connect\s*\(", text))
    if "customContextMenuRequested" in text or "contextMenuEvent" in text:
        desktop_context_files.append(path.name)
    if "doubleClicked" in text or "mouseDoubleClickEvent" in text:
        desktop_double_files.append(path.name)

report = {
    "pages": {"desktop": len(page_names), "web_labels": sum(name in WEB_TEXT for name in page_names.values()), "missing": [name for name in page_names.values() if name not in WEB_TEXT]},
    "dialogs": {"desktop": manifest["summary"]["dialog_count"], "web_catalog": "dialog-catalog" in WEB_TEXT, "signals": manifest["summary"]["connection_count"]},
    "settings": {"desktop_keys": len(desktop_setting_keys), "web_keys": len(web_setting_keys), "runtime_only_keys": sorted(runtime_only_setting_keys & desktop_setting_keys), "missing_keys": sorted(key for key in desktop_setting_keys - web_setting_keys - runtime_only_setting_keys if "{" not in key and "}" not in key)},
    "page_signals": {"desktop_connect_calls": desktop_connects},
    "mouse": {"desktop_context_pages": sorted(set(desktop_context_files)), "desktop_double_click_pages": sorted(set(desktop_double_files)), "web_context_engine": "contextmenu" in WEB_TEXT, "web_double_engine": "dblclick" in WEB_TEXT},
    "responsive": {"viewport_meta": "width=device-width" in WEB_TEXT, "mobile_breakpoint": "max-width:760px" in WEB_TEXT, "touch_long_press": "pointerdown" in WEB_TEXT and "pointerup" in WEB_TEXT},
    "sector": {"technical": "teknik_servis" in WEB_TEXT, "automotive": "otomotiv" in WEB_TEXT},
    "ocr": {"desktop_parser_endpoint": "StockImportParser" in (ROOT / "Main.py").read_text(encoding="utf-8"), "pdf": ".pdf" in WEB_TEXT, "image": "PaddleOCR" in WEB_TEXT},
}
print(json.dumps(report, ensure_ascii=False, indent=2))
