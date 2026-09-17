# -*- coding: utf-8 -*-


import sqlite3
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

def debug_cogs():
    print("Debugging COGS Calculation...")
    
    from src.database import Database
    db = Database()
    
    # 1. Check used_parts content
    print("\n--- used_parts Content ---")
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM used_parts")
    rows = cursor.fetchall()
    
    if not rows:
        print("used_parts table is EMPTY.")
    else:
        for r in rows:
            print(dict(r))

    # 2. Check calculate_cogs Logic
    print("\n--- Testing calculate_cogs ---")
    
    # Mock date range for "Year" (2026 as per user screenshot imply 2026 context, but let's check current date too)
    # The user screenshot says "2026 yılı Gelir Vergisi...", so let's see what date range the app uses.
    # FinanceManager uses datetime.now() for "year". If system time is 2026, it filters for 2026.
    
    current_year = datetime.now().year
    print(f"Current System Year: {current_year}")
    
    start_date = f"{current_year}-01-01"
    end_date = f"{current_year}-12-31 23:59:59"
    
    print(f"Querying for range: {start_date} to {end_date}")
    
    sql = """
        SELECT quantity, purchase_price_snapshot
        FROM used_parts 
        WHERE used_at BETWEEN ? AND ?
    """
    
    cursor.execute(sql, (start_date, end_date))
    results = cursor.fetchall()
    
    total_cogs = 0.0
    for row in results:
        qty = row[0]
        price = row[1]
        print(f"Found Item - Qty: {qty}, Snapshot Price: {price}")
        total_cogs += qty * price
        
    print(f"\nCalculated COGS: {total_cogs}")

if __name__ == "__main__":
    debug_cogs()
