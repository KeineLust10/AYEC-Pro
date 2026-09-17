import sqlite3
import json

def get_schema():
    conn = sqlite3.connect('ayecpro.db')
    cur = conn.cursor()
    
    tables = ['devices', 'customers', 'used_parts', 'parts', 'accounting']
    schema_info = {}
    
    for table in tables:
        try:
            cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
            res = cur.fetchone()
            schema_info[table] = res[0] if res else "NOT FOUND"
        except Exception as e:
            schema_info[table] = f"ERROR: {str(e)}"
            
    conn.close()
    for table, sql in schema_info.items():
        print(f"--- {table} ---")
        print(sql)
        print("\n")

if __name__ == "__main__":
    get_schema()
