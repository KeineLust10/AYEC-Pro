import sqlite3
import os

db_path = "ayecpro.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    print("--- currency_transactions Schema ---")
    cursor.execute("PRAGMA table_info(currency_transactions)")
    for col in cursor.fetchall():
        print(col)
    
    print("\n--- First 3 rows ---")
    cursor.execute("SELECT * FROM currency_transactions LIMIT 3")
    for row in cursor.fetchall():
        print(dict(zip([d[0] for d in cursor.description], row)))
    
    conn.close()
else:
    print("Database not found")
