import sqlite3
import os

def check_db():
    conn = sqlite3.connect("ayecpro.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    
    print(f"{'Table':<30} | {'Count':<10}")
    print("-" * 45)
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            count = cursor.fetchone()[0]
            status = "CLEAN" if count == 0 else "KEPT"
            if t in ["users", "license_info", "registration", "auth_groups"]:
                status = "SYSTEM"
            print(f"{t:<30} | {count:<10} | {status}")
        except:
            print(f"{t:<30} | ERROR")
    conn.close()

if __name__ == "__main__":
    check_db()
