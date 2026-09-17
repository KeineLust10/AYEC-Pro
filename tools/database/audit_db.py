
import sqlite3
import os

def audit(path):
    if not os.path.exists(path):
        print(f"--- {path} does not exist ---")
        return
    print(f"--- Auditing {path} ---")
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in c.fetchall()]
        print("Tables:", tables)
        for t in ['personnel', 'settings', 'devices', 'customers', 'accounting']:
            if t in tables:
                c.execute(f"SELECT COUNT(*) FROM {t}")
                count = c.fetchone()[0]
                print(f"  [{t}] count: {count}")
                if t == 'personnel' and count > 0:
                    c.execute("SELECT id, name, telegram_username, lat, lng, status FROM personnel")
                    rows = c.fetchall()
                    for r in rows:
                        print(f"    - ID:{r['id']} Name:{r['name']} Tele:@{r['telegram_username']} Lat:{r['lat']} Lng:{r['lng']} Status:{r['status']}")
        conn.close()
    except Exception as e:
        print(f"Error auditing {path}: {e}")

if __name__ == "__main__":
    audit('ayecpro.db')
    audit('backend/ayecpro.db')
    # Also check if there's any other .db in current dir
    for f in os.listdir('.'):
        if f.endswith('.db') and f != 'ayecpro.db':
            audit(f)
