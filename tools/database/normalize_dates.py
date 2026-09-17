import sqlite3
import os
import re
from datetime import datetime

def normalize_date(date_str):
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    
    # DD.MM.YYYY -> YYYY-MM-DD
    if re.match(r'^\d{2}\.\d{2}\.\d{4}$', date_str):
        d, m, y = date_str.split('.')
        return f"{y}-{m}-{d}"
    
    # If already YYYY-MM-DD, return as is
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        return date_str[:10]
        
    return date_str

def run_fix():
    appdata = os.getenv('LOCALAPPDATA')
    # Check both old and new paths just in case
    paths = [
        os.path.join(appdata, "AYECPro", "ayecpro.db"),
        os.path.join(appdata, "AYECPro", "ayecpro.db"),
        "ayecpro.db"
    ]
    
    for db_path in paths:
        if not os.path.exists(db_path):
            continue
            
        print(f"Checking DB: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        try:
            # 1. Normalize accounting table dates
            cursor.execute("SELECT id, date FROM accounting")
            rows = cursor.fetchall()
            updated = 0
            for row_id, date_val in rows:
                new_date = normalize_date(date_val)
                if new_date != date_val:
                    cursor.execute("UPDATE accounting SET date = ? WHERE id = ?", (new_date, row_id))
                    updated += 1
            
            # 2. Add try_equivalent to accounting if missing
            try:
                cursor.execute("ALTER TABLE accounting ADD COLUMN try_equivalent REAL")
                print("Added try_equivalent column to accounting.")
            except:
                pass
                
            # 3. Fill try_equivalent if null
            cursor.execute("UPDATE accounting SET try_equivalent = amount WHERE try_equivalent IS NULL")
            
            conn.commit()
            print(f"Done! Updated {updated} dates in {db_path}")
            
        except Exception as e:
            print(f"Error fixing {db_path}: {e}")
        finally:
            conn.close()

if __name__ == "__main__":
    run_fix()
