import sqlite3
import os

app_data = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')), "AYEC Pro")
db_path = os.path.join(app_data, "ayecpro.db")

if not os.path.exists(db_path):
    print(f"ERROR: DB not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM settings WHERE key='asistan_sessiz_mod'")
    row = cur.fetchone()
    if row:
        print(f"Setting: {row[0]} = {row[1]}")
    else:
        print("Setting: asistan_sessiz_mod NOT FOUND (default: 0)")
    conn.close()
except Exception as e:
    print(f"ERROR: {e}")
