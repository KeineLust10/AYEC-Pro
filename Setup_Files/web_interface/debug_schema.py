
import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ayecpro.db"))
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

def get_table_info(table_name):
    cur.execute(f"PRAGMA table_info({table_name})")
    return cur.fetchall()

print("--- devices TABLOSU ---")
print(get_table_info('devices'))

print("\n--- service_definitions TABLOSU ---")
print(get_table_info('service_definitions'))

print("\n--- used_parts TABLOSU ---")
print(get_table_info('used_parts'))

conn.close()

