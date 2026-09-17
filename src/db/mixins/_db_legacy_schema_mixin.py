# -*- coding: utf-8 -*-

import sqlite3
from src.utils.logger import logger

class DBLegacySchemaMixin:
    """Schema creation and migration methods for legacy components."""

    def _safe_identifier(self, identifier):
        """SQL injection prevention for column/table identifiers."""
        if not identifier: return ""
        return "".join(c for c in identifier if c.isalnum() or c == "_")

    def create_customer_services_table(self):
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
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS quick_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_name TEXT,
                label TEXT,
                is_active INTEGER DEFAULT 1,
                category TEXT DEFAULT 'Genel'
            )
        """)
        self.conn.commit()
        self.cursor.execute("SELECT COUNT(*) FROM quick_notes")
        if self.cursor.fetchone()[0] == 0:
            defaults = [
                ("service_notes", "EKRAN KIRIK", 1, "Telefon"),
                ("service_notes", "BATARYA ŞİŞİK", 1, "Telefon"),
                ("service_notes", "SIVI TEMAS", 1, "Genel"),
                ("service_notes", "DARBEYE BAĞLI", 1, "Genel"),
                ("service_notes", "AÇILMIYOR", 1, "Genel"),
                ("service_notes", "ŞARJ ALMIYOR", 1, "Telefon"),
                ("customer_notes", "CİHAZ YAPILDI", 1, "Genel"),
                ("customer_notes", "PARÇA BEKLİYOR", 1, "Genel"),
                ("customer_notes", "İADE EDİLDİ", 1, "Genel"),
                ("customer_notes", "TESLİM EDİLDİ", 1, "Genel"),
                ("technical_notes", "TEST OK", 1, "Genel"),
                ("technical_notes", "Fiyat Onayı Alındı", 1, "Genel"),
                ("technical_notes", "Parça Siparişi Geçildi", 1, "Genel"),
                ("technical_notes", "VIP Müşteri", 1, "Genel"),
                ("accessories_notes", "SIM Kart", 1, "Aksesuar"),
                ("accessories_notes", "SD Kart", 1, "Aksesuar"),
                ("accessories_notes", "Kılıf", 1, "Aksesuar"),
                ("accessories_notes", "Şarj Aleti", 1, "Aksesuar"),
                ("accessories_notes", "Kutu", 1, "Aksesuar"),
                ("accessories_notes", "Kablo", 1, "Aksesuar"),
            ]
            self.cursor.executemany("INSERT INTO quick_notes (group_name, label, is_active, category) VALUES (?, ?, ?, ?)", defaults)
            self.conn.commit()

    def create_company_info_table(self):
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
        try:
            self.cursor.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='company_info'"
            )
            if not self.cursor.fetchone():
                self.create_company_info_table()
                return
            self.cursor.execute("PRAGMA table_info(company_info)")
            cols = [row[1] for row in (self.cursor.fetchall() or [])]
            if "logo_path" not in cols:
                self.cursor.execute("ALTER TABLE company_info ADD COLUMN logo_path TEXT")
                self.conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update company_info schema: {e}")

    def create_fast_notes_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS fast_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                label TEXT, 
                is_active INTEGER DEFAULT 1,
                display_order INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def update_accounting_schema(self):
        self.create_accounting_table()
        try:
            self.cursor.execute("PRAGMA table_info(accounting)")
            cols = [row[1] for row in self.cursor.fetchall()]
            extra_cols = [
                ("customer_id", "INTEGER"), ("customer_name", "TEXT"), ("created_at", "TEXT"),
                ("is_invoiced", "INTEGER DEFAULT 0"), ("currency", "TEXT DEFAULT 'TRY'"),
                ("exchange_rate", "REAL DEFAULT 1.0"), ("original_amount", "REAL"),
                ("try_equivalent", "REAL"), ("project_id", "INTEGER"), ("tracking_no", "TEXT"),
                ("payment_method", "TEXT"), ("bank_account_id", "INTEGER"), ("related_account_id", "INTEGER"),
                ("ref_no", "TEXT"), ("selected_services", "TEXT"), ("product_service_id", "INTEGER"),
                ("product_service_type", "TEXT")
            ]
            for name, ddl in extra_cols:
                if name not in cols:
                    self.cursor.execute(f"ALTER TABLE accounting ADD COLUMN {self._safe_identifier(name)} {ddl}")
            self.conn.commit()
        except Exception as e:
            logger.error(f"Failed to update accounting schema: {e}")

    def create_bank_accounts_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name TEXT, account_holder TEXT, iban TEXT, account_number TEXT,
                branch_code TEXT, currency TEXT DEFAULT 'TRY', is_active INTEGER DEFAULT 1,
                created_at TEXT, current_balance REAL DEFAULT 0, is_deleted INTEGER DEFAULT 0, deleted_at TEXT
            )
        """)
        self.conn.commit()

    def create_contracts_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER, title TEXT, start_date TEXT, end_date TEXT,
                contract_type TEXT, price REAL DEFAULT 0, status TEXT DEFAULT 'Aktif',
                description TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def create_audit_log_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT, table_name TEXT, action TEXT, details TEXT, created_at TEXT
            )
        """)
        self.conn.commit()

    def create_sms_log_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sms_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT, phone TEXT, message TEXT, twilio_sid TEXT, sent_at TEXT
            )
        """)
        self.conn.commit()

    def create_indexes(self):
        try:
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_devices_tracking ON devices(tracking_no)",
                "CREATE INDEX IF NOT EXISTS idx_devices_status ON devices(status)",
                "CREATE INDEX IF NOT EXISTS idx_accounting_date ON accounting(date)",
                "CREATE INDEX IF NOT EXISTS idx_accounting_customer ON accounting(customer_id)",
                "CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(name)"
            ]
            for idx_sql in indices:
                self.cursor.execute(idx_sql)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Index creation error: {e}")

    def update_advanced_schema(self):
        migrations = [
            ("users", "commission_rate", "REAL DEFAULT 0"),
            ("parts", "barcode", "TEXT"),
            ("parts", "min_stock", "INTEGER DEFAULT 5"),
            ("devices", "photo_paths", "TEXT"),
            ("devices", "payment_status", "TEXT DEFAULT 'Beklemede'"),
            ("devices", "is_archived", "INTEGER DEFAULT 0"),
            ("devices", "exit_date", "TEXT"),
        ]
        for table, col, dtype in migrations:
            try:
                self.cursor.execute(f"PRAGMA table_info({self._safe_identifier(table)})")
                cols = [row[1] for row in self.cursor.fetchall()]
                if col not in cols:
                    self.cursor.execute(f"ALTER TABLE {self._safe_identifier(table)} ADD COLUMN {self._safe_identifier(col)} {dtype}")
            except Exception as e:
                logger.error(f"Advanced migration error ({table}.{col}): {e}")
        self.conn.commit()

    def create_settings_tables(self):
        self.cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS whatsapp_templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, content TEXT)")
        self.conn.commit()

    def create_announcements_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, priority TEXT,
                title TEXT, content TEXT, author TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def create_support_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, subject TEXT,
                description TEXT, status TEXT DEFAULT 'OPEN', priority TEXT DEFAULT 'NORMAL',
                created_at TEXT, updated_at TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS kb_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT, tags TEXT, created_at TEXT
            )
        """)
        self.conn.commit()

    def create_licensing_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS registration (
                id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT, email TEXT,
                company_name TEXT, phone TEXT, purpose TEXT, is_verified INTEGER DEFAULT 0,
                trial_start_date TEXT, registration_date TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS license_info (
                id INTEGER PRIMARY KEY AUTOINCREMENT, encrypted_key TEXT, license_type TEXT,
                start_date TEXT, expiry_date TEXT, last_check_date TEXT, hwid TEXT, total_licenses INTEGER DEFAULT 0
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT, device_name TEXT, hwid TEXT UNIQUE, last_login TEXT
            )
        """)
        self.conn.commit()

    def create_assistant_notifications_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS assistant_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT, message TEXT, type TEXT,
                is_critical INTEGER DEFAULT 0, status TEXT DEFAULT 'unread',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
