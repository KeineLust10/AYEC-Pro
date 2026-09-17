# -*- coding: utf-8 -*-

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta
from src.utils.status_utils import normalize_device_status

from src.utils.logger import logger
from src.utils.path_helper import PathHelper


class DatabaseLegacyPart3Mixin:
    def create_accounting_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT, -- Gelir, Gider
                category TEXT, -- Fatura, Maaş, Satış, Kira vb.
                amount REAL,
                try_equivalent REAL,
                currency TEXT DEFAULT 'TRY',
                exchange_rate REAL DEFAULT 1.0,
                original_amount REAL,
                description TEXT,
                date TEXT,
                created_at TEXT,
                customer_id INTEGER,
                customer_name TEXT,
                is_invoiced INTEGER DEFAULT 0,
                payment_method TEXT,
                bank_account_id INTEGER,
                related_account_id INTEGER,
                project_id INTEGER,
                tracking_no TEXT,
                ref_no TEXT,
                selected_services TEXT
            )
        """)
        self.conn.commit()


    def create_photos_table(self):
        """Cihaz fotoğrafları için bağımsız tablo"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracking_no TEXT,
                    photo_path TEXT,
                    photo_label TEXT,
                    stage TEXT, -- 'Giriş' veya 'İşlem'
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Create photos table error: {e}")


    def add_photo(self, tracking_no, path, label="", stage="Giriş"):
        """Fotoğraf kaydı ekle"""
        try:
            self.cursor.execute("""
                INSERT INTO photos (tracking_no, photo_path, photo_label, stage)
                VALUES (?, ?, ?, ?)
            """, (tracking_no, path, label, stage))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Add photo error: {e}")
            return None


    def get_photos(self, tracking_no, stage=None):
        """Fotoğrafları getir (opsiyonel aşama filtresi)"""
        try:
            if stage:
                self.cursor.execute("""
                    SELECT id, photo_path, photo_label, stage, created_at 
                    FROM photos WHERE tracking_no=? AND stage=? ORDER BY id ASC
                """, (tracking_no, stage))
            else:
                self.cursor.execute("""
                    SELECT id, photo_path, photo_label, stage, created_at 
                    FROM photos WHERE tracking_no=? ORDER BY id ASC
                """, (tracking_no,))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get photos error: {e}")
            return []


    def update_photo_label(self, photo_id, new_label):
        try:
            self.cursor.execute("UPDATE photos SET photo_label=? WHERE id=?", (new_label, photo_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Update photo label error: {e}")
            return False


    def delete_photo(self, photo_id):
        try:
            self.cursor.execute("DELETE FROM photos WHERE id=?", (photo_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Delete photo error: {e}")
            return False

    def get_transaction_by_id(self, txn_id):
        self.cursor.execute("SELECT * FROM accounting WHERE id = ? AND COALESCE(is_deleted, 0) = 0", (txn_id,))
        return self.cursor.fetchone()


    def update_transaction(self, txn_id, txn_type, category, amount, description, date, customer_name=None, customer_id=None, payment_method=None, bank_account_id=None, related_account_id=None):
        try:
            self.cursor.execute("PRAGMA table_info(accounting)")
            cols = [r[1] for r in self.cursor.fetchall()]
            
            self.cursor.execute("SELECT * FROM accounting WHERE id=? AND COALESCE(is_deleted, 0) = 0", (txn_id,))
            old_txn = self.cursor.fetchone()
            if old_txn:
                old_dict = {cols[i]: old_txn[i] for i in range(len(cols))}
                old_bank_id = old_dict.get('bank_account_id')
                old_amount = float(old_dict.get('amount') or 0.0)
                old_type = old_dict.get('type')
                
                if old_bank_id:
                    old_delta = -old_amount if str(old_type).lower() == "gelir" else old_amount
                    try:
                        self.update_bank_balance(old_bank_id, old_delta)
                    except Exception:
                        pass

            updates = ["type=?", "category=?", "amount=?", "description=?", "date=?", "customer_name=?", "customer_id=?"]
            values = [txn_type, category, amount, description, date, customer_name, customer_id]
            if "payment_method" in cols:
                updates.append("payment_method=?")
                values.append(payment_method)
            if "bank_account_id" in cols:
                updates.append("bank_account_id=?")
                values.append(bank_account_id)
            if "related_account_id" in cols:
                updates.append("related_account_id=?")
                values.append(related_account_id)
            values.append(txn_id)
            self.cursor.execute(
                "UPDATE accounting SET {assignments} WHERE id=?".format(
                    assignments=", ".join(updates)
                ),
                tuple(values),
            )
            self.conn.commit()
            
            if bank_account_id:
                new_delta = amount if str(txn_type).lower() == "gelir" else -float(amount or 0)
                try:
                    self.update_bank_balance(bank_account_id, new_delta)
                except Exception:
                    pass
                    
            return True
        except Exception as e:
            logger.error(f"Update txn error: {e}")
            return False


    def get_cari_list(self, search_query=""):
        """Tüm müşterilerin bakiye özetini getir (Borç, Alacak, Bakiye)"""
        try:
            customers = self.get_customers()
            cari_data = []
            for c in customers:
                if search_query and search_query.lower() not in c[1].lower():
                    continue
                    
                c_id = c[0]
                name = c[1]
                phone = c[2]
                
                # 1. Total Debt (Service Fees + Parts)
                self.cursor.execute("SELECT tracking_no, labor_cost FROM devices WHERE customer_id = ?", (c_id,))
                devices = self.cursor.fetchall()
                total_debt = 0.0
                for tno, labor in devices:
                    total_debt += (labor or 0.0)
                    self.cursor.execute("SELECT SUM(price) FROM used_parts WHERE tracking_no = ?", (tno,))
                    ps = self.cursor.fetchone()[0]
                    total_debt += (ps or 0.0)
                
                # 2. Total Paid (Accounting Gelir)
                self.cursor.execute("SELECT SUM(amount) FROM accounting WHERE customer_id = ? AND type = 'Gelir' AND COALESCE(is_deleted, 0) = 0", (c_id,))
                total_paid = self.cursor.fetchone()[0] or 0.0
                
                balance = total_debt - total_paid
                
                cari_data.append({
                    'id': c_id,
                    'name': name,
                    'phone': phone,
                    'total_debt': total_debt,
                    'total_paid': total_paid,
                    'balance': balance
                })
            return cari_data
        except Exception as e:
            logger.error(f"Cari list error: {e}")
            return []


    def create_personnel_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT,
                phone TEXT,
                salary REAL DEFAULT 0,
                commission REAL DEFAULT 0, -- Prim oranı (%)
                created_at TEXT,
                email TEXT,
                active INTEGER DEFAULT 1	
            )
        """)
        self.conn.commit()


    def update_schema(self):
        # Mevcut tabloya yeni kolonları ekle (Eğer yoksa)
        columns = [
            ("tracking_no", "TEXT"),
            ("customer_name", "TEXT"),
            ("device_brand", "TEXT"),
            ("device_model", "TEXT"),
            ("serial_no", "TEXT"),
            ("fault_category", "TEXT"),
            ("urgency", "TEXT"),
            ("status", "TEXT"),
            ("entry_date", "TEXT"),
            ("estimated_date", "TEXT"),
            ("price", "REAL DEFAULT 0"),
            ("customer_id", "INTEGER"), # Normalize için eklendi
            ("device_type", "TEXT"),
            ("imei", "TEXT"),
            ("pattern_lock", "TEXT"),
            ("customer_type", "TEXT"),
            ("customer_tax_id", "TEXT"),
            ("customer_contact", "TEXT"),
            ("fault_description", "TEXT"),
            ("photo_path", "TEXT"),
            ("device_password", "TEXT"),
            ("approval_status", "TEXT DEFAULT 'Bekleme'"),
            ("labor_cost", "REAL DEFAULT 0"),
            ("repair_details", "TEXT"),
            ("technician", "TEXT"),
            # Gelişmiş Özellikler 2.0
            ("warranty_end_date", "TEXT"),
            ("warranty_status", "TEXT DEFAULT 'Yok'"),
            ("priority", "TEXT DEFAULT 'Normal'"),
            ("internal_notes", "TEXT"),
            ("cost_price", "REAL DEFAULT 0"),
            ("checklist_status", "TEXT"),
            ("created_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "TEXT DEFAULT CURRENT_TIMESTAMP"),
            # Image 1 Requirements
            ("cargo_fee", "REAL DEFAULT 0"),
            ("delivery_type", "TEXT"),
            ("accessories", "TEXT"),
            ("service_ref", "TEXT"),
            ("photo_paths", "TEXT"),
            ("is_archived", "INTEGER DEFAULT 0"),
            ("delivered_at", "TEXT"),
            ("vehicle_plate", "TEXT"),
            ("vehicle_vin", "TEXT"),
            ("vehicle_maintenance_card_id", "INTEGER"),
            ("service_source", "TEXT"),
            ("fault_codes", "TEXT"),
            ("obd_notes", "TEXT"),
            ("inspection_summary", "TEXT"),
            ("approval_requested_at", "TEXT"),
            ("approval_decision_at", "TEXT"),
            ("invoice_ready_at", "TEXT")
        ]
        
        try:
            self.cursor.execute("PRAGMA table_info(devices)")
            existing_cols = [row[1] for row in self.cursor.fetchall()]
            
            for col_name, col_type in columns:
                if col_name not in existing_cols:
                    logger.info(f"Kolon ekleniyor: {col_name}")
                    self.cursor.execute(
                        f"ALTER TABLE {self._safe_identifier('devices')} "
                        f"ADD COLUMN {self._safe_identifier(col_name)} {col_type}"
                    )
            self.conn.commit()
            
            # Parts Table Update
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='parts'")
            if self.cursor.fetchone():
                self.cursor.execute("PRAGMA table_info(parts)")
                part_cols = [row[1] for row in self.cursor.fetchall()]
                if "code" not in part_cols:
                    logger.info("Kolon ekleniyor: parts.code")
                    self.cursor.execute("ALTER TABLE parts ADD COLUMN code TEXT")
                    self.conn.commit()
                for col_name, col_type in (
                    ("min_stock", "INTEGER DEFAULT 5"),
                    ("purchase_price", "REAL DEFAULT 0"),
                    ("currency", "TEXT DEFAULT 'TRY'"),
                    ("description", "TEXT"),
                    ("shelf_number", "TEXT"),
                    ("photo_path", "TEXT"),
                    ("oem_code", "TEXT"),
                    ("equivalent_code", "TEXT"),
                    ("compatible_models", "TEXT"),
                ):
                    if col_name not in part_cols:
                        logger.info(f"Kolon ekleniyor: parts.{col_name}")
                        self.cursor.execute(
                            f"ALTER TABLE {self._safe_identifier('parts')} "
                            f"ADD COLUMN {self._safe_identifier(col_name)} {col_type}"
                        )
                self.conn.commit()
                
        except Exception as e:
            logger.error(f"Schema update error: {e}")


    def update_customer_schema_extended(self):
        """Müşteri tablosunu genişletilmiş alanlarla güncelle"""
        new_columns = [
            ("tax_no", "TEXT"),
            ("tax_office", "TEXT"),
            ("district", "TEXT"),
            ("city", "TEXT"),
            ("neighborhood", "TEXT"),
            ("notes", "TEXT"),
            ("term_days", "INTEGER DEFAULT 0"),
            ("limit_amount", "REAL DEFAULT 0"),
            ("sms_enabled", "INTEGER DEFAULT 1"),
            ("is_problematic", "INTEGER DEFAULT 0"),
            ("phone2", "TEXT"),
            ("zip_code", "TEXT"),
            ("tc_no", "TEXT"),
            ("company_name", "TEXT"),
            ("is_partner", "INTEGER DEFAULT 0"),
            ("contract_type", "TEXT"),
            ("sla_level", "TEXT"),
        ]
        
        try:
            self.cursor.execute("PRAGMA table_info(customers)")
            existing = [row[1] for row in self.cursor.fetchall()]
            
            for col, dtype in new_columns:
                if col not in existing:
                    logger.info(f"Adding column to customers: {col}")
                    self.cursor.execute(
                        f"ALTER TABLE {self._safe_identifier('customers')} "
                        f"ADD COLUMN {self._safe_identifier(col)} {dtype}"
                    )
            self.cursor.execute(
                """
                UPDATE customers
                SET is_partner = 1
                WHERE COALESCE(is_partner, 0) = 0
                  AND UPPER(TRIM(COALESCE(type, ''))) IN
                      ('BAYI', 'BAY\u0130', 'TEDARIKCI', 'TEDAR\u0130K\u00c7\u0130')
                """
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Customer schema update error: {e}")


    def update_personnel_schema_extended(self):
        new_cols = [
            ("tc_no", "TEXT"),
            ("email", "TEXT"),
            ("department", "TEXT"),
            ("password_hash", "TEXT"),
            ("is_active", "INTEGER DEFAULT 1"),
            ("commission_rate", "REAL DEFAULT 0"),
            ("username", "TEXT") 
        ]
        try:
            self.cursor.execute("PRAGMA table_info(personnel)")
            existing = [row[1] for row in self.cursor.fetchall()]
            for col, dtype in new_cols:
                if col not in existing:
                    self.cursor.execute(
                        f"ALTER TABLE {self._safe_identifier('personnel')} "
                        f"ADD COLUMN {self._safe_identifier(col)} {dtype}"
                    )
            self.conn.commit()
            try:
                self.cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_personnel_username ON personnel(username)")
                self.conn.commit()
            except Exception as e:
                logger.warning(f"Personnel username index error: {e}")
        except Exception as e:
            logger.warning(f"Personnel schema extended update error: {e}")


    def update_personnel_schema_telegram(self):
        """Telegram ve Konum takibi için gerekli alanlar"""
        new_cols = [
            ("telegram_username", "TEXT"), # Telegram kullanıcı adı (@username)
            ("telegram_chat_id", "TEXT"),  # Bot ile olan Chat ID (Mesaj göndermek için) - Opsiyonel
            ("lat", "TEXT"),               # Enlem
            ("lng", "TEXT"),               # Boylam
            ("last_seen", "TEXT"),         # Son görülme zamanı
            ("status", "TEXT DEFAULT 'Boşta'") # Durum (Görevde, Boşta)
        ]
        try:
            self.cursor.execute("PRAGMA table_info(personnel)")
            existing = [row[1] for row in self.cursor.fetchall()]
            
            for col, dtype in new_cols:
                if col not in existing:
                    self.cursor.execute(
                        f"ALTER TABLE {self._safe_identifier('personnel')} "
                        f"ADD COLUMN {self._safe_identifier(col)} {dtype}"
                    )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Telegram schema update error: {e}")


    def update_appointments_schema(self):
        """Randevu tablosunu genişlet (Personel, Cihaz, Marka, Model, Seri No, Aciliyet, Renk)"""
        new_cols = [
            ("personnel", "TEXT"),
            ("personnel_name", "TEXT"), # Added for UI compatibility
            ("device", "TEXT"),
            ("brand", "TEXT"),
            ("model", "TEXT"),
            ("serial_no", "TEXT"),
            ("urgency", "TEXT"),
            ("color", "TEXT"),
            ("fault", "TEXT"),
            ("customer", "TEXT"),      # UI uses 'customer' generally
            ("customer_id", "INTEGER"),
            ("personnel_id", "INTEGER"),
            ("type", "TEXT"),
            ("notes", "TEXT")
        ]
        try:
            self.cursor.execute("PRAGMA table_info(appointments)")
            existing = [row[1] for row in self.cursor.fetchall()]
            for col, dtype in new_cols:
                if col not in existing:
                     self.cursor.execute(
                         f"ALTER TABLE {self._safe_identifier('appointments')} "
                         f"ADD COLUMN {self._safe_identifier(col)} {dtype}"
                     )
            self.conn.commit()
        except Exception as e:
            logger.warning(f"Appointments schema update error: {e}")


    def update_currency_transactions_schema(self):
        """Add current_balance and is_invoiced to currency_transactions"""
        try:
            # Check existing columns
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='currency_transactions'")
            if cursor.fetchone() is None:
                return
            cursor.execute("PRAGMA table_info(currency_transactions)")
            cols = [c[1] for c in cursor.fetchall()]
            
            if 'current_balance' not in cols:
                cursor.execute("ALTER TABLE currency_transactions ADD COLUMN current_balance REAL DEFAULT 0.0")
                logger.info("Added current_balance to currency_transactions")
            
            if 'is_invoiced' not in cols:
                cursor.execute("ALTER TABLE currency_transactions ADD COLUMN is_invoiced INTEGER DEFAULT 0")
                logger.info("Added is_invoiced to currency_transactions")
                
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating currency_transactions schema: {e}")


    def update_customer_currency_balances_schema(self):
        """Ensure consistency in customer_currency_balances"""
        try:
            # Table already contains balance, ensuring it's commit ready
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error updating customer_currency_balances schema: {e}")


    def recalculate_all_balances(self):
        """Recalculate running balances for all customers and currencies"""
        try:
            cursor = self.conn.cursor()
            # 1. Reset all local currency balance summaries
            cursor.execute("UPDATE customer_currency_balances SET balance = 0.0")
            
            # 2. Get all transactions ordered by absolute date
            cursor.execute("""
                SELECT id, customer_id, currency, transaction_type, amount 
                FROM currency_transactions 
                ORDER BY created_at ASC
            """)
            rows = cursor.fetchall()
            
            # 3. Track balances in memory per customer/currency
            bals = {} # {(customer_id, currency): balance}
            
            for row in rows:
                tid, cid, curr, ttype, amt = row
                key = (cid, curr)
                if key not in bals: bals[key] = 0.0
                
                if ttype == 'DEBIT':
                    bals[key] -= amt
                else: # CREDIT
                    bals[key] += amt
                
                cursor.execute("UPDATE currency_transactions SET current_balance = ? WHERE id = ?", (round(bals[key], 2), tid))
            
            # 4. Sync the final balances to the master balance table
            for (cid, curr), bal in bals.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO customer_currency_balances (customer_id, currency, balance, last_updated)
                    VALUES (?, ?, ?, ?)
                """, (cid, curr, round(bal, 2), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                
            self.conn.commit()
            logger.info("Analytical balances successfully recalculated.")
            return True
        except Exception as e:
            logger.error(f"Error recalculating balances: {e}")
            self.conn.rollback()
            return False


    def add_personnel_extended(self, name, role, phone, salary, commission, tc, email, dept, password):
        try:
            # Check if exists (by TC or Email?)
            # Just insert for now
            self.cursor.execute("""
                INSERT INTO personnel (name, role, phone, salary, commission_rate, tc_no, email, department, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, role, phone, salary, commission, tc, email, dept, password)) # In real app, hash password
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add personnel error: {e}")
            return False


    def add_appointment_extended(self, data):
        """
        data: dict with keys matching columns
        """
        try:
            keys = ", ".join(data.keys())
            placeholders = ", ".join(["?"] * len(data))
            values = tuple(data.values())
            
            sql = "INSERT INTO appointments ({keys}) VALUES ({placeholders})".format(
                keys=keys,
                placeholders=placeholders,
            )
            self.cursor.execute(sql, values)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add appointment error: {e}")
            return False


    def check_critical_stock(self, limit=5):
        try:
            query = "SELECT name, stock FROM parts WHERE stock <= ?"
            try:
                cols = self._get_table_columns("parts")
                deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
                if deleted_col:
                    query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            except Exception:
                pass
            self.cursor.execute(query, (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Stock check error: {e}")
            return []


    def get_critical_devices(self, limit=5):
        try:
            self.cursor.execute("""
                SELECT * FROM devices 
                WHERE status NOT IN ('Tamamlandı', 'İptal') 
                AND urgency IN ('Kritik', 'Yüksek') 
                ORDER BY entry_date DESC LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Critical devices fetch error: {e}")
            return []


    def get_personnel_performance(self):
        # Performans: Tamamlanan cihaz sayısı ve toplam ciro (işçilik + parça karı olabilir ama şimdilik işçilik)
        # Technician bilgisi devices tablosuna eklendiği için oradan çekiyoruz.
        
        self.cursor.execute("""
            SELECT technician, 
                   COUNT(*) as device_count, 
                   SUM(labor_cost) as total_revenue 
            FROM devices 
            WHERE status='Tamamlandı' AND technician IS NOT NULL
            GROUP BY technician
        """)
        return self.cursor.fetchall()


    def add_log(self, tracking_no, log_type, message, user="Teknisyen"):
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("INSERT INTO service_logs (device_tracking_no, log_type, message, created_at, user) VALUES (?, ?, ?, ?, ?)",
                                (tracking_no, log_type, message, created_at, user))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Log hatası: {e}")


    def get_logs(self, tracking_no):
        self.cursor.execute("SELECT * FROM service_logs WHERE device_tracking_no=? ORDER BY created_at DESC", (tracking_no,))
        return self.cursor.fetchall()


    def get_recent_logs(self, limit=10):
        try:
            self.cursor.execute("""
                SELECT device_tracking_no, log_type, message, created_at, user 
                FROM service_logs 
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Recent logs error: {e}")
            return []


    def add_appointment(self, customer_name, phone, date, time, description):
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("INSERT INTO appointments (customer_name, phone, date, time, description, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                                (customer_name, phone, date, time, description, created_at))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Appointment add error: {e}")
            return False


    def get_appointments(self):
        query = "SELECT * FROM appointments"
        try:
            cols = self._get_table_columns("appointments")
            deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
            if deleted_col:
                query += f" WHERE {deleted_col}=0 OR {deleted_col} IS NULL"
        except Exception:
            pass
        query += " ORDER BY date, time"
        self.cursor.execute(query)
        return self.cursor.fetchall()


    def delete_appointment(self, appt_id):
        try:
            return self.soft_delete_record("appointments", "id", appt_id)
        except Exception as e:
            logger.error(f"Appointment delete error: {e}")
            return False


    def update_appointment_status(self, appt_id, status):
        try:
            self.cursor.execute("UPDATE appointments SET status=? WHERE id=?", (status, appt_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Appointment status update error: {e}")
            return False
    

    def get_daily_appointments(self):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute(
                """
                SELECT time, customer_name, description
                FROM appointments
                WHERE date = ?
                ORDER BY time ASC
                """,
                (today,),
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Daily appointments error: {e}")
            return []


    def add_reminder(self, tracking_no, message, due_date):
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("INSERT INTO reminders (tracking_no, message, due_date, created_at) VALUES (?, ?, ?, ?)",
                                (tracking_no, message, due_date, created_at))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Reminder add error: {e}")
            return False


    def get_active_reminders(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT * FROM reminders WHERE is_read=0 AND due_date <= ?", (today,))
        return self.cursor.fetchall()


    def mark_reminder_read(self, rem_id):
        self.cursor.execute("UPDATE reminders SET is_read=1 WHERE id=?", (rem_id,))
        self.conn.commit()


    def delete_device(self, tracking_no):
        try:
            self.add_audit_log("Sistem", "devices", "UPDATE", f"Cihaz arşivlendi (soft delete): {tracking_no}")
            # Soft delete: is_archived=1 instead of hard DELETE
            self.cursor.execute("UPDATE devices SET is_archived=1 WHERE tracking_no=?", (tracking_no,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Device delete error: {e}")
            return False

    # get_all_parts duplicate removed


    def add_stock(self, name, category, quantity, purchase_price, sale_price):
        try:
            # CRITICAL: Ensure parts table exists and has correct schema
            # This is especially important after wipe_all_user_data()
            try:
                self.create_parts_table()
                self.update_parts_schema()
            except Exception as e:
                logger.warning(f"Schema check failed in add_stock, continuing: {e}")
            
            # Check if exists
            self.cursor.execute("SELECT id, stock FROM parts WHERE name=?", (name,))
            row = self.cursor.fetchone()
            if row:
                # Update existing part
                self.cursor.execute("UPDATE parts SET stock = stock + ?, price = ? WHERE id=?", (quantity, sale_price, row[0]))
                # Update purchase_price if column exists
                try:
                    self.cursor.execute("PRAGMA table_info(parts)")
                    cols = {r[1] for r in self.cursor.fetchall()}
                    if "purchase_price" in cols and purchase_price:
                        self.cursor.execute("UPDATE parts SET purchase_price = ? WHERE id=?", (purchase_price, row[0]))
                    if "category" in cols and category:
                        self.cursor.execute("UPDATE parts SET category = ? WHERE id=?", (category, row[0]))
                    updates = []
                    if "is_deleted" in cols:
                        updates.append("is_deleted=0")
                    if "is_archived" in cols:
                        updates.append("is_archived=0")
                    if updates:
                        self.cursor.execute(
                            "UPDATE parts SET {assignments} WHERE id=?".format(
                                assignments=", ".join(updates)
                            ),
                            (row[0],),
                        )
                except Exception as e:
                    logger.warning(f"Could not update part flags: {e}")
            else:
                # Insert new part - FIXED: Use correct column mapping
                # Get available columns to build dynamic INSERT
                self.cursor.execute("PRAGMA table_info(parts)")
                cols = {r[1] for r in self.cursor.fetchall()}
                
                # Build column list and values based on what exists
                insert_cols = ["name", "stock", "price"]
                insert_vals = [name, quantity, sale_price]
                
                if "category" in cols:
                    insert_cols.append("category")
                    insert_vals.append(category or "Genel")
                
                if "purchase_price" in cols:
                    insert_cols.append("purchase_price")
                    insert_vals.append(purchase_price or 0)
                
                if "code" in cols:
                    insert_cols.append("code")
                    insert_vals.append("")
                
                if "created_at" in cols:
                    insert_cols.append("created_at")
                    insert_vals.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                
                # Execute INSERT with correct columns
                placeholders = ", ".join(["?"] * len(insert_vals))
                columns_str = ", ".join(insert_cols)
                self.cursor.execute(
                    "INSERT INTO parts ({columns}) VALUES ({placeholders})".format(
                        columns=columns_str,
                        placeholders=placeholders,
                    ),
                    insert_vals,
                )
                part_id = self.cursor.lastrowid
                
                # Verify insertion succeeded
                if not part_id or part_id <= 0:
                    logger.error(f"Failed to insert part: Invalid part_id ({part_id})")
                    self.conn.rollback()
                    return False
                
                # Set soft-delete flags if columns exist
                try:
                    self.cursor.execute("PRAGMA table_info(parts)")
                    cols = {r[1] for r in self.cursor.fetchall()}
                    updates = []
                    if "is_deleted" in cols:
                        updates.append("is_deleted=0")
                    if "is_archived" in cols:
                        updates.append("is_archived=0")
                    if updates:
                        self.cursor.execute(
                            "UPDATE parts SET {assignments} WHERE id=?".format(
                                assignments=", ".join(updates)
                            ),
                            (part_id,),
                        )
                except Exception as e:
                    logger.warning(f"Could not set deletion flags: {e}")
            
            self.conn.commit()
            self.notify_jarvis(f"{name} stoğu güncellendi. Yeni miktar: +{quantity}", 'stock')
            return True
        except Exception as e:
            logger.error(f"Stock add error: {e}", exc_info=True)
            try:
                self.conn.rollback()
            except Exception as rollback_error:
                logger.warning(f"Rollback failed in add_stock: {rollback_error}")
            return False




    def add_device(self, data):
        try:
            # Safeguard: Yeni cihazlarda durum her zaman "Bekliyor" olmalı
            if "status" not in data or not data["status"]:
                data["status"] = "Bekliyor"
                
            # Data tuple uzunluğu kontrol edilmeli veya dictionary kullanılmalı
            # Basitlik için dictionary yapısına geçiyoruz
            keys = ", ".join(data.keys())
            values_ph = ", ".join(["?"] * len(data))
            values = tuple(data.values())
            
            sql = "INSERT INTO devices ({keys}) VALUES ({values_ph})".format(
                keys=keys,
                values_ph=values_ph,
            )
            self.cursor.execute(sql, values)
            self.add_audit_log("Sistem", "devices", "INSERT", f"Yeni cihaz eklendi: {data.get('tracking_no', 'Unknown')}")
            try:
                self.add_log(
                    data.get("tracking_no", "Unknown"),
                    "Giriş",
                    f"Servis kaydı oluşturuldu: {data.get('customer_name', 'Müşteri')} - "
                    f"{data.get('device_brand', '')} {data.get('device_model', '')}".strip(),
                    user="Sistem",
                )
            except Exception:
                pass
            self.conn.commit()

            # ── Cari Borç Kaydı ──────────────────────────────────────────────
            # Servis oluşturulduğunda hemen DEBIT kaydı aç (durum ne olursa olsun).
            # Bu sayede Müşteri 360 paneli borcu anında gösterir.
            try:
                tracking_no = data.get("tracking_no")
                customer_id = data.get("customer_id")
                customer_name = data.get("customer_name", "Müşteri")
                price = float(data.get("price") or data.get("labor_cost") or 0.0)
                if tracking_no and customer_id and price > 0:
                    # Mükerrer kontrol
                    self.cursor.execute(
                        "SELECT id FROM currency_transactions WHERE tracking_no=? AND transaction_type='DEBIT' AND customer_id=?",
                        (tracking_no, customer_id),
                    )
                    if not self.cursor.fetchone():
                        self.add_currency_transaction(
                            customer_id=customer_id,
                            amount=price,
                            currency="TRY",
                            transaction_type="DEBIT",
                            exchange_rate=1.0,
                            description=f"Servis Açıldı: #{tracking_no} - {customer_name}",
                            tracking_no=tracking_no,
                        )
            except Exception as debt_err:
                logger.warning(f"add_device cari borç kaydı atlandı: {debt_err}")
            # ─────────────────────────────────────────────────────────────────

            self.notify_jarvis(f"Yeni servis kaydı: {data.get('customer_name', 'Müşteri')} - {data.get('device_brand', '')} {data.get('device_model', '')}", 'device')
            return True
        except Exception as e:
            logger.error(f"Device add error: {e}")
            return False


    def update_status(self, tracking_no, status):
        try:
            status = normalize_device_status(status)
            exit_date = None
            delivered_at = None
            if status == "Teslim Edildi":
                now = datetime.now()
                exit_date = now.strftime("%Y-%m-%d")
                delivered_at = now.strftime("%Y-%m-%d %H:%M:%S")
            
            self.add_audit_log("Sistem", "devices", "UPDATE", f"{tracking_no} durumu {status} olarak güncellendi")
            self.trigger_status_notification(tracking_no, status)
            
            if exit_date:
                self.cursor.execute(
                    "UPDATE devices SET status=?, exit_date=?, delivered_at=? WHERE tracking_no=?",
                    (status, exit_date, delivered_at, tracking_no),
                )
                
                # FİNANS ENTEGRASYONU: Teslim Edildi işlendiğinde otomatik Ciro/Gelir kaydı
                try:
                    self.cursor.execute("SELECT price, customer_name, customer_id FROM devices WHERE tracking_no=?", (tracking_no,))
                    dev_row = self.cursor.fetchone()
                    if dev_row:
                        dev_price = float(dev_row[0] or 0.0)
                        dev_cname = dev_row[1]
                        dev_cid = dev_row[2]

                        # Parça toplamını hesapla (used_parts tablosundan)
                        self.cursor.execute(
                            "SELECT COALESCE(SUM(price), 0) FROM used_parts WHERE tracking_no=? AND (is_deleted IS NULL OR is_deleted=0)",
                            (tracking_no,)
                        )
                        parts_total = float(self.cursor.fetchone()[0] or 0.0)
                        total_amount = dev_price + parts_total

                        if total_amount > 0:
                            desc_tag = f"Servis Geliri: {tracking_no}"
                            # Mükerrer gelir kontrolü (accounting tablosu)
                            self.cursor.execute("SELECT id FROM accounting WHERE description LIKE ? AND COALESCE(is_deleted, 0) = 0", (f"%{desc_tag}%",))
                            if not self.cursor.fetchone():
                                self.add_transaction(
                                    t_type="Gelir",
                                    category="Servis Geliri",
                                    amount=total_amount,
                                    description=f"{desc_tag} - {dev_cname or 'Müşteri'}",
                                    payment_method="Nakit",
                                    customer_name=dev_cname,
                                    customer_id=dev_cid
                                )

                            # Müşteri 360 Cari Borç kaydı (currency_transactions DEBIT)
                            if dev_cid:
                                self.cursor.execute(
                                    "SELECT id FROM currency_transactions WHERE tracking_no=? AND transaction_type='DEBIT' AND customer_id=?",
                                    (tracking_no, dev_cid)
                                )
                                if not self.cursor.fetchone():
                                    self.add_currency_transaction(
                                        customer_id=dev_cid,
                                        amount=total_amount,
                                        currency="TRY",
                                        transaction_type="DEBIT",
                                        exchange_rate=1.0,
                                        description=f"Servis Ücreti: #{tracking_no} - {dev_cname or 'Müşteri'}",
                                        tracking_no=tracking_no
                                    )
                except Exception as ex:
                    logger.error(f"Gelir entegrasyon hatası (Teslim Edildi): {ex}")

                try:
                    self.add_log(
                        tracking_no,
                        "Teslim",
                        f"Cihaz teslim edildi. Teslim tarihi: {delivered_at}",
                        user="Sistem",
                    )
                except Exception:
                    pass
                    
            else:
                self.cursor.execute(
                    "UPDATE devices SET status=?, exit_date=NULL, delivered_at=NULL WHERE tracking_no=?",
                    (status, tracking_no),
                )
                try:
                    self.add_log(
                        tracking_no,
                        "Durum",
                        f"Cihaz durumu güncellendi: {status}",
                        user="Sistem",
                    )
                except Exception:
                    pass
                
            self.conn.commit()
            self.notify_jarvis(f"{tracking_no} durumu '{status}' olarak güncellendi.", 'device')
            return True
        except Exception as e:
            logger.error(f"Status update error: {e}")
            return False


    def get_recent_services(self, limit=10):
        try:
            self.cursor.execute("SELECT * FROM devices ORDER BY id DESC LIMIT ?", (limit,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Recent services error: {e}")
            return []


    def get_all_devices(self, include_archived=False):
        try:
            # Otomatik arşivleme: Teslim edilen cihaz aynı gün görünür kalır, ertesi gün arşive düşer.
            self.cursor.execute("""
                UPDATE devices 
                SET is_archived = 1 
                WHERE status = 'Teslim Edildi'
                  AND is_archived = 0
                  AND (
                        (delivered_at IS NOT NULL AND date(delivered_at, 'localtime') < date('now', 'localtime'))
                     OR (delivered_at IS NULL AND exit_date IS NOT NULL AND date(exit_date) < date('now', 'localtime'))
                  )
            """)
            self.conn.commit()
            
            if include_archived:
                self.cursor.execute("SELECT * FROM devices ORDER BY id DESC")
            else:
                self.cursor.execute("SELECT * FROM devices WHERE is_archived = 0 ORDER BY id DESC")
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Get all devices error: {e}")
            return []


    def get_devices_by_status(self, status):
        self.cursor.execute("SELECT * FROM devices WHERE status=?", (status,))
        return self.cursor.fetchall()
    

    def search_devices(self, query):
        q = f"%{query}%"
        self.cursor.execute("""
            SELECT * FROM devices WHERE 
            customer_name LIKE ? OR 
            tracking_no LIKE ? OR 
            serial_no LIKE ? OR 
            fault_category LIKE ?
        """, (q, q, q, q))
        return self.cursor.fetchall()


