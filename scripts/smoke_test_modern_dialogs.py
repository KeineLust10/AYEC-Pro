# -*- coding: utf-8 -*-

import argparse
import importlib
import inspect
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from PyQt6.QtWidgets import QWidget


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "src"


DISCOVERY_PATTERN = re.compile(
    r"^class\s+(\w+)\(([^)]*(?:ModernDialog|BaseModernDialog)[^)]*)\):",
    re.MULTILINE,
)


def discover_dialogs():
    dialogs = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        module_name = ".".join(path.relative_to(ROOT).with_suffix("").parts)
        for match in DISCOVERY_PATTERN.finditer(text):
            dialogs.append(
                {
                    "module": module_name,
                    "class_name": match.group(1),
                    "path": str(path.relative_to(ROOT)),
                }
            )
    return dialogs


class NoOpCursor:
    def __init__(self):
        self._rows = []
        self._row = None

    def execute(self, sql, params=()):
        sql_lower = (sql or "").lower()
        if "sqlite_master" in sql_lower and "photos" in sql_lower:
            self._row = (1,)
            self._rows = [(1,)]
            return self
        if "pragma table_info(devices)" in sql_lower:
            self._rows = [
                (0, "id", "INTEGER", 0, None, 1),
                (1, "tracking_no", "TEXT", 0, None, 0),
                (2, "photo_paths", "TEXT", 0, None, 0),
            ]
            self._row = self._rows[0]
            return self
        self._rows = []
        self._row = None
        return self

    def fetchall(self):
        return list(self._rows)

    def fetchone(self):
        return self._row


class NoOpConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def commit(self):
        return None


class GenericDbStub:
    def __init__(self):
        self.cursor = NoOpCursor()
        self.conn = NoOpConnection(self.cursor)

    def get_setting(self, _key, default=""):
        return default

    def get_customers(self):
        return [(1, "Smoke Customer")]

    def get_all_personnel(self):
        return [(1, "Smoke Personnel")]

    def _get_table_columns(self, table):
        defaults = {
            "bank_accounts": [
                "id", "bank_name", "branch", "account_name", "account_no",
                "iban", "currency", "is_active", "created_at", "current_balance",
            ],
            "accounting": [
                "id", "date", "type", "category", "amount", "description",
                "bank_account_id", "currency", "try_equivalent",
            ],
        }
        return defaults.get(table, ["id", "name"])

    def get_fast_notes(self, category):
        if category == "Aksesuar":
            return [(1, category, "SIM Kart", 1), (2, category, "Şarj Aleti", 1)]
        if category == "Arıza Notu":
            return [(1, category, "EKRAN KIRIK", 1), (2, category, "ŞARJ ALMIYOR", 1)]
        return []

    def get_quick_notes(self, _key):
        return []

    def get_vehicle_history_snapshot(self, _plate):
        return [], []

    def get_parts_paginated(self, **_kwargs):
        return [], 0

    def add_customer(self, _data):
        return True

    def add_device(self, _data):
        return True

    def add_photo(self, *_args, **_kwargs):
        return True

    def get_next_service_number(self):
        return "SRV1001"

    def __getattr__(self, name):
        if name.startswith(("get_", "list_", "fetch_")):
            return lambda *args, **kwargs: []
        if name.startswith(("add_", "set_", "update_", "delete_", "save_")):
            return lambda *args, **kwargs: True
        if name.startswith("check_"):
            return lambda *args, **kwargs: False
        raise AttributeError(name)


