import sqlite3
import os
from src.utils.path_helper import PathHelper

def verify():
    db_path = PathHelper.get_db_path("ayecpro.db")
    print(f"Checking database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Check loaner_devices columns
    cur.execute("PRAGMA table_info(loaner_devices)")
    columns = [row[1] for row in cur.fetchall()]
    print(f"loaner_devices columns: {columns}")
    
    if "shelf_no" in columns:
        print("SUCCESS: shelf_no column exists.")
    else:
        print("FAILURE: shelf_no column missing.")
        
    conn.close()

if __name__ == "__main__":
    verify()
