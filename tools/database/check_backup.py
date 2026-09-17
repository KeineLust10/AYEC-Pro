import sqlite3
import os

def check_backup(path):
    if not os.path.exists(path):
        print("Not found")
        return
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    for t in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            count = cursor.fetchone()[0]
            if count > 0:
                print(f"{t}: {count}")
        except:
            pass
    conn.close()

if __name__ == "__main__":
    check_backup("backups/ayecpro_backup_20260117_194011.db")
