"""Merge AppData/ayecpro.db -> AppData/ayecpro.db (consolidation helper).
Backs up both DBs first into Setup_Files/backups/<timestamp>.
Copies parts, stock_movements, users (dedupe) and remaps part_id for movements.
"""
import os, shutil, sqlite3
from datetime import datetime

APPDATA = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')), 'AYEC Pro')
SRC = os.path.join(APPDATA, 'ayecpro.db')
TGT = os.path.join(APPDATA, 'ayecpro.db')
ROOT = os.path.abspath(os.getcwd())
BACKUP_DIR = os.path.join(ROOT, 'Setup_Files', 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)
TS = datetime.now().strftime('%Y%m%d_%H%M%S')
BACK = os.path.join(BACKUP_DIR, f'appdata_merge_{TS}')
os.makedirs(BACK, exist_ok=True)

if not os.path.exists(SRC):
    print('Source ayecpro.db not found at', SRC)
    raise SystemExit(1)
if not os.path.exists(TGT):
    print('Target ayecpro.db not found at', TGT)
    print('Creating empty target...')
    conn = sqlite3.connect(TGT); conn.close()

# backup both
shutil.copy2(SRC, os.path.join(BACK, 'ayecpro.db'))
shutil.copy2(TGT, os.path.join(BACK, 'ayecpro_target.db'))
print('Backed up to', BACK)

# helpers
def table_exists(conn, t):
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT 1 FROM {t} LIMIT 1")
        return True
    except Exception:
        return False

# open DBs
sconn = sqlite3.connect(SRC)
tconn = sqlite3.connect(TGT)
try:
    tcur = tconn.cursor()
    scur = sconn.cursor()
    summary = {'parts_inserted':0,'movements_inserted':0,'users_inserted':0}

    # build existing sets
    existing_codes = set()
    existing_names = set()
    if table_exists(tconn,'parts'):
        tcur.execute('SELECT code,name FROM parts')
        for r in tcur.fetchall():
            code,name = r
            if code: existing_codes.add(code)
            if name: existing_names.add(name)

    # migrate parts — insert only columns that exist in target
    if table_exists(sconn,'parts') and table_exists(tconn,'parts'):
        # target columns
        tcur.execute("PRAGMA table_info('parts')")
        t_cols = [r[1] for r in tcur.fetchall()]

        scur.execute('SELECT * FROM parts')
        s_cols = [d[0] for d in scur.description]
        rows = scur.fetchall()
        id_map = {}
        for row in rows:
            rowd = dict(zip(s_cols,row))
            code = rowd.get('code')
            name = rowd.get('name')
            # dedupe
            found = None
            if code and code in existing_codes:
                tcur.execute('SELECT id FROM parts WHERE code=? LIMIT 1',(code,))
                r = tcur.fetchone(); found = r[0] if r else None
            elif name and name in existing_names:
                tcur.execute('SELECT id FROM parts WHERE name=? LIMIT 1',(name,))
                r = tcur.fetchone(); found = r[0] if r else None
            if found:
                id_map[rowd.get('id')] = found
                continue
            # compute insert columns as intersection (exclude id)
            insert_cols = [c for c in s_cols if c != 'id' and c in t_cols]
            if not insert_cols:
                continue
            placeholders = ','.join(['?']*len(insert_cols))
            values = [rowd.get(c) for c in insert_cols]
            try:
                tcur.execute(f"INSERT INTO parts ({','.join(insert_cols)}) VALUES ({placeholders})", values)
                tconn.commit()
                new_id = tcur.lastrowid
                id_map[rowd.get('id')] = new_id
                summary['parts_inserted'] += 1
                if code: existing_codes.add(code)
                if name: existing_names.add(name)
            except Exception as e:
                print('Failed to insert part', rowd.get('name'), e)
    else:
        print('Parts table missing in source or target; skipping parts migration')
        id_map = {}

    # migrate stock_movements
    if table_exists(sconn,'stock_movements') and table_exists(tconn,'stock_movements'):
        # compute target cols
        tcur.execute("PRAGMA table_info('stock_movements')")
        tsm_cols = [r[1] for r in tcur.fetchall()]

        scur.execute('SELECT * FROM stock_movements')
        s_cols = [d[0] for d in scur.description]
        rows = scur.fetchall()
        for row in rows:
            rowd = dict(zip(s_cols,row))
            old_pid = rowd.get('part_id')
            new_pid = id_map.get(old_pid)
            if new_pid is None:
                continue
            rowd['part_id'] = new_pid
            if 'id' in rowd: rowd.pop('id')
            insert_cols = [c for c in rowd.keys() if c in tsm_cols]
            if not insert_cols:
                continue
            placeholders = ','.join(['?']*len(insert_cols))
            values = [rowd[c] for c in insert_cols]
            try:
                tcur.execute(f"INSERT INTO stock_movements ({','.join(insert_cols)}) VALUES ({placeholders})", values)
                tconn.commit()
                summary['movements_inserted'] += 1
            except Exception:
                pass
    else:
        print('stock_movements table missing in source or target; skipping movements')

    # migrate users
    if table_exists(sconn,'users') and table_exists(tconn,'users'):
        # target user cols
        tcur.execute("PRAGMA table_info('users')")
        tu_cols = [r[1] for r in tcur.fetchall()]

        scur.execute('SELECT * FROM users')
        s_cols = [d[0] for d in scur.description]
        rows = scur.fetchall()
        for row in rows:
            rowd = dict(zip(s_cols,row))
            uname = rowd.get('username')
            if uname:
                tcur.execute('SELECT id FROM users WHERE username=? LIMIT 1',(uname,))
                if tcur.fetchone():
                    continue
            insert_cols = [c for c in s_cols if c!='id' and c in tu_cols]
            if not insert_cols:
                continue
            placeholders = ','.join(['?']*len(insert_cols))
            values = [rowd.get(c) for c in insert_cols]
            try:
                tcur.execute(f"INSERT INTO users ({','.join(insert_cols)}) VALUES ({placeholders})", values)
                tconn.commit()
                summary['users_inserted'] += 1
            except Exception:
                pass
    else:
        print('users table missing in source or target; skipping users')

    print('Merge summary:', summary)
finally:
    sconn.close(); tconn.close()

print('Merge complete. Backups at', BACK)
print('Please restart the application now and check the Stocks UI.')
