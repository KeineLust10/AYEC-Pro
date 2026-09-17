import sqlite3
import os

def total_wipe():
    db_path = "ayecpro.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tables to PROTECT (ESSENTIAL FOR SYSTEM ACCESS/LICENSING)
    tables_to_keep = ["users", "license_info", "registration", "auth_groups", "sqlite_sequence"]

    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        all_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Total tables detected: {len(all_tables)}")
        
        for table in all_tables:
            if table in tables_to_keep:
                print(f"[-] Preserving system table: {table}")
                continue
            
            try:
                cursor.execute(f"DELETE FROM {table}")
                # Reset auto-increment
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                print(f"[X] Wiped table: {table}")
            except sqlite3.OperationalError as e:
                # FTS tables might need different handling but DELETE usually works
                print(f"[!] Warning: Could not wipe {table}: {e}")

        conn.commit()
        print("\n" + "="*40)
        print("SUCCESS: SYSTEM FULLY RESET TO FACTORY STATE.")
        print("Kept: Users, License, Registration, Auth Structure.")
        print("DELETED: All Customers, Devices, Accounting, Settings, Parts, Personnel etc.")
        print("="*40)
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    total_wipe()
    # Vacuum to reclaim space and ensure clean file
    try:
        conn = sqlite3.connect("ayecpro.db")
        conn.execute("VACUUM")
        conn.close()
        print("Database vacuumed and optimized.")
    except:
        pass
