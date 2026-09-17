
import sqlite3
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

def check_schema():
    print("Checking Schema...")
    conn = sqlite3.connect("ayecpro.db")
    cursor = conn.cursor()
    
    # Check used_parts
    print("\n--- used_parts Schema ---")
    try:
        cursor.execute("PRAGMA table_info(used_parts)")
        cols = cursor.fetchall()
        for c in cols:
            print(c)
            
        print("\n--- Content Count ---")
        cursor.execute("SELECT count(*) FROM used_parts")
        print(f"Row count: {cursor.fetchone()[0]}")
        
    except Exception as e:
        print(f"Error checking used_parts: {e}")

    # Check parts
    print("\n--- parts Schema ---")
    try:
        cursor.execute("PRAGMA table_info(parts)")
        cols = cursor.fetchall()
        for c in cols:
            print(c)
    except:
        pass

if __name__ == "__main__":
    check_schema()