class GenericWidgetStub(QWidget):
    def __init__(self):
        super().__init__()
        self.main_window = None
        self.db = GenericDbStub()
        self.products = []
        self.filtered_products = []
        self.selected_items = []
        self.data = {}
        self.current_scenario_name = ""

    main_window = None
    db = GenericDbStub()
    products = []
    filtered_products = []
    selected_items = []
    data = {}
    current_scenario_name = ""

    def _init_action_options(self, combo):
        combo.addItem("Smoke Action", {"type": "noop"})

    def _get_scenarios(self):
        return []

    def _save_scenarios(self, _scenarios):
        return True

    def refresh_products(self):
        return []

    def test_active_scenario(self):
        return None

    def add_scenario(self):
        name = "Smoke Scenario"
        self.data.setdefault(name, {"triggers": [], "action": None})
        self.current_scenario_name = name

    def delete_scenario_by_name(self, name):
        self.data.pop(name, None)

    def add_trigger_to_scenario(self, name, trigger):
        cfg = self.data.setdefault(name, {"triggers": [], "action": None})
        if trigger:
            cfg.setdefault("triggers", []).append(trigger)

    def delete_trigger_from_scenario(self, name, trigger):
        cfg = self.data.get(name, {})
        cfg["triggers"] = [item for item in cfg.get("triggers", []) if item != trigger]

    def set_scenario_action(self, name, payload, auto_search=False):
        cfg = self.data.setdefault(name, {"triggers": [], "action": None})
        cfg["action"] = payload
        cfg["auto_search"] = bool(auto_search)

    def _refresh_product_table(self, _query=""):
        self.filtered_products = list(self.products)

    def _append_product_to_offer(self, **_kwargs):
        return None

    def _refresh_selected_table(self):
        return None

    def _update_offer_badge(self):
        return None


def sample_bank_row():
    return (1, "Smoke Bank", "Smoke Branch", "Smoke Account", "0001", "TR000000000000000000000000", "TRY", 1, "2026-01-01", 1000.0)


def build_special_arg(class_name, name):
    samples = {
        "AutomotiveChecklistDialog": {
            "templates": {"servis_kabul": [{"name": "Fren Kontrolu", "required": True}]},
            "existing_data": {},
        },
        "CriticalAlertDialog": {
            "notifications": [{"title": "Smoke", "content": "Smoke alert", "message": "Smoke alert", "level": "critical"}],
        },
        "CustomerHistoryDialog": {
            "customer_name": "Smoke Customer",
            "history_data": [],
        },
        "OfferPreviewDialog": {
            "note_data": (1, "Not", "Smoke content", "2026-01-01"),
        },
        "EarlyClosureDialog": {
            "loan_data": {"principal": 1000, "remaining_balance": 800, "interest_rate": 1.5},
            "unpaid_installments": [{"amount": 100, "principal": 80, "interest": 20}],
        },
        "PartnerFinanceDialog": {
            "partner": {"id": 1, "name": "Smoke Partner"},
        },
        "PartnerShipmentDialog": {
            "partner": {"id": 1, "name": "Smoke Partner"},
        },
        "ReportDialog": {
            "device_data": (1, "SRV1001", "Smoke Customer", "Telefon", "Smoke Model"),
        },
        "ServiceImportPreviewDialog": {
            "parse_result": {
                "raw_rows": [{"service_name": "Smoke Service", "price": 100}],
                "detected_columns": ["service_name", "price"],
            },
        },
        "VehicleHistoryQrDialog": {
            "plate": "34ABC123",
        },
        "VehicleMaintenanceItemsDialog": {
            "service_date": "2026-01-01",
            "current_odometer": 10000,
            "items": [],
        },
        "EditBankAccountDialog": {
            "account_row": sample_bank_row(),
        },
        "AccountDetailDialog": {
            "account_row": sample_bank_row(),
        },
        "TransferDialog": {
            "from_account_row": sample_bank_row(),
            "all_accounts": [
                sample_bank_row(),
                (2, "Target Bank", "Target Branch", "Target Account", "0002", "TR000000000000000000000001", "TRY", 1, "2026-01-01", 0.0),
            ],
        },
        "UnitProductsDialog": {
            "project_id": 1,
            "unit": {"id": 1, "unit_no": "A1", "block_name": "A"},
        },
        "DeliveryPaymentDialog": {
            "context": {"tracking_no": "SRV1001", "customer_name": "Smoke Customer", "total_amount": 100},
        },
        "VoiceHealthcheckResultDialog": {
            "payload": {"ok": True, "checks": [], "summary": "Smoke"},
        },
        "VoiceScenarioEditorDialog": {
            "widget": GenericWidgetStub(),
        },
        "SmartHomeProductPoolDialog": {
            "parent_page": GenericWidgetStub(),
        },
        "ProformaDialog": {
            "cart_items": [{"name": "Smoke Product", "qty": 1, "price": 100}],
            "totals": {"subtotal": 100, "tax": 20, "total": 120},
            "customer_name": "Smoke Customer",
        },
        "MultiSelectServiceDialog": {
            "services_data": {"Smoke Service": {"price": 100, "description": "Smoke"}},
        },
        "BankDetailDialog": {
            "acc_data": sample_bank_row(),
        },
    }
    return samples.get(class_name, {}).get(name, None)


