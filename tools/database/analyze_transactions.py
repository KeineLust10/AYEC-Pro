import sqlite3
import os

db_path = "ayecpro.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Transaction Type Counts ---")
    cursor.execute("SELECT transaction_type, COUNT(*) FROM currency_transactions GROUP BY transaction_type")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]}")
    
    conn.close()
else:
    print("Database not found")
