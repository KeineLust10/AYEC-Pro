import sqlite3
import os

db_path = 'ayecpro.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM registration LIMIT 1")
    reg = cursor.fetchone()
    print(f"REGISTRATION: {reg}")
    
    cursor.execute("SELECT key, value FROM settings WHERE key='remember_me'")
    rem = cursor.fetchone()
    print(f"REMEMBER_ME: {rem}")
    
    conn.close()
else:
    print(f"Database {db_path} not found!")
