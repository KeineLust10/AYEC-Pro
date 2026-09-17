# -*- coding: utf-8 -*-

"""
Schema Mixin
Veritabanı şema yönetimi ve migration ile ilgili metodlar
"""

import os
import re
from datetime import datetime
from src.utils.logger import logger
from src.utils.path_helper import PathHelper


class SchemaMixin:
    def _schema_quote_identifier(self, name):
        if hasattr(self, "_quote_identifier"):
            return self._quote_identifier(name)
        if not isinstance(name, str) or not name.replace("_", "").isalnum():
            raise ValueError(f"Invalid SQL identifier: {name!r}")
        return '"' + name.replace('"', '""') + '"'

    """Veritabanı şema ve yapı yönetimi için metodlar"""
    
    def backup_database(self, target_name=None):
        temp_path = None
        """Veritabanını yedekle"""
        try:
            backups_dir = os.path.join(PathHelper.get_app_data_dir(), "backups")
            os.makedirs(backups_dir, exist_ok=True)

            if target_name:
                safe_name = os.path.basename(str(target_name))
                if safe_name != str(target_name) or not safe_name:
                    raise ValueError("Invalid backup file name")
                backup_path = os.path.join(backups_dir, safe_name)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = os.path.join(backups_dir, f"ayecpro_backup_{timestamp}.db")

            temp_path = f"{backup_path}.tmp-{os.getpid()}"
            if os.path.exists(temp_path):
                os.remove(temp_path)

            db_name = getattr(self, "_db_name", "ayecpro.db")
            db_path = PathHelper.get_db_path(db_name)
            if os.path.exists(db_path):
                try:
                    self.conn.commit()
                    self.cursor.execute("PRAGMA wal_checkpoint(FULL)")
                    self.cursor.fetchall()
                except Exception as checkpoint_err:
                    logger.warning("Backup checkpoint warning: %s", checkpoint_err)

                from src.database import SQLCIPHER_AVAILABLE, sqlite3 as dbapi

                target_conn = dbapi.connect(temp_path)
                try:
                    if SQLCIPHER_AVAILABLE:
                        from src.utils.config import config

                        db_key = str(config.database_key).replace("'", "''")
                        target_conn.execute(f"PRAGMA key = '{db_key}'")
                        target_conn.execute("PRAGMA cipher_page_size = 4096")
                        target_conn.execute("PRAGMA kdf_iter = 256000")
                    self.conn.backup(target_conn)
                    integrity = target_conn.execute("PRAGMA integrity_check").fetchone()
                    if not integrity or integrity[0] != "ok":
                        raise RuntimeError(f"Backup integrity check failed: {integrity}")
                    target_conn.commit()
                finally:
                    target_conn.close()

                os.replace(temp_path, backup_path)
                temp_path = None

                # Zaman damgali manuel yedeklerde eski dosyalari temizle.
                if not target_name:
                    backups = sorted(
                        [os.path.join(backups_dir, f) for f in os.listdir(backups_dir) if f.endswith(".db")]
                    )
                    if len(backups) > 10:
                        for old_backup in backups[:-10]:
                            try:
                                os.remove(old_backup)
                            except OSError as cleanup_error:
                                logger.warning(
                                    "Old backup cleanup failed for %s: %s",
                                    old_backup,
                                    cleanup_error,
                                )
                return backup_path
            raise FileNotFoundError(f"Database file not found: {db_path}")
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return None
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError as cleanup_error:
                    logger.warning(
                        "Backup temp cleanup failed for %s: %s",
                        temp_path,
                        cleanup_error,
                    )

    def restore_database(self, source_path):
        """Restore a validated SQLite backup through the live connection."""
        source_path = os.path.abspath(str(source_path or ""))
        if not os.path.isfile(source_path):
            logger.error("Restore source does not exist: %s", source_path)
            return False

        source_conn = None
        try:
            from src.database import SQLCIPHER_AVAILABLE, sqlite3 as dbapi

            source_conn = dbapi.connect(source_path)
            if SQLCIPHER_AVAILABLE:
                from src.utils.config import config

                db_key = str(config.database_key).replace("'", "''")
                source_conn.execute(f"PRAGMA key = '{db_key}'")
                source_conn.execute("PRAGMA cipher_page_size = 4096")
                source_conn.execute("PRAGMA kdf_iter = 256000")

            integrity = source_conn.execute("PRAGMA integrity_check").fetchone()
            if not integrity or integrity[0] != "ok":
                raise RuntimeError(f"Restore integrity check failed: {integrity}")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_name = f"before_restore_{timestamp}.db"
            if not self.backup_database(target_name=safety_name):
                raise RuntimeError("Pre-restore safety backup could not be created")

            with self.lock:
                self.conn.commit()
                source_conn.backup(self.conn)
                self.conn.commit()
                self.cursor.execute("PRAGMA foreign_keys = ON")
                try:
                    self.cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    self.cursor.fetchall()
                except Exception as checkpoint_err:
                    logger.warning("Restore checkpoint warning: %s", checkpoint_err)

                restored_integrity = self.cursor.execute(
                    "PRAGMA integrity_check"
                ).fetchone()
                if not restored_integrity or restored_integrity[0] != "ok":
                    raise RuntimeError(
                        f"Restored database integrity check failed: {restored_integrity}"
                    )
            return True
        except Exception as e:
            logger.error("Restore error: %s", e)
            return False
        finally:
            if source_conn is not None:
                source_conn.close()
    
    def auto_backup(self):
        """Otomatik yedekleme (sessiz)"""
        try:
            self.backup_database()
            logger.info("Auto backup completed")
        except Exception as e:
            logger.error(f"Auto backup error: {e}")
    
    def update_soft_delete_schema(self):
        """Ensure all soft-delete columns exist in critical tables."""
        tables_to_check = {
            "services": ["is_deleted", "deleted_at"],
            "stock_movements": ["is_deleted", "deleted_at"],
            "used_parts": ["is_deleted", "deleted_at"]
        }
        for table, cols in tables_to_check.items():
            try:
                table_sql = self._schema_quote_identifier(table)
                self.cursor.execute("PRAGMA table_info({t})".format(t=table_sql))
                existing_cols = [row[1] for row in self.cursor.fetchall()]
                for col in cols:
                    if col not in existing_cols:
                        logger.info("Adding {c} to {t}".format(c=col, t=table))
                        dtype = "INTEGER DEFAULT 0" if col.startswith("is_") else "TEXT"
                        col_sql = self._schema_quote_identifier(col)
                        self.cursor.execute("ALTER TABLE {t} ADD COLUMN {c} {d}".format(t=table_sql, c=col_sql, d=dtype))
                self.conn.commit()
            except Exception as e:
                logger.error("Error updating soft delete for {t}: {e}".format(t=table, e=e))

    def update_registration_schema(self):
        """Registration tablosunu güncelle (registration_date kolonu)"""
        try:
            self.cursor.execute("PRAGMA table_info(registration)")
            columns = [row[1] for row in self.cursor.fetchall()]
            
            if "registration_date" not in columns:
                logger.info("Adding registration_date column to registration table")
                self.cursor.execute("ALTER TABLE registration ADD COLUMN registration_date TEXT")
                self.conn.commit()
        except Exception as e:
            logger.error(f"Registration schema update error: {e}")
    
    def create_indexes(self):
        """Performans indeksleri oluştur"""
        try:
            index_statements = [
                "CREATE INDEX IF NOT EXISTS idx_devices_tracking ON devices(tracking_no)",
                "CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)",
                "CREATE INDEX IF NOT EXISTS idx_devices_active_status ON devices(status, is_deleted, is_archived)",
                "CREATE INDEX IF NOT EXISTS idx_devices_customer ON devices(customer_id)",
                "CREATE INDEX IF NOT EXISTS idx_devices_customer_name ON devices(customer_name)",
                "CREATE INDEX IF NOT EXISTS idx_devices_dates ON devices(entry_date, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_devices_delivery ON devices(delivered_at, exit_date)",
                "CREATE INDEX IF NOT EXISTS idx_accounting_date ON accounting(date)",
                "CREATE INDEX IF NOT EXISTS idx_accounting_type_date ON accounting(type, date)",
                "CREATE INDEX IF NOT EXISTS idx_accounting_customer ON accounting(customer_id)",
                "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)",
                "CREATE INDEX IF NOT EXISTS idx_customers_deleted_name ON customers(is_deleted, name)",
                "CREATE INDEX IF NOT EXISTS idx_customers_partner_name ON customers(is_partner, name)",
                "CREATE INDEX IF NOT EXISTS idx_customer_balances_customer_currency ON customer_currency_balances(customer_id, currency)",
                "CREATE INDEX IF NOT EXISTS idx_currency_transactions_customer_type_balance ON currency_transactions(customer_id, transaction_type, current_balance)",
                "CREATE INDEX IF NOT EXISTS idx_parts_deleted_name ON parts(is_deleted, name)",
                "CREATE INDEX IF NOT EXISTS idx_parts_deleted_category ON parts(is_deleted, category)",
                "CREATE INDEX IF NOT EXISTS idx_parts_barcode ON parts(barcode)",
                "CREATE INDEX IF NOT EXISTS idx_parts_code ON parts(code)",
                "CREATE INDEX IF NOT EXISTS idx_used_parts_tracking ON used_parts(tracking_no)",
                "CREATE INDEX IF NOT EXISTS idx_used_parts_tracking_date ON used_parts(tracking_no, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_stock_movements_part_date ON stock_movements(part_id, date)",
                "CREATE INDEX IF NOT EXISTS idx_stock_movements_type_date ON stock_movements(type, date)",
                "CREATE INDEX IF NOT EXISTS idx_payments_customer_date ON payments(customer_id, payment_date)",
                "CREATE INDEX IF NOT EXISTS idx_payment_debt_payment ON payment_debt_links(payment_id)",
                "CREATE INDEX IF NOT EXISTS idx_payment_debt_debt ON payment_debt_links(debt_transaction_id)",
                "CREATE INDEX IF NOT EXISTS idx_appointments_date_status ON appointments(date, status)",
                "CREATE INDEX IF NOT EXISTS idx_service_logs_tracking_date ON service_logs(device_tracking_no, created_at)",
                "CREATE INDEX IF NOT EXISTS idx_partner_shipments_partner ON partner_shipments(partner_id)",
                "CREATE INDEX IF NOT EXISTS idx_partner_documents_partner ON partner_documents(partner_id)",
                "CREATE INDEX IF NOT EXISTS idx_partner_timeline_partner_date ON partner_timeline(partner_id, event_date)",
            ]
            for sql in index_statements:
                try:
                    self.cursor.execute(sql)
                except Exception as index_err:
                    logger.debug(f"Index skipped: {sql} ({index_err})")
            self.conn.commit()
        except Exception as e:
            logger.error(f"Index creation error: {e}")
    
    def execute_read_only_query(self, sql):
        """Salt-okunur SQL sorgusu çalıştır (Jarvis için)"""
        try:
            # Güvenlik kontrolü - sadece SELECT
            if not sql.strip().upper().startswith("SELECT"):
                logger.warning(f"Non-SELECT query blocked: {sql}")
                return None
            
            normalized_sql = str(sql or "").strip()
            blocked_tables = {
                "users",
                "settings",
                "internal_settings",
                "bank_accounts",
                "audit_logs",
                "licensing",
                "license_keys",
                "api_keys",
            }
            table_refs = {
                match.group(2).lower()
                for match in re.finditer(
                    r"\b(from|join)\s+[`\"']?([a-zA-Z_][a-zA-Z0-9_]*)[`\"']?",
                    normalized_sql,
                    flags=re.IGNORECASE,
                )
            }
            blocked_refs = table_refs & blocked_tables
            if blocked_refs:
                logger.warning("Read-only query blocked for sensitive table(s): %s", ", ".join(sorted(blocked_refs)))
                return None

            self.cursor.execute(normalized_sql)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Read-only query error: {e}")
            return None
    
    def close(self):
        """Veritabanı bağlantısını kapat"""
        try:
            if self.conn:
                self.conn.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Close error: {e}")
        try:
            if hasattr(self, "_is_closed"):
                self._is_closed = True
            if hasattr(self, "_conn"):
                self._conn = None
            if hasattr(self, "_cursor"):
                self._cursor = None
        except Exception:
            pass
