import sqlite3
import os

db_path = "ayecpro.db"

def fix_db():
    print(f"Checking database: {db_path}")
    if not os.path.exists(db_path):
        print("Database not found.")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current columns
        cursor.execute("PRAGMA table_info(personnel)")
        cols = cursor.fetchall()
        col_names = [c[1] for c in cols]
        print(f"Current columns in 'personnel': {col_names}")
        
        required_cols = [
            ("username", "TEXT"), # Removed UNIQUE for ADD COLUMN compatibility
            ("password", "TEXT"),
            ("email", "TEXT"),
            ("active", "INTEGER DEFAULT 1"),
            ("salary", "REAL DEFAULT 0"),
            ("commission", "REAL DEFAULT 0"),
            ("tc_no", "TEXT"),
            ("department", "TEXT")
        ]
        
        for col_name, col_type in required_cols:
            if col_name not in col_names:
                print(f"Adding missing column: {col_name}...")
                try:
                    cursor.execute(f"ALTER TABLE personnel ADD COLUMN {col_name} {col_type}")
                    print(f"  - Added {col_name}")
                except Exception as e:
                    print(f"  - Failed to add {col_name}: {e}")
            else:
                print(f"Column {col_name} exists.")

        # Add constraints/indexes separately
        try:
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_personnel_username ON personnel(username)")
            print("Verified username unique index.")
        except Exception as e:
            print(f"Index error: {e}")
                
        conn.commit()
        
        # Verify again
        cursor.execute("PRAGMA table_info(personnel)")
        final_cols = [c[1] for c in cursor.fetchall()]
        print(f"Final columns: {final_cols}")
        
        conn.close()
        print("Database fix completed.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_db()
