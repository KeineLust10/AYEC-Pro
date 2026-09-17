# -*- coding: utf-8 -*-

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import datetime, timedelta

from src.utils.logger import logger
from src.utils.path_helper import PathHelper


class DatabaseLegacyPart6Mixin:
    def update_users_schema(self):
        """Users tablosuna eksik kolonları ekler"""
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN email TEXT")
            self.conn.commit()
            logger.info("Users table updated with email column")
        except Exception as e:
            logger.debug(f"Users email column might already exist: {e}")
            
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN permissions TEXT")
            self.conn.commit()
            logger.info("Users table updated with permissions column")
        except Exception as e:
            logger.debug(f"Users permissions column might already exist: {e}")

        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN personnel_id INTEGER")
            self.conn.commit()
            logger.info("Users table updated with personnel_id column")
        except Exception as e:
            logger.debug(f"Users personnel_id column might already exist: {e}")

        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT")
            self.conn.commit()
            logger.info("Users table updated with created_at column")
        except Exception as e:
            logger.debug(f"Users created_at column might already exist: {e}")

        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            self.conn.commit()
            logger.info("Users table updated with full_name column")
        except Exception as e:
            logger.debug(f"Users full_name column might already exist: {e}")

        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN secret_question TEXT")
            self.conn.commit()
            logger.info("Users table updated with secret_question column")
        except Exception as e:
            logger.debug(f"Users secret_question column might already exist: {e}")

        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN secret_answer TEXT")
            self.conn.commit()
            logger.info("Users table updated with secret_answer column")
        except Exception as e:
            logger.debug(f"Users secret_answer column might already exist: {e}")
        
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1")
            self.conn.commit()
            logger.info("Users table updated with active column")
        except Exception as e:
            logger.debug(f"Users active column might already exist: {e}")
        
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN interface_edit_access INTEGER DEFAULT 0")
            self.conn.commit()
            logger.info("Users table updated with interface_edit_access column")
        except Exception as e:
            logger.debug(f"Users interface_edit_access column might already exist: {e}")

        # Otomatik Giriş ve Session için gerekli kolonlar
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN last_login TEXT")
            self.cursor.execute("ALTER TABLE users ADD COLUMN remember_token TEXT")
            self.cursor.execute("ALTER TABLE users ADD COLUMN auto_login INTEGER DEFAULT 0")
            self.conn.commit()
            logger.info("Users table updated with auto-login columns")
        except Exception as e:
            logger.debug(f"Users auto-login columns might already exist: {e}")



    def create_logistics_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS logistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                customer_name TEXT,
                status TEXT, -- Hazırlanıyor, Kargoda, Teslim Edildi
                cargo_firm TEXT,
                type TEXT, -- Giden, Gelen
                date TEXT,
                created_at TEXT
            )
        """)
        self.conn.commit()


    def add_logistics_item(self, tracking_no, customer_name, status, cargo_firm, l_type, date):
        self.create_logistics_table()
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO logistics (tracking_no, customer_name, status, cargo_firm, type, date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (tracking_no, customer_name, status, cargo_firm, l_type, date, created_at))
        self.conn.commit()
        return self.cursor.lastrowid


    def create_service_definitions_table(self):
        """Hizmet tanımları tablosu (Web interface için)"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS service_definitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    category TEXT,
                    price REAL DEFAULT 0,
                    duration TEXT,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Service definitions table creation error: {e}")


    def create_logistics_table(self):
        """Lojistik takip tablosu (Web interface için)"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS logistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracking_no TEXT,
                    customer_name TEXT,
                    status TEXT,
                    cargo_firm TEXT,
                    type TEXT,
                    date TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
        except Exception as e:
            logger.error(f"Logistics table creation error: {e}")



    def create_multi_currency_tables(self):
        '''Çoklu para birimi tabloları oluştur'''
        try:
            # 1. Müşteri döviz bakiyeleri
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_currency_balances (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    currency TEXT NOT NULL,
                    balance REAL DEFAULT 0,
                    last_updated TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(id),
                    UNIQUE(customer_id, currency)
                )
            ''')
            
            # 2. Dövizli işlemler
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS currency_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    transaction_type TEXT,
                    amount REAL,
                    currency TEXT,
                    exchange_rate REAL,
                    try_equivalent REAL,
                    description TEXT,
                    tracking_no TEXT,
                    created_at TEXT,
                    current_balance REAL DEFAULT 0.0,
                    is_invoiced INTEGER DEFAULT 0,
                    FOREIGN KEY (customer_id) REFERENCES customers(id)
                )
            ''')
            
            # 3. Döviz kurları
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS exchange_rates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    currency TEXT NOT NULL,
                    buying_rate REAL,
                    selling_rate REAL,
                    effective_date TEXT,
                    source TEXT DEFAULT 'TCMB',
                    created_at TEXT
                )
            ''')

            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_customer_balances_customer_currency "
                "ON customer_currency_balances(customer_id, currency)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_currency_transactions_customer_type_balance "
                "ON currency_transactions(customer_id, transaction_type, current_balance)"
            )
            self.cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_currency_transactions_created_at "
                "ON currency_transactions(created_at)"
            )
            
            self.conn.commit()
            logger.info('Multi-currency tables created successfully')
        except Exception as e:
            logger.error(f'Multi-currency tables creation error: {e}')

    def create_internal_settings_table(self):
        """Dahili ayarlar tablosu (Setup durumu vb.)"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS internal_settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        self.conn.commit()


    def get_internal_setting(self, key, default=None):
        try:
            return self._get_cached_setting_value("internal_settings", key, default)
        except Exception as e:
            logger.debug(f"Internal setting read fallback for {key}: {e}")
            return default


    def set_internal_setting(self, key, value):
        try:
            return self._set_cached_setting_value("internal_settings", key, value)
        except Exception as e:
            logger.error(f"Internal setting error: {e}")
            return False

    # --- E-INVOICE ---

    def create_einvoice_table(self):
        """E-Faturaların tutulduğu tablo"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS e_invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT UNIQUE, -- GIB ETTN
                invoice_type TEXT DEFAULT 'SATIS',
                receiver_name TEXT,
                receiver_vkn TEXT,
                amount REAL,
                status TEXT DEFAULT 'DRAFT', -- DRAFT, QUEUED, SENT, APPROVED, REJECTED, FAILED
                pdf_path TEXT,
                json_data TEXT, -- Yedek olarak gönderilen JSON
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

