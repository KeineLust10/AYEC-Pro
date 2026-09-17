"""
Database schema update for authentication features
"""

import sqlite3

conn = sqlite3.connect(r'C:\Users\Admin\AppData\Local\AYECPro\ayecpro.db')
cursor = conn.cursor()

print("=== UPDATING DATABASE SCHEMA ===\n")

# Check and add columns to users table
columns_to_add = [
    ("auto_login", "INTEGER DEFAULT 0"),
    ("last_login", "TEXT"),
    ("remember_token", "TEXT"),
    ("email", "TEXT"),
    ("created_at", "TEXT")
]

for column_name, column_def in columns_to_add:
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if column_name not in columns:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_def}")
            print(f"[OK] Added column: {column_name}")
        else:
            print(f"[SKIP] Column already exists: {column_name}")
    except Exception as e:
        print(f"[ERROR] {column_name}: {e}")

conn.commit()
conn.close()

print("\n[SUCCESS] Database schema updated!")
