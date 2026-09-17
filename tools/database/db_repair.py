import sqlite3
import os

def repair_db():
    db_path = 'ayecpro.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Debug: Check schema
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(f"Tables found: {[t[0] for t in c.fetchall()]}")
    
    # Repair Personnel
    c.execute("SELECT name FROM sqlite_master WHERE name='personnel'")
    if c.fetchone():
        c.execute("UPDATE personnel SET status='Bosta' WHERE status LIKE 'Bo%'")
        print(f"Personnel status 'Bosta' updated: {c.rowcount} rows")
        
        c.execute("SELECT COUNT(*) FROM personnel")
        if c.fetchone()[0] == 0:
            print("Personnel table empty, adding default technicians...")
            default_staff = [
                ('Engin MAMU', 'Teknisyen', 'Bosta', '0555 111 2233'),
                ('Gurkan AYDIN', 'Teknisyen', 'Bosta', '0555 111 2244')
            ]
            c.executemany("INSERT INTO personnel (name, role, status, phone) VALUES (?, ?, ?, ?)", default_staff)
            print(f"Added {len(default_staff)} personnel.")
        
        c.execute("SELECT * FROM personnel")
        print(f"Current Personnel: {c.fetchall()}")
    else:
        print("Warning: personnel table not found!")
    
    # Repair Devices/Arsivlendi (if table exists)
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
    if c.fetchone():
        c.execute("UPDATE devices SET status='Arsivlendi' WHERE status LIKE 'ar%'")
        print(f"Devices status 'Arsivlendi' updated: {c.rowcount} rows")
        
        c.execute("UPDATE devices SET status='Arsivlendi' WHERE status LIKE 'Ar%'")
        print(f"Devices status (Ar%) updated: {c.rowcount} rows")

    conn.commit()
    conn.close()
    print("Database repair complete.")

if __name__ == "__main__":
    repair_db()
