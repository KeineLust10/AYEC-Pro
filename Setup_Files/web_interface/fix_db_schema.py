# -*- coding: utf-8 -*-


import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ayecpro.db"))

def fix_schema():
    print(f"Veritabanı yolu: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. used_parts tablosuna 'quantity' sütunu ekle
    try:
        cur.execute("ALTER TABLE used_parts ADD COLUMN quantity INTEGER DEFAULT 1")
        print("Sütun eklendi: used_parts -> quantity")
    except sqlite3.OperationalError as e:
        print(f"used_parts sütun eklemede hata (veya zaten var): {e}")

    # 2. Accounting (accounting_records) tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS accounting_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            description TEXT,
            category TEXT,
            amount REAL,
            type TEXT, -- Gelir / Gider
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 3. Logs (system_logs) tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            message TEXT,
            source TEXT
        )
    """)

    # 4. Personnel (personnel) tablosu
    cur.execute("""
        CREATE TABLE IF NOT EXISTS personnel (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            role TEXT,
            phone TEXT,
            email TEXT,
            status TEXT DEFAULT 'Active'
        )
    """)

    conn.commit()
    conn.close()
    print("Veritabanı şeması onarıldı.")

if __name__ == "__main__":
    fix_schema()