def build_arg(name, class_name=None):
    special = build_special_arg(class_name, name)
    if special is not None:
        return special
    lower = name.lower()
    if lower in {"db", "database"}:
        return GenericDbStub()
    if lower == "parent":
        return None
    if lower.endswith("_id") or lower in {"id", "amount", "total", "balance"}:
        return 1
    if lower in {"title", "message", "text", "label"}:
        return "Smoke"
    if lower in {"name", "customer_name", "username", "display_name"}:
        return "Smoke Customer"
    if lower in {"tracking_no", "service_no"}:
        return "SRV1001"
    if lower in {"phone"}:
        return "05550001122"
    if lower in {"email"}:
        return "smoke@example.com"
    if lower in {"address"}:
        return "Smoke Address"
    if "data" in lower or "record" in lower or "row" in lower or "item" in lower:
        return None
    if lower.startswith(("is_", "has_", "use_", "show_", "edit_")):
        return False
    return "Smoke"


def instantiate_dialog(module_name, class_name):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("AYECPRO_SAFE_UI", "1")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    module = importlib.import_module(module_name)
    dialog_cls = getattr(module, class_name)
    signature = inspect.signature(dialog_cls.__init__)
    kwargs = {}
    args = []

    for param in list(signature.parameters.values())[1:]:
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if param.default is not inspect._empty:
            continue
        value = build_arg(param.name, class_name)
        if param.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD):
            args.append(value)
        else:
            kwargs[param.name] = value

    dialog = dialog_cls(*args, **kwargs)
    dialog.show()
    app.processEvents()
    dialog.close()
    app.processEvents()
    dialog.deleteLater()
    app.processEvents()


def run_single(module_name, class_name):
    try:
        instantiate_dialog(module_name, class_name)
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}), flush=True)
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
    print(json.dumps({"ok": True}), flush=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0)


def run_all():
    results = []
    for dialog in discover_dialogs():
        cmd = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--single",
            dialog["module"],
            dialog["class_name"],
        ]
        try:
            completed = subprocess.run(
                cmd,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=12,
            )
            stdout = (completed.stdout or "").strip().splitlines()
            payload = {"ok": False, "error": "No result payload"}
            if stdout:
                try:
                    payload = json.loads(stdout[-1])
                except Exception:
                    payload = {"ok": False, "error": stdout[-1]}
            ok = completed.returncode == 0 and payload.get("ok") is True
            error = payload.get("error", "")
        except subprocess.TimeoutExpired:
            ok = False
            error = "Timeout (>12s)"
        results.append(
            {
                **dialog,
                "ok": ok,
                "error": error,
            }
        )

    passed = [r for r in results if r["ok"]]
    failed = [r for r in results if not r["ok"]]

    print(f"Modern dialog smoke test: {len(passed)}/{len(results)} passed")
    for item in failed:
        print(f"FAIL {item['module']}::{item['class_name']} -> {item['error']}")

    report_path = ROOT / "tests" / "modern_dialog_smoke_report.json"
    report_path.write_text(
        json.dumps(
            {
                "total": len(results),
                "passed": len(passed),
                "failed": len(failed),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Report: {report_path}")
    return 0 if not failed else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", nargs=2, metavar=("MODULE", "CLASS"))
    args = parser.parse_args()

    if args.single:
        return run_single(args.single[0], args.single[1])
    return run_all()


if __name__ == "__main__":
    raise SystemExit(main())
