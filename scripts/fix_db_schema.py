# -*- coding: utf-8 -*-


import sqlite3
import os
import sys

# Add src path to allow imports if needed, though we use direct sqlite3 here
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

DB_PATH = os.path.join(os.getenv('LOCALAPPDATA'), 'AYECPro', 'ayecpro.db')
if not os.path.exists(DB_PATH):
    # Try legacy or alternative path
    DB_PATH = os.path.join(os.getenv('APPDATA'), 'AYECPro', 'ayecpro.db')

def fix_schema():
    print(f"Connecting to database: {DB_PATH}")
    if not os.path.exists(DB_PATH):
        print("Database not found!")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Fix: Missing 'internal_settings' table
    try:
        print("Checking 'internal_settings' table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS internal_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Checked/Created 'internal_settings' table.")
    except Exception as e:
        print(f"Error creating internal_settings: {e}")

    # 2. Fix: Missing 'is_invoiced' column in 'accounting'
    try:
        print("Checking 'is_invoiced' column in 'accounting'...")
        cursor.execute("PRAGMA table_info(accounting)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'is_invoiced' not in columns:
            print("Adding 'is_invoiced' column...")
            cursor.execute("ALTER TABLE accounting ADD COLUMN is_invoiced INTEGER DEFAULT 0")
        else:
            print("'is_invoiced' column exists.")
            
        if 'project_id' not in columns:
             print("Adding 'project_id' column...")
             cursor.execute("ALTER TABLE accounting ADD COLUMN project_id INTEGER")
        else:
            print("'project_id' column exists.")

    except Exception as e:
        print(f"Error checking accounting schema: {e}")
        
    # 3. Fix: Missing 'loan_installments' columns?
    # Log: table loan_installments has no column named amount
    # Code uses 'total_amount'. 'amounts' was likely a typo in older code or migration issue.
    # We will check if 'total_amount' exists.
    try:
        print("Checking 'loan_installments' schema...")
        cursor.execute("PRAGMA table_info(loan_installments)")
        columns = [info[1] for info in cursor.fetchall()]
        print(f"Columns: {columns}")
        
        # Ensure total_amount exists
        if 'total_amount' not in columns:
             # If 'amount' exists, rename it?
             if 'amount' in columns:
                 print("Renaming 'amount' to 'total_amount'...")
                 cursor.execute("ALTER TABLE loan_installments RENAME COLUMN amount TO total_amount")
             else:
                 print("Adding 'total_amount'...")
                 cursor.execute("ALTER TABLE loan_installments ADD COLUMN total_amount REAL DEFAULT 0")
    except Exception as e:
        print(f"Error checking loan_installments: {e}")

    # 4. Fix: currency_transactions missing is_invoiced?
    # Log: Hata onarımı başarısız: no such column: is_invoiced (in Database.auto_repair line 550)
    try:
        print("Checking 'currency_transactions' schema for auto_repair compatibility...")
        cursor.execute("PRAGMA table_info(currency_transactions)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'is_invoiced' not in columns:
            print("Adding 'is_invoiced' to currency_transactions...")
            cursor.execute("ALTER TABLE currency_transactions ADD COLUMN is_invoiced INTEGER DEFAULT 0")
        else:
            print("'is_invoiced' in currency_transactions exists.")
    except Exception as e:
        print(f"Error checking currency_transactions: {e}")

    conn.commit()
    conn.close()
    print("Schema fix complete.")

if __name__ == "__main__":
    fix_schema()
