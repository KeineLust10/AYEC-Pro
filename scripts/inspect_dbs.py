import os
import sqlite3
import json

results = {}

# Paths
cwd_db = os.path.join(os.getcwd(), 'ayecpro.db')
appdata_db = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')), 'AYEC Pro', 'ayecpro.db')
paths = {'cwd': cwd_db, 'appdata': appdata_db}

for key, path in paths.items():
    info = {'path': path, 'exists': os.path.exists(path)}
    if not os.path.exists(path):
        results[key] = info
        continue
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # parts count
        try:
            cur.execute('SELECT COUNT(*) as c FROM parts')
            info['parts_count'] = cur.fetchone()['c']
        except Exception as e:
            info['parts_count_error'] = str(e)
        # parts schema and all parts (small DBs expected)
        try:
            cur.execute("PRAGMA table_info('parts')")
            info['parts_schema'] = [list(r) for r in cur.fetchall()]
        except Exception as e:
            info['parts_schema_error'] = str(e)
        try:
            cur.execute('SELECT * FROM parts ORDER BY id DESC')
            rows = cur.fetchall()
            # convert sqlite3.Row to dicts safely
            info['parts_all'] = [dict(r) for r in rows]
        except Exception as e:
            info['parts_all_error'] = str(e)
        # stock_movements count
        try:
            cur.execute('SELECT COUNT(*) as c FROM stock_movements')
            info['movements_count'] = cur.fetchone()['c']
        except Exception as e:
            info['movements_count_error'] = str(e)
        # last 5 movements (try multiple column variants)
        try:
            # We'll first dump table schema for diagnostics
            cur.execute("PRAGMA table_info('stock_movements')")
            cols = cur.fetchall()
            info['stock_movements_schema'] = [list(r) for r in cols]
        except Exception as e:
            info['stock_movements_schema_error'] = str(e)
        try:
            # Try selecting common variants safely by checking available columns
            available = {c[1] for c in info.get('stock_movements_schema', [])}
            # Prefer id, part_id, movement_type/type, amount/change_amount, new_stock/current_stock, description, created_at/date
            sel_cols = []
            for cand in ['id','part_id','movement_type','type','amount','change_amount','new_stock','current_stock','description','created_at','date']:
                if cand in available:
                    sel_cols.append(cand)
            if not sel_cols:
                info['last_movements_error'] = 'No recognizable columns in stock_movements'
            else:
                q = 'SELECT ' + ', '.join(sel_cols) + ' FROM stock_movements ORDER BY id DESC LIMIT 5'
                cur.execute(q)
                info['last_movements'] = [dict(r) for r in cur.fetchall()]
        except Exception as e:
            info['last_movements_error'] = str(e)
        conn.close()
    except Exception as e:
        info['error'] = str(e)
    results[key] = info

print(json.dumps(results, indent=2, ensure_ascii=False))
