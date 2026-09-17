import sqlite3
import os

def final_restore():
    src_db = "ayecpro.db.repair"
    dst_db = "ayecpro.db"
    
    if not os.path.exists(src_db):
        print("Source not found.")
        return

    s_conn = sqlite3.connect(src_db)
    d_conn = sqlite3.connect(dst_db)
    
    tables = ["users", "license_info", "registration"]
    
    for table in tables:
        try:
            print(f"Restoring {table}...")
            # Get data
            rows = s_conn.execute(f"SELECT * FROM {table}").fetchall()
            
            # Get Schema from Dest
            cursor = d_conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            cols = cursor.fetchall()
            if not cols:
                print(f"Table {table} does not exist in destination. Creating...")
                # Simple create if missing? No, Database() should have created it.
                # Let's check why it's missing.
                continue

            placeholders = ",".join(["?"] * len(cols))
            cursor.execute(f"DELETE FROM {table}")
            cursor.executemany(f"INSERT INTO {table} VALUES ({placeholders})", rows)
            d_conn.commit()
            print(f"Success: {len(rows)} rows restored to {table}")
        except Exception as e:
            print(f"Error restoring {table}: {e}")

    s_conn.close()
    d_conn.close()
    print("Final restore complete.")

if __name__ == "__main__":
    final_restore()
