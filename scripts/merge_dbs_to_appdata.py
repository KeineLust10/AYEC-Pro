"""Merge other local DBs into AppData ayecpro.db with backups.

Behavior:
"""
# For each source DB (cwd ayecpro.db and any others in workspace root matching *.db):

import os
import shutil
import sqlite3
from datetime import datetime

ROOT = os.path.abspath(os.getcwd())
APPDATA = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')), 'AYEC Pro')
TARGET_NAME = 'ayecpro.db'
TARGET_PATH = os.path.join(APPDATA, TARGET_NAME)
BACKUP_DIR = os.path.join(ROOT, 'Setup_Files', 'backups')

os.makedirs(BACKUP_DIR, exist_ok=True)

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
THIS_BACKUP = os.path.join(BACKUP_DIR, TIMESTAMP)
os.makedirs(THIS_BACKUP, exist_ok=True)

# Candidate DB files: any *.db in root and the AppData target
candidates = []
for name in os.listdir(ROOT):
    if name.lower().endswith('.db'):
        candidates.append(os.path.join(ROOT, name))
# include target if exists
if os.path.exists(TARGET_PATH):
    if TARGET_PATH not in candidates:
        candidates.append(TARGET_PATH)

# Ensure target exists (create empty DB if needed)
if not os.path.exists(TARGET_PATH):
    print(f"Creating target DB at {TARGET_PATH}")
    os.makedirs(APPDATA, exist_ok=True)
    conn = sqlite3.connect(TARGET_PATH)
    conn.close()

# Backup all candidate DBs (copy)
backed_up = []
for path in candidates:
    try:
        dest = os.path.join(THIS_BACKUP, os.path.basename(path))
        shutil.copy2(path, dest)
        backed_up.append(dest)
    except Exception as e:
        print(f"Warning: failed to backup {path}: {e}")

print('Backed up files:')
for b in backed_up:
    print(' -', b)

# Helper DB functions

def table_exists(conn, table):
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except Exception:
        return False


def get_part_by_code(conn, code):
    cur = conn.cursor()
    cur.execute("SELECT id FROM parts WHERE code = ?", (code,))
    r = cur.fetchone()
    return r[0] if r else None


def get_user_by_username(conn, username):
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    r = cur.fetchone()
    return r[0] if r else None

# Open target connection
tconn = sqlite3.connect(TARGET_PATH)
ts = tconn

summary = {
    'parts_inserted': 0,
    'movements_inserted': 0,
    'users_inserted': 0,
    'sources_processed': 0,
    'skipped_targets': 0,
}

# Build a set of existing part codes/names in target for quick checks
tcur = tconn.cursor()
existing_codes = set()
existing_names = set()
if table_exists(tconn, 'parts'):
    tcur.execute('SELECT id, code, name FROM parts')
    for r in tcur.fetchall():
        _, code, name = r
        if code:
            existing_codes.add(code)
        if name:
            existing_names.add(name)

# Process each source DB except target itself
for path in candidates:
    if os.path.abspath(path) == os.path.abspath(TARGET_PATH):
        continue
    summary['sources_processed'] += 1
    print(f"\nProcessing source DB: {path}")
    sconn = sqlite3.connect(path)
    src = sconn
    try:
        # Only process if parts table exists
        if not table_exists(sconn, 'parts'):
            print(' - no parts table, skipping')
            continue
        # Map old part id -> new part id
        id_map = {}
        scur = sconn.cursor()
        scur.execute('SELECT * FROM parts')
        cols = [d[0] for d in scur.description]
        rows = scur.fetchall()
        for row in rows:
            rowd = dict(zip(cols, row))
            code = rowd.get('code')
            name = rowd.get('name')
            # dedupe by code, then name
            target_id = None
            if code and code in existing_codes:
                target_id = get_part_by_code(tconn, code)
            elif name and name in existing_names:
                # try to find by name
                tcur.execute('SELECT id FROM parts WHERE name = ? LIMIT 1', (name,))
                r = tcur.fetchone()
                if r:
                    target_id = r[0]
            if target_id:
                id_map[rowd.get('id')] = target_id
                continue
            # Insert into target (preserve fields except id)
            insert_cols = [c for c in cols if c != 'id']
            placeholders = ','.join(['?'] * len(insert_cols))
            values = [rowd.get(c) for c in insert_cols]
            try:
                tcur.execute(f"INSERT INTO parts ({','.join(insert_cols)}) VALUES ({placeholders})", values)
                tconn.commit()
                new_id = tcur.lastrowid
                id_map[rowd.get('id')] = new_id
                summary['parts_inserted'] += 1
                if rowd.get('code'):
                    existing_codes.add(rowd.get('code'))
                if rowd.get('name'):
                    existing_names.add(rowd.get('name'))
            except Exception as e:
                print(' - failed to insert part', rowd.get('name'), e)
        # Now copy stock_movements if table exists in source and target
        if table_exists(sconn, 'stock_movements') and table_exists(tconn, 'stock_movements'):
            scur.execute('SELECT * FROM stock_movements')
            cols = [d[0] for d in scur.description]
            rows = scur.fetchall()
            for row in rows:
                rowd = dict(zip(cols, row))
                old_pid = rowd.get('part_id')
                new_pid = id_map.get(old_pid)
                if new_pid is None:
                    # skip movements for parts that were not migrated
                    continue
                rowd['part_id'] = new_pid
                # remove id to let target assign
                if 'id' in rowd:
                    rowd.pop('id')
                insert_cols = list(rowd.keys())
                placeholders = ','.join(['?'] * len(insert_cols))
                values = [rowd[c] for c in insert_cols]
                try:
                    tcur.execute(f"INSERT INTO stock_movements ({','.join(insert_cols)}) VALUES ({placeholders})", values)
                    tconn.commit()
                    summary['movements_inserted'] += 1
                except Exception as e:
                    print(' - failed to insert movement', e)
        # Copy users (dedupe by username)
        if table_exists(sconn, 'users') and table_exists(tconn, 'users'):
            scur.execute('SELECT * FROM users')
            cols = [d[0] for d in scur.description]
            rows = scur.fetchall()
            for row in rows:
                rowd = dict(zip(cols, row))
                uname = rowd.get('username')
                if uname and get_user_by_username(tconn, uname):
                    continue
                # insert without id
                insert_cols = [c for c in cols if c != 'id']
                placeholders = ','.join(['?'] * len(insert_cols))
                values = [rowd.get(c) for c in insert_cols]
                try:
                    tcur.execute(f"INSERT INTO users ({','.join(insert_cols)}) VALUES ({placeholders})", values)
                    tconn.commit()
                    summary['users_inserted'] += 1
                except Exception as e:
                    print(' - failed to insert user', uname, e)
    finally:
        sconn.close()

print('\nMerge Summary:')
for k,v in summary.items():
    print(f' - {k}: {v}')
print('\nBackups stored in:', THIS_BACKUP)
print('\nIMPORTANT: No files were deleted. To remove redundant DBs, run the delete step after you verify the merged database is correct.')
print('To delete redundant DBs, run: scripts/delete_redundant_dbs.py')
