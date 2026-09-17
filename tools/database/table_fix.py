# -*- coding: utf-8 -*-

import sqlite3
import os

DB_PATH = "ayecpro.db"

def run_fix():
    print("======== PREMIUM BULUT TABLO ONARIM SİSTEMİ ========")
    if not os.path.exists(DB_PATH):
        print(f"[UYARI] {DB_PATH} bulunamadı, yeni oluşturulacak.")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    tables = {
        "service_definitions": """
            CREATE TABLE IF NOT EXISTS service_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_name TEXT NOT NULL,
                category TEXT,
                price REAL DEFAULT 0,
                duration INTEGER,
                description TEXT
            )
        """,
        "customers": """
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT,
                email TEXT,
                address TEXT,
                tax_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "devices": """
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT UNIQUE,
                customer_name TEXT,
                device_brand TEXT,
                device_model TEXT,
                fault_description TEXT,
                urgency TEXT,
                entry_date TEXT,
                status TEXT,
                customer_id INTEGER,
                labor_cost REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "used_parts": """
            CREATE TABLE IF NOT EXISTS used_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                part_name TEXT,
                price REAL,
                quantity INTEGER DEFAULT 1,
                created_at TEXT
            )
        """,
        "parts": """
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                stock INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 0,
                price REAL DEFAULT 0,
                code TEXT,
                category TEXT
            )
        """,
        "stock": """
            CREATE TABLE IF NOT EXISTS stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_name TEXT,
                quantity INTEGER DEFAULT 0,
                min_stock INTEGER DEFAULT 0,
                price REAL DEFAULT 0
            )
        """,
        "customer_services": """
            CREATE TABLE IF NOT EXISTS customer_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                service_id INTEGER,
                service_name TEXT,
                quantity INTEGER,
                unit_price REAL,
                total_amount REAL,
                notes TEXT,
                date TEXT
            )
        """,
        "accounting": """
            CREATE TABLE IF NOT EXISTS accounting (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                customer_name TEXT,
                type TEXT,
                category TEXT,
                amount REAL,
                description TEXT,
                date TEXT
            )
        """,
        "accounting_records": """
            CREATE TABLE IF NOT EXISTS accounting_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                description TEXT,
                category TEXT,
                type TEXT,
                amount REAL
            )
        """,
        "personnel": """
            CREATE TABLE IF NOT EXISTS personnel (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                role TEXT,
                phone TEXT,
                email TEXT,
                salary REAL
            )
        """,
        "contracts": """
            CREATE TABLE IF NOT EXISTS contracts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_no TEXT,
                customer_id INTEGER,
                contract_type TEXT,
                start_date TEXT,
                end_date TEXT,
                amount REAL,
                status TEXT
            )
        """,
        "appointments": """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                phone TEXT,
                date TEXT,
                time TEXT,
                customer_id INTEGER,
                description TEXT,
                status TEXT,
                type TEXT,
                notes TEXT,
                created_at TEXT
            )
        """,
        "logistics": """
            CREATE TABLE IF NOT EXISTS logistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                description TEXT
            )
        """,
        "field_operations": """
            CREATE TABLE IF NOT EXISTS field_operations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                lat REAL,
                lng REAL,
                status TEXT
            )
        """,
        "system_logs": """
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                message TEXT,
                user TEXT
            )
        """
    }

    for table_name, schema in tables.items():
        try:
            cur.execute(schema)
            print(f"[OK] Tablo kontrol edildi: {table_name}")
        except Exception as e:
            print(f"[HATA] {table_name} oluşturulamadı: {e}")

    conn.commit()
    conn.close()
    print("\n[TAMAMLANDI] Tüm tablolar hazır. Şimdi siteyi tekrar deneyebilirsiniz.")
    # input("\nÇıkmak için Enter'a basın...")

if __name__ == "__main__":
    run_fix()
