import sqlite3
import os
from datetime import datetime

DB_PATHS = {
    'cwd': os.path.join(os.getcwd(), 'ayecpro.db'),
    'appdata': os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')), 'AYEC Pro', 'ayecpro.db')
}

def get_columns(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info('{table}')")
    return [r[1] for r in cur.fetchall()]


def alter_add_column(conn, table, col_def):
    cur = conn.cursor()
    try:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
        conn.commit()
        return True
    except Exception as e:
        return False


def fix_stock_movements(conn):
    cur = conn.cursor()
    cols = set(get_columns(conn, 'stock_movements'))
    actions = []
    # Add 'type' if missing (backend expects 'type')
    if 'type' not in cols:
        added = alter_add_column(conn, 'stock_movements', "type TEXT")
        actions.append(('type', added))
        if added and 'movement_type' in cols:
            try:
                cur.execute("UPDATE stock_movements SET type = movement_type WHERE movement_type IS NOT NULL AND (type IS NULL OR type = '')")
                conn.commit()
            except Exception:
                pass
    # Add 'current_stock' if missing
    if 'current_stock' not in cols:
        added = alter_add_column(conn, 'stock_movements', "current_stock INTEGER")
        actions.append(('current_stock', added))
        if added and 'new_stock' in cols:
            try:
                cur.execute("UPDATE stock_movements SET current_stock = new_stock WHERE new_stock IS NOT NULL AND (current_stock IS NULL OR current_stock = '')")
                conn.commit()
            except Exception:
                pass
    # Add 'date' if missing
    if 'date' not in cols:
        added = alter_add_column(conn, 'stock_movements', "date TEXT")
        actions.append(('date', added))
        if added and 'created_at' in cols:
            try:
                cur.execute("UPDATE stock_movements SET date = created_at WHERE created_at IS NOT NULL AND (date IS NULL OR date = '')")
                conn.commit()
            except Exception:
                pass
    return actions


def fix_users_table(conn):
    cols = set(get_columns(conn, 'users'))
    actions = []
    if 'is_active' not in cols:
        added = alter_add_column(conn, 'users', "is_active INTEGER DEFAULT 1")
        actions.append(('is_active', added))
        try:
            conn.commit()
        except Exception:
            pass
    return actions


def ensure_table_exists(conn, table):
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT 1 FROM {table} LIMIT 1")
        return True
    except Exception:
        return False


def process_db(path_key, path):
    print(f"\nProcessing {path_key}: {path}")
    if not os.path.exists(path):
        print("  - DB not found")
        return
    conn = sqlite3.connect(path)
    try:
        # Ensure stock_movements exists
        if ensure_table_exists(conn, 'stock_movements'):
            actions = fix_stock_movements(conn)
            for col, ok in actions:
                print(f"  - stock_movements: added column '{col}': {ok}")
        else:
            print("  - stock_movements table missing")
        # Ensure users exists
        if ensure_table_exists(conn, 'users'):
            actions = fix_users_table(conn)
            for col, ok in actions:
                print(f"  - users: added column '{col}': {ok}")
        else:
            print("  - users table missing")
    finally:
        conn.close()


if __name__ == '__main__':
    print('DB Schema Fix Script - started at', datetime.now())
    for k,p in DB_PATHS.items():
        process_db(k,p)
    print('Done')
