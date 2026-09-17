# -*- coding: utf-8 -*-

import json
import sqlite3
from datetime import datetime, timedelta

from src.utils.logger import logger
from src.utils.status_utils import normalize_device_status


class DatabaseLegacyPart4Mixin:
    def advanced_search(self, criteria):
        # criteria: {'customer': '', 'tracking': '', 'serial': '', 'fault': '', 'date_start': '', 'date_end': ''}
        query = "SELECT * FROM devices WHERE 1=1"
        params = []
        
        if criteria.get('customer'):
            query += " AND customer_name LIKE ?"
            params.append(f"%{criteria['customer']}%")
        
        if criteria.get('tracking'):
            query += " AND tracking_no LIKE ?"
            params.append(f"%{criteria['tracking']}%")
            
        if criteria.get('serial'):
            query += " AND serial_no LIKE ?"
            params.append(f"%{criteria['serial']}%")
            
        if criteria.get('fault') and criteria['fault'] != "Tümü":
            query += " AND fault_category = ?"
            params.append(criteria['fault'])
            
        if criteria.get('date_start'):
            query += " AND entry_date >= ?"
            params.append(criteria['date_start'])
            
        if criteria.get('date_end'):
            query += " AND entry_date <= ?"
            params.append(criteria['date_end'])
            
        self.cursor.execute(query, params)
        return self.cursor.fetchall()


    def close(self):
        """Veritabanı bağlantısını kapat"""
        try:
            self._is_closed = True
            if self._conn is not None:
                self._conn.close()
        except Exception as e:
            logger.warning(f"Database connection close error: {e}")
        try:
            self._conn = None
            self._cursor = None
        except Exception:
            pass


    def get_stats(self):
        try:
            self.cursor.execute("SELECT status, COUNT(*) FROM devices WHERE is_archived = 0 GROUP BY status")
            return dict(self.cursor.fetchall())
        except Exception as e:
            logger.error(f"Get stats error: {e}")
            return {}

    # --- DIŞ SERVİS / GARANTİ TAKİP ---

    def create_loaner_tables(self):
        """Create/repair loaner (consignment) device tracking tables."""
        try:
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS loaner_devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_type TEXT,
                    brand_model TEXT NOT NULL,
                    serial_mac TEXT NOT NULL UNIQUE,
                    status TEXT DEFAULT 'Depoda',
                    daily_penalty_fee REAL DEFAULT 0,
                    shelf_no TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS loaner_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id INTEGER NOT NULL,
                    customer_name TEXT NOT NULL,
                    customer_phone TEXT,
                    tracking_no TEXT,
                    condition_out TEXT,
                    condition_in TEXT,
                    date_given TEXT DEFAULT CURRENT_TIMESTAMP,
                    expected_return TEXT,
                    date_returned TEXT,
                    penalty_applied REAL DEFAULT 0,
                    status TEXT DEFAULT 'Aktif',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES loaner_devices(id) ON DELETE CASCADE
                )
                """
            )

            # Migration safety for existing databases
            self._ensure_column("loaner_devices", "device_type", "TEXT")
            self._ensure_column("loaner_devices", "brand_model", "TEXT")
            self._ensure_column("loaner_devices", "serial_mac", "TEXT")
            self._ensure_column("loaner_devices", "status", "TEXT DEFAULT 'Depoda'")
            self._ensure_column("loaner_devices", "daily_penalty_fee", "REAL DEFAULT 0")
            self._ensure_column("loaner_devices", "shelf_no", "TEXT")
            self._ensure_column("loaner_devices", "notes", "TEXT")
            self._ensure_column("loaner_devices", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

            self._ensure_column("loaner_transactions", "device_id", "INTEGER")
            self._ensure_column("loaner_transactions", "customer_name", "TEXT")
            self._ensure_column("loaner_transactions", "customer_phone", "TEXT")
            self._ensure_column("loaner_transactions", "tracking_no", "TEXT")
            self._ensure_column("loaner_transactions", "condition_out", "TEXT")
            self._ensure_column("loaner_transactions", "condition_in", "TEXT")
            self._ensure_column("loaner_transactions", "date_given", "TEXT DEFAULT CURRENT_TIMESTAMP")
            self._ensure_column("loaner_transactions", "expected_return", "TEXT")
            self._ensure_column("loaner_transactions", "date_returned", "TEXT")
            self._ensure_column("loaner_transactions", "penalty_applied", "REAL DEFAULT 0")
            self._ensure_column("loaner_transactions", "status", "TEXT DEFAULT 'Aktif'")
            self._ensure_column("loaner_transactions", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")

            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_loaner_devices_status ON loaner_devices(status)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_loaner_tx_status ON loaner_transactions(status)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_loaner_tx_device_id ON loaner_transactions(device_id)"
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"create_loaner_tables error: {e}")
            self.conn.rollback()


    def _ensure_column(self, table_name, column_name, ddl):
        """Add a column if it does not exist."""
        try:
            cols = self._get_table_columns(table_name)
            if column_name not in cols:
                safe_table = self._safe_identifier(table_name)
                safe_column = self._safe_identifier(column_name)
                self.cursor.execute(
                    "ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}".format(
                        table_name=safe_table,
                        column_name=safe_column,
                        ddl=ddl,
                    )
                )
        except Exception as e:
            logger.debug(f"ensure_column skipped ({table_name}.{column_name}): {e}")


    def create_external_tracking_table(self):
        """Dış servis / Garanti takip tablosunu oluştur"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS external_warranty_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                internal_tracking_no TEXT, -- Müşteri Emanet No
                customer_name TEXT,
                product_name TEXT,
                external_service_name TEXT, -- Gönderilen Servis/Yer
                external_service_no TEXT,   -- Servis Kayıt Numarası
                sent_date TEXT,
                outbound_cargo_no TEXT,
                inbound_cargo_no TEXT,
                status TEXT,               -- Servise Ulaştı, Onarımda, vb.
                notes TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()


    def get_external_trackings(self):
        self.cursor.execute("SELECT * FROM external_warranty_tracking ORDER BY id DESC")
        return self.cursor.fetchall()


    def add_external_tracking(self, data):
        self.cursor.execute("""
            INSERT INTO external_warranty_tracking (
                internal_tracking_no, customer_name, product_name, 
                external_service_name, external_service_no, sent_date, 
                outbound_cargo_no, inbound_cargo_no, status, notes, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('internal_no'), data.get('customer'), data.get('product'),
            data.get('service'), data.get('service_no'), data.get('date'),
            data.get('out_cargo'), data.get('in_cargo'), data.get('status'),
            data.get('notes'), datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        self.conn.commit()
        return self.cursor.lastrowid


    def update_external_tracking(self, track_id, data):
        self.cursor.execute("""
            UPDATE external_warranty_tracking SET 
                internal_tracking_no=?, customer_name=?, product_name=?, 
                external_service_name=?, external_service_no=?, sent_date=?, 
                outbound_cargo_no=?, inbound_cargo_no=?, status=?, notes=?
            WHERE id=?
        """, (
            data.get('internal_no'), data.get('customer'), data.get('product'),
            data.get('service'), data.get('service_no'), data.get('date'),
            data.get('out_cargo'), data.get('in_cargo'), data.get('status'),
            data.get('notes'), track_id
        ))
        self.conn.commit()


    def delete_external_tracking(self, track_id):
        self.soft_delete_record("external_warranty_tracking", "id", track_id)


    def get_summary_data(self):
        """Yönetici Özeti için toplu veri analizi."""
        now = datetime.now()
        today_iso = now.strftime("%Y-%m-%d")
        from src.utils.date_utils import format_turkish_date
        today_tr = format_turkish_date(now, "short")

        def _table_exists(table_name: str) -> bool:
            try:
                self.cursor.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
                    (table_name,),
                )
                return self.cursor.fetchone() is not None
            except Exception:
                return False

        def _table_columns(table_name: str) -> set:
            try:
                self.cursor.execute(
                    "PRAGMA table_info({table_name})".format(
                        table_name=self._safe_identifier(table_name)
                    )
                )
                return {r[1] for r in (self.cursor.fetchall() or [])}
            except Exception:
                return set()

        def _safe_scalar(sql: str, params=(), default=0):
            try:
                self.cursor.execute(sql, params)
                row = self.cursor.fetchone()
                if not row:
                    return default
                val = row[0]
                return default if val is None else val
            except Exception:
                return default

        daily_turnover = 0
        total_receivables = 0
        new_jobs_today = 0
        brand_dist = []
        critical_stock_count = 0
        inventory_value = 0
        unique_customers = 0

        if _table_exists("accounting"):
            cols = _table_columns("accounting")
            if {"type", "date"}.issubset(cols) and ("amount" in cols or "try_equivalent" in cols):
                daily_turnover = _safe_scalar(
                    "SELECT SUM(COALESCE(try_equivalent, amount)) FROM accounting WHERE type='Gelir' AND date = ? AND COALESCE(is_deleted, 0) = 0",
                    (today_iso,),
                    0,
                )

        if _table_exists("devices"):
            cols = _table_columns("devices")
            if "price" in cols and "status" in cols:
                total_receivables = _safe_scalar(
                    "SELECT SUM(price) FROM devices WHERE status != 'Teslim Edildi' AND status != 'İptal'",
                    (),
                    0,
                )

            if "entry_date" in cols:
                new_jobs_today = _safe_scalar(
                    "SELECT COUNT(*) FROM devices WHERE entry_date LIKE ? OR entry_date LIKE ?",
                    (f"{today_iso}%", f"%{today_tr}%"),
                    0,
                )

            if "device_brand" in cols:
                try:
                    self.cursor.execute(
                        "SELECT device_brand, COUNT(*) as c FROM devices GROUP BY device_brand ORDER BY c DESC LIMIT 5"
                    )
                    brand_dist = self.cursor.fetchall() or []
                except Exception:
                    brand_dist = []

            if "customer_name" in cols:
                unique_customers = _safe_scalar(
                    "SELECT COUNT(DISTINCT customer_name) FROM devices",
                    (),
                    0,
                )

        if _table_exists("parts"):
            cols = _table_columns("parts")
            stock_col = "stock" if "stock" in cols else None
            # Envanter değeri için mümkünse alış fiyatını (purchase_price) kullan
            cost_col = "purchase_price" if "purchase_price" in cols else ("price" if "price" in cols else None)
            min_stock_col = "min_stock" if "min_stock" in cols else None

            if stock_col and min_stock_col:
                critical_stock_count = _safe_scalar(
                    f"SELECT COUNT(*) FROM parts WHERE {stock_col} <= {min_stock_col}",
                    (),
                    0,
                )
            elif stock_col:
                critical_stock_count = _safe_scalar(
                    f"SELECT COUNT(*) FROM parts WHERE {stock_col} <= 5",
                    (),
                    0,
                )

            if stock_col and cost_col:
                inventory_value = _safe_scalar(
                    f"SELECT SUM({stock_col} * {cost_col}) FROM parts",
                    (),
                    0,
                )

        elif _table_exists("stock"):
            cols = _table_columns("stock")
            qty_col = "quantity" if "quantity" in cols else ("stock" if "stock" in cols else None)
            min_col = "min_stock" if "min_stock" in cols else None
            cost_col = "purchase_price" if "purchase_price" in cols else ("price" if "price" in cols else ("unit_price" if "unit_price" in cols else None))

            if qty_col and min_col:
                critical_stock_count = _safe_scalar(
                    f"SELECT COUNT(*) FROM stock WHERE {qty_col} <= {min_col}",
                    (),
                    0,
                )
            elif qty_col:
                critical_stock_count = _safe_scalar(
                    f"SELECT COUNT(*) FROM stock WHERE {qty_col} <= 5",
                    (),
                    0,
                )

            if qty_col and cost_col:
                inventory_value = _safe_scalar(
                    f"SELECT SUM({qty_col} * {cost_col}) FROM stock",
                    (),
                    0,
                )

        return {
            "daily_turnover": daily_turnover,
            "total_receivables": total_receivables,
            "new_jobs_today": new_jobs_today,
            "brand_dist": brand_dist,
            "critical_stock_count": critical_stock_count,
            "inventory_value": inventory_value,
            "unique_customers": unique_customers,
        }

    def get_sectoral_widget_data(self):
        try:
            today_iso = datetime.now().strftime("%Y-%m-%d")
            sector = self.get_internal_setting("current_sector", "teknik_servis")
            data = {
                "pending_repair": 0,
                "delivered_today": 0,
                "service_revenue": 0.0,
                "critical_parts": 0,
                "inspection_due": 0,
                "approval_pending": 0,
            }

            summary = self.get_summary_data() if hasattr(self, "get_summary_data") else {}
            data["critical_parts"] = int(summary.get("critical_stock_count", 0) or 0)

            try:
                self.cursor.execute(
                    """
                    SELECT status, delivered_at, exit_date
                    FROM devices
                    WHERE COALESCE(is_deleted, 0)=0
                      AND COALESCE(is_archived, 0)=0
                    """
                )
                rows = self.cursor.fetchall() or []
                if sector == "otomotiv":
                    data["pending_repair"] = sum(
                        1
                        for row in rows
                        if normalize_device_status(row[0] if row else None) not in ("Teslim Edildi", "İptal")
                    )
                    data["delivered_today"] = sum(
                        1
                        for row in rows
                        if normalize_device_status(row[0] if row else None) == "Teslim Edildi"
                        and (
                            str((row[1] if len(row) > 1 else "") or "")[:10] == today_iso
                            or str((row[2] if len(row) > 2 else "") or "")[:10] == today_iso
                        )
                    )
                else:
                    data["pending_repair"] = sum(
                        1
                        for row in rows
                        if normalize_device_status(row[0] if row else None) == "Bekliyor"
                    )
            except Exception:
                pass

            if sector != "otomotiv":
                try:
                    self.cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM devices
                        WHERE COALESCE(is_deleted, 0)=0
                          AND (status='Teslim Edildi')
                          AND (
                              COALESCE(substr(delivered_at, 1, 10), '')=?
                              OR COALESCE(exit_date, '')=?
                          )
                        """,
                        (today_iso, today_iso),
                    )
                    data["delivered_today"] = int((self.cursor.fetchone() or [0])[0] or 0)
                except Exception:
                    pass

            try:
                self.cursor.execute(
                    """
                    SELECT COALESCE(SUM(COALESCE(try_equivalent, amount)), 0)
                    FROM accounting
                    WHERE type='Gelir' AND date=?
                      AND COALESCE(is_deleted, 0)=0
                    """,
                    (today_iso,),
                )
                data["service_revenue"] = float((self.cursor.fetchone() or [0])[0] or 0)
            except Exception:
                pass

            if sector == "otomotiv":
                try:
                    self.cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM vehicle_maintenance_cards
                        WHERE COALESCE(inspection_notice_date, '') <= ?
                          AND COALESCE(inspection_due_date, '') >= ?
                        """,
                        (today_iso, today_iso),
                    )
                    data["inspection_due"] = int((self.cursor.fetchone() or [0])[0] or 0)
                except Exception:
                    pass

                try:
                    self.cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM devices
                        WHERE COALESCE(is_deleted, 0)=0
                          AND COALESCE(is_archived, 0)=0
                          AND COALESCE(approval_status, '') IN ('Musteri Onayi Bekliyor', 'Beklemede', 'Bekleme')
                        """
                    )
                    data["approval_pending"] = int((self.cursor.fetchone() or [0])[0] or 0)
                except Exception:
                    pass

            return data
        except Exception as e:
            logger.error(f"get_sectoral_widget_data error: {e}")
            return {}


    def get_technician_performance(self):
        """Teknisyenlerin kapattığı iş sayıları."""
        # service_logs tablosundan log_type 'Technician' olan ve mesajda status değişikliği içerenleri sayalım
        try:
            self.cursor.execute("""
                SELECT user, COUNT(*) as jobs 
                FROM service_logs 
                WHERE message LIKE '%Durum değiştirildi%' 
                GROUP BY user 
                ORDER BY jobs DESC
            """)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Technician performance fetch error: {e}")
            return []

    # Shadowed stock methods (use_part, add_used_part, etc.) have been moved to StockMixin


    def save_test_results(self, tracking_no, tests, technician="Teknisyen"):
        # Önce eskileri temizle
        self.cursor.execute("DELETE FROM device_tests WHERE tracking_no=?", (tracking_no,))
        
        test_date = datetime.now().strftime("%Y-%m-%d")
        for test_name, result in tests.items():
            self.cursor.execute("INSERT INTO device_tests (tracking_no, test_name, result, technician, test_date) VALUES (?, ?, ?, ?, ?)",
                                (tracking_no, test_name, result, technician, test_date))
        self.conn.commit()


    def get_test_results(self, tracking_no):
        self.cursor.execute("SELECT test_name, result FROM device_tests WHERE tracking_no=?", (tracking_no,))
        return dict(self.cursor.fetchall())


    def update_financials(self, tracking_no, labor_cost, repair_details):
        self.cursor.execute("UPDATE devices SET labor_cost=?, repair_details=? WHERE tracking_no=?",
                            (labor_cost, repair_details, tracking_no))
        self.conn.commit()

    # --- Muhasebe Metodları ---

    def add_transaction(
        self,
        t_type,
        category,
        amount,
        description,
        customer_name=None,
        customer_id=None,
        date=None,
        payment_method=None,
        bank_account_id=None,
        related_account_id=None,
        project_id=None,
        tracking_no=None,
        ref_no=None,
        selected_services=None,
        currency='TRY',
        original_amount=None,
        exchange_rate=None,
        product_service_id=None,
        product_service_type=None,
        commit=True,
    ):
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("PRAGMA table_info(accounting)")
        cols = [r[1] for r in self.cursor.fetchall()]

        # Currency and TRY equivalent
        currency = (currency or 'TRY').upper()
        orig_amount = float(
            original_amount if original_amount is not None else amount
        )
        try_equiv = float(amount)

        rate = 1.0
        if currency != 'TRY':
            from src.utils.currency_helper import CurrencyHelper

            rate = (
                float(exchange_rate)
                if exchange_rate is not None
                else CurrencyHelper.require_rate(self, currency)
            )
            if rate <= 0:
                raise ValueError(
                    f"Exchange rate unavailable: {currency}"
                )
            try_equiv = round(orig_amount * rate, 2)
            amount = try_equiv
            sym = (
                "$"
                if currency == "USD"
                else "\u20ac"
                if currency == "EUR"
                else currency
            )
            description = (
                f"{description} | {orig_amount:,.2f} {sym} = "
                f"{try_equiv:,.2f} \u20ba (TCMB kuru: {rate:.4f})"
            )

        # Payment number
        pay_no = None
        if "payment_no" in cols:
            try:
                prefix = self.get_setting("payment_number_prefix", "PAY")
                next_n = int(self.get_setting("payment_number_next", "1"))
                pay_no = f"{prefix}-{next_n:06d}"
                self.cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    ("payment_number_next", str(next_n + 1)),
                )
                if hasattr(self, "update_settings_cache_entry"):
                    self.update_settings_cache_entry(
                        "settings",
                        "payment_number_next",
                        str(next_n + 1),
                    )
            except (sqlite3.Error, TypeError, ValueError) as exc:
                logger.warning("Payment number could not be generated: %s", exc)
                pay_no = None

        insert_cols = ["type", "category", "amount", "description", "date", "created_at", "customer_name", "customer_id"]
        values = [t_type, category, amount, description, date, created, customer_name, customer_id]

        if "payment_method" in cols:
            insert_cols.append("payment_method"); values.append(payment_method)
        if "bank_account_id" in cols:
            insert_cols.append("bank_account_id"); values.append(bank_account_id)
        if "related_account_id" in cols:
            insert_cols.append("related_account_id"); values.append(related_account_id)
        if "project_id" in cols:
            insert_cols.append("project_id"); values.append(project_id)
        if "tracking_no" in cols:
            insert_cols.append("tracking_no"); values.append(tracking_no)
        if "ref_no" in cols:
            ref_val = ref_no or tracking_no
            insert_cols.append("ref_no"); values.append(ref_val)
        if "selected_services" in cols:
            encoded = None
            if isinstance(selected_services, (list, tuple, set, dict)):
                try:
                    encoded = json.dumps(selected_services, ensure_ascii=False)
                except (TypeError, ValueError) as exc:
                    raise ValueError(
                        "Selected service details could not be serialized"
                    ) from exc
            elif isinstance(selected_services, str):
                encoded = selected_services
            insert_cols.append("selected_services"); values.append(encoded)
        if "product_service_id" in cols and product_service_id:
            insert_cols.append("product_service_id"); values.append(product_service_id)
        if "product_service_type" in cols and product_service_type:
            insert_cols.append("product_service_type"); values.append(product_service_type)
        if "currency" in cols:
            insert_cols.append("currency"); values.append(currency)
        if "exchange_rate" in cols:
            insert_cols.append("exchange_rate"); values.append(rate)
        if "try_equivalent" in cols:
            insert_cols.append("try_equivalent"); values.append(try_equiv)
        if "original_amount" in cols:
            insert_cols.append("original_amount"); values.append(orig_amount)
        if "payment_no" in cols and pay_no:
            insert_cols.append("payment_no"); values.append(pay_no)

        # Validate column names
        for col in insert_cols:
            if not col.replace('_', '').isalnum():
                logger.error(f"Invalid column name in INSERT: {col}")
                return None

        placeholders = ", ".join(["?"] * len(insert_cols))
        col_list = ", ".join(self._safe_identifier(col) for col in insert_cols)
        try:
            self.cursor.execute(
                "INSERT INTO accounting ({columns}) VALUES ({placeholders})".format(
                    columns=col_list,
                    placeholders=placeholders,
                ),
                tuple(values),
            )
            transaction_id = self.cursor.lastrowid
            if bank_account_id:
                delta = amount if str(t_type).lower() == "gelir" else -float(amount or 0)
                updated_balance = self.update_bank_balance(
                    bank_account_id,
                    delta,
                    cursor=self.cursor,
                )
                if updated_balance is None:
                    raise RuntimeError("Bank balance could not be updated")
            if commit:
                self.conn.commit()
        except Exception:
            if commit:
                self.conn.rollback()
            raise

        pm = str(payment_method or "").lower()
        if commit and (
            bank_account_id
            or pm in ("banka", "havale", "eft", "transfer")
        ):
            try:
                from src.utils.audit_logger import get_audit_logger
                audit = get_audit_logger(self)
                audit.log_action("accounting", "BANK_TX", f"{t_type} | {category} | {amount} | {payment_method or ''} | Bank ID {bank_account_id or ''}")
            except Exception as exc:
                logger.warning("Bank transaction audit failed: %s", exc)
        msg = f"{amount} TL {t_type} giri\u015fi: {category}"
        if customer_name:
            msg = (
                f"{customer_name} taraf\u0131ndan {amount} TL "
                f"\u00f6deme al\u0131nd\u0131."
            )
        if commit:
            try:
                self.notify_jarvis(msg, 'payment', t_type == 'Gelir')
            except Exception as exc:
                logger.warning("Payment voice notification failed: %s", exc)
        return transaction_id






    def get_transactions(self):
        self.cursor.execute("SELECT * FROM accounting WHERE COALESCE(is_deleted, 0) = 0 ORDER BY date DESC")
        return self.cursor.fetchall()


    def get_balance(self):
        self.cursor.execute("SELECT SUM(amount) FROM accounting WHERE type='Gelir' AND COALESCE(is_deleted, 0) = 0")
        income = self.cursor.fetchone()[0] or 0
        self.cursor.execute("SELECT SUM(amount) FROM accounting WHERE type='Gider' AND COALESCE(is_deleted, 0) = 0")
        expense = self.cursor.fetchone()[0] or 0
        return income, expense, income - expense


    def auto_backup(self):
        """Program açılışında veya kritik anlarda sessizce yedek al"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_database(
                target_name=f"autobackup_{timestamp}.db"
            )
            if not backup_path:
                raise RuntimeError("Automatic database snapshot failed")
            self.add_audit_log("Sistem", "database", "BACKUP", f"Otomatik yedek alındı: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Auto backup error: {e}")
            return None


    def get_weekly_stats(self):
        """Son 7 günün iş sayılarını getir (Grafik için)"""
        stats = []
        import datetime as dt
        for i in range(6, -1, -1):
            date_str = (dt.datetime.now() - dt.timedelta(days=i)).strftime("%Y-%m-%d")
            self.cursor.execute("SELECT COUNT(*) FROM devices WHERE entry_date LIKE ?", (f"{date_str}%",))
            stats.append(self.cursor.fetchone()[0])
        return stats


    def export_to_csv(self, table_name, file_path):
        """Herhangi bir tabloyu CSV'ye aktar (Pandas/Excel bağımsız)"""
        try:
            import csv
            safe_table = self._safe_identifier(table_name)
            self.cursor.execute("SELECT * FROM {table_name}".format(table_name=safe_table))
            rows = self.cursor.fetchall()
            
            self.cursor.execute("PRAGMA table_info({table_name})".format(table_name=safe_table))
            headers = [col[1] for col in self.cursor.fetchall()]
            
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(headers)
                writer.writerows(rows)
            
            self.add_audit_log("Sistem", safe_table, "EXPORT", f"Tablo CSV'ye aktarıldı: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Export error: {e}")
            return False


    def get_part_by_barcode(self, barcode):
        self.cursor.execute("SELECT * FROM parts WHERE barcode=?", (barcode,))
        return self.cursor.fetchone()


    def get_staff_productivity(self):
        """Personel verimlilik puanlarını hesapla (Kurumsal Takip)"""
        # Formül: (Tamamlanan İş * 10) + (Toplam Tahsilat / 100)
        self.cursor.execute("""
            SELECT technician, 
                   COUNT(*) as total_jobs,
                   SUM(price) as total_volume
            FROM devices 
            WHERE status='Tamamlandı' AND technician IS NOT NULL
            GROUP BY technician
        """)
        raw_stats = self.cursor.fetchall()
        
        scores = []
        for tech, jobs, volume in raw_stats:
            score = (jobs * 10) + (volume / 100)
            scores.append({
                "name": tech,
                "jobs": jobs,
                "volume": volume,
                "score": round(score, 1)
            })
        return sorted(scores, key=lambda x: x['score'], reverse=True)

    # --- Personel Metodları ---

    def add_personnel(self, name, role, phone, salary, commission=0):
        start_date = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute("INSERT INTO personnel (name, role, phone, salary, start_date, commission_rate) VALUES (?, ?, ?, ?, ?, ?)",
                            (name, role, phone, salary, start_date, commission))
        self.conn.commit()


    def get_all_personnel(self):
        self.cursor.execute("SELECT * FROM personnel")
        return self.cursor.fetchall()


    def get_kb_articles(self, query=""):
        if not query:
            self.cursor.execute("SELECT * FROM kb_articles ORDER BY id DESC")
            return self.cursor.fetchall()
            
        # Gelişmiş Arama Algoritması: Anahtar Kelime Skorlama
        keywords = query.lower().split()
        self.cursor.execute("SELECT * FROM kb_articles")
        all_articles = self.cursor.fetchall()
        
        scored_articles = []
        for art in all_articles:
            # art: (id, title, content, tags, created_at)
            id_val, title, content, tags, created_at = art
            score = 0
            
            title_lower = title.lower() if title else ""
            content_lower = content.lower() if content else ""
            tags_lower = tags.lower() if tags else ""
            
            for kw in keywords:
                # Başlıkta eşleşme (Yüksek öncelik)
                if kw in title_lower:
                    score += 10
                # Etiketlerde eşleşme (Orta öncelik)
                if kw in tags_lower:
                    score += 5
                # İçerikte eşleşme (Düşük öncelik)
                if kw in content_lower:
                    score += 1
            
            if score > 0:
                scored_articles.append((score, art))
        
        # Skora göre azalan şekilde sırala
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        return [art for score, art in scored_articles]


    def add_kb_article(self, title, content, tags=""):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO kb_articles (title, content, tags, created_at) VALUES (?, ?, ?, ?)",
                            (title, content, tags, now))
        self.conn.commit()

    # --- HİZMET YÖNETİMİ METODLARI ---


    def create_services_table(self):
        """Hizmetler tablosu oluştur"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                price REAL DEFAULT 0,
                currency TEXT DEFAULT 'TRY',
                description TEXT,
                created_at TEXT,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
        """)
        self.conn.commit()
    


    def update_services_schema(self):
        """Services tablosuna runtime uyumlu alanları ekle"""
        try:
            self.cursor.execute("PRAGMA table_info(services)")
            columns = [row[1] for row in self.cursor.fetchall()]
            if "barcode" not in columns:
                self.cursor.execute("ALTER TABLE services ADD COLUMN barcode TEXT")
            if "currency" not in columns:
                self.cursor.execute("ALTER TABLE services ADD COLUMN currency TEXT DEFAULT 'TRY'")
                self.conn.commit()
        except Exception as e:
            logger.error(f"Services schema update error: {e}")


    def get_services_list(self):
        """Tüm hizmetleri listele (En yeni üstte)"""
        try:
            # Ensure table exists
            self.create_services_table()
            self.update_services_schema()
            
            # Fetch services ordered by created_at DESC (as proxy for date)
            self.cursor.execute("SELECT id, name, price, currency, description, barcode, created_at FROM services WHERE COALESCE(is_deleted, 0) = 0 ORDER BY created_at DESC")
            rows = self.cursor.fetchall()
            return [{'id': r[0], 'name': r[1], 'price': r[2], 'currency': r[3] or 'TRY', 'description': r[4] or '', 'barcode': r[5] or '', 'date': r[6]} for r in rows]
        except Exception as e:
            logger.error(f"Services list error: {e}")
            return []
            

    def get_service_by_barcode(self, barcode):
        """Barkod ile hizmet ara"""
        try:
            self.cursor.execute("SELECT id, name, price, description, barcode FROM services WHERE barcode=? AND COALESCE(is_deleted, 0) = 0", (barcode,))
            row = self.cursor.fetchone()
            if row:
                return {'id': row[0], 'name': row[1], 'price': row[2], 'description': row[3], 'barcode': row[4]}
            return None
        except Exception as e:
            logger.error(f"Get service by barcode error: {e}")
            return None
    

    def add_service(self, name, price, description="", barcode="", currency="TRY"):
        """Yeni hizmet ekle"""
        try:
            self.create_services_table()
            self.update_services_schema()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "INSERT INTO services (name, price, currency, description, barcode, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (name, price, (currency or "TRY").upper(), description, barcode, created_at)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Service add error: {e}")
            raise e
    

    def update_service(self, service_id, name, price, description="", barcode="", currency="TRY"):
        """Hizmet güncelle"""
        try:
            self.update_services_schema()
            self.cursor.execute(
                "UPDATE services SET name=?, price=?, currency=?, description=?, barcode=? WHERE id=?",
                (name, price, (currency or "TRY").upper(), description, barcode, service_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Service update error: {e}")
            raise e
    

    def delete_service(self, service_id):
        """Hizmet sil"""
        try:
            return self.soft_delete_record("services", "id", service_id)
        except Exception as e:
            logger.error(f"Service delete error: {e}")
            raise e


    def add_transaction_with_customer(self, customer_id, date, description, amount, t_type="Gelir", category="Satış", vat_rate=0, payment_method=None, bank_account_id=None):
        """Müşteriye bağlı işlem ekle"""
        try:
            # Get customer name for redundancy/easier querying
            customer_name = "Peşin Satış (Genel)"
            
            if customer_id:
                try:
                    self.cursor.execute("SELECT name FROM customers WHERE id=?", (customer_id,))
                    row = self.cursor.fetchone()
                    if row:
                        customer_name = row[0]
                except Exception as e:
                    logger.debug(f"Could not fetch customer name for transaction {customer_id}: {e}")

            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("PRAGMA table_info(accounting)")
            cols = [r[1] for r in self.cursor.fetchall()]
            insert_cols = ["type", "category", "amount", "description", "date", "created_at", "customer_id", "customer_name"]
            values = [t_type, category, amount, description, date, created_at, customer_id, customer_name]
            if "payment_method" in cols:
                insert_cols.append("payment_method")
                values.append(payment_method)
            if "bank_account_id" in cols:
                insert_cols.append("bank_account_id")
                values.append(bank_account_id)
            # Validate all column names to prevent SQL injection
            for col in insert_cols:
                if not col.replace('_', '').isalnum():
                    logger.error(f"Invalid column name in INSERT: {col}")
                    return None
            
            placeholders = ", ".join(["?"] * len(insert_cols))
            col_list = ", ".join(self._safe_identifier(col) for col in insert_cols)
            try:
                self.cursor.execute(
                    "INSERT INTO accounting ({columns}) VALUES ({placeholders})".format(
                        columns=col_list,
                        placeholders=placeholders,
                    ),
                    tuple(values),
                )
                transaction_id = self.cursor.lastrowid
                if bank_account_id:
                    delta = amount if str(t_type).lower() == "gelir" else -float(amount or 0)
                    updated_balance = self.update_bank_balance(
                        bank_account_id,
                        delta,
                        cursor=self.cursor,
                    )
                    if updated_balance is None:
                        raise RuntimeError("Bank balance could not be updated")
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

            pm = str(payment_method or "").lower()
            if bank_account_id or pm in ("banka", "havale", "eft", "transfer"):
                try:
                    from src.utils.audit_logger import get_audit_logger
                    audit = get_audit_logger(self)
                    audit.log_action("accounting", "BANK_TX", f"{t_type} | {category} | {amount} | {payment_method or ''} | Bank ID {bank_account_id or ''}")
                except Exception as audit_error:
                    logger.warning(
                        "Bank transaction audit failed: %s",
                        audit_error,
                    )
            return transaction_id
        except Exception as e:
            logger.error(f"Transaction add error: {e}")
            raise e


    def get_uninvoiced_transactions(self, customer_id):
        """Faturalanmamış satış işlemlerini (TL + Döviz) getir"""
        try:
            transactions = []
            
            # 1. TL İşlemleri (accounting tablosu)
            self.cursor.execute("""
                SELECT id, date, description, amount, category 
                FROM accounting 
                WHERE customer_id = ? AND type = 'Gelir' AND category = 'Satış' AND is_invoiced = 0
                ORDER BY date DESC
            """, (customer_id,))
            for r in self.cursor.fetchall():
                transactions.append({
                    'id': r[0], 'date': r[1], 'description': r[2], 
                    'amount': r[3], 'currency': 'TRY', 'source': 'accounting'
                })
                
            # 2. Dövizli İşlemler (currency_transactions tablosu)
            # transaction_type = 'DEBIT' (Müşteri Borç / Satış)
            self.cursor.execute("""
                SELECT id, created_at, description, amount, currency, try_equivalent
                FROM currency_transactions
                WHERE customer_id = ? AND transaction_type = 'DEBIT' AND is_invoiced = 0
                ORDER BY created_at DESC
            """, (customer_id,))
            for r in self.cursor.fetchall():
                transactions.append({
                    'id': r[0], 'date': r[1], 'description': r[2], 
                    'amount': r[3], 'currency': r[4], 'try_equivalent': r[5], 'source': 'currency'
                })
                
            return transactions
        except Exception as e:
            logger.error(f"Get uninvoiced error: {e}")
            return []


    def mark_transactions_as_invoiced(self, transaction_list):
        """İşlemleri faturalandı olarak işaretle (Hibrit Liste)
        Args:
            transaction_list: [{'id': 1, 'source': 'accounting'}, ...]
        """
        if not transaction_list: return
        try:
            acc_ids = [t['id'] for t in transaction_list if t['source'] == 'accounting']
            curr_ids = [t['id'] for t in transaction_list if t['source'] == 'currency']
            
            if acc_ids:
                placeholders = ','.join(['?'] * len(acc_ids))
                self.cursor.execute(
                    "UPDATE accounting SET is_invoiced = 1 WHERE id IN ({placeholders})".format(
                        placeholders=placeholders
                    ),
                    acc_ids,
                )
                
            if curr_ids:
                placeholders = ','.join(['?'] * len(curr_ids))
                self.cursor.execute(
                    "UPDATE currency_transactions SET is_invoiced = 1 WHERE id IN ({placeholders})".format(
                        placeholders=placeholders
                    ),
                    curr_ids,
                )
                
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Mark invoiced error: {e}")
            return False


