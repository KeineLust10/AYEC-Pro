# -*- coding: utf-8 -*-

import os
import sqlite3
from datetime import datetime
from src.utils.logger import logger
from src.utils.path_helper import PathHelper

class DBLegacyMaintenanceMixin:
    """Database maintenance, repair, and backup logic."""

    def auto_repair(self):
        """Program her açıldığında veritabanını otomatik olarak denetler."""
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in self.cursor.fetchall() or []}
            if "personnel" in existing_tables:
                self.cursor.execute("PRAGMA table_info(personnel)")
                personnel_columns = {row[1] for row in self.cursor.fetchall() or []}
                if "status" in personnel_columns:
                    self.cursor.execute("UPDATE personnel SET status='Bosta' WHERE status LIKE 'Bo%'")
                    self.cursor.execute("UPDATE personnel SET status='Gorevde' WHERE status LIKE 'G%'")
            if "audit_logs" in existing_tables:
                self.cursor.execute("UPDATE audit_logs SET details = REPLACE(details, 'arYivlendi', 'arsivlendi')")
            self.conn.commit()
        except Exception as e:
            logger.warning(f"Auto repair error (safe to ignore): {e}")

    def wipe_all_user_data(self):
        """Schema korunarak kullanici verilerini temizler."""
        logger.info("WIPE ALL DATA STARTED")
        completed = False
        try:
            with self.lock:
                backup_name = datetime.now().strftime("pre_wipe_%Y%m%d_%H%M%S.db")
                if not self.backup_database(target_name=backup_name):
                    raise RuntimeError("Pre-wipe backup could not be created")
                cursor = self.conn.cursor()
                cursor.execute("PRAGMA foreign_keys = OFF")
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                all_tables = [row[0] for row in (cursor.fetchall() or []) if row and row[0]]
                keep_tables = {
                    "settings", "internal_settings", "company_info", "license_info", "registration",
                    "whatsapp_templates", "sector_presets", "device_brands", "app_labels", "users",
                    "kb_articles", "kb_articles_fts", "kb_articles_fts_config", "kb_articles_fts_data",
                    "kb_articles_fts_docsize", "kb_articles_fts_idx"
                }
                for table in all_tables:
                    if table in keep_tables: continue
                    safe_table = table.replace('"', '""')
                    cursor.execute(f'DELETE FROM "{safe_table}"')
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))

                current_year = datetime.now().year
                current_date = f"{current_year}-01-01"
                next_date = f"{current_year+1}-01-01"
                reset_values = {
                    "fiscal_year_start": current_date,
                    "fiscal_rollover_date": next_date,
                    "is_first_run": "0",
                }
                for key, val in reset_values.items():
                    cursor.execute(
                        "INSERT OR REPLACE INTO internal_settings (key, value) VALUES (?, ?)",
                        (key, val),
                    )

                cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    ("last_login_user", "admin"),
                )
                self.conn.commit()
                self.ensure_default_settings()
                if hasattr(self, "update_settings_cache_entry"):
                    for key, val in reset_values.items():
                        self.update_settings_cache_entry(
                            "internal_settings",
                            key,
                            val,
                            notify=True,
                        )
                    self.update_settings_cache_entry(
                        "settings",
                        "last_login_user",
                        "admin",
                        notify=True,
                    )
                completed = True
        except Exception as e:
            logger.error(f"Wipe all data failed: {e}")
            try:
                self.conn.rollback()
            except sqlite3.Error as rollback_error:
                logger.critical(
                    "Wipe rollback failed: %s",
                    rollback_error,
                )
        finally:
            try:
                self.conn.execute("PRAGMA foreign_keys = ON")
                state = self.conn.execute("PRAGMA foreign_keys").fetchone()
                foreign_keys_enabled = bool(state and int(state[0]) == 1)
                if not foreign_keys_enabled:
                    completed = False
                    logger.critical(
                        "Foreign key enforcement could not be restored after wipe"
                    )
            except sqlite3.Error as cleanup_error:
                completed = False
                logger.critical(
                    "Wipe cleanup failed while restoring foreign keys: %s",
                    cleanup_error,
                )
        return completed

    def backup_database(self, target_name=None):
        """Create a validated SQLite snapshot of the active database."""
        temp_path = None
        try:
            backups_dir = os.path.join(PathHelper.get_app_data_dir(), "backups")
            os.makedirs(backups_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if target_name:
                safe_name = os.path.basename(str(target_name))
                if not safe_name.lower().endswith(".db"):
                    safe_name = f"{safe_name}.db"
            else:
                safe_name = f"ayecpro_backup_{timestamp}.db"
            backup_path = os.path.join(backups_dir, safe_name)
            temp_path = f"{backup_path}.tmp"

            with self.lock:
                destination = sqlite3.connect(temp_path)
                try:
                    self.conn.backup(destination)
                    check = destination.execute("PRAGMA quick_check").fetchone()
                    if not check or str(check[0]).lower() != "ok":
                        raise sqlite3.DatabaseError(
                            f"Backup quick_check failed: {check!r}"
                        )
                    destination.commit()
                finally:
                    destination.close()

            os.replace(temp_path, backup_path)
            temp_path = None
            backups = sorted(
                os.path.join(backups_dir, filename)
                for filename in os.listdir(backups_dir)
                if filename.endswith(".db")
            )
            for old_backup in backups[:-10]:
                try:
                    os.remove(old_backup)
                except OSError as retention_error:
                    logger.warning(
                        "Old backup could not be removed (%s): %s",
                        old_backup,
                        retention_error,
                    )
            return backup_path
        except Exception as e:
            logger.error(f"Backup error: {e}")
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError as cleanup_error:
                    logger.warning(
                        "Temporary backup could not be removed (%s): %s",
                        temp_path,
                        cleanup_error,
                    )
        return None
