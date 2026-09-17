
import sqlite3
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def verify_and_populate():
    print("Verifying SMM Logic & Populating Data...")
    
    from src.database import Database
    from src.utils.finance_manager import FinanceManager
    from src.utils.path_helper import PathHelper
    
    print(f"DB Path verified: {PathHelper.get_db_path('ayecpro.db')}")
    
    db = Database()
    fm = FinanceManager(db)
    
    # 1. Get a test part
    print("Fetching a test part...")
    part = db.cursor.execute("SELECT id, name, purchase_price, stock FROM parts WHERE stock > 0 LIMIT 1").fetchone()
    
    if not part:
        print("No parts found with stock!")
        return
        
    pid, pname, pprice, pstock = part
    print(f"Test Part: {pname} (ID: {pid}) - Purchase Price: {pprice}, Current Stock: {pstock}")
    
    # 2. Simulate Usage (Backend Check)
    print("\n--- Simulating usage (db.use_part) ---")
    tracking_no = f"TEST-SMM-{datetime.now().strftime('%H%M%S')}"
    qty_used = 1
    
    # BEFORE
    cnt_before = db.cursor.execute("SELECT COUNT(*) FROM used_parts").fetchone()[0]
    
    # Commit to clear any read transaction locks
    db.conn.commit()
    
    # EXECUTE
    print(f"Calling use_part({pid}, {qty_used}, {tracking_no})...")
    success = db.use_part(pid, qty_used, tracking_no)
    print(f"db.use_part returned: {success}")
    
    print(f"db.use_part returned: {success}")
    
    # AFTER
    cnt_after = db.cursor.execute("SELECT COUNT(*) FROM used_parts").fetchone()[0]
    
    print(f"Count Before: {cnt_before}, Count After: {cnt_after}")
    
    if cnt_after == cnt_before:
        print("FAILURE: Count did not increase via logic. Attempting RAW INSERT...")
        try:
            db.cursor.execute("INSERT INTO used_parts (tracking_no, part_id, quantity, used_at) VALUES (?, ?, ?, datetime('now'))", 
                              ("RAW-TEST", pid, 1))
            db.conn.commit()
            cnt_raw = db.cursor.execute("SELECT COUNT(*) FROM used_parts").fetchone()[0]
            if cnt_raw > cnt_after:
                print(f"SUCCESS: RAW INSERT worked! Count is now {cnt_raw}. The issue IS in use_part logic.")
            else:
                print("FAILURE: RAW INSERT also failed to increase count!")
        except Exception as e:
            print(f"RAW INSERT Exception: {e}")
    
    if success and cnt_after > cnt_before:
        print(f"SUCCESS: 'use_part' worked. Row count increased {cnt_before} -> {cnt_after}")
        
        # Verify stored price
        stored_row = db.cursor.execute("SELECT * FROM used_parts WHERE tracking_no=?", (tracking_no,)).fetchone()
        print(f"Stored Row: {dict(stored_row)}")
        if float(stored_row['purchase_price_snapshot']) == float(pprice):
            print("SUCCESS: Purchase price snapshot matches.")
        else:
            print(f"FAILURE: Price snapshot mismatch! Expected {pprice}, got {stored_row['purchase_price_snapshot']}")
            
    else:
        print("FAILURE: 'use_part' did not add a row or returned False.")
    
    # 3. Check COGS Calculation
    print("\n--- Checking FinanceManager.calculate_cogs ---")
    start, end = fm._get_date_range("year")
    cogs = fm.calculate_cogs(start, end)
    print(f"Calculated COGS for Year: {cogs}")
    
    if cogs > 0:
        print("SUCCESS: FinanceManager correctly calculates SMM from DB.")
    else:
        print("FAILURE: COGS is still 0 despite data.")
        
    print("\n--- Populating more test data for user visibility ---")
    # Add a few more usages to make the number significant for the demo
    parts = db.cursor.execute("SELECT id, purchase_price FROM parts LIMIT 5").fetchall()
    for p in parts:
        try:
            db.use_part(p[0], 2, f"DEMO-{datetime.now().strftime('%f')}")
            print(f"Added usage for Part ID {p[0]}")
        except Exception as e:
            print(f"Err: {e}")
            
    print("Done.")

if __name__ == "__main__":
    verify_and_populate()
