# -*- coding: utf-8 -*-

import sqlite3
import os

db_path = "ayecpro.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print("--- Tables and Row Counts ---")
    for (table_name,) in tables:
        cursor.execute(f"SELECT COUNT(*) FROM \"{table_name}\"")
        count = cursor.fetchone()[0]
        print(f"{table_name}: {count}")
    
    # Check customers to find Ahmet Yılmaz
    print("\n--- Searching for Ahmet Yılmaz ---")
    cursor.execute("SELECT id, name FROM customers WHERE name LIKE '%Ahmet Yılmaz%'")
    customer = cursor.fetchone()
    if customer:
        print(f"Found: ID={customer[0]}, Name={customer[1]}")
        cust_id = customer[0]
        
        # Check devices
        cursor.execute("SELECT COUNT(*) FROM devices WHERE customer_name=?", (customer[1],))
        print(f"Devices count: {cursor.fetchone()[0]}")
        
        # Check accounting
        cursor.execute("SELECT COUNT(*) FROM accounting WHERE customer_id=?", (cust_id,))
        print(f"Accounting rows: {cursor.fetchone()[0]}")
        
        # Check currency_transactions
        cursor.execute("SELECT COUNT(*) FROM currency_transactions WHERE customer_id=?", (cust_id,))
        print(f"Currency transactions: {cursor.fetchone()[0]}")
    else:
        print("Ahmet Yılmaz not found in customers table")

    conn.close()
else:
    print("Database not found")
