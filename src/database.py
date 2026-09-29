# -*- coding: utf-8 -*-

try:
    from pysqlcipher3 import dbapi2 as sqlite3
    SQLCIPHER_AVAILABLE = True
except Exception:
    import sqlite3
    SQLCIPHER_AVAILABLE = False
import hashlib
from datetime import datetime, timedelta
import os
import shutil
import json
import threading
from src.utils.logger import logger

# Modular mixins - ALL 16 categories
from src.db.mixins import (
    SettingsMixin,
    BankMixin,
    RemindersMixin,
    SupportMixin,
    PersonnelMixin,
    AppointmentsMixin,
    ServicesMixin,
    CustomerMixin,
    AccountingMixin,
    DeviceMixin,
    StockMixin,
    StockLocationMixin,
    LoggingMixin,
    SecurityMixin,
    SchemaMixin,
    ReportsMixin,
    FinanceMixin,
    ProjectMixin,
    LabelMixin,
    NotificationMixin,
    ProductBankMappingMixin,
    MaintenanceMixin,
)
from src.db.mixins.currency_mixin import CurrencyMixin
from src.db.migrations import MigrationManager
from src.utils.path_helper import PathHelper
from src.db.mixins.database_legacy_part1_mixin import DatabaseLegacyPart1Mixin
from src.db.mixins.database_legacy_part2_mixin import DatabaseLegacyPart2Mixin
from src.db.mixins.database_legacy_part3_mixin import DatabaseLegacyPart3Mixin
from src.db.mixins.database_legacy_part4_mixin import DatabaseLegacyPart4Mixin
from src.db.mixins.database_legacy_part5_mixin import DatabaseLegacyPart5Mixin
from src.db.mixins.database_legacy_part6_mixin import DatabaseLegacyPart6Mixin

# Logging is now handled by src.utils.logger


