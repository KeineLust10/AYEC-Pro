
import sqlite3
import os

db_path = "ayecpro.db"
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

tables = ["customers", "customer_services", "accounting", "devices"]
for table in tables:
    print(f"\n--- {table} ---")
    cur.execute(f"PRAGMA table_info({table})")
    for row in cur.fetchall():
        print(row)

conn.close()
