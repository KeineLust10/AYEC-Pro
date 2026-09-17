import sqlite3
import os
import sys

def fix_db():
    # Target the SPECIFIC known bad AppData path
    appdata_path = os.path.join(os.getenv("LOCALAPPDATA"), "AYECPro", "ayecpro.db")
    print(f"Targeting DB: {appdata_path}")
    
    if not os.path.exists(appdata_path):
        print("File not found.")
        return

    try:
        conn = sqlite3.connect(appdata_path)
        cursor = conn.cursor()
        
        # Check columns
        cursor.execute("PRAGMA table_info(personnel)")
        existing_cols = [c[1] for c in cursor.fetchall()]
        print(f"Existing columns: {existing_cols}")
        
        required_cols = [
            ("username", "TEXT"),
            ("password", "TEXT"),
            ("email", "TEXT"),
            ("active", "INTEGER DEFAULT 1"), # 1: Active, 0: Passive
            ("salary", "REAL DEFAULT 0"),
            ("commission", "REAL DEFAULT 0"),
            ("tc_no", "TEXT"),
            ("department", "TEXT")
        ]
        
        for col_name, col_type in required_cols:
            if col_name not in existing_cols:
                print(f"Adding {col_name}...")
                try:
                    cursor.execute(f"ALTER TABLE personnel ADD COLUMN {col_name} {col_type}")
                except Exception as e:
                    print(f"Error adding {col_name}: {e}")
            else:
                print(f"Skipping {col_name} (exists)")
                
        # Index
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_personnel_username ON personnel(username)")
            print("Index ensured.")
        except Exception as e:
            print(f"Index error: {e}")
            
        conn.commit()
        conn.close()
        print("Repair complete.")
        
    except Exception as e:
        print(f"Critical error: {e}")

if __name__ == "__main__":
    fix_db()
