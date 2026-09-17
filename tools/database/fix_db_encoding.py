import sqlite3
import os

def check_column_exists(cursor, table_name, column_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [col[1] for col in cursor.fetchall()]
    return column_name in columns

def fix_db():
    db_path = "ayecpro.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("Starting database cleanup with improved schema detection...")

        # 1. Fix Personnel Statuses (Checking columns first)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='personnel'")
        if cursor.fetchone():
            if check_column_exists(cursor, 'personnel', 'status'):
                cursor.execute("UPDATE personnel SET status = 'Bosta' WHERE status LIKE 'Bo%'")
                cursor.execute("UPDATE personnel SET status = 'Gorevde' WHERE status LIKE 'Go%'")
                cursor.execute("UPDATE personnel SET status = 'Mesgul' WHERE status LIKE 'Me%'")
                print("Personnel statuses updated.")
            else:
                print("Skipping personnel status update (column 'status' not found).")
        
        # 2. Fix Device Statuses
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
        if cursor.fetchone():
            if check_column_exists(cursor, 'devices', 'status'):
                # Handle cases where Turkish characters are already mangled or used as placeholders
                cursor.execute("UPDATE devices SET status = 'Arsivlendi' WHERE status LIKE 'ar%ivlendi' OR status LIKE 'Ar%ivlendi' OR status LIKE 'Ars%'")
                cursor.execute("UPDATE devices SET status = 'Beklemede' WHERE status LIKE 'Bek%'")
                cursor.execute("UPDATE devices SET status = 'Tamamlandi' WHERE status LIKE 'Tam%'")
                print("Device statuses updated.")

        # 3. Fix Customer Types
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        if cursor.fetchone():
            if check_column_exists(cursor, 'customers', 'type'):
                cursor.execute("UPDATE customers SET type = 'Bireysel' WHERE type LIKE 'Bir%'")
                cursor.execute("UPDATE customers SET type = 'Kurumsal' WHERE type LIKE 'Kur%'")
                print("Customer types updated.")

        conn.commit()
        print("Cleanup successful!")
    except Exception as e:
        print(f"Error during cleanup: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_db()