class Database(
    SettingsMixin,
    BankMixin,
    RemindersMixin,
    SupportMixin,
    PersonnelMixin,
    AppointmentsMixin,
    ServicesMixin,
    CustomerMixin,
    AccountingMixin,
    DeviceMixin,
    StockMixin,
    StockLocationMixin,
    LoggingMixin,
    SecurityMixin,
    SchemaMixin,
    ReportsMixin,
    CurrencyMixin,
    FinanceMixin,
    ProjectMixin,
    LabelMixin,
    NotificationMixin,
    ProductBankMappingMixin,
    MaintenanceMixin,
    DatabaseLegacyPart1Mixin,
    DatabaseLegacyPart2Mixin,
    DatabaseLegacyPart3Mixin,
    DatabaseLegacyPart4Mixin,
    DatabaseLegacyPart5Mixin,
    DatabaseLegacyPart6Mixin,
):
    CURRENT_SCHEMA_VERSION = 17
    VALID_INIT_MODES = {"auth", "full", "connection_only"}

    def __init__(self, db_name="ayecpro.db", init_mode="full"):
        self._db_name = db_name or "ayecpro.db"
        self._init_mode = (init_mode or "full").strip().lower()
        if self._init_mode not in self.VALID_INIT_MODES:
            raise ValueError(f"Unsupported database init mode: {self._init_mode}")
        self._full_initialized = False
        self._local = threading.local()
        self._local.conn = None
        self._local.cursor = None
        self._is_closed = False
        self.lock = threading.RLock()

        # Migrate data from local root to AppData if necessary
        PathHelper.migrate_if_needed(db_name)

        self._open_connection()

        if self._init_mode == "auth":
            self._initialize_auth_schema()
        elif self._init_mode == "full":
            self._initialize_full_schema()

        if self._init_mode != "connection_only":
            try:
                from src.utils.currency_helper import CurrencyHelper

                CurrencyHelper.register_db(self)
            except Exception:
                pass

    def _initialize_auth_schema(self):
        try:
            self.create_settings_tables()
        except Exception as e:
            logger.error(
                f"Failed to create settings tables during auth initialization: {e}"
            )
        try:
            self.update_users_schema()
        except Exception as e:
            logger.error(
                f"Failed to update users schema during auth initialization: {e}"
            )
        try:
            self.create_users_table()
        except Exception as e:
            logger.error(
                f"Failed to create users table during auth initialization: {e}"
            )

    def _initialize_full_schema(self):
        if getattr(self, "_full_initialized", False):
            return

        current_version = int(
            self.cursor.execute("PRAGMA user_version").fetchone()[0] or 0
        )
        required_tables = {
            "settings",
            "users",
            "parts",
            "customers",
            "devices",
            "accounting",
        }
        existing_tables = {
            str(row[0])
            for row in self.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        migration_008_ready = False
        latest_migration_ready = False
        latest_migration_version = f"{self.CURRENT_SCHEMA_VERSION:03d}"
        if "_migrations" in existing_tables:
            row = self.cursor.execute(
                "SELECT 1 FROM _migrations WHERE version=? LIMIT 1",
                ("008",),
            ).fetchone()
            migration_008_ready = bool(row)
            row = self.cursor.execute(
                "SELECT 1 FROM _migrations WHERE version=? LIMIT 1",
                (latest_migration_version,),
            ).fetchone()
            latest_migration_ready = bool(row)
        if (
            current_version >= self.CURRENT_SCHEMA_VERSION
            and required_tables.issubset(existing_tables)
            and latest_migration_ready
        ):
            self._full_initialized = True
            self._init_mode = "full"
            return
        if required_tables.issubset(existing_tables) and migration_008_ready:
            MigrationManager(self.conn).migrate()
            self.cursor.execute(
                f"PRAGMA user_version = {self.CURRENT_SCHEMA_VERSION}"
            )
            self.conn.commit()
            self._full_initialized = True
            self._init_mode = "full"
            return

        self.create_table()
        self.update_schema()
        self.create_parts_table()
        self.create_stock_tables()
        self.create_logs_table()
        self.create_report_tables()
        self.create_accounting_table()
        self.create_personnel_table()
        self.create_customers_table()
        self.update_customers_schema()
        self.create_photos_table()
        self.create_support_tables()
        self.update_users_schema()
        self.create_users_table()
        self.create_settings_tables()
        self.update_parts_schema()
        self.update_advanced_schema()
        self.create_audit_log_table()
        self.create_sms_log_table()
        self.update_customer_schema_extended()
        self.update_personnel_schema_extended()
        self.update_personnel_schema_telegram()
        self.update_appointments_schema()
        self.update_accounting_schema()
        self.update_customer_currency_balances_schema()
        self.create_indexes()
        self.create_bank_accounts_table()
        self.create_contracts_table()
        self.update_reminders_schema()
        self.create_announcements_table()
        self.create_licensing_tables()
        self.update_registration_schema()
        self.create_assistant_notifications_table()
        self.create_external_tracking_table()
        self.update_company_info_schema()
        self.create_customer_notes_table()
        self.create_quick_notes_table()
        self.create_fast_notes_table()
        self.create_customer_services_table()
        self.create_service_definitions_table()
        self.create_services_table()
        self.create_logistics_table()
        self.create_multi_currency_tables()
        self.update_currency_transactions_schema()
        self.create_company_info_table()
        self.create_finance_tables()
        self.create_product_bank_mappings_table()
        self.create_project_tables()
        self.create_label_tables()
        self.create_einvoice_table()
        self.create_internal_settings_table()
        self.create_notification_table()
        self.create_vehicle_maintenance_tables()
        self.create_offer_tables()
        self.ensure_runtime_schema_compatibility()
        self.ensure_sector_extension_tables()
        self.migrate_legacy_automotive_extensions()
        self.ensure_default_settings()
        self.create_loaner_tables()
        self.create_device_brands_table()
        self.auto_repair()

        MigrationManager(self.conn).migrate()
        self.cursor.execute(
            f"PRAGMA user_version = {self.CURRENT_SCHEMA_VERSION}"
        )
        self.conn.commit()

        self._full_initialized = True
        self._init_mode = "full"

    def create_offer_tables(self):
        try:
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    offer_no TEXT UNIQUE,
                    customer_id INTEGER,
                    customer_name TEXT,
                    company_name TEXT,
                    contact_name TEXT,
                    project_name TEXT,
                    template_type TEXT,
                    currency_code TEXT,
                    currency_symbol TEXT,
                    exchange_rate REAL DEFAULT 1,
                    subtotal REAL DEFAULT 0,
                    discount REAL DEFAULT 0,
                    vat_rate REAL DEFAULT 0,
                    vat_amount REAL DEFAULT 0,
                    total REAL DEFAULT 0,
                    subtotal_try REAL DEFAULT 0,
                    discount_try REAL DEFAULT 0,
                    vat_amount_try REAL DEFAULT 0,
                    total_try REAL DEFAULT 0,
                    status TEXT DEFAULT 'draft',
                    source TEXT,
                    created_by TEXT,
                    pdf_path TEXT,
                    payload_json TEXT,
                    accepted_at TEXT,
                    accepted_by TEXT,
                    accepted_payment REAL DEFAULT 0,
                    accepted_payment_try REAL DEFAULT 0,
                    remaining_amount REAL DEFAULT 0,
                    remaining_try REAL DEFAULT 0,
                    payment_method TEXT,
                    processed_tracking_no TEXT,
                    processing_error TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS offer_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    offer_id INTEGER NOT NULL,
                    item_id INTEGER,
                    item_type TEXT,
                    service TEXT,
                    description TEXT,
                    brand TEXT,
                    qty REAL DEFAULT 1,
                    unit_price REAL DEFAULT 0,
                    line_total REAL DEFAULT 0,
                    payload_json TEXT,
                    FOREIGN KEY(offer_id) REFERENCES offers(id) ON DELETE CASCADE
                )
                """
            )
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS offer_reversals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    offer_id INTEGER NOT NULL,
                    original_tracking_no TEXT NOT NULL,
                    reversal_tracking_no TEXT NOT NULL UNIQUE,
                    reason TEXT NOT NULL,
                    reversed_by TEXT,
                    payload_json TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(offer_id, original_tracking_no),
                    FOREIGN KEY(offer_id) REFERENCES offers(id)
                )
                """
            )
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_customer_id ON offers(customer_id)")
            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_offers_created_at ON offers(created_at)")
            self.conn.commit()
            self._ensure_columns(
                "offers",
                {
                    "accepted_at": "TEXT",
                    "accepted_by": "TEXT",
                    "accepted_payment": "REAL DEFAULT 0",
                    "accepted_payment_try": "REAL DEFAULT 0",
                    "remaining_amount": "REAL DEFAULT 0",
                    "remaining_try": "REAL DEFAULT 0",
                    "payment_method": "TEXT",
                    "processed_tracking_no": "TEXT",
                    "processing_error": "TEXT",
                    "created_by": "TEXT",
                },
            )
            self._repair_legacy_offer_vat_rates()
        except Exception as e:
            logger.error(f"create_offer_tables error: {e}")

    @staticmethod
    def _normalize_offer_vat_ratio(value):
        try:
            rate = float(value or 0)
        except (TypeError, ValueError):
            return 0.0
        if rate > 1:
            rate /= 100.0
        return max(0.0, min(rate, 1.0))

    def _repair_legacy_offer_vat_rates(self):
        rows = self.cursor.execute(
            """
            SELECT id, status, subtotal, discount, subtotal_try, discount_try,
                   vat_rate, payload_json
            FROM offers
            WHERE CAST(COALESCE(vat_rate, 0) AS REAL) > 1
            """
        ).fetchall()
        for row in rows:
            (
                offer_id,
                status,
                subtotal,
                discount,
                subtotal_try,
                discount_try,
                stored_rate,
                payload_json,
            ) = row
            vat_rate = self._normalize_offer_vat_ratio(stored_rate)
            mutable = str(status or "").strip().lower() not in {
                "accepted",
                "processed",
            }
            net = float(subtotal or 0) - float(discount or 0)
            net_try = float(subtotal_try or 0) - float(discount_try or 0)
            vat_amount = round(net * vat_rate, 2)
            vat_amount_try = round(net_try * vat_rate, 2)
            total = round(net + vat_amount, 2)
            total_try = round(net_try + vat_amount_try, 2)

            payload = None
            try:
                payload = json.loads(payload_json) if payload_json else None
            except (TypeError, ValueError, json.JSONDecodeError):
                payload = None
            if isinstance(payload, dict):
                payload_totals = payload.get("totals")
                if isinstance(payload_totals, dict):
                    payload_totals["vat_rate"] = vat_rate
                    if mutable:
                        payload_totals["vat_amount"] = vat_amount
                        payload_totals["total"] = total
                payload_try = payload.get("totals_try")
                if isinstance(payload_try, dict):
                    payload_try["vat_rate"] = vat_rate
                    if mutable:
                        payload_try["vat_amount"] = vat_amount_try
                        payload_try["total"] = total_try
                payload_json = json.dumps(
                    payload,
                    ensure_ascii=False,
                    default=str,
                )

            if mutable:
                self.cursor.execute(
                    """
                    UPDATE offers
                    SET vat_rate=?, vat_amount=?, total=?,
                        vat_amount_try=?, total_try=?, payload_json=?
                    WHERE id=?
                    """,
                    (
                        vat_rate,
                        vat_amount,
                        total,
                        vat_amount_try,
                        total_try,
                        payload_json,
                        int(offer_id),
                    ),
                )
            else:
                self.cursor.execute(
                    """
                    UPDATE offers
                    SET vat_rate=?, payload_json=?
                    WHERE id=?
                    """,
                    (vat_rate, payload_json, int(offer_id)),
                )
        if rows:
            self.conn.commit()

    def save_offer_record(self, data):
        self.create_offer_tables()
        items = list(data.get("items") or [])
        offer_no = str(data.get("offer_no") or "").strip()
        totals = dict(data.get("totals") or {})
        totals_try = dict(data.get("totals_try") or totals)
        vat_rate = self._normalize_offer_vat_ratio(
            totals.get("vat_rate", totals_try.get("vat_rate", 0))
        )
        totals["vat_rate"] = vat_rate
        totals_try["vat_rate"] = vat_rate
        data = dict(data)
        data["totals"] = totals
        data["totals_try"] = totals_try
        payload = dict(data)
        payload["items"] = items
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        offer_id = data.get("offer_id")
        if offer_id:
            self.cursor.execute(
                "SELECT id, status FROM offers WHERE id=?",
                (int(offer_id),),
            )
        else:
            self.cursor.execute(
                "SELECT id, status FROM offers WHERE offer_no=?",
                (offer_no,),
            )
        existing = self.cursor.fetchone()
        if existing:
            existing_status = str(existing[1] or "").strip().lower()
            existing_status = (
                existing_status.replace("\u0131", "i")
                .replace("\u015f", "s")
                .replace("\u0130", "i")
                .replace("\u015e", "s")
                .replace("\u0307", "")
            )
            if (
                existing_status in {
                    "accepted", "processed", "accepted offer", "islenmis", "kabul edildi",
                }
                or "islen" in existing_status
                or "kabul" in existing_status
            ):
                raise ValueError("Accepted offers cannot be edited.")
            offer_id = int(existing[0])
            self.cursor.execute(
                """
                UPDATE offers
                SET offer_no=?, customer_id=?, customer_name=?, company_name=?,
                    contact_name=?, project_name=?, template_type=?,
                    currency_code=?, currency_symbol=?, exchange_rate=?,
                    subtotal=?, discount=?, vat_rate=?, vat_amount=?, total=?,
                    subtotal_try=?, discount_try=?, vat_amount_try=?, total_try=?,
                    status=?, source=?,
                    created_by=COALESCE(NULLIF(created_by, ''), ?),
                    pdf_path=?, payload_json=?,
                    processing_error=NULL, updated_at=CURRENT_TIMESTAMP
                WHERE id=?
                """,
                (
                    offer_no,
                    data.get("customer_id"),
                    data.get("customer_name", ""),
                    data.get("company_name", ""),
                    data.get("contact_name", ""),
                    data.get("project_name", ""),
                    data.get("template_type", ""),
                    data.get("currency_code", ""),
                    data.get("currency_symbol", ""),
                    float(data.get("exchange_rate") or 1),
                    float(totals.get("subtotal") or 0),
                    float(totals.get("discount") or 0),
                    float(totals.get("vat_rate") or 0),
                    float(totals.get("vat_amount") or 0),
                    float(totals.get("total") or 0),
                    float(totals_try.get("subtotal") or 0),
                    float(totals_try.get("discount") or 0),
                    float(totals_try.get("vat_amount") or 0),
                    float(totals_try.get("total") or 0),
                    data.get("status", "created"),
                    data.get("source", "proforma"),
                    data.get("created_by", ""),
                    data.get("pdf_path", ""),
                    payload_json,
                    offer_id,
                ),
            )
        else:
            self.cursor.execute(
                """
                INSERT INTO offers (
                    offer_no, customer_id, customer_name, company_name, contact_name,
                    project_name, template_type, currency_code, currency_symbol,
                    exchange_rate, subtotal, discount, vat_rate, vat_amount, total,
                    subtotal_try, discount_try, vat_amount_try, total_try, status,
                    source, created_by, pdf_path, payload_json, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    offer_no,
                    data.get("customer_id"),
                    data.get("customer_name", ""),
                    data.get("company_name", ""),
                    data.get("contact_name", ""),
                    data.get("project_name", ""),
                    data.get("template_type", ""),
                    data.get("currency_code", ""),
                    data.get("currency_symbol", ""),
                    float(data.get("exchange_rate") or 1),
                    float(totals.get("subtotal") or 0),
                    float(totals.get("discount") or 0),
                    float(totals.get("vat_rate") or 0),
                    float(totals.get("vat_amount") or 0),
                    float(totals.get("total") or 0),
                    float(totals_try.get("subtotal") or 0),
                    float(totals_try.get("discount") or 0),
                    float(totals_try.get("vat_amount") or 0),
                    float(totals_try.get("total") or 0),
                    data.get("status", "created"),
                    data.get("source", "proforma"),
                    data.get("created_by", ""),
                    data.get("pdf_path", ""),
                    payload_json,
                ),
            )
            offer_id = self.cursor.lastrowid
        if offer_id:
            self.cursor.execute("DELETE FROM offer_items WHERE offer_id=?", (offer_id,))
            for item in items:
                qty = float(item.get("qty", item.get("count", 1)) or 1)
                price = float(item.get("price", item.get("unit_price", 0)) or 0)
                self.cursor.execute(
                    """
                    INSERT INTO offer_items (
                        offer_id, item_id, item_type, service, description,
                        brand, qty, unit_price, line_total, payload_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        offer_id,
                        item.get("item_id"),
                        item.get("type", item.get("item_type", "")),
                        item.get("service", item.get("name", "")),
                        item.get("description", ""),
                        item.get("brand", ""),
                        qty,
                        price,
                        qty * price,
                        json.dumps(item, ensure_ascii=False, default=str),
                    ),
                )
        self.conn.commit()
        return offer_id

    def get_customer_offers(self, customer_id):
        self.create_offer_tables()
        self.cursor.execute(
            """
            SELECT id, offer_no, created_at, company_name, contact_name, project_name,
                   currency_symbol, total, status, pdf_path
            FROM offers
            WHERE customer_id=?
            ORDER BY datetime(created_at) DESC, id DESC
            """,
            (customer_id,),
        )
        return self.cursor.fetchall()

    def get_offer_items(self, offer_id):
        self.create_offer_tables()
        self.cursor.execute(
            """
            SELECT service, description, qty, unit_price, line_total
            FROM offer_items
            WHERE offer_id=?
            ORDER BY id
            """,
            (offer_id,),
        )
        return self.cursor.fetchall()

    def get_offer_record(self, offer_id):
        self.create_offer_tables()
        self.cursor.execute("SELECT * FROM offers WHERE id=?", (int(offer_id),))
        return self.cursor.fetchone()

    def get_offer_items_detailed(self, offer_id):
        self.create_offer_tables()
        self.cursor.execute(
            """
            SELECT id, offer_id, item_id, item_type, service, description,
                   brand, qty, unit_price, line_total, payload_json
            FROM offer_items
            WHERE offer_id=?
            ORDER BY id
            """,
            (int(offer_id),),
        )
        return self.cursor.fetchall()

    def update_offer_processing_state(
        self,
        offer_id,
        status,
        tracking_no="",
        error="",
        accepted_by="",
        payment_amount=0.0,
        payment_try=0.0,
        remaining_amount=0.0,
        remaining_try=0.0,
        payment_method="",
    ):
        self.create_offer_tables()
        accepted_at = (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if str(status).lower() == "accepted"
            else None
        )
        self.cursor.execute(
            """
            UPDATE offers
            SET status=?, processed_tracking_no=?, processing_error=?,
                accepted_at=COALESCE(?, accepted_at), accepted_by=?,
                accepted_payment=?, accepted_payment_try=?,
                remaining_amount=?, remaining_try=?, payment_method=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                status,
                tracking_no or "",
                error or "",
                accepted_at,
                accepted_by or "",
                float(payment_amount or 0),
                float(payment_try or 0),
                float(remaining_amount or 0),
                float(remaining_try or 0),
                payment_method or "",
                int(offer_id),
            ),
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def run_daily_local_backup_if_due(self, trigger="scheduled"):
        """
        Gun icinde en fazla bir kez calisan tek dosyali yerel yedek.
        Hem gecikmeli zamanlayici hem de kapanis akisi bu metodu kullanir.
        """
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            last_backup_date = self.get_internal_setting(
                "daily_local_backup_last_date", ""
            )
            if last_backup_date == today:
                logger.info(
                    "Daily local backup skipped for %s; already created today.", trigger
                )
                return None

            backup_path = self.backup_database(
                target_name="ayecpro_daily_local_backup.db"
            )
            if not backup_path:
                return None

            self.set_internal_setting("daily_local_backup_last_date", today)
            self.set_internal_setting("daily_local_backup_last_trigger", trigger)
            self.set_internal_setting(
                "daily_local_backup_last_file", os.path.basename(backup_path)
            )
            logger.info("Daily local backup created by %s: %s", trigger, backup_path)
            return backup_path
        except Exception as e:
            logger.error(f"Daily local backup check error ({trigger}): {e}")
            return None

    def ensure_default_settings(self):
        """Seed safe default settings after fresh install or wipe-all."""
        try:
            if not self._table_exists("settings"):
                return

            defaults = {
                "job_number_prefix": "JOB",
                "job_number_next": "1",
                "service_number_prefix": "SRV",
                "service_number_next": "1",
                "project_number_prefix": "PRJ",
                "project_number_next": "1",
                "reference_number_prefix": "REF",
                "reference_number_next": "1",
                "payment_number_prefix": "PAY",
                "payment_number_next": "1",
                "service_contract": "",
                "offer_contract": "",
                "proforma_template_path": "",
                "backup_server_ip": "85.117.239.60:8000",
                "backup_daily_enabled": "0",
                "backup_daily_time": "12:00",
                "backup_on_exit": "1",
                "backup_auto_morning": "0",
                "backup_auto_evening": "0",
                "last_login_user": "admin",
            }

            cur = self.conn.cursor()
            for key, value in defaults.items():
                cur.execute("SELECT value FROM settings WHERE key=?", (key,))
                row = cur.fetchone()
                if row is None:
                    cur.execute(
                        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        (key, value),
                    )
            self.conn.commit()
        except Exception as e:
            logger.error(f"ensure_default_settings error: {e}")

    def ensure_sector_extension_tables(self, commit=True):
        """Sektöre özel extension tablolarını oluştur."""
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS customer_automotive_extension (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL UNIQUE,
                    vehicle_plate TEXT,
                    vehicle_vin TEXT,
                    vehicle_brand TEXT,
                    vehicle_model TEXT,
                    vehicle_year TEXT,
                    vehicle_engine TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS service_automotive_extension (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL UNIQUE,
                    vehicle_plate TEXT,
                    vehicle_vin TEXT,
                    current_km TEXT,
                    service_type TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS customer_technical_service_extension (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL UNIQUE,
                    device_type TEXT,
                    device_brand TEXT,
                    device_model TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(customer_id) REFERENCES customers(id) ON DELETE CASCADE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS service_technical_service_extension (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL UNIQUE,
                    device_type TEXT,
                    serial_no TEXT,
                    warranty_status TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_automotive_extension (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    part_id INTEGER NOT NULL UNIQUE,
                    oem_code TEXT,
                    equivalent_code TEXT,
                    compatible_models TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(part_id) REFERENCES parts(id) ON DELETE CASCADE
                )
                """
            )
            if commit:
                self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"ensure_sector_extension_tables error: {e}")
            return False

    def migrate_legacy_automotive_extensions(self):
        """Eski otomotiv kolonlarını extension tablolara kopyala."""
        try:
            self.ensure_sector_extension_tables()
            cur = self.conn.cursor()

            device_cols = (
                set(self._get_table_columns("devices"))
                if hasattr(self, "_get_table_columns")
                else set()
            )
            if {"id", "vehicle_plate", "vehicle_vin"}.issubset(device_cols):
                cur.execute(
                    """
                    INSERT INTO service_automotive_extension (
                        device_id, vehicle_plate, vehicle_vin, created_at, updated_at
                    )
                    SELECT
                        d.id,
                        COALESCE(d.vehicle_plate, ''),
                        COALESCE(d.vehicle_vin, ''),
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    FROM devices d
                    WHERE (COALESCE(TRIM(d.vehicle_plate), '') != '' OR COALESCE(TRIM(d.vehicle_vin), '') != '')
                      AND NOT EXISTS (
                          SELECT 1 FROM service_automotive_extension s WHERE s.device_id = d.id
                      )
                    """
                )

            part_cols = (
                set(self._get_table_columns("parts"))
                if hasattr(self, "_get_table_columns")
                else set()
            )
            required_part_cols = {
                "id",
                "oem_code",
                "equivalent_code",
                "compatible_models",
            }
            if required_part_cols.issubset(part_cols):
                cur.execute(
                    """
                    INSERT INTO stock_automotive_extension (
                        part_id, oem_code, equivalent_code, compatible_models, created_at, updated_at
                    )
                    SELECT
                        p.id,
                        COALESCE(p.oem_code, ''),
                        COALESCE(p.equivalent_code, ''),
                        COALESCE(p.compatible_models, ''),
                        CURRENT_TIMESTAMP,
                        CURRENT_TIMESTAMP
                    FROM parts p
                    WHERE (
                        COALESCE(TRIM(p.oem_code), '') != ''
                        OR COALESCE(TRIM(p.equivalent_code), '') != ''
                        OR COALESCE(TRIM(p.compatible_models), '') != ''
                    )
                      AND NOT EXISTS (
                          SELECT 1 FROM stock_automotive_extension s WHERE s.part_id = p.id
                      )
                    """
                )

            self.conn.commit()
        except Exception as e:
            logger.error(f"migrate_legacy_automotive_extensions error: {e}")

    def get_sector_extension(self, entity, parent_id, sector_id="otomotiv"):
        table_map = {
            ("customer", "otomotiv"): ("customer_automotive_extension", "customer_id"),
            ("service", "otomotiv"): ("service_automotive_extension", "device_id"),
            ("customer", "teknik_servis"): (
                "customer_technical_service_extension",
                "customer_id",
            ),
            ("service", "teknik_servis"): (
                "service_technical_service_extension",
                "device_id",
            ),
            ("stock", "otomotiv"): ("stock_automotive_extension", "part_id"),
        }
        table_info = table_map.get((entity, sector_id))
        if not table_info or not parent_id:
            return None
        table_name, fk_name = table_info
        try:
            table_name = self._safe_identifier(table_name)
            fk_name = self._safe_identifier(fk_name)
            cur = self.conn.cursor()
            cur.execute(
                "SELECT * FROM {table_name} WHERE {fk_name}=?".format(
                    table_name=table_name,
                    fk_name=fk_name,
                ),
                (parent_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"get_sector_extension error ({entity}, {sector_id}): {e}")
            return None

    def upsert_sector_extension(
        self,
        entity,
        parent_id,
        payload,
        sector_id="otomotiv",
        commit=True,
    ):
        table_map = {
            ("customer", "otomotiv"): ("customer_automotive_extension", "customer_id"),
            ("service", "otomotiv"): ("service_automotive_extension", "device_id"),
            ("customer", "teknik_servis"): (
                "customer_technical_service_extension",
                "customer_id",
            ),
            ("service", "teknik_servis"): (
                "service_technical_service_extension",
                "device_id",
            ),
            ("stock", "otomotiv"): ("stock_automotive_extension", "part_id"),
        }
        table_info = table_map.get((entity, sector_id))
        if not table_info or not parent_id:
            return False
        table_name, fk_name = table_info
        try:
            table_name = self._safe_identifier(table_name)
            fk_name = self._safe_identifier(fk_name)
            if not self.ensure_sector_extension_tables(commit=commit):
                raise RuntimeError("Sector extension schema is unavailable")
            cur = self.conn.cursor()
            valid_columns = (
                set(self._get_table_columns(table_name))
                if hasattr(self, "_get_table_columns")
                else set()
            )
            safe_payload = {
                key: value
                for key, value in (payload or {}).items()
                if key in valid_columns
                and key not in {"id", fk_name, "created_at", "updated_at"}
            }
            cur.execute(
                "SELECT id FROM {table_name} WHERE {fk_name}=?".format(
                    table_name=table_name,
                    fk_name=fk_name,
                ),
                (parent_id,),
            )
            existing = cur.fetchone()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if existing:
                assignments = [f"{fk_name}=?", "updated_at=?"]
                values = [parent_id, now]
                for key, value in safe_payload.items():
                    assignments.append(f"{self._safe_identifier(key)}=?")
                    values.append(value)
                values.append(parent_id)
                cur.execute(
                    f"UPDATE {table_name} SET {', '.join(assignments)} WHERE {fk_name}=?",
                    tuple(values),
                )
            else:
                insert_payload = {
                    fk_name: parent_id,
                    **safe_payload,
                    "created_at": now,
                    "updated_at": now,
                }
                keys = ", ".join(
                    self._safe_identifier(key) for key in insert_payload.keys()
                )
                placeholders = ", ".join(["?"] * len(insert_payload))
                cur.execute(
                    f"INSERT INTO {table_name} ({keys}) VALUES ({placeholders})",
                    tuple(insert_payload.values()),
                )
            if commit:
                self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"upsert_sector_extension error ({entity}, {sector_id}): {e}")
            return False

    def get_customer_with_extensions(self, customer_id, sector_id="otomotiv"):
        try:
            cur = self.conn.cursor()
            try:
                cur.execute(
                    "SELECT * FROM customers WHERE id=? AND COALESCE(is_deleted, 0)=0",
                    (customer_id,),
                )
            except Exception:
                cur.execute("SELECT * FROM customers WHERE id=?", (customer_id,))
            core_row = cur.fetchone()
            if not core_row:
                return None
            merged = dict(core_row)
            extension_row = self.get_sector_extension(
                "customer", customer_id, sector_id=sector_id
            )
            if extension_row:
                merged.update(extension_row)
            return merged
        except Exception as e:
            logger.error(f"get_customer_with_extensions error: {e}")
            return None

    def get_device_with_extensions(
        self, device_id=None, tracking_no=None, sector_id="otomotiv"
    ):
        try:
            cur = self.conn.cursor()
            if device_id is not None:
                try:
                    cur.execute(
                        "SELECT * FROM devices WHERE id=? AND COALESCE(is_deleted, 0)=0",
                        (device_id,),
                    )
                except Exception:
                    cur.execute("SELECT * FROM devices WHERE id=?", (device_id,))
            else:
                try:
                    cur.execute(
                        "SELECT * FROM devices WHERE tracking_no=? AND COALESCE(is_deleted, 0)=0",
                        (tracking_no,),
                    )
                except Exception:
                    cur.execute(
                        "SELECT * FROM devices WHERE tracking_no=?", (tracking_no,)
                    )
            core_row = cur.fetchone()
            if not core_row:
                return None
            merged = dict(core_row)
            extension_row = self.get_sector_extension(
                "service", merged.get("id"), sector_id=sector_id
            )
            if extension_row:
                merged.update(extension_row)
            return merged
        except Exception as e:
            logger.error(f"get_device_with_extensions error: {e}")
            return None

    def get_part_with_extensions(self, part_id, sector_id="otomotiv"):
        try:
            cur = self.conn.cursor()
            try:
                cur.execute(
                    "SELECT * FROM parts WHERE id=? AND COALESCE(is_deleted, 0)=0",
                    (part_id,),
                )
            except Exception:
                cur.execute("SELECT * FROM parts WHERE id=?", (part_id,))
            core_row = cur.fetchone()
            if not core_row:
                return None
            merged = dict(core_row)
            extension_row = self.get_sector_extension(
                "stock", part_id, sector_id=sector_id
            )
            if extension_row:
                merged.update(extension_row)
            return merged
        except Exception as e:
            logger.error(f"get_part_with_extensions error: {e}")
            return None

    # Compatibility wrappers for stock API
    # Keep these in Database class to avoid runtime breaks if mixin resolution
    # differs between old/new entry points.
    def get_parts_paginated(
        self, limit=50, offset=0, search_query="", category="T\u00fcm\u00fc", critical_only=False,
        metric_filter="all"
    ):
        try:
            return StockMixin.get_parts_paginated(
                self,
                limit=limit,
                offset=offset,
                search_query=search_query,
                category=category,
                critical_only=critical_only,
                metric_filter=metric_filter,
            )
        except Exception as e:
            logger.error(f"Database.get_parts_paginated fallback error: {e}")
            return [], 0

    def adjust_stock(
        self,
        part_id,
        delta,
        description="",
        type_val=None,
        commit=True,
    ):
        try:
            return StockMixin.adjust_stock(
                self,
                part_id=part_id,
                delta=delta,
                description=description,
                type_val=type_val,
                commit=commit,
            )
        except Exception as e:
            logger.error(f"Database.adjust_stock fallback error: {e}")
            return False

    def ensure_full_initialized(self):
        self._initialize_full_schema()

    def _open_connection(self):
        self._open_connection_for_thread()

    def refresh_current_thread_connection(self):
        with self.lock:
            connection = getattr(self._local, "conn", None)
            if connection is not None:
                try:
                    connection.rollback()
                except sqlite3.Error:
                    pass
                connection.close()
            self._local.conn = None
            self._local.cursor = None
            self._is_closed = True
            self._open_connection_for_thread()

    def _open_connection_for_thread(self):
        db_path = self._db_name if self._db_name == ":memory:" else PathHelper.get_db_path(self._db_name)
        conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
        if self._db_name != ":memory:":
            try:
                from src.utils.config import config
                if SQLCIPHER_AVAILABLE:
                    db_key = str(config.database_key).replace("'", "''")
                    conn.execute(f"PRAGMA key = '{db_key}'")
                    conn.execute("PRAGMA cipher_page_size = 4096")
                    conn.execute("PRAGMA kdf_iter = 256000")
                elif os.environ.get("AYEC_REQUIRE_SQLCIPHER") == "1":
                    raise RuntimeError(
                        "SQLCipher is required but pysqlcipher3/sqlcipher3 is not installed."
                    )
            except Exception:
                conn.close()
                raise
        conn.text_factory = lambda b: (
            b.decode("utf-8", errors="replace")
            if isinstance(b, (bytes, bytearray))
            else ("" if b is None else str(b))
        )
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.execute("PRAGMA cache_size = -32768")
        cursor.execute("PRAGMA temp_store = MEMORY")
        conn.commit()
        self._local.conn = conn
        self._local.cursor = cursor
        self._is_closed = False

    def _reopen_if_needed(self):
        try:
            if self._is_closed or not hasattr(self._local, "conn") or self._local.conn is None or not hasattr(self._local, "cursor") or self._local.cursor is None:
                self._open_connection()
        except sqlite3.Error as e:
            logger.error(f"Failed to reopen database connection: {e}")

    @property
    def _conn(self):
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._open_connection_for_thread()
        return self._local.conn

    @_conn.setter
    def _conn(self, value):
        self._local.conn = value

    @property
    def _cursor(self):
        if not hasattr(self._local, "cursor") or self._local.cursor is None:
            self._open_connection_for_thread()
        return self._local.cursor

    @_cursor.setter
    def _cursor(self, value):
        self._local.cursor = value

    @property
    def conn(self):
        self._reopen_if_needed()
        return self._conn

    @conn.setter
    def conn(self, value):
        self._conn = value

    @property
    def cursor(self):
        self._reopen_if_needed()
        return self._cursor

    @cursor.setter
    def cursor(self, value):
        self._cursor = value

    def _is_safe_identifier(self, name):
        if not name or not isinstance(name, str):
            return False
        return name.replace("_", "").isalnum()

    def _safe_identifier(self, name):
        if not self._is_safe_identifier(name):
            raise ValueError(f"Invalid SQL identifier: {name!r}")
        return name

    def _quote_identifier(self, name):
        name = self._safe_identifier(name)
        return '"' + name.replace('"', '""') + '"'

    def _get_table_columns(self, table_name):
        try:
            if not self._is_safe_identifier(table_name):
                return []
            cur = self.conn.cursor()
            cur.execute(
                "PRAGMA table_info({table_name})".format(
                    table_name=self._safe_identifier(table_name)
                )
            )
            return [row[1] for row in cur.fetchall()]
        except sqlite3.Error:
            return []

    def _table_exists(self, table_name):
        try:
            if not self._is_safe_identifier(table_name):
                return False
            cur = self.conn.cursor()
            cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            return cur.fetchone() is not None
        except sqlite3.Error:
            return False

    def _ensure_columns(self, table_name, columns):
        if not self._is_safe_identifier(table_name) or not isinstance(columns, dict):
            return False
        existing = set(self._get_table_columns(table_name))
        cur = self.conn.cursor()
        changed = False
        had_error = False
        for col_name, ddl in columns.items():
            try:
                if not self._is_safe_identifier(col_name):
                    continue
                if col_name in existing:
                    continue
                cur.execute(
                    f"ALTER TABLE {self._safe_identifier(table_name)} "
                    f"ADD COLUMN {self._safe_identifier(col_name)} {ddl}"
                )
                changed = True
                existing.add(col_name)
            except sqlite3.Error as e:
                had_error = True
                logger.warning(
                    f"Schema ensure skipped for {table_name}.{col_name}: {e}"
                )
        if changed:
            self.conn.commit()
        return not had_error

    def ensure_runtime_schema_compatibility(self):
        """Central repair pass for frequently mismatched runtime tables."""
        try:
            if hasattr(self, "update_used_parts_schema"):
                self.update_used_parts_schema()
            if hasattr(self, "_ensure_stock_movements_schema"):
                self._ensure_stock_movements_schema()
            if hasattr(self, "ensure_stock_location_schema"):
                self.ensure_stock_location_schema()

            if self._table_exists("users"):
                self._ensure_columns(
                    "users",
                    {
                        "email": "TEXT",
                        "permissions": "TEXT",
                        "personnel_id": "INTEGER",
                        "created_at": "TEXT",
                        "full_name": "TEXT",
                        "secret_question": "TEXT",
                        "secret_answer": "TEXT",
                        "active": "INTEGER DEFAULT 1",
                        "interface_edit_access": "INTEGER DEFAULT 0",
                        "last_login": "TEXT",
                        "remember_token": "TEXT",
                        "auto_login": "INTEGER DEFAULT 0",
                    },
                )

            if self._table_exists("devices"):
                self._ensure_columns(
                    "devices",
                    {
                        "delivery_method": "TEXT",
                        "service_location": "TEXT",
                        "other_info": "TEXT",
                        "delivered_by_name": "TEXT",
                        "delivered_by_phone": "TEXT",
                    },
                )

            if self._table_exists("company_info"):
                self._ensure_columns(
                    "company_info",
                    {
                        "logo_path": "TEXT",
                    },
                )

            if self._table_exists("bank_accounts"):
                self._ensure_columns(
                    "bank_accounts",
                    {
                        "currency": "TEXT DEFAULT 'TRY'",
                        "is_active": "INTEGER DEFAULT 1",
                        "created_at": "TEXT",
                        "current_balance": "REAL DEFAULT 0",
                        "is_deleted": "INTEGER DEFAULT 0",
                        "deleted_at": "TEXT",
                    },
                )

            if self._table_exists("used_parts"):
                self._ensure_columns(
                    "used_parts",
                    {
                        "part_id": "INTEGER",
                        "quantity": "INTEGER DEFAULT 1",
                        "purchase_price_snapshot": "REAL DEFAULT 0",
                        "currency": "TEXT DEFAULT 'TRY'",
                        "is_deleted": "INTEGER DEFAULT 0",
                        "deleted_at": "TEXT",
                    },
                )

            if self._table_exists("currency_transactions"):
                self._ensure_columns(
                    "currency_transactions",
                    {
                        "current_balance": "REAL DEFAULT 0.0",
                        "is_invoiced": "INTEGER DEFAULT 0",
                    },
                )

            if self._table_exists("customer_currency_balances"):
                self._ensure_columns(
                    "customer_currency_balances",
                    {
                        "last_updated": "TEXT",
                    },
                )

            if self._table_exists("projects"):
                self._ensure_columns(
                    "projects",
                    {
                        "cost": "REAL DEFAULT 0",
                        "payment_method": "TEXT DEFAULT 'Peşin'",
                        "customer_id": "INTEGER",
                        "customer_name": "TEXT",
                        "ref_no": "TEXT",
                        "is_archived": "INTEGER DEFAULT 0",
                        "currency": "TEXT DEFAULT 'TRY'",
                        "exchange_rate": "REAL DEFAULT 1.0",
                    },
                )

            if self._table_exists("project_transactions"):
                self._ensure_columns(
                    "project_transactions",
                    {
                        "original_amount": "REAL",
                        "original_currency": "TEXT DEFAULT 'TRY'",
                        "exchange_rate": "REAL DEFAULT 1.0",
                    },
                )

            if self._table_exists("parts"):
                self._ensure_columns(
                    "parts",
                    {
                        "brand": "TEXT",
                    },
                )

            if self._table_exists("loans"):
                self._ensure_columns(
                    "loans",
                    {
                        "loan_type": "TEXT DEFAULT 'Taksitli'",
                        "loan_title": "TEXT",
                        "kkdf_rate": "REAL DEFAULT 0",
                        "bsmv_rate": "REAL DEFAULT 0",
                        "is_deleted": "INTEGER DEFAULT 0",
                        "deleted_at": "TEXT",
                    },
                )

            if self._table_exists("loan_installments"):
                self._ensure_columns(
                    "loan_installments",
                    {
                        "kkdf_amount": "REAL DEFAULT 0.0",
                        "bsmv_amount": "REAL DEFAULT 0.0",
                        "is_deleted": "INTEGER DEFAULT 0",
                        "deleted_at": "TEXT",
                    },
                )

            if not self._table_exists("jarvis_notifications"):
                cur = self.conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS jarvis_notifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message TEXT,
                        type TEXT,
                        is_critical INTEGER DEFAULT 0,
                        status TEXT DEFAULT 'unread',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                self.conn.commit()

            if self._table_exists("assistant_notifications"):
                self._ensure_columns(
                    "assistant_notifications",
                    {
                        "status": "TEXT DEFAULT 'unread'",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    },
                )

            if self._table_exists("notifications"):
                self._ensure_columns(
                    "notifications",
                    {
                        "status": "TEXT DEFAULT 'unread'",
                        "priority": "TEXT DEFAULT 'normal'",
                        "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                        "read_at": "TIMESTAMP",
                    },
                )

            if self._table_exists("services"):
                self._ensure_columns(
                    "services",
                    {
                        "barcode": "TEXT",
                        "is_deleted": "INTEGER DEFAULT 0",
                        "deleted_at": "TEXT",
                    },
                )

            if self._table_exists("accounting"):
                self._ensure_columns(
                    "accounting",
                    {
                        "is_deleted": "INTEGER DEFAULT 0",
                        "deleted_at": "TEXT",
                        "bank_account_id": "INTEGER",
                    },
                )

            if self._table_exists("devices"):
                self._ensure_columns(
                    "devices",
                    {
                        "is_deleted": "INTEGER DEFAULT 0",
                        "deleted_at": "TEXT",
                    },
                )

            if self._table_exists("stock_movements"):
                self._ensure_columns(
                    "stock_movements",
                    {
                        "is_deleted": "INTEGER DEFAULT 0",
                        "deleted_at": "TEXT",
                    },
                )

            if self._table_exists("customers"):
                self._ensure_columns(
                    "customers",
                    {
                        "is_deleted": "INTEGER DEFAULT 0",
                        "deleted_at": "TEXT",
                    },
                )
        except Exception as e:
            logger.error(f"ensure_runtime_schema_compatibility error: {e}")

    def _get_soft_delete_column(self, table_name, columns=None):
        cols = columns or self._get_table_columns(table_name)
        if "is_deleted" in cols:
            return "is_deleted"
        if "is_archived" in cols:
            return "is_archived"
        return None

    def _ensure_soft_delete_columns(self, table_name):
        if not self._is_safe_identifier(table_name):
            return None
        cols = self._get_table_columns(table_name)
        deleted_col = self._get_soft_delete_column(table_name, cols)
        if not deleted_col:
            try:
                self.cursor.execute(
                    "ALTER TABLE {table_name} ADD COLUMN is_deleted INTEGER DEFAULT 0".format(
                        table_name=table_name
                    )
                )
                self.conn.commit()
                deleted_col = "is_deleted"
                cols.append("is_deleted")
            except sqlite3.Error:
                return None
        if "deleted_at" not in cols:
            try:
                self.cursor.execute(
                    "ALTER TABLE {table_name} ADD COLUMN deleted_at TEXT".format(
                        table_name=table_name
                    )
                )
                self.conn.commit()
            except sqlite3.Error as e:
                logger.warning(f"Could not add deleted_at column on {table_name}: {e}")
        return deleted_col

    def soft_delete_record(self, table_name, id_col, record_id):
        if not self._is_safe_identifier(table_name) or not self._is_safe_identifier(
            id_col
        ):
            return False
        try:
            deleted_col = self._ensure_soft_delete_columns(table_name)
            if not deleted_col:
                return False
            deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                f"UPDATE {table_name} SET {deleted_col}=1, deleted_at=? WHERE {id_col}=?",
                (deleted_at, record_id),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Soft delete error ({table_name}): {e}")
            return False

    def restore_record(self, table_name, id_col, record_id):
        if not self._is_safe_identifier(table_name) or not self._is_safe_identifier(
            id_col
        ):
            return False
        try:
            deleted_col = self._ensure_soft_delete_columns(table_name)
            if not deleted_col:
                return False
            table_sql = self._quote_identifier(table_name)
            deleted_sql = self._quote_identifier(deleted_col)
            id_sql = self._quote_identifier(id_col)
            self.cursor.execute(
                f"UPDATE {table_sql} SET {deleted_sql}=0, deleted_at=NULL WHERE {id_sql}=?",
                (record_id,),
            )
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Restore record error ({table_name}): {e}")
            return False

    def restore_all_soft_deleted(self):
        restored = {}
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in self.cursor.fetchall() or []]
            for table in tables:
                if not self._is_safe_identifier(table):
                    continue
                cols = self._get_table_columns(table)
                deleted_col = self._get_soft_delete_column(table, cols)
                if not deleted_col:
                    continue
                try:
                    if "deleted_at" not in cols:
                        self.cursor.execute(
                            f"ALTER TABLE {self._quote_identifier(table)} ADD COLUMN deleted_at TEXT"
                        )
                    table_sql = self._quote_identifier(table)
                    deleted_sql = self._quote_identifier(deleted_col)
                    self.cursor.execute(
                        f"UPDATE {table_sql} SET {deleted_sql}=0, deleted_at=NULL WHERE {deleted_sql}=1"
                    )
                    count = self.cursor.rowcount
                    if count:
                        restored[table] = count
                except sqlite3.Error as e:
                    logger.warning(f"Restore all skipped for {table}: {e}")
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"restore_all_soft_deleted error: {e}")
        return restored

    def notify_jarvis(self, message, category="general", is_positive=True):
        """
        Notification system for database events.
        Logs important database operations and can be extended for external notifications.

        Args:
            message (str): The notification message
            category (str): Category of notification ('stock', 'device', 'payment', 'general')
            is_positive (bool): Whether this is a positive/success notification
        """
        try:
            # Log the notification
            log_level = logger.info if is_positive else logger.warning
            log_level(f"[{category.upper()}] {message}")

            # Future enhancement: Can integrate with:
            # - Telegram bot notifications
            # - Email alerts
            # - Desktop notifications
            # - SMS alerts for critical events

        except Exception as e:
            logger.error(f"Notification error: {e}")
