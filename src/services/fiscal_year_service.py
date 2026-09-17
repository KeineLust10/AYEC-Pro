import logging
import os
import sqlite3
import json
from datetime import date, datetime

from src.utils.path_helper import PathHelper

logger = logging.getLogger(__name__)


class FiscalYearService:
    """
    Mali yil devir / sifirlama akislarini yoneten servis.

    Not:
    - Normal startup akisinda test tetikleyicisi otomatik kurulmaz.
    - Arsiv kopyasi yalniz planli devir/reset tarihinde devreye girer.
    - Test modu manuel olarak ayarlanmadikca destructive olmayan pasif izleme yapar.
    """

    TEST_FORCE_TODAY_KEY = "fiscal_test_force_today"
    TEST_MODE_KEY = "fiscal_test_mode"
    RESET_DATE_KEY = "fiscal_reset_date"
    ROLLOVER_DATE_KEY = "fiscal_rollover_date"
    LAST_CHECK_KEY = "fiscal_last_check_date"
    LAST_RESET_KEY = "fiscal_last_reset_date"
    LAST_ROLLOVER_KEY = "fiscal_last_rollover_date"
    LAST_ARCHIVE_KEY = "fiscal_last_archive_file"
    LAST_STATUS_KEY = "fiscal_last_status"
    LAST_REPORT_KEY = "fiscal_last_opening_report"
    YEAR_START_KEY = "fiscal_year_start"
    SAFE_COUNT_TABLES = {
        "accounting",
        "stock_movements",
        "devices",
        "customers",
        "bank_accounts",
    }
    OPENING_TAG = "[FISCAL_OPENING]"

    def __init__(self, main_window):
        self.main_window = main_window
        self.db = main_window.db

    def configure_today_test_trigger(self):
        today = self._today_iso()
        self.db.set_internal_setting(self.TEST_FORCE_TODAY_KEY, "1")
        self.db.set_internal_setting(self.TEST_MODE_KEY, "dry_run")
        self.db.set_internal_setting(self.RESET_DATE_KEY, today)
        self.db.set_internal_setting(self.ROLLOVER_DATE_KEY, today)
        self.db.set_internal_setting(self.LAST_RESET_KEY, "")
        self.db.set_internal_setting(self.LAST_ROLLOVER_KEY, "")
        self.db.set_internal_setting(self.LAST_STATUS_KEY, f"armed:{today}")
        logger.info("Fiscal year test trigger armed for today: %s", today)

    def run_startup_check(self):
        try:
            today = self._today_iso()
            self.ensure_next_cycle_dates()
            self.db.set_internal_setting(self.LAST_CHECK_KEY, today)

            rollover_date = self.db.get_internal_setting(self.ROLLOVER_DATE_KEY, "")
            reset_date = self.db.get_internal_setting(self.RESET_DATE_KEY, "")
            test_mode = self.db.get_internal_setting(self.TEST_MODE_KEY, "dry_run")

            if rollover_date == today:
                self._run_rollover(test_mode=test_mode)
            elif rollover_date and rollover_date < today:
                status = f"rollover_overdue:{rollover_date}:review_required"
                self.db.set_internal_setting(self.LAST_STATUS_KEY, status)
                self._notify("Mali yil devri gecikmis. Manuel inceleme gerekli.", "warning")
            if reset_date == today:
                self._run_reset(test_mode=test_mode)
        except Exception as e:
            logger.error("Fiscal year startup check error: %s", e, exc_info=True)

    def initialize_fiscal_year(self):
        try:
            self.ensure_next_cycle_dates()
            self._navigate_to_accounting()
        except Exception as e:
            logger.error("Fiscal year initialization error: %s", e)

    def ensure_next_cycle_dates(self):
        """Bir sonraki mali yil icin varsayilan tetik tarihlerini olusturur."""
        try:
            today = date.today()
            current_year_start = date(today.year, 1, 1).isoformat()
            next_year_start = date(today.year + 1, 1, 1).isoformat()
            rollover_date = self.db.get_internal_setting(self.ROLLOVER_DATE_KEY, "")
            reset_date = self.db.get_internal_setting(self.RESET_DATE_KEY, "")
            fiscal_year_start = self.db.get_internal_setting(self.YEAR_START_KEY, "")

            if not fiscal_year_start:
                self.db.set_internal_setting(
                    self.YEAR_START_KEY, current_year_start
                )
            else:
                try:
                    parsed_start = date.fromisoformat(str(fiscal_year_start))
                except Exception:
                    parsed_start = None
                if parsed_start is None or parsed_start > today:
                    logger.warning(
                        "Invalid future fiscal_year_start detected (%s). Resetting to %s.",
                        fiscal_year_start,
                        current_year_start,
                    )
                    self.db.set_internal_setting(self.YEAR_START_KEY, current_year_start)
            if not rollover_date:
                self.db.set_internal_setting(self.ROLLOVER_DATE_KEY, next_year_start)
            if not reset_date:
                self.db.set_internal_setting(self.RESET_DATE_KEY, next_year_start)
        except Exception as e:
            logger.error("Fiscal year cycle initialization error: %s", e)

    def get_status_snapshot(self):
        self.ensure_next_cycle_dates()
        return {
            "rollover_date": self.db.get_internal_setting(self.ROLLOVER_DATE_KEY, ""),
            "reset_date": self.db.get_internal_setting(self.RESET_DATE_KEY, ""),
            "last_check": self.db.get_internal_setting(self.LAST_CHECK_KEY, ""),
            "last_rollover": self.db.get_internal_setting(self.LAST_ROLLOVER_KEY, ""),
            "last_reset": self.db.get_internal_setting(self.LAST_RESET_KEY, ""),
            "last_archive": self.db.get_internal_setting(self.LAST_ARCHIVE_KEY, ""),
            "last_status": self.db.get_internal_setting(self.LAST_STATUS_KEY, ""),
            "test_mode": self.db.get_internal_setting(self.TEST_MODE_KEY, "dry_run"),
            "fiscal_year_start": self.db.get_internal_setting(self.YEAR_START_KEY, ""),
            "last_report": self.get_last_opening_report(),
        }

    def _normalize_rollover_selections(self, selections=None):
        supplied = selections if isinstance(selections, dict) else {}
        return {
            "bank": bool(supplied.get("bank", True)),
            "customer": bool(supplied.get("customer", True)),
        }

    def get_manual_rollover_plan(self, selections=None):
        """Return a read-only, auditable summary before a manual rollover."""
        selected = self._normalize_rollover_selections(selections)
        opening_date = self._resolve_manual_opening_date()
        integrity = "unknown"
        try:
            row = self.db.cursor.execute("PRAGMA integrity_check").fetchone()
            integrity = str(row[0]).lower() if row else "failed"
        except Exception as exc:
            integrity = f"failed:{exc}"

        entries = []
        if selected["bank"]:
            entries.extend(self._collect_bank_openings())
        if selected["customer"]:
            entries.extend(self._collect_customer_openings())
        bank_entries = [item for item in entries if item.get("bank_account_id")]
        customer_entries = [item for item in entries if item.get("customer_id")]
        return {
            "opening_date": opening_date.isoformat(),
            "can_execute": opening_date <= date.today() and integrity == "ok",
            "integrity": integrity,
            "selections": selected,
            "bank_count": len(bank_entries),
            "customer_count": len(customer_entries),
            "entry_count": len(entries),
            "total_try": round(
                sum(
                    self._to_try(item.get("amount"), item.get("currency"), item.get("exchange_rate"))
                    for item in entries
                ),
                2,
            ),
        }

    def trigger_manual_rollover(self, selections=None, approved_by=""):
        """
        Manuel mali yil devir akisi.
        Guvenli davranir: arsiv alir, acilis fislerini olusturur, durum kaydini yazar,
        sonraki yil tarihlerini kurar.
        """
        try:
            selected = self._normalize_rollover_selections(selections)
            today = self._today_iso()
            opening_date = self._resolve_manual_opening_date()
            if opening_date > date.today():
                return {
                    "ok": False,
                    "error": (
                        "Mali yil devri yeni yil baslamadan yapilamaz. "
                        f"En erken tarih: {opening_date.isoformat()}"
                    ),
                }
            plan = self.get_manual_rollover_plan(selected)
            if plan.get("integrity") != "ok":
                return {
                    "ok": False,
                    "error": "Veritabani tutarlilik kontrolu basarisiz. Devir baslatilmadi.",
                    "plan": plan,
                }
            archive_year = opening_date.year - 1
            archive_name = self.archive_old_data(archive_year)
            if not archive_name:
                return {
                    "ok": False,
                    "error": "Mali yil arsivi olusturulamadi. Acilis fisleri yazilmadi.",
                }

            recovered = self._opening_exists(opening_date)
            opening_summary = (
                {"count": 0, "skipped": True, "entries": [], "recovered": True}
                if recovered
                else self._create_opening_entries(opening_date, selected)
            )
            opening_summary["selections"] = selected
            opening_summary["approved_by"] = str(approved_by or "").strip()
            opening_error = (opening_summary or {}).get("error")
            status = (
                f"manual_rollover:{today}:archive={archive_name}:"
                f"openings={opening_summary.get('count', 0)}"
            )
            if recovered:
                status += ":recovered=1"
            if opening_error:
                status += ":opening_error=1"
                self.db.set_internal_setting(self.LAST_STATUS_KEY, status)
                return {
                    "ok": False,
                    "archive_name": archive_name,
                    "opening_summary": opening_summary,
                    "status": status,
                    "snapshot": self.get_status_snapshot(),
                    "error": opening_error,
                }

            self.db.set_internal_setting(self.YEAR_START_KEY, opening_date.isoformat())
            self.db.set_internal_setting(self.LAST_ROLLOVER_KEY, today)
            self._set_next_cycle_dates(opening_date.year + 1)
            self.db.set_internal_setting(self.LAST_STATUS_KEY, status)
            report = self._build_opening_report(
                opening_date, archive_name, opening_summary, selected, approved_by
            )
            notify_message = f"Manuel mali yil devir islemi tamamlandi. Arsiv: {archive_name}"
            self._notify(notify_message, "info")
            return {
                "ok": True,
                "archive_name": archive_name,
                "opening_summary": opening_summary,
                "report": report,
                "status": status,
                "snapshot": self.get_status_snapshot(),
            }
        except Exception as e:
            logger.error("Manual fiscal rollover error: %s", e, exc_info=True)
            return {"ok": False, "error": str(e)}

    def archive_old_data(self, year_to_archive):
        try:
            db_path = PathHelper.get_db_path("ayecpro.db")
            archive_name = f"archive_{year_to_archive}.db"
            archive_path = PathHelper.get_db_path(archive_name)

            if not os.path.exists(db_path):
                raise FileNotFoundError(db_path)

            src = sqlite3.connect(db_path)
            try:
                dst = sqlite3.connect(archive_path)
                try:
                    src.backup(dst)
                    dst.commit()
                finally:
                    dst.close()
            finally:
                src.close()

            verify = sqlite3.connect(archive_path)
            try:
                result = verify.execute("PRAGMA integrity_check").fetchone()
                if not result or str(result[0]).lower() != "ok":
                    raise RuntimeError("Archive integrity check failed")
            finally:
                verify.close()

            self.db.set_internal_setting(self.LAST_ARCHIVE_KEY, archive_name)
            logger.info("Fiscal archive created: %s", archive_path)
            return archive_name
        except Exception as e:
            logger.error("Archive error: %s", e, exc_info=True)
            return None

    def load_archive(self, archive_db_path):
        try:
            if hasattr(self.main_window, "load_archived_database"):
                result = self.main_window.load_archived_database(archive_db_path)
                if result:
                    self._navigate_to_accounting()
                return result
        except Exception as e:
            logger.error("Load archive error: %s", e)
        return False

    def _run_rollover(self, test_mode="dry_run"):
        today = self._today_iso()
        if self.db.get_internal_setting(self.LAST_ROLLOVER_KEY, "") == today:
            return

        opening_date = self._resolve_rollover_date()
        if opening_date < date.today():
            status = f"rollover_overdue:{opening_date.isoformat()}:review_required"
            self.db.set_internal_setting(self.LAST_STATUS_KEY, status)
            self._notify("Mali yil devri gecikmis. Manuel inceleme gerekli.", "warning")
            return
        if opening_date > date.today():
            logger.info(
                "Fiscal rollover skipped: planned date is in the future (%s)",
                opening_date.isoformat(),
            )
            return
        archive_name = self.archive_old_data(opening_date.year - 1)
        if not archive_name:
            self.db.set_internal_setting(
                self.LAST_STATUS_KEY, "rollover_archive_error:opening_not_written"
            )
            self._notify("Mali yil arsivi olusturulamadi. Devir durduruldu.", "warning")
            return
        if archive_name:
            opening_summary = self._create_opening_entries(opening_date)
            opening_error = (opening_summary or {}).get("error")
            if not opening_error:
                self.db.set_internal_setting(
                    self.YEAR_START_KEY, opening_date.isoformat()
                )
                self.db.set_internal_setting(self.LAST_ROLLOVER_KEY, today)
                self._set_next_cycle_dates(opening_date.year + 1)
                self._build_opening_report(opening_date, archive_name, opening_summary)
            self.db.set_internal_setting(
                self.LAST_STATUS_KEY,
                (
                    f"rollover:{today}:mode={test_mode}:archive={archive_name}:"
                    f"openings={opening_summary.get('count', 0)}"
                    f"{':opening_error=1' if opening_error else ''}"
                ),
            )
            self._notify(
                (
                    f"Mali yil devir testi tetiklendi. Arsiv: {archive_name}"
                    + (f" | Acilis hatasi: {opening_error}" if opening_error else "")
                ),
                "warning" if opening_error else "info",
            )

    def _run_reset(self, test_mode="dry_run"):
        today = self._today_iso()
        if self.db.get_internal_setting(self.LAST_RESET_KEY, "") == today:
            return

        if test_mode == "live":
            status = self._perform_live_reset()
        else:
            status = self._perform_dry_run_reset()

        self.db.set_internal_setting(self.LAST_RESET_KEY, today)
        self.db.set_internal_setting(self.LAST_STATUS_KEY, status)
        self._notify(
            "Mali yil sifirlama testi bugun icin tetiklendi. Detay loglara yazildi.",
            "info",
        )

    def _perform_dry_run_reset(self):
        counts = {}
        for table in (
            "accounting",
            "stock_movements",
            "devices",
            "customers",
            "bank_accounts",
        ):
            counts[table] = self._safe_count(table)
        status = "reset_dry_run:" + ",".join(f"{k}={v}" for k, v in counts.items())
        logger.info("Fiscal reset dry-run completed: %s", status)
        return status

    def _perform_live_reset(self):
        """
        Canli mod su an kontrollu olarak sadece durum kaydi olusturur.
        Gercek veri silme / tasima burada daha sonra acilabilir.
        """
        status = "reset_live_guarded:no_destructive_action"
        logger.warning("Fiscal reset live mode requested but guarded: %s", status)
        return status

    def _safe_count(self, table_name):
        try:
            if table_name not in self.SAFE_COUNT_TABLES:
                return -1
            self.db.cursor.execute(
                "SELECT COUNT(*) FROM {table_name}".format(table_name=table_name)
            )
            row = self.db.cursor.fetchone()
            return int(row[0]) if row else 0
        except Exception as e:
            logger.debug("Fiscal count skipped for %s: %s", table_name, e)
            return -1

    def _today_iso(self):
        forced = self.db.get_internal_setting(self.TEST_FORCE_TODAY_KEY, "0") == "1"
        current = date.today().isoformat()
        return current if forced else current

    def _parse_iso_date(self, value):
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except Exception:
            return None

    def _resolve_rollover_date(self):
        configured = self._parse_iso_date(
            self.db.get_internal_setting(self.ROLLOVER_DATE_KEY, "")
        )
        today = date.today()
        current_year_start = date(today.year, 1, 1)
        if configured:
            if configured > today:
                last_status = str(
                    self.db.get_internal_setting(self.LAST_STATUS_KEY, "") or ""
                )
                if "opening_error=1" in last_status:
                    logger.warning(
                        "Fiscal rollover date self-healed from future value %s to %s after opening error",
                        configured.isoformat(),
                        current_year_start.isoformat(),
                    )
                    return current_year_start
            return configured
        return current_year_start

    def _set_next_cycle_dates(self, year_value):
        next_year_start = date(int(year_value), 1, 1).isoformat()
        self.db.set_internal_setting(self.ROLLOVER_DATE_KEY, next_year_start)
        self.db.set_internal_setting(self.RESET_DATE_KEY, next_year_start)

    def _resolve_active_fiscal_year_start(self):
        configured = self._parse_iso_date(
            self.db.get_internal_setting(self.YEAR_START_KEY, "")
        )
        today = date.today()
        current_year_start = date(today.year, 1, 1)
        if configured and configured <= today:
            return date(configured.year, 1, 1)
        return current_year_start

    def _resolve_manual_opening_date(self):
        active_year_start = self._resolve_active_fiscal_year_start()
        return date(active_year_start.year + 1, 1, 1)

    def _accounting_has_column(self, name):
        try:
            cols = (
                self.db._get_table_columns("accounting")
                if hasattr(self.db, "_get_table_columns")
                else []
            )
            return name in set(cols or [])
        except Exception:
            return False

    def _bank_has_column(self, name):
        try:
            cols = (
                self.db._get_table_columns("bank_accounts")
                if hasattr(self.db, "_get_table_columns")
                else []
            )
            return name in set(cols or [])
        except Exception:
            return False

    def _currency_tx_has_column(self, name):
        try:
            cols = (
                self.db._get_table_columns("currency_transactions")
                if hasattr(self.db, "_get_table_columns")
                else []
            )
            return name in set(cols or [])
        except Exception:
            return False

    def _customers_has_column(self, name):
        try:
            cols = (
                self.db._get_table_columns("customers")
                if hasattr(self.db, "_get_table_columns")
                else []
            )
            return name in set(cols or [])
        except Exception:
            return False

    def _to_try(self, amount, currency, rate):
        try:
            amount = float(amount or 0)
            currency = str(currency or "TRY").upper()
            rate = float(rate or 1.0) or 1.0
            return round(amount if currency == "TRY" else amount * rate, 2)
        except Exception:
            return 0.0

    def _collect_bank_openings(self):
        balance_col = "current_balance"
        bank_name_col = "bank_name" if self._bank_has_column("bank_name") else None
        account_name_col = None
        if self._bank_has_column("account_name"):
            account_name_col = "account_name"
        elif self._bank_has_column("account_holder"):
            account_name_col = "account_holder"
        currency_col = "currency" if self._bank_has_column("currency") else None
        is_deleted_col = "is_deleted" if self._bank_has_column("is_deleted") else None
        if not self._bank_has_column(balance_col):
            return []
        where_clause = (
            f"WHERE COALESCE({is_deleted_col}, 0) = 0" if is_deleted_col else ""
        )
        select_bank_name = f"COALESCE({bank_name_col}, '')" if bank_name_col else "''"
        select_account_name = (
            f"COALESCE({account_name_col}, '')" if account_name_col else "''"
        )
        select_currency = (
            f", UPPER(COALESCE({currency_col}, 'TRY'))" if currency_col else ", 'TRY'"
        )
        rows = self.db.cursor.execute(
            f"""
            SELECT id, {select_bank_name}, {select_account_name}, COALESCE({balance_col}, 0){select_currency}
            FROM bank_accounts
            {where_clause}
            """
        ).fetchall()
        entries = []
        for account_id, bank_name, account_name, balance, currency in rows:
            amount = float(balance or 0)
            if abs(amount) < 0.0001:
                continue
            entries.append(
                {
                    "type": "Acilis",
                    "category": "Banka Devir Bakiyesi",
                    "amount": abs(amount),
                    "currency": str(currency or "TRY").upper(),
                    "exchange_rate": 1.0,
                    "description": (
                        f"{self.OPENING_TAG} Banka devri | {bank_name or 'Banka'} | {account_name or '-'} | "
                        f"{'Pozitif' if amount >= 0 else 'Negatif'} bakiye"
                    ),
                    "bank_account_id": account_id,
                }
            )
        return entries

    def _collect_customer_openings(self):
        if not hasattr(self.db, "_get_table_columns"):
            return []

        balance_cols = set(
            self.db._get_table_columns("customer_currency_balances") or []
        )
        customer_cols = set(self.db._get_table_columns("customers") or [])
        if not {"customer_id", "currency", "balance"}.issubset(balance_cols):
            return []

        customer_name_expr = "''"
        if "name" in customer_cols:
            customer_name_expr = "COALESCE(c.name, '')"

        rows = self.db.cursor.execute(
            f"""
            SELECT b.customer_id,
                   {customer_name_expr},
                   UPPER(COALESCE(b.currency, 'TRY')),
                   COALESCE(b.balance, 0),
                   1.0
            FROM customer_currency_balances b
            LEFT JOIN customers c ON c.id = b.customer_id
            WHERE ABS(COALESCE(b.balance, 0)) > 0.0001
            """
        ).fetchall()
        entries = []
        for customer_id, customer_name, currency, current_balance, rate in rows:
            bal = float(current_balance or 0)
            if abs(bal) < 0.0001:
                continue
            balance_type = "Bekleyen Alacak Devri" if bal < 0 else "Musteri Avans Devri"
            entries.append(
                {
                    "type": "Acilis",
                    "category": "Cari Devir Bakiyesi",
                    "amount": abs(bal),
                    "currency": str(currency or "TRY").upper(),
                    "exchange_rate": float(rate or 1.0) or 1.0,
                    "customer_id": customer_id,
                    "customer_name": customer_name,
                    "description": f"{self.OPENING_TAG} {balance_type} | {customer_name}",
                }
            )
        return entries

    def _opening_exists(self, opening_date):
        row = self.db.cursor.execute(
            """
            SELECT COUNT(*)
            FROM accounting
            WHERE date = ?
              AND description LIKE ?
            """,
            (opening_date.isoformat(), f"{self.OPENING_TAG}%"),
        ).fetchone()
        return bool(row and int(row[0] or 0) > 0)

    def _create_opening_entries(self, opening_date, selections=None):
        try:
            if self._opening_exists(opening_date):
                return {"count": 0, "skipped": True, "entries": []}
            selected = self._normalize_rollover_selections(selections)
            entries = []
            if selected["bank"]:
                entries.extend(self._collect_bank_openings())
            if selected["customer"]:
                entries.extend(self._collect_customer_openings())
            if not entries:
                return {"count": 0, "skipped": False, "entries": []}
            has_created_at = self._accounting_has_column("created_at")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            count = 0
            for entry in entries:
                columns = [
                    "date",
                    "type",
                    "category",
                    "amount",
                    "currency",
                    "exchange_rate",
                    "try_equivalent",
                    "original_amount",
                    "description",
                ]
                values = [
                    opening_date.isoformat(),
                    entry["type"],
                    entry["category"],
                    entry["amount"],
                    entry["currency"],
                    entry["exchange_rate"],
                    self._to_try(
                        entry["amount"], entry["currency"], entry["exchange_rate"]
                    ),
                    entry["amount"],
                    entry["description"],
                ]
                if has_created_at:
                    columns.append("created_at")
                    values.append(created_at)
                for opt_col in ("customer_id", "customer_name", "bank_account_id"):
                    if opt_col in entry and self._accounting_has_column(opt_col):
                        columns.append(opt_col)
                        values.append(entry[opt_col])
                if self._accounting_has_column("selected_services"):
                    columns.append("selected_services")
                    values.append(
                        json.dumps({"kind": "fiscal_opening"}, ensure_ascii=False)
                    )
                placeholders = ", ".join(["?"] * len(columns))
                col_list = ", ".join(self.db._safe_identifier(col) for col in columns)
                self.db.cursor.execute(
                    f"INSERT INTO accounting ({col_list}) VALUES ({placeholders})",
                    tuple(values),
                )
                count += 1
            self.db.conn.commit()
            return {"count": count, "skipped": False, "entries": entries}
        except Exception as e:
            logger.error("Opening entries error: %s", e, exc_info=True)
            try:
                self.db.conn.rollback()
            except Exception:
                pass
            return {"count": 0, "skipped": False, "error": str(e), "entries": []}

    def _build_opening_report(
        self, opening_date, archive_name, opening_summary, selections=None, approved_by=""
    ):
        entries = list((opening_summary or {}).get("entries") or [])
        report = {
            "opening_date": opening_date.isoformat(),
            "archive_name": archive_name or "",
            "opening_count": int((opening_summary or {}).get("count", 0) or 0),
            "bank_count": 0,
            "bank_total_try": 0.0,
            "customer_count": 0,
            "receivable_total_try": 0.0,
            "advance_total_try": 0.0,
            "next_rollover_date": self.db.get_internal_setting(
                self.ROLLOVER_DATE_KEY, ""
            ),
            "fiscal_year_start": self.db.get_internal_setting(self.YEAR_START_KEY, ""),
            "selections": self._normalize_rollover_selections(selections),
            "approved_by": str(approved_by or "").strip(),
            "approved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        for entry in entries:
            amount_try = self._to_try(
                entry.get("amount"),
                entry.get("currency"),
                entry.get("exchange_rate"),
            )
            category = str(entry.get("category") or "").strip().lower()
            description = str(entry.get("description") or "").strip().lower()
            if "banka devir" in category:
                report["bank_count"] += 1
                report["bank_total_try"] += amount_try
            elif "cari devir" in category:
                report["customer_count"] += 1
                if "bekleyen alacak" in description:
                    report["receivable_total_try"] += amount_try
                else:
                    report["advance_total_try"] += amount_try
        for key in ("bank_total_try", "receivable_total_try", "advance_total_try"):
            report[key] = round(float(report[key] or 0), 2)
        try:
            self.db.set_internal_setting(
                self.LAST_REPORT_KEY,
                json.dumps(report, ensure_ascii=False),
            )
        except Exception as e:
            logger.error("Opening report persist error: %s", e, exc_info=True)
        return report

    def get_last_opening_report(self):
        raw = self.db.get_internal_setting(self.LAST_REPORT_KEY, "")
        if not raw:
            return {}
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _notify(self, message, n_type="info"):
        try:
            if hasattr(self.main_window, "show_notification"):
                self.main_window.show_notification(message, n_type)
        except Exception as e:
            logger.debug("Fiscal notification skipped: %s", e)

    def _navigate_to_accounting(self):
        try:
            if hasattr(self.main_window, "on_menu_click"):
                self.main_window.on_menu_click(101)
        except Exception as e:
            logger.error("Navigation to accounting error: %s", e)
