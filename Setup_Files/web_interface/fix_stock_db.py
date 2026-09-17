
import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ayecpro.db"))

def check_and_fix_stock():
    print(f"DB Path: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # 1. STOCK Table Check
    try:
        cur.execute("SELECT * FROM stock LIMIT 1")
        print("Stock table exists.")
    except sqlite3.OperationalError:
        print("Stock table MISSING! Creating...")
        cur.execute("""
            CREATE TABLE stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_name TEXT,
                stock_quantity INTEGER DEFAULT 0,
                min_stock_level INTEGER DEFAULT 5,
                price REAL DEFAULT 0.0,
                category TEXT
            )
        """)
        print("Stock table created.")

    # 2. DEVICES Table Columns Check
    print("\n--- DEVICES Columns ---")
    data = cur.execute("PRAGMA table_info(devices)").fetchall()
    cols = [d[1] for d in data]
    print(cols)
    
    if 'customer_id' not in cols:
        print("Adding customer_id to devices...")
        try:
            cur.execute("ALTER TABLE devices ADD COLUMN customer_id INTEGER")
        except: pass

    conn.commit()
    conn.close()

if __name__ == "__main__":
    check_and_fix_stock()

