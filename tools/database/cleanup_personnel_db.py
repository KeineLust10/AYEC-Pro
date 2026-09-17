import sqlite3

def clean_db():
    try:
        conn = sqlite3.connect('ayecpro.db')
        c = conn.cursor()
        
        # Ensure columns exist
        cols = [('lat', 'REAL'), ('lng', 'REAL'), ('status', "TEXT DEFAULT 'Bosta'"), ('last_seen', 'TEXT')]
        for col_name, col_type in cols:
            try:
                c.execute(f"ALTER TABLE personnel ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name}")
            except sqlite3.OperationalError:
                pass # Already exists
        
        # Cleanup status and seed location
        c.execute("UPDATE personnel SET status='Bosta' WHERE status LIKE 'Bo%' OR status IS NULL")
        c.execute("UPDATE personnel SET status='Gorevde' WHERE status LIKE 'G%'")
        c.execute("UPDATE personnel SET lat=39.6484, lng=27.8826 WHERE lat IS NULL")
        
        conn.commit()
        print("Database cleaned and patched successfully.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    clean_db()
