import sqlite3
import os
import sys

# Try to find the DB in multiple potential locations
potential_paths = [
    "ayecpro.db",
    os.path.join(os.getcwd(), "ayecpro.db"),
    os.path.join(os.getenv("APPDATA"), "AYECPro", "ayecpro.db"),
    os.path.join(os.getenv("LOCALAPPDATA"), "AYECPro", "ayecpro.db"),
    os.path.join(os.getenv("APPDATA"), "AYECPro", "ayecpro.db"),
    os.path.join(os.getenv("LOCALAPPDATA"), "AYECPro", "ayecpro.db"),
]

print(f"CWD: {os.getcwd()}")
print("-" * 50)

found_dbs = []

for path in potential_paths:
    if os.path.exists(path):
        print(f"Found DB at: {path}")
        found_dbs.append(path)
        try:
            conn = sqlite3.connect(path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(personnel)")
            cols = cursor.fetchall()
            col_names = [c[1] for c in cols]
            print(f"  Schema: {col_names}")
            
            if "username" in col_names:
                print("  ✅ 'username' column EXISTS.")
            else:
                print("  ❌ 'username' column MISSING. Attempting FIX...")
                try:
                    cursor.execute("ALTER TABLE personnel ADD COLUMN username TEXT")
                    print("    -> Added 'username' column.")
                except Exception as e:
                    print(f"    -> Add failed: {e}")
                    
            if "password" not in col_names:
                print("  ❌ 'password' column MISSING. Attempting FIX...")
                try:
                    cursor.execute("ALTER TABLE personnel ADD COLUMN password TEXT")
                    print("    -> Added 'password' column.")
                except Exception as e:
                    print(f"    -> Add failed: {e}")

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"  Error reading DB: {e}")
    else:
        print(f"No DB at: {path}")
            
print("-" * 50)
if not found_dbs:
    print("CRITICAL: No database file found anywhere!")
else:
    print(f"Total DBs found: {len(found_dbs)}")
