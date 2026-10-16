"""AYEC Pro masaüstü ile web portu arasındaki statik kapsam farklarını raporlar."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT.parent
WEB_TEXT = "\n".join(
    path.read_text(encoding="utf-8", errors="ignore")
    for path in (ROOT / "web").glob("*.*")
)
WEB_TEXT = re.sub(
    r"\\u(?:\{([0-9a-fA-F]+)\}|([0-9a-fA-F]{4}))",
    lambda match: chr(int(match.group(1) or match.group(2), 16)),
    WEB_TEXT,
)


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
dynamic_setting_keys = sorted(key for key in desktop_setting_keys if "{" in key or "}" in key)
identity_module_keys = [
    "operations", "finance", "stock", "projects", "crm", "personnel", "asistan",
]
identity_feature_keys = [
    "wizard_upload", "iban_verify", "voice_alerts", "scheduled_alerts",
    "usage_guides", "right_click", "double_click",
]
sms_loop_keys = ["repaired", "approval", "parts", "testing", "done"]
identity_module_missing = [
    f"module_{key}_active" for key in identity_module_keys
    if f"module_{key}_active" not in WEB_TEXT
]
identity_feature_missing = [
    f"feature_{key}_active" for key in identity_feature_keys
    if f"feature_{key}_active" not in WEB_TEXT
]
sms_loop_template_supported = all(
    token in WEB_TEXT
    for token in ("`loop_active_${key}`", "`loop_${key}`", "`loop_template_${key}`")
)
sms_loop_stages_missing = [
    key for key in sms_loop_keys
    if f'["{key}"' not in WEB_TEXT
]
user_location_templates = {
    "template_supported": "`map_default_${suffix}_user_${locationUsername}`" in WEB_TEXT,
    "address": 'saveUserAddress("address"' in WEB_TEXT,
    "city": 'saveUserAddress("city"' in WEB_TEXT,
    "district": 'saveUserAddress("district"' in WEB_TEXT,
    "latitude": 'saveUserAddress("lat"' in WEB_TEXT,
    "longitude": 'saveUserAddress("lng"' in WEB_TEXT,
}
integration_tree = ast.parse(
    (DESKTOP / "src" / "ui" / "pages" / "settings_widgets" / "integration_hub.py").read_text(encoding="utf-8")
)
integration_tab_keys = []
for node in ast.walk(integration_tree):
    if isinstance(node, ast.Assign) and any(
        isinstance(target, ast.Name) and target.id == "tab_structure"
        for target in node.targets
    ):
        integration_tab_keys = [ast.literal_eval(item.elts[2]) for item in node.value.elts]
        break
integration_web_routes = {
    "gemini": "ai-settings",
    "autonomous_agents": "autonomous-agents",
    "voice_assistant": "voice-settings",
    "voice_training": "voice-command-settings",
    "voice_shortcuts": "voice-shortcuts",
    "sms": "sms-settings",
    "sms_templates": "sms-templates",
    "smtp": "smtp-settings",
    "telegram": "messaging",
    "whatsapp": "messaging",
}
integration_missing_routes = [
    {"desktop_tab": key, "web_route": integration_web_routes.get(key)}
    for key in integration_tab_keys
    if not integration_web_routes.get(key) or integration_web_routes[key] not in WEB_TEXT
]
runtime_only_setting_keys = {"last_login_user"}
internal_only_setting_keys = {"financial_defaults_revision"}
native_only_setting_keys = {
    "print_document_printer",
    "print_label_printer",
    "print_receipt_printer",
}
retired_setting_keys = {"backup_auto_morning", "backup_auto_evening"}

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
    "settings": {
        "desktop_keys": len(desktop_setting_keys),
        "web_keys": len(web_setting_keys),
        "runtime_only_keys": sorted(runtime_only_setting_keys & desktop_setting_keys),
        "internal_only_keys": sorted(internal_only_setting_keys & desktop_setting_keys),
        "native_only_keys": sorted(native_only_setting_keys & desktop_setting_keys),
        "retired_keys": sorted(retired_setting_keys & desktop_setting_keys),
        "dynamic_keys": dynamic_setting_keys,
        "dynamic_families": {
            "identity_modules": {"expected": len(identity_module_keys), "missing": identity_module_missing},
            "identity_features": {"expected": len(identity_feature_keys), "missing": identity_feature_missing},
            "sms_loops": {
                "expected": len(sms_loop_keys),
                "template_supported": sms_loop_template_supported,
                "missing_stages": sms_loop_stages_missing,
            },
            "user_location_fields": user_location_templates,
        },
        "missing_keys": sorted(
            key
            for key in desktop_setting_keys
            - web_setting_keys
            - runtime_only_setting_keys
            - internal_only_setting_keys
            - native_only_setting_keys
            - retired_setting_keys
            if "{" not in key and "}" not in key
        ),
    },
    "integration_tabs": {
        "desktop": len(integration_tab_keys),
        "missing_web_routes": integration_missing_routes,
    },
    "page_signals": {"desktop_connect_calls": desktop_connects},
    "mouse": {"desktop_context_pages": sorted(set(desktop_context_files)), "desktop_double_click_pages": sorted(set(desktop_double_files)), "web_context_engine": "contextmenu" in WEB_TEXT, "web_double_engine": "dblclick" in WEB_TEXT},
    "responsive": {"viewport_meta": "width=device-width" in WEB_TEXT, "mobile_breakpoint": "max-width:760px" in WEB_TEXT, "touch_long_press": "pointerdown" in WEB_TEXT and "pointerup" in WEB_TEXT},
    "sector": {"technical": "teknik_servis" in WEB_TEXT, "automotive": "otomotiv" in WEB_TEXT},
    "ocr": {"desktop_parser_endpoint": "StockImportParser" in (ROOT / "Main.py").read_text(encoding="utf-8"), "pdf": ".pdf" in WEB_TEXT, "image": "PaddleOCR" in WEB_TEXT},
}
print(json.dumps(report, ensure_ascii=False, indent=2))
