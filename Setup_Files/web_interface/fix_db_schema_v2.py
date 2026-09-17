# -*- coding: utf-8 -*-


import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ayecpro.db"))

def complete_schema():
    print(f"Veritabanı yolu: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Appointments (Randevular)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            customer_name TEXT,
            service_type TEXT,
            status TEXT DEFAULT 'Pending'
        )
    """)
    print("- Randevular tablosu kontrol edildi.")

    # 2. Contracts (Sözleşmeler)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_no TEXT,
            customer_name TEXT,
            contract_type TEXT,
            start_date TEXT,
            end_date TEXT,
            amount REAL
        )
    """)
    print("- Sözleşmeler tablosu kontrol edildi.")

    # 3. Logistics (Lojistik) - shipment_out yerine logistics_tracking diyebiliriz
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tracking_no TEXT,
            customer_name TEXT,
            status TEXT,
            carrier TEXT,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("- Lojistik tablosu kontrol edildi.")

    # 4. Field Service (Saha)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS field_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            personnel TEXT,
            location TEXT,
            status TEXT,
            task_details TEXT
        )
    """)
    print("- Saha Operasyonları tablosu kontrol edildi.")
    
    conn.commit()
    conn.close()
    print("Veritabanı eksikleri tamamlandı.")

if __name__ == "__main__":
    complete_schema()

