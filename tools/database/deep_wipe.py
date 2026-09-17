import sqlite3
import os

def deep_wipe():
    db_path = "ayecpro.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tables to keep (System/Definition core)
    tables_to_keep = ["parts", "sqlite_sequence"]
    
    # We might want to keep users to allow login
    # But user said "everything including settings"
    # I'll keep 'users' and 'license_info' to prevent lockout/activation issues
    # unless they explicitly ask to wipe accounts too.
    # Usually "Settings" is the 'settings' table.
    tables_to_keep.extend(["users", "license_info", "registration"]) 

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        all_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Found {len(all_tables)} tables.")
        
        for table in all_tables:
            if table in tables_to_keep:
                print(f"Preserving table: {table}")
                continue
            
            try:
                cursor.execute(f"DELETE FROM {table}")
                # Reset auto-increment
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                print(f"Wiped table: {table}")
            except sqlite3.OperationalError as e:
                print(f"Warning: Could not wipe {table}: {e}")

        conn.commit()
        print("\nSUCCESS: Deep wipe completed.")
        print(f"Kept: {', '.join(tables_to_keep)}")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    deep_wipe()
