# -*- coding: utf-8 -*-

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta

from src.utils.logger import logger
from src.utils.path_helper import PathHelper


class DatabaseLegacyPart1Mixin:
    def create_customer_services_table(self):
        """Hizmet ve Satış Detayları Tablosu (Sihirbaz ve Masaüstü Senkronu için)"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                service_id INTEGER DEFAULT 0,
                service_name TEXT,
                quantity INTEGER DEFAULT 1,
                unit_price REAL DEFAULT 0,
                total_amount REAL DEFAULT 0,
                notes TEXT,
                date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def create_quick_notes_table(self):
        """Hızlı Notlar Tablosu (Ayarlardan Özelleştirilebilir)"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS quick_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT, -- 'service_notes', 'customer_notes', 'technical_notes'
                label TEXT,
                is_active INTEGER DEFAULT 1,
                category TEXT DEFAULT 'Genel' -- 'Telefon', 'Laptop', 'Kamera' vb.
            )
        """)
        self.conn.commit()

        # Varsayılan Notlar (Eğer boşsa)
        self.cursor.execute("SELECT COUNT(*) FROM quick_notes")
        if self.cursor.fetchone()[0] == 0:
            defaults = [
                # Servis Notları
                ("service_notes", "EKRAN KIRIK", 1, "Telefon"),
                ("service_notes", "BATARYA ŞİŞİK", 1, "Telefon"),
                ("service_notes", "SIVI TEMAS", 1, "Genel"),
                ("service_notes", "DARBEYE BAĞLI", 1, "Genel"),
                ("service_notes", "AÇILMIYOR", 1, "Genel"),
                ("service_notes", "ŞARJ ALMIYOR", 1, "Telefon"),
                # Müşteri Görecek
                ("customer_notes", "CİHAZ YAPILDI", 1, "Genel"),
                ("customer_notes", "PARÇA BEKLİYOR", 1, "Genel"),
                ("customer_notes", "İADE EDİLDİ", 1, "Genel"),
                ("customer_notes", "TESLİM EDİLDİ", 1, "Genel"),
                # Teknik Notlar
                ("technical_notes", "TEST OK", 1, "Genel"),
                ("technical_notes", "Fiyat Onayı Alındı", 1, "Genel"),
                ("technical_notes", "Parça Siparişi Geçildi", 1, "Genel"),
                ("technical_notes", "VIP Müşteri", 1, "Genel"),
                # Aksesuarlar
                ("accessories_notes", "SIM Kart", 1, "Aksesuar"),
                ("accessories_notes", "SD Kart", 1, "Aksesuar"),
                ("accessories_notes", "Kılıf", 1, "Aksesuar"),
                ("accessories_notes", "Şarj Aleti", 1, "Aksesuar"),
                ("accessories_notes", "Kutu", 1, "Aksesuar"),
                ("accessories_notes", "Kablo", 1, "Aksesuar"),
            ]
            self.cursor.executemany(
                "INSERT INTO quick_notes (group_name, label, is_active, category) VALUES (?, ?, ?, ?)",
                defaults,
            )
            self.conn.commit()

    def get_quick_notes(self, group_name=None):
        if group_name:
            self.cursor.execute(
                "SELECT * FROM quick_notes WHERE group_name=? ORDER BY id",
                (group_name,),
            )
        else:
            self.cursor.execute("SELECT * FROM quick_notes ORDER BY group_name, id")
        return self.cursor.fetchall()

    def add_quick_note(self, group_name, label, category="Genel"):
        self.cursor.execute(
            "INSERT INTO quick_notes (group_name, label, is_active, category) VALUES (?, ?, 1, ?)",
            (group_name, label, category),
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def update_quick_note(self, note_id, label, is_active, category):
        self.cursor.execute(
            "UPDATE quick_notes SET label=?, is_active=?, category=? WHERE id=?",
            (label, is_active, category, note_id),
        )
        self.conn.commit()

    def delete_quick_note(self, note_id):
        self.cursor.execute("DELETE FROM quick_notes WHERE id=?", (note_id,))
        self.conn.commit()

    # --- FAST NOTES METHODS (Dinamik Toggle Butonları) ---

    def get_fast_notes(self, category=None):
        query = "SELECT * FROM fast_notes"
        params = []
        if category:
            query += " WHERE category=?"
            params.append(category)
        query += " ORDER BY display_order ASC"
        return self.cursor.execute(query, params).fetchall()

    def add_fast_note(self, category, label, is_active=1, order=0):
        self.cursor.execute(
            "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, ?, ?)",
            (category, label, is_active, order),
        )
        self.conn.commit()

    def update_fast_note(self, note_id, label, is_active, category, order=0):
        self.cursor.execute(
            "UPDATE fast_notes SET label=?, is_active=?, category=?, display_order=? WHERE id=?",
            (label, is_active, category, order, note_id),
        )
        self.conn.commit()

    def delete_fast_note(self, note_id):
        self.cursor.execute("DELETE FROM fast_notes WHERE id=?", (note_id,))
        self.conn.commit()

    def create_company_info_table(self):
        """Şirket Bilgileri Tablosu (Setup Wizard için)"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                authorized_person TEXT,
                phone TEXT,
                email TEXT,
                address TEXT,
                tax_office TEXT,
                tax_number TEXT,
                logo_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def update_company_info_schema(self):
        """Company Info şemasına eksik kolonları ekler"""
        try:
            self.cursor.execute("PRAGMA table_info(company_info)")
            cols = [row[1] for row in (self.cursor.fetchall() or [])]
            if "logo_path" not in cols:
                self.cursor.execute(
                    "ALTER TABLE company_info ADD COLUMN logo_path TEXT"
                )
                self.conn.commit()
                logger.info("Added logo_path to company_info table")
        except Exception as e:
            logger.warning(f"Failed to add logo_path to company_info: {e}")

    def create_fast_notes_table(self):
        """Teknisyen Paneli Makroları için Tablo"""
        computer_fault_defaults = [
            "GÖRÜNTÜ YOK",
            "AÇILMIYOR",
            "ŞARJ OLMUYOR",
            "ISINMA / FAN SESİ",
            "YAVAŞ ÇALIŞIYOR",
            "MAVİ EKRAN",
            "KLAVYE ÇALIŞMIYOR",
            "PORT / SOKET SORUNU",
        ]
        computer_process_defaults = [
            "FORMAT ATILDI",
            "PARÇA DEĞİŞTİ",
            "TEMİZLİK YAPILDI",
            "TEST EDİLİYOR",
            "ONAY BEKLİYOR",
        ]
        computer_private_defaults = [
            "TEST OK",
            "VERİ YEDEKLENDİ",
            "SIVI TEMASI ŞÜPHELİ",
            "ACİL TESLİM",
        ]
        computer_accessory_defaults = [
            "Güç Adaptörü",
            "Şarj Kablosu",
            "HDMI / Görüntü Kablosu",
            "Mouse",
            "Klavye",
            "Taşıma Çantası",
        ]

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fast_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT, -- 'Arıza Notu', 'İşlem Detayı', 'Gizli Not'
                label TEXT, 
                is_active INTEGER DEFAULT 1,
                display_order INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

        # Varsayılanlar
        self.cursor.execute("SELECT COUNT(*) FROM fast_notes")
        if self.cursor.fetchone()[0] == 0:
            defaults = [
                # Arıza Notu
                *[
                    ("Arıza Notu", label, 1, idx)
                    for idx, label in enumerate(computer_fault_defaults)
                ],
                # İşlem Detayı (Müşteri için)
                *[
                    ("İşlem Detayı", label, 1, idx)
                    for idx, label in enumerate(computer_process_defaults)
                ],
                # Gizli Not
                *[
                    ("Gizli Not", label, 1, idx)
                    for idx, label in enumerate(computer_private_defaults)
                ],
            ]
            self.cursor.executemany(
                "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, ?, ?)",
                defaults,
            )
            self.conn.commit()

        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM fast_notes WHERE category='Arıza Hızlı Seçimi'"
            )
            has_fault_quick = (self.cursor.fetchone()[0] or 0) > 0
            if not has_fault_quick:
                for idx, label in enumerate(computer_fault_defaults):
                    self.cursor.execute(
                        "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, ?, ?)",
                        ("Arıza Hızlı Seçimi", label, 1, idx),
                    )
                self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to update device categories: {e}")

        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM fast_notes WHERE category='Aksesuar'"
            )
            has_acc = (self.cursor.fetchone()[0] or 0) > 0
            if not has_acc:
                acc_rows = []
                try:
                    self.cursor.execute(
                        "SELECT label, is_active FROM quick_notes WHERE group_name=? ORDER BY id",
                        ("accessories_notes",),
                    )
                    acc_rows = self.cursor.fetchall()
                except Exception:
                    acc_rows = []

                if not acc_rows:
                    acc_rows = [(label, 1) for label in computer_accessory_defaults]

                for idx, row in enumerate(acc_rows):
                    label = row[0]
                    is_active = int(row[1]) if len(row) > 1 else 1
                    self.cursor.execute(
                        "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, ?, ?)",
                        ("Aksesuar", label, is_active, idx),
                    )
                self.conn.commit()
        except Exception as e:
            logger.warning(f"Aksesuar fast notes update error: {e}")

        try:
            legacy_faults = {
                "EKRAN KIRIK",
                "SIVI TEMAS",
                "BATARYA ŞİŞİK",
                "ŞARJ ALMIYOR",
                "KAPANDI AÇILMIYOR",
                "KAMERA SORUNU",
                "SES GELMİYOR",
                "MİKROFON ÇALIŞMIYOR",
            }
            self.cursor.execute(
                "SELECT COUNT(*) FROM fast_notes WHERE category='Arıza Hızlı Seçimi'"
            )
            total_faults = int(self.cursor.fetchone()[0] or 0)
            self.cursor.execute(
                "SELECT COUNT(*) FROM fast_notes WHERE category='Arıza Hızlı Seçimi' AND label IN ({})".format(
                    ",".join(["?"] * len(legacy_faults))
                ),
                tuple(legacy_faults),
            )
            legacy_fault_count = int(self.cursor.fetchone()[0] or 0)
            if total_faults and total_faults == legacy_fault_count:
                self.cursor.execute(
                    "DELETE FROM fast_notes WHERE category='Arıza Hızlı Seçimi'"
                )
                for idx, label in enumerate(computer_fault_defaults):
                    self.cursor.execute(
                        "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, ?, ?)",
                        ("Arıza Hızlı Seçimi", label, 1, idx),
                    )
                self.conn.commit()
        except Exception as e:
            logger.warning(f"Arıza Hızlı Seçimi migration error: {e}")

        try:
            legacy_accs = {
                "SIM Kart",
                "SD Kart",
                "Kılıf",
                "Şarj Aleti",
                "Kutu",
                "Kablo",
            }
            self.cursor.execute(
                "SELECT COUNT(*) FROM fast_notes WHERE category='Aksesuar'"
            )
            total_accs = int(self.cursor.fetchone()[0] or 0)
            self.cursor.execute(
                "SELECT COUNT(*) FROM fast_notes WHERE category='Aksesuar' AND label IN ({})".format(
                    ",".join(["?"] * len(legacy_accs))
                ),
                tuple(legacy_accs),
            )
            legacy_acc_count = int(self.cursor.fetchone()[0] or 0)
            if total_accs and total_accs == legacy_acc_count:
                self.cursor.execute("DELETE FROM fast_notes WHERE category='Aksesuar'")
                for idx, label in enumerate(computer_accessory_defaults):
                    self.cursor.execute(
                        "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, ?, ?)",
                        ("Aksesuar", label, 1, idx),
                    )
                self.conn.commit()
        except Exception as e:
            logger.warning(f"Aksesuar migration error: {e}")

    def update_accounting_schema(self):
        """Muhasebe tablosunu güncel şemaya migrate et (çoklu para birimi uyumu dahil)."""
        self.create_accounting_table()

        try:
            self.cursor.execute("PRAGMA table_info(accounting)")
            cols = [row[1] for row in self.cursor.fetchall()]

            def add_col(name, ddl):
                if name in cols:
                    return
                try:
                    # Validate column name and DDL to prevent SQL injection
                    if not name.replace("_", "").isalnum():
                        logger.error(f"Invalid column name: {name}")
                        return
                    # Only allow specific DDL types
                    allowed_types = ["INTEGER", "TEXT", "REAL", "BLOB", "NULL"]
                    ddl_parts = ddl.upper().split()
                    if not ddl_parts:
                        logger.error(f"Empty DDL type: {ddl}")
                        return
                    ddl_upper = ddl_parts[0]
                    if not any(allowed in ddl_upper for allowed in allowed_types):
                        logger.error(f"Invalid DDL type: {ddl}")
                        return
                    safe_name = self._safe_identifier(name)
                    self.cursor.execute(
                        "ALTER TABLE accounting ADD COLUMN {column_name} {ddl}".format(
                            column_name=safe_name,
                            ddl=ddl,
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to add column {name}: {e}")

            add_col("customer_id", "INTEGER")
            add_col("customer_name", "TEXT")
            add_col("created_at", "TEXT")
            add_col("is_invoiced", "INTEGER DEFAULT 0")
            add_col("currency", "TEXT DEFAULT 'TRY'")
            add_col("exchange_rate", "REAL DEFAULT 1.0")
            add_col("original_amount", "REAL")
            add_col("try_equivalent", "REAL")
            add_col("project_id", "INTEGER")
            add_col("tracking_no", "TEXT")
            add_col("payment_method", "TEXT")
            add_col("bank_account_id", "INTEGER")
            add_col("related_account_id", "INTEGER")
            add_col("ref_no", "TEXT")
            add_col("selected_services", "TEXT")
            add_col("product_service_id", "INTEGER")
            add_col("product_service_type", "TEXT")

            self.conn.commit()

            try:
                self.cursor.execute("PRAGMA table_info(accounting)")
                cols2 = [row[1] for row in self.cursor.fetchall()]
            except Exception as e:
                logger.warning(
                    f"Failed to get accounting table info, using cached columns: {e}"
                )
                cols2 = cols

            previous_busy_timeout = None
            try:
                self.cursor.execute("PRAGMA busy_timeout")
                busy_row = self.cursor.fetchone()
                previous_busy_timeout = (
                    int(busy_row[0]) if busy_row and busy_row[0] is not None else None
                )
            except Exception:
                previous_busy_timeout = None

            # Şema migration sırasında opsiyonel toplu UPDATE'lerde UI beklemesini azalt.
            # Tablo kilitliyse uzun süre bloklamak yerine hızlıca atlanır.
            try:
                self.cursor.execute("PRAGMA busy_timeout = 1200")
            except Exception:
                pass

            def run_best_effort_update(sql, tag):
                try:
                    self.cursor.execute(sql)
                    return True
                except sqlite3.OperationalError as op_err:
                    if "locked" in str(op_err).lower():
                        try:
                            self.conn.rollback()
                        except Exception:
                            pass
                        logger.info(f"Skipped {tag} due to temporary DB lock")
                        return False
                    logger.warning(f"Failed to update {tag}: {op_err}")
                    return False
                except Exception as ex:
                    logger.warning(f"Failed to update {tag}: {ex}")
                    return False

            if "try_equivalent" in cols2:
                run_best_effort_update(
                    "UPDATE accounting SET try_equivalent = amount WHERE try_equivalent IS NULL",
                    "try_equivalent defaults",
                )
            if "currency" in cols2:
                run_best_effort_update(
                    "UPDATE accounting SET currency = 'TRY' WHERE currency IS NULL OR currency = ''",
                    "currency defaults",
                )
            if "exchange_rate" in cols2:
                run_best_effort_update(
                    "UPDATE accounting SET exchange_rate = 1.0 WHERE exchange_rate IS NULL OR exchange_rate = 0",
                    "exchange_rate defaults",
                )

            try:
                if {
                    "currency",
                    "exchange_rate",
                    "try_equivalent",
                    "amount",
                    "category",
                    "description",
                }.issubset(set(cols2)):
                    from src.utils.exchange_rate_manager import ExchangeRateManager

                    self.cursor.execute(
                        """
                        SELECT id, amount, currency, exchange_rate, description
                        FROM accounting
                        WHERE category LIKE 'Stok Al%'
                          AND UPPER(COALESCE(currency, 'TRY')) IN ('TRY', 'USD', 'EUR')
                          AND (exchange_rate IS NULL OR exchange_rate = 0 OR exchange_rate = 1)
                        """
                    )
                    rows = self.cursor.fetchall() or []
                    for rid, amount, currency, ex_rate, description in rows:
                        try:
                            rate = float(
                                ExchangeRateManager.get_current_rate(
                                    self,
                                    effective_currency
                                    if "effective_currency" in locals()
                                    else currency,
                                    "selling",
                                )
                                or 1.0
                            )
                        except Exception:
                            rate = 1.0
                        if rate and rate != 1.0:
                            original_amount = float(amount or 0)
                            try_equiv = round(original_amount * rate, 2)
                            updates = [
                                "amount = ?",
                                "try_equivalent = ?",
                                "exchange_rate = ?",
                            ]
                            values = [try_equiv, try_equiv, rate]
                            if (
                                "effective_currency" in locals()
                                and effective_currency != str(currency).upper()
                                and "currency" in cols2
                            ):
                                updates.append("currency = ?")
                                values.append(effective_currency)
                            if "original_amount" in cols2:
                                updates.append("original_amount = ?")
                                values.append(original_amount)
                            desc_text = str(description or "")
                            effective_currency = str(currency).upper()
                            if effective_currency == "TRY":
                                try:
                                    self.cursor.execute(
                                        "SELECT UPPER(COALESCE(currency,'TRY')), COALESCE(purchase_price,0) FROM parts WHERE name = TRIM(SUBSTR(?, INSTR(?, 'x') + 1)) ORDER BY id DESC LIMIT 1",
                                        (
                                            desc_text.split(":", 1)[-1].split("|", 1)[
                                                0
                                            ],
                                            desc_text.split(":", 1)[-1].split("|", 1)[
                                                0
                                            ],
                                        ),
                                    )
                                    part_row = self.cursor.fetchone()
                                    if part_row and str(part_row[0]).upper() in (
                                        "USD",
                                        "EUR",
                                    ):
                                        effective_currency = str(part_row[0]).upper()
                                except Exception:
                                    pass
                            symbol = "$" if effective_currency == "USD" else "?"
                            if symbol not in desc_text and "TCMB kuru" not in desc_text:
                                desc_text = f"{desc_text} | {original_amount:,.2f} {symbol} = {try_equiv:,.2f} TL (TCMB kuru: {rate:.4f})"
                                updates.append("description = ?")
                                values.append(desc_text)
                            values.append(rid)
                            assignments = ", ".join(
                                f"{self._safe_identifier(update.split('=', 1)[0].strip())} = ?"
                                for update in updates
                            )
                            self.cursor.execute(
                                "UPDATE accounting SET {assignments} WHERE id = ?".format(
                                    assignments=assignments
                                ),
                                tuple(values),
                            )
            except Exception as e:
                logger.warning(f"Failed to normalize legacy stock purchases: {e}")

            if previous_busy_timeout is not None:
                try:
                    self.cursor.execute(
                        f"PRAGMA busy_timeout = {max(0, int(previous_busy_timeout))}"
                    )
                except Exception:
                    pass

            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to update accounting schema: {e}")
            try:
                self.conn.commit()
            except Exception as commit_error:
                logger.error(
                    f"Failed to commit after accounting schema error: {commit_error}"
                )

    def create_bank_accounts_table(self):
        """Banka Hesapları Tablosu"""
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name TEXT,
                account_holder TEXT,
                iban TEXT,
                account_number TEXT,
                branch_code TEXT,
                currency TEXT DEFAULT 'TRY',
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                current_balance REAL DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
        """)
        self.conn.commit()
        try:
            cur.execute("PRAGMA table_info(bank_accounts)")
            cols = [r[1] for r in cur.fetchall()]
            if "current_balance" not in cols:
                cur.execute(
                    "ALTER TABLE bank_accounts ADD COLUMN current_balance REAL DEFAULT 0"
                )
                self.conn.commit()
            if "is_deleted" not in cols:
                cur.execute(
                    "ALTER TABLE bank_accounts ADD COLUMN is_deleted INTEGER DEFAULT 0"
                )
                self.conn.commit()
            if "deleted_at" not in cols:
                cur.execute("ALTER TABLE bank_accounts ADD COLUMN deleted_at TEXT")
                self.conn.commit()
        except Exception as e:
            logger.warning(f"Bank accounts column check error: {e}")

    def create_contracts_table(self):
        """Bakım Sözleşmeleri Tablosu"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                title TEXT,
                start_date TEXT,
                end_date TEXT,
                contract_type TEXT, -- Bakım, Kiralama, Servis
                price REAL DEFAULT 0,
                status TEXT DEFAULT 'Aktif', -- Aktif, Bitti, İptal
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def create_audit_log_table(self):
        """Hangi kullanıcı hangi işlemi yaptı (Kurumsal Güvenlik)"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                table_name TEXT,
                action TEXT, -- INSERT, UPDATE, DELETE
                details TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()

    def create_sms_log_table(self):
        """SMS gönderim geçmişini kaydet"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sms_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                phone TEXT,
                message TEXT,
                twilio_sid TEXT,
                sent_at TEXT
            )
        """)
        self.conn.commit()

    def create_indexes(self):
        """Performans için kritik kolonlara indeks ekle"""
        try:
            try:
                self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {
                    r[0] for r in (self.cursor.fetchall() or []) if r and r[0]
                }
            except Exception as e:
                logger.warning(f"Failed to get existing tables for indexing: {e}")
                existing_tables = set()

            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_devices_tracking ON devices(tracking_no)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_accounting_date ON accounting(date)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_accounting_customer ON accounting(customer_id)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)"
            )
            if "currency_transactions" in existing_tables:
                self.cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_curr_trans_customer ON currency_transactions(customer_id)"
                )
                self.cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_curr_trans_date ON currency_transactions(created_at)"
                )
                self.cursor.execute(
                    "CREATE INDEX IF NOT EXISTS idx_fix_balance ON currency_transactions(customer_id, transaction_type)"
                )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Index creation error: {e}")

    def auto_repair(self):
        """Program her a??ld???nda veritaban?n? otomatik olarak denetler"""
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = {row[0] for row in self.cursor.fetchall() or []}

            if "personnel" in existing_tables:
                personnel_cols = {
                    row[1]
                    for row in self.cursor.execute(
                        "PRAGMA table_info(personnel)"
                    ).fetchall()
                }
                if "status" in personnel_cols:
                    self.cursor.execute(
                        "UPDATE personnel SET status='Bosta' WHERE status LIKE 'Bo%'"
                    )
                    self.cursor.execute(
                        "UPDATE personnel SET status='Gorevde' WHERE status LIKE 'G%'"
                    )

            if "audit_logs" in existing_tables:
                audit_cols = {
                    row[1]
                    for row in self.cursor.execute(
                        "PRAGMA table_info(audit_logs)"
                    ).fetchall()
                }
                if "details" in audit_cols:
                    self.cursor.execute(
                        "UPDATE audit_logs SET details = REPLACE(details, 'arYivlendi', 'arsivlendi')"
                    )

            try:
                if "currency_transactions" in existing_tables:
                    ct_cols = {
                        row[1]
                        for row in self.cursor.execute(
                            "PRAGMA table_info(currency_transactions)"
                        ).fetchall()
                    }
                    if "is_invoiced" in ct_cols:
                        self.cursor.execute(
                            "UPDATE currency_transactions SET is_invoiced = 0 WHERE is_invoiced IS NULL"
                        )
            except Exception as e:
                logger.error(f"Hata onar?m? ba?ar?s?z: {e}")

            try:
                if "devices" in existing_tables:
                    device_cols = {
                        row[1]
                        for row in self.cursor.execute(
                            "PRAGMA table_info(devices)"
                        ).fetchall()
                    }
                    if {"status", "is_archived"}.issubset(device_cols):
                        active_statuses = (
                            "Bekliyor",
                            "Beklemede",
                            "Tamirde",
                            "Par?a Bekliyor",
                            "Test S?recinde",
                            "Test A?amas?",
                            "Onay Bekliyor",
                            "Haz?r",
                        )
                        placeholders = ", ".join(["?"] * len(active_statuses))
                        self.cursor.execute(
                            f"UPDATE devices SET is_archived=0 WHERE status IN ({placeholders}) AND (is_archived=1 OR is_archived IS NULL)",
                            active_statuses,
                        )
                        if self.cursor.rowcount > 0:
                            logger.info(
                                f"Auto-repair: {self.cursor.rowcount} devices unarchived (from 1 or NULL)."
                            )
            except Exception as e:
                logger.warning(f"Archive sync repair error: {e}")

            self.conn.commit()
        except Exception as e:
            logger.warning(f"Auto repair error (safe to ignore if tables missing): {e}")

    def wipe_all_user_data(self):
        """DANGER ZONE: Tüm kullanıcı verilerini siler ve tabloları yeniden oluşturur.

        Korunan tablolar (kemik iskelet):
        - settings / internal_settings: uygulama ayarları, modül/feature flag'leri
        - company_info: şirket bilgileri
        - license_info / registration: lisans
        - whatsapp_templates: mesaj şablonları
        - notifications: sistem bildirimleri
        - sector_presets: sektör ön ayarları (seed verisi)
        - device_brands: cihaz marka listesi (seed verisi)
        - service_definitions: kullanıcının tanımladığı hizmet listesi
        - kb_articles + fts tabloları: bilgi bankası
        """
        logger.info("WIPE ALL DATA STARTED")
        try:
            self.cursor.execute("PRAGMA foreign_keys = OFF")

            # Sadece admin kullanıcısını sakla (diğer kullanıcılar silinecek)
            saved_admin = None
            try:
                self.cursor.execute("SELECT * FROM users WHERE username=?", ("admin",))
                row = self.cursor.fetchone()
                if row:
                    col_names = [d[0] for d in self.cursor.description]
                    saved_admin = dict(zip(col_names, row))
            except Exception:
                pass

            self.cursor.execute(
                "SELECT name, sql FROM sqlite_master WHERE type='table'"
            )
            all_table_rows = self.cursor.fetchall() or []

            # Kemik iskelet: kullanıcı verisi OLMAYAN, program altyapısına ait tablolar
            # users burada YOK — wipe sonrası sadece admin geri yüklenir
            keep_tables = [
                # SQLite sistem
                "sqlite_sequence",
                "sqlite_stat1",
                "sqlite_master",
                # Uygulama ayarları
                "settings",
                "internal_settings",
                # Şirket / lisans
                "company_info",
                "license_info",
                "registration",
                # Seed / şablon verileri
                "whatsapp_templates",
                "sector_presets",
                "device_brands",
                "service_definitions",
                # Bildirimler
                "notifications",
                # Bilgi bankası (FTS dahil)
                "kb_articles",
                "kb_articles_fts",
                "kb_articles_fts_config",
                "kb_articles_fts_data",
                "kb_articles_fts_docsize",
                "kb_articles_fts_idx",
            ]

            virtual_tables = []
            regular_tables = []
            for row in all_table_rows:
                table = row[0]
                create_sql = (row[1] or "").upper()
                if table in keep_tables:
                    continue
                if "VIRTUAL TABLE" in create_sql:
                    virtual_tables.append(table)
                else:
                    regular_tables.append(table)

            for table in virtual_tables + regular_tables:
                try:
                    self.cursor.execute(
                        'DROP TABLE IF EXISTS "{table_name}"'.format(table_name=table)
                    )
                    logger.info(f"Dropped table: {table}")
                except Exception as e:
                    logger.error(f"Failed to drop {table}: {e}")

            try:
                self.cursor.execute("DELETE FROM sqlite_sequence")
            except Exception:
                pass

            self.conn.commit()

            logger.info("Re-initializing schema...")
            self._full_initialized = False
            self._initialize_full_schema()
            try:
                if hasattr(self, "ensure_runtime_schema_compatibility"):
                    self.ensure_runtime_schema_compatibility()
                if hasattr(self, "ensure_default_settings"):
                    self.ensure_default_settings()
            except Exception as e:
                logger.warning(f"Post-wipe schema/default repair skipped: {e}")

            try:
                if hasattr(self, "create_internal_settings_table"):
                    self.create_internal_settings_table()
                # is_first_run sıfırlanmasın — kullanıcı zaten kurulum yaptı
                self.cursor.execute(
                    "INSERT OR IGNORE INTO internal_settings (key, value) VALUES (?, ?)",
                    ("is_first_run", "0"),
                )
            except Exception:
                pass

            try:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                    ("last_login_user", "admin"),
                )
            except Exception:
                pass

            # users tablosu silindi (keep_tables dışında) — sadece admin geri yüklenir.
            # Oluşturulan diğer tüm kullanıcılar wipe ile silinir.
            try:
                if saved_admin:
                    self.cursor.execute("PRAGMA table_info(users)")
                    current_cols = {r[1] for r in self.cursor.fetchall()}
                    filtered = {
                        k: v for k, v in saved_admin.items() if k in current_cols
                    }
                    placeholders = ", ".join(["?"] * len(filtered))
                    col_str = ", ".join(f'"{c}"' for c in filtered.keys())
                    self.cursor.execute(
                        f"INSERT OR IGNORE INTO users ({col_str}) VALUES ({placeholders})",
                        list(filtered.values()),
                    )
                    logger.info("Admin user restored after wipe.")
                else:
                    # Admin hiç yoksa yeniden oluştur
                    try:
                        self.create_users_table()
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"Post-wipe admin restore skipped: {e}")

            self.cursor.execute("PRAGMA foreign_keys = ON")
            self.conn.commit()

            logger.info("WIPE ALL DATA COMPLETED SUCCESSFULLY")
            try:
                self.cursor.execute("VACUUM")
            except Exception as e:
                logger.warning(f"VACUUM failed: {e}")

            return True

        except Exception as e:
            logger.error(f"Wipe all data failed: {e}")
            self.conn.rollback()
            return False

    def backup_database(self):
        """Veritabanını otomatik yedekle"""
        try:
            # Use PathHelper to get absolute paths
            backups_dir = os.path.join(PathHelper.get_app_data_dir(), "backups")
            if not os.path.exists(backups_dir):
                os.makedirs(backups_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backups_dir, f"ayecpro_backup_{timestamp}.db")

            db_path = PathHelper.get_db_path("ayecpro.db")

            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_path)

                # Cleanup old backups
                backups = sorted(
                    [
                        os.path.join(backups_dir, f)
                        for f in os.listdir(backups_dir)
                        if f.endswith(".db")
                    ]
                )
                if len(backups) > 10:
                    for old_backup in backups[:-10]:
                        try:
                            os.remove(old_backup)
                        except Exception as e:
                            logger.error(f"Eski yedek dosyası silinemedi: {e}")

                return backup_path  # Return the path for UI/Worker
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return None

    def add_audit_log(self, user, table, action, details):
        """Tüm kritik işlemleri kayıt altına al"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                """
                INSERT INTO audit_logs (user_id, table_name, action, details, created_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user, table, action, details, now),
            )
            self.conn.commit()
        except Exception as e:
            logger.error(f"Audit log error: {e}")

    def get_audit_logs(self, limit=50):
        self.cursor.execute(
            "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)
        )
        return self.cursor.fetchall()

    def update_advanced_schema(self):
        """İleri düzey özellikler için tablo güncellemeleri."""
        migrations = [
            ("users", "commission_rate", "REAL DEFAULT 0"),
            ("parts", "barcode", "TEXT"),
            ("parts", "min_stock", "INTEGER DEFAULT 5"),
            ("devices", "photo_paths", "TEXT"),  # Virgülle ayrılmış dosya yolları
            ("devices", "payment_status", "TEXT DEFAULT 'Beklemede'"),
            ("devices", "is_archived", "INTEGER DEFAULT 0"),
            ("devices", "exit_date", "TEXT"),
        ]

        for table, col, dtype in migrations:
            try:
                # Validate table and column names to prevent SQL injection
                if (
                    not table.replace("_", "").isalnum()
                    or not col.replace("_", "").isalnum()
                ):
                    logger.error(f"Invalid table or column name: {table}.{col}")
                    continue
                # Validate DDL type
                allowed_types = ["INTEGER", "TEXT", "REAL", "BLOB", "NULL"]
                dtype_parts = dtype.upper().split()
                if not dtype_parts:
                    logger.error(f"Empty DDL type: {dtype}")
                    continue
                dtype_upper = dtype_parts[0]
                if not any(allowed in dtype_upper for allowed in allowed_types):
                    logger.error(f"Invalid DDL type: {dtype}")
                    continue
                # Kolonun olup olmadığını kontrol et
                safe_table = self._safe_identifier(table)
                self.cursor.execute(
                    "PRAGMA table_info({table_name})".format(table_name=safe_table)
                )
                cols = [row[1] for row in self.cursor.fetchall()]
                if col not in cols:
                    safe_col = self._safe_identifier(col)
                    self.cursor.execute(
                        "ALTER TABLE {table_name} ADD COLUMN {column_name} {dtype}".format(
                            table_name=safe_table,
                            column_name=safe_col,
                            dtype=dtype,
                        )
                    )
            except Exception as e:
                logger.error(f"Migration error ({table}.{col}): {e}")
        self.conn.commit()

    def create_settings_tables(self):
        # Ayarlar Tablosu
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # WhatsApp Şablonları
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                content TEXT
            )
        """)
        self.conn.commit()

    def create_announcements_table(self):
        """Duyurular tablosunu oluştur"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                priority TEXT,
                title TEXT,
                content TEXT,
                author TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def create_support_tables(self):
        # Destek Biletleri (Tickets)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                subject TEXT,
                description TEXT,
                status TEXT DEFAULT 'OPEN', -- OPEN, IN_PROGRESS, RESOLVED, CLOSED
                priority TEXT DEFAULT 'NORMAL', -- LOW, NORMAL, HIGH
                created_at TEXT,
                updated_at TEXT
            )
        """)

        # Bilgi Bankası (Knowledge Base)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                tags TEXT,
                created_at TEXT
            )
        """)

        # FTS5 Sanal Tablosu (Gelişmiş Arama)
        try:
            self.cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS kb_articles_fts USING fts5(
                    title, 
                    content, 
                    tags, 
                    content='kb_articles', 
                    content_rowid='id'
                )
            """)

            # Tetikleyiciler (Triggers) - Senkronizasyon için
            self.cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS kb_articles_ai AFTER INSERT ON kb_articles BEGIN
                    INSERT INTO kb_articles_fts(rowid, title, content, tags) VALUES (new.id, new.title, new.content, new.tags);
                END;
            """)
            self.cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS kb_articles_ad AFTER DELETE ON kb_articles BEGIN
                    INSERT INTO kb_articles_fts(kb_articles_fts, rowid, title, content, tags) VALUES('delete', old.id, old.title, old.content, old.tags);
                END;
            """)
            self.cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS kb_articles_au AFTER UPDATE ON kb_articles BEGIN
                    INSERT INTO kb_articles_fts(kb_articles_fts, rowid, title, content, tags) VALUES('delete', old.id, old.title, old.content, old.tags);
                    INSERT INTO kb_articles_fts(rowid, title, content, tags) VALUES (new.id, new.title, new.content, new.tags);
                END;
            """)
        except Exception as e:
            logger.error(f"FTS5 Error: {e}", exc_info=True)

        self.conn.commit()

    def get_tickets(self):
        # Müşteri ismini de çekerek biletleri getir
        self.cursor.execute("""
            SELECT t.id, c.name, t.subject, t.status, t.priority, t.created_at 
            FROM tickets t 
            LEFT JOIN customers c ON t.customer_id = c.id 
            ORDER BY t.id DESC
        """)
        return self.cursor.fetchall()

    def get_ticket_details(self, ticket_id):
        self.cursor.execute(
            """
            SELECT t.id, c.name, t.subject, t.description, t.status, t.priority, t.created_at, t.updated_at 
            FROM tickets t 
            LEFT JOIN customers c ON t.customer_id = c.id 
            WHERE t.id=?
        """,
            (ticket_id,),
        )
        return self.cursor.fetchone()

    def add_ticket(self, customer_id, subject, description, priority):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            """
            INSERT INTO tickets (customer_id, subject, description, status, priority, created_at, updated_at) 
            VALUES (?, ?, ?, 'OPEN', ?, ?, ?)
        """,
            (customer_id, subject, description, priority, now, now),
        )
        self.conn.commit()

    def update_ticket(self, ticket_id, status, priority, description):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            """
            UPDATE tickets 
            SET status=?, priority=?, description=?, updated_at=?
            WHERE id=?
        """,
            (status, priority, description, now, ticket_id),
        )
        self.conn.commit()

    def get_kb_articles(self, query=""):
        if query:
            # Gelişmiş arama (FTS5)
            q = f"{query}*"
            self.cursor.execute(
                """
                SELECT id, title, content, tags, created_at 
                FROM kb_articles 
                WHERE id IN (SELECT rowid FROM kb_articles_fts WHERE kb_articles_fts MATCH ?)
                ORDER BY rank
            """,
                (q,),
            )
        else:
            self.cursor.execute("SELECT * FROM kb_articles ORDER BY id DESC")
        return self.cursor.fetchall()

    def add_kb_article(self, title, content, tags):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO kb_articles (title, content, tags, created_at) VALUES (?, ?, ?, ?)",
            (title, content, tags, now),
        )
        self.conn.commit()

    def delete_kb_article(self, article_id):
        self.cursor.execute("DELETE FROM kb_articles WHERE id=?", (article_id,))
        self.conn.commit()

    def create_licensing_tables(self):
        """Lisanslama ve Kayıt tablolarını oluşturur ve günceller."""
        # Kayıt Bilgileri (Kurumsal Adım 1)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS registration (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT,
                email TEXT,
                company_name TEXT,
                phone TEXT,
                purpose TEXT,
                is_verified INTEGER DEFAULT 0,
                trial_start_date TEXT,
                registration_date TEXT
            )
        """)

        # Lisans Bilgileri (Şifreli saklanacak - Kurumsal Adım 3 & 5)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS license_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                encrypted_key TEXT,
                license_type TEXT -- TRIAL, PRO, ENTERPRISE
            )
        """)

        # --- Şema Güncelleme (Mevcut kurulumlar için) ---
        try:
            self.cursor.execute("PRAGMA table_info(license_info)")
            cols = [row[1] for row in (self.cursor.fetchall() or [])]

            # Eklenecek sütunları ve türlerini tanımla
            columns_to_add = {
                "start_date": "TEXT",
                "expiry_date": "TEXT",
                "last_check_date": "TEXT",
                "hwid": "TEXT",
                "total_licenses": "INTEGER DEFAULT 0",
            }

            for col_name, col_type in columns_to_add.items():
                if col_name not in cols:
                    safe_col = self._safe_identifier(col_name)
                    self.cursor.execute(
                        "ALTER TABLE license_info ADD COLUMN {column_name} {col_type}".format(
                            column_name=safe_col,
                            col_type=col_type,
                        )
                    )
                    logger.info(f"Sütun eklendi: license_info.{col_name}")

        except Exception as e:
            logger.warning(f"Lisans tablosu şema güncelleme hatası: {e}")

        # Cihaz Sınırı ve Aktivasyonlar (Kurumsal Adım 4)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT,
                hwid TEXT UNIQUE,
                last_login TEXT
            )
        """)
        self.conn.commit()

    def create_assistant_notifications_table(self):
        """Asistan için olay bazlı bildirim tablosu"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS assistant_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT,
                type TEXT, -- 'info', 'payment', 'stock', 'device'
                is_critical INTEGER DEFAULT 0,
                status TEXT DEFAULT 'unread', -- 'unread', 'read'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def notify_assistant(self, message, n_type="info", is_critical=False):
        """Asistana yeni bir olay bildirir"""
        try:
            self.cursor.execute(
                """
                INSERT INTO assistant_notifications (message, type, is_critical)
                VALUES (?, ?, ?)
            """,
                (message, n_type, 1 if is_critical else 0),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Notify Assistant error: {e}")
            return False

    def get_unread_assistant_notifications(self, limit=10):
        """Asistan için okunmamış bildirimleri getirir ve okundu olarak işaretler"""
        try:
            self.cursor.execute(
                """
                SELECT id, message, type, is_critical, created_at 
                FROM assistant_notifications 
                WHERE status = 'unread' 
                ORDER BY created_at ASC LIMIT ?
            """,
                (limit,),
            )
            rows = self.cursor.fetchall()

            if rows:
                ids = [row[0] for row in rows]
                placeholders = ",".join(["?"] * len(ids))
                self.cursor.execute(
                    "UPDATE assistant_notifications SET status='read' WHERE id IN ({placeholders})".format(
                        placeholders=placeholders
                    ),
                    ids,
                )
                self.conn.commit()

            return rows
        except Exception as e:
            logger.error(f"Get unread notifications error: {e}")
            return []

    # --- Bank Accounts ---
