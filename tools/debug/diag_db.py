import sqlite3
import os

databases = ['ayecpro.db', 'ayecpro.db', 'ayec_pro.db', 'ayec.db']

for db in databases:
    if not os.path.exists(db):
        continue
    print(f"\n--- Database: {db} ---")
    try:
        conn = sqlite3.connect(db)
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            c.execute(f"PRAGMA table_info({table_name})")
            columns = c.fetchall()
            for col in columns:
                print(f"  Column: {col[1]} ({col[2]})")
        conn.close()
    except Exception as e:
        print(f"Error checking {db}: {e}")
