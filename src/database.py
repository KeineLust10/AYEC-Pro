# -*- coding: utf-8 -*-

import sqlite3
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
    def __init__(self, db_name="ayecpro.db", init_mode="full"):
        self._db_name = db_name or "ayecpro.db"
        self._init_mode = (init_mode or "full").strip().lower()
        self._full_initialized = False
        self._conn = None
        self._cursor = None
        self._is_closed = False
        self.lock = threading.Lock()

        # Migrate data from local root to AppData if necessary
        PathHelper.migrate_if_needed(db_name)

        self._open_connection()

        if self._init_mode == "auth":
            self._initialize_auth_schema()
        else:
            self._initialize_full_schema()

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
        self.ensure_runtime_schema_compatibility()
        self.ensure_sector_extension_tables()
        self.migrate_legacy_automotive_extensions()
        self.ensure_default_settings()
        self.update_accounting_schema()  # Add project_id column
        self.create_loaner_tables()  # Yeni: Emanet Cihaz Takip
        self.create_device_brands_table()  # Cihaz Türü ve Marka Listesi
        self.auto_repair()

        # Bakiye düzeltme: eski ters hesaplama mantığından kalan verileri düzelt
        try:
            self.recalculate_all_customer_balances()
        except Exception as e:
            logger.error(f"Balance recalculation skipped: {e}")

        self._full_initialized = True
        self._init_mode = "full"

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

    def ensure_sector_extension_tables(self):
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
            self.conn.commit()
        except Exception as e:
            logger.error(f"ensure_sector_extension_tables error: {e}")

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

    def upsert_sector_extension(self, entity, parent_id, payload, sector_id="otomotiv"):
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
            self.ensure_sector_extension_tables()
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
        self, limit=50, offset=0, search_query="", category="Tümü", critical_only=False
    ):
        try:
            return StockMixin.get_parts_paginated(
                self,
                limit=limit,
                offset=offset,
                search_query=search_query,
                category=category,
                critical_only=critical_only,
            )
        except Exception as e:
            logger.error(f"Database.get_parts_paginated fallback error: {e}")
            return [], 0

    def adjust_stock(self, part_id, delta, description="", type_val=None):
        try:
            return StockMixin.adjust_stock(
                self,
                part_id=part_id,
                delta=delta,
                description=description,
                type_val=type_val,
            )
        except Exception as e:
            logger.error(f"Database.adjust_stock fallback error: {e}")
            return False

    def ensure_full_initialized(self):
        self._initialize_full_schema()

    def _open_connection(self):
        db_path = PathHelper.get_db_path(self._db_name)
        conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
        conn.text_factory = lambda b: (
            b.decode("utf-8", errors="replace")
            if isinstance(b, (bytes, bytearray))
            else ("" if b is None else str(b))
        )
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        self._conn = conn
        self._cursor = cursor
        self._is_closed = False

    def _reopen_if_needed(self):
        try:
            if self._is_closed or self._conn is None or self._cursor is None:
                self._open_connection()
        except sqlite3.Error as e:
            logger.error(f"Failed to reopen database connection: {e}")

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
            self.cursor.execute(
                f"UPDATE {table_name} SET {deleted_col}=0, deleted_at=NULL WHERE {id_col}=?",
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
                    self.cursor.execute(
                        f"UPDATE {table} SET {deleted_col}=0, deleted_at=NULL WHERE {deleted_col}=1"
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
