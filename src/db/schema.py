# -*- coding: utf-8 -*-

"""
Database Schema Modülü
Tüm tablo oluşturma ve schema güncelleme metodları burada toplanacak.
Bu dosya database.py'den refactor edilecek.
"""
import sqlite3
from src.utils.logger import logger


def _safe_identifier(name: str) -> str:
    if not name or not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQL identifier: {name}")
    return name


class DatabaseSchema:
    """
    Database schema yönetimi için helper class.
    Database sınıfı bu metodları kullanabilir.
    """
    
    @staticmethod
    def create_devices_table(cursor, conn):
        """Devices tablosunu oluştur"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT UNIQUE,
                customer_name TEXT,
                device_brand TEXT,
                device_model TEXT,
                serial_no TEXT,
                fault_category TEXT,
                urgency TEXT,
                status TEXT,
                entry_date TEXT,
                estimated_date TEXT,
                price REAL DEFAULT 0,
                device_type TEXT,
                imei TEXT,
                pattern_lock TEXT,
                customer_type TEXT,
                customer_tax_id TEXT,
                customer_contact TEXT,
                fault_description TEXT,
                photo_path TEXT,
                approval_status TEXT DEFAULT 'Beklemede',
                customer_id INTEGER,
                vehicle_plate TEXT,
                vehicle_vin TEXT,
                vehicle_maintenance_card_id INTEGER,
                service_source TEXT,
                fault_codes TEXT,
                obd_notes TEXT,
                inspection_summary TEXT,
                delivery_method TEXT,
                service_location TEXT,
                other_info TEXT,
                delivered_by_name TEXT,
                delivered_by_phone TEXT,
                approval_requested_at TEXT,
                approval_decision_at TEXT,
                invoice_ready_at TEXT,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT
            )
        """)
        conn.commit()

    @staticmethod
    def create_bank_accounts_table(cursor, conn):
        """Banka hesapları tablosunu oluştur"""
        cursor.execute("""
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
        conn.commit()

    @staticmethod
    def create_contracts_table(cursor, conn):
        """Bakım sözleşmeleri tablosunu oluştur"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                title TEXT,
                start_date TEXT,
                end_date TEXT,
                contract_type TEXT,
                price REAL DEFAULT 0,
                status TEXT DEFAULT 'Aktif',
                description TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    
    @staticmethod
    def update_customers_schema(cursor, conn):
        """Customers tablosuna yeni kolonlar ekle"""
        customer_columns = [
            ("phone2", "TEXT"),
            ("company_name", "TEXT"),
            ("tc_no", "TEXT"),
            ("tax_no", "TEXT"),
            ("tax_office", "TEXT"),
            ("district", "TEXT"),
            ("city", "TEXT"),
            ("neighborhood", "TEXT"),
            ("street", "TEXT"),
            ("zip_code", "TEXT"),
        ]
        
        for col_name, col_type in customer_columns:
            try:
                cursor.execute(
                    f"ALTER TABLE customers ADD COLUMN {_safe_identifier(col_name)} {col_type}"
                )
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    logger.warning(f"Could not add column {col_name}: {e}")
        conn.commit()
    
    @staticmethod
    def create_parts_table(cursor, conn):
        """Parts tablosunu oluştur"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                brand TEXT,
            stock REAL,
                price REAL,
                code TEXT,
                barcode TEXT,
                category TEXT DEFAULT 'Genel',
            min_stock REAL DEFAULT 5,
                purchase_price REAL DEFAULT 0,
                currency TEXT DEFAULT 'TRY',
                description TEXT,
                shelf_number TEXT,
                photo_path TEXT,
                oem_code TEXT,
                equivalent_code TEXT,
                compatible_models TEXT
            )
        """)
        conn.commit()
    
    @staticmethod
    def create_accounting_table(cursor, conn):
        """Accounting tablosunu oluştur"""
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT,
                category TEXT,
                amount REAL,
                description TEXT,
                date TEXT,
                customer_id INTEGER,
                customer_name TEXT,
                is_invoiced INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                bank_account_id INTEGER
            )
        """)
        conn.commit()
