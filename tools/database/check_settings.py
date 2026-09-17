import os
import sqlite3

def check_db():
    db_path = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')), 'AYECPro', 'ayecpro.db')
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # List settings
    print("--- SETTINGS ---")
    cursor.execute("SELECT key, value FROM settings")
    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    check_db()
