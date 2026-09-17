# -*- coding: utf-8 -*-

import json
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.database import Database
from src.utils.asistan_motoru import BulutAsistan
from src.utils.finance_manager import FinanceManager
from src.utils.path_helper import PathHelper


def load_wake_word():
    db_path = PathHelper.get_db_path("ayecpro.db")
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key='asistan_ozel_adi' LIMIT 1"
        ).fetchone()
        return (row[0] if row and row[0] else "asistan").strip()
    finally:
        conn.close()


def emit_for(assistant, phrase):
    captured = []

    def _capture(action, param):
        captured.append((action, param))

    assistant.tetik_sinyali.connect(_capture)
    try:
        assistant.komut_coz(phrase)
    finally:
        assistant.tetik_sinyali.disconnect(_capture)
    return captured


def check_db_dependencies(db):
    checks = []

    checks.append(("apply_stock_price_increase", callable(getattr(db, "apply_stock_price_increase", None))))
    checks.append(("check_critical_stock", callable(getattr(db, "check_critical_stock", None))))
    checks.append(("get_daily_appointments", callable(getattr(db, "get_daily_appointments", None))))
    checks.append(("get_customer_id_by_name", callable(getattr(db, "get_customer_id_by_name", None))))
    checks.append(("search_devices", callable(getattr(db, "search_devices", None))))
    checks.append(("add_reminder", callable(getattr(db, "add_reminder", None))))
    checks.append(("get_total_debt", callable(getattr(db, "get_total_debt", None))))
    checks.append(("get_discount_advice", callable(getattr(db, "get_discount_advice", None))))
    checks.append(("get_customer_loyalty_score", callable(getattr(db, "get_customer_loyalty_score", None))))

    try:
        summary = FinanceManager(db).get_financial_summary("month") or {}
        checks.append(("finance_manager_summary", bool(summary)))
    except Exception:
        checks.append(("finance_manager_summary", False))

    return checks


def _scenario_ok(emitted, expected_action, require_payload=False):
    if not emitted:
        return False
    action, payload = emitted[0]
    if action != expected_action:
        return False
    if require_payload and not str(payload or "").strip():
        return False
    return True


def main():
    wake_word = load_wake_word()
    assistant = BulutAsistan()
    db = Database(init_mode="full")

    scenarios = [
        {"phrase": f"{wake_word} finans özet", "expected_action": "accounting_summary"},
        {"phrase": f"{wake_word} kritik stokları listele", "expected_action": "list_critical_stock"},
        {"phrase": f"{wake_word} stoklara yüzde on zam yap", "expected_action": "apply_zam", "require_payload": True},
        {"phrase": "evet", "expected_action": "confirm_yes"},
        {"phrase": "iptal", "expected_action": "confirm_no"},
        {"phrase": f"{wake_word} yeni servis aç", "expected_action": "servis_ac"},
        {"phrase": f"{wake_word} bugünkü randevular", "expected_action": "check_appointments"},
        {"phrase": f"{wake_word} teknisyen paneli", "expected_action": "panel_ac"},
        {"phrase": f"{wake_word} stok özeti", "expected_action": "stock_summary"},
        {"phrase": f"{wake_word} yönetici özeti", "expected_action": "managerial_summary"},
        {"phrase": f"{wake_word} gelişmiş finansal özet", "expected_action": "financial_summary"},
        {"phrase": f"{wake_word} sezer ipek müşteri 360 aç", "expected_action": "customer_360", "require_payload": True},
        {"phrase": f"{wake_word} müşteri 360 sezer ipek", "expected_action": "customer_360", "require_payload": True},
        {"phrase": f"{wake_word} sezer ipek cihaz durumu sorgula", "expected_action": "device_status_query", "require_payload": True},
        {"phrase": f"{wake_word} sezer ipek için indirim tavsiyesi ver", "expected_action": "discount_advice", "require_payload": True},
        {"phrase": f"{wake_word} borç özeti", "expected_action": "loan_summary"},
        {"phrase": f"{wake_word} çek senet özeti", "expected_action": "check_summary"},
        {"phrase": f"{wake_word} laptop stok karşılaştırma yap", "expected_action": "stock_comparison", "require_payload": True},
        {"phrase": f"{wake_word} toplantı notu al yarın müşteriyi ara", "expected_action": "add_quick_note_voice", "require_payload": True},
        {"phrase": f"{wake_word} yarın saat 14:30 için ödeme hatırlatıcı ekle", "expected_action": "add_reminder_voice", "require_payload": True},
        {"phrase": f"{wake_word} gün kapanış özeti", "expected_action": "closing_routine"},
    ]

    results = {
        "wake_word": wake_word,
        "scenario_results": [],
        "db_dependency_results": [],
    }

    for item in scenarios:
        phrase = item["phrase"]
        expected = item["expected_action"]
        require_payload = bool(item.get("require_payload"))
        emitted = emit_for(assistant, phrase)
        matched = _scenario_ok(emitted, expected, require_payload=require_payload)
        results["scenario_results"].append(
            {
                "phrase": phrase,
                "expected_action": expected,
                "require_payload": require_payload,
                "emitted": emitted,
                "ok": matched,
            }
        )

    for name, ok in check_db_dependencies(db):
        results["db_dependency_results"].append({"name": name, "ok": ok})

    scenario_ok = all(item["ok"] for item in results["scenario_results"])
    db_ok = all(item["ok"] for item in results["db_dependency_results"])
    results["overall_ok"] = scenario_ok and db_ok

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
