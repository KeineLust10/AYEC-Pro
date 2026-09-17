# -*- coding: utf-8 -*-


import sqlite3
import os

def fix_db():
    try:
        # Target the local database in the current directory
        db_path = "ayecpro.db"
        if not os.path.exists(db_path):
            print(f"Database bulunamadı: {os.path.abspath(db_path)}")
            return

        print(f"Opening database: {os.path.abspath(db_path)}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if start_date exists
        cursor.execute("PRAGMA table_info(license_info)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "start_date" not in columns:
            print("Adding start_date column...")
            cursor.execute("ALTER TABLE license_info ADD COLUMN start_date TEXT")
            conn.commit()
            print("Column added successfully.")
        else:
            print("Column start_date already exists.")
            
        conn.close()
        print("Success.")
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    fix_db()
