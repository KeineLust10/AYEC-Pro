import sqlite3

try:
    conn = sqlite3.connect('ayecpro.db')
    cur = conn.cursor()
    cur.execute('SELECT id, name, role, lat, lng FROM personnel')
    rows = cur.fetchall()
    print(f'Total: {len(rows)}')
    for r in rows:
        # Safe print
        safe_name = str(r[1]).encode('ascii', 'ignore').decode()
        safe_role = str(r[2]).encode('ascii', 'ignore').decode()
        print(f'User: {safe_name} | Role: {safe_role} | Lat: {r[3]} | Lng: {r[4]}')
    conn.close()
except Exception as e:
    print(f"Error: {e}")
