# -*- coding: utf-8 -*-


import sqlite3
import os
import json
from datetime import datetime

# DB Yolu
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ayecpro.db"))
print(f"DB Path: {DB_PATH}")

def run_simulation():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        print("\n1. Customer Check...")
        cur.execute("SELECT id, name FROM customers LIMIT 1")
        cust = cur.fetchone()
        
        if not cust:
            print("   -> No customer, creating...")
            cur.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", ("Test Müşteri", "5551234567"))
            cust_id = cur.lastrowid
            cust_name = "Test Müşteri"
        else:
            cust_id = cust['id']
            cust_name = cust['name']
            print(f"   -> Found Customer: ID={cust_id}, Name={cust_name}")

        print("\n2. Device Insert Simulation...")
        
        cur.execute("SELECT MAX(id) as max_id FROM devices")
        row = cur.fetchone()
        max_id = row['max_id'] if row and row['max_id'] else 0
        tracking_no = f"SRV{max_id + 1:05d}"
        print(f"   -> Tracking No: {tracking_no}")
        
        process_date = datetime.now().strftime("%Y-%m-%d")
        desc_str = "Test Hizmeti (1x)"
        
        print("   -> Executing INSERT devices...")
        
        try:
            # Try with customer_id
            cur.execute("""
                INSERT INTO devices (
                    tracking_no, customer_name, device_brand, device_model,
                    fault_description, urgency, entry_date, status, customer_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tracking_no, cust_name, "Hızlı İşlem", "Genel Hizmet",
                f"Sihirbaz Kaydı: {desc_str}", "Normal", process_date, "Yeni Kayıt", cust_id
            ))
            print("   [OK] INSERT Success (with customer_id)")
            
        except sqlite3.OperationalError as e:
            print(f"   [WARN] Error with customer_id: {e}")
            print("   -> Trying fallback (without customer_id)...")
            
            cur.execute("""
                INSERT INTO devices (
                    tracking_no, customer_name, device_brand, device_model,
                    fault_description, urgency, entry_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tracking_no, cust_name, "Hızlı İşlem", "Genel Hizmet",
                f"Sihirbaz Kaydı: {desc_str}", "Normal", process_date, "Yeni Kayıt"
            ))
            print("   [OK] INSERT Success (Fallback)")

        service_id = cur.lastrowid
        print(f"   -> Service ID: {service_id}")

        print("\n3. Used Parts Insert...")
        # Check used_parts columns first
        print("   -> Checking used_parts schema...")
        parts_cols = [c[1] for c in cur.execute("PRAGMA table_info(used_parts)").fetchall()]
        print(f"   -> Columns: {parts_cols}")

        if 'quantity' not in parts_cols:
             print("   [ERROR] 'quantity' column MISSING in used_parts!")
        
        cur.execute("""
            INSERT INTO used_parts (tracking_no, part_name, price, quantity, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (tracking_no, "Test Parça", 100.0, 1, datetime.now().isoformat()))
        print("   [OK] Used Part Inserted.")
        
        conn.commit() # Commit to be sure no locks prevent it
        print("\n[SUCCESS] TEST COMPLETED WITHOUT ERRORS.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR]:\n{e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    run_simulation()

