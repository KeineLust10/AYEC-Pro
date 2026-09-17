
import sqlite3

def upgrade_db():
    try:
        conn = sqlite3.connect('ayecpro.db')
        cursor = conn.cursor()
        
        # Check columns
        cursor.execute("PRAGMA table_info(customers)")
        cols = [col[1] for col in cursor.fetchall()]
        
        if 'latitude' not in cols:
            print("Adding latitude column...")
            cursor.execute("ALTER TABLE customers ADD COLUMN latitude REAL DEFAULT 0")
            
        if 'longitude' not in cols:
            print("Adding longitude column...")
            cursor.execute("ALTER TABLE customers ADD COLUMN longitude REAL DEFAULT 0")
            
        conn.commit()
        conn.close()
        print("Database upgrade successful!")
    except Exception as e:
        print(f"Upgrade failed: {e}")

if __name__ == "__main__":
    upgrade_db()
