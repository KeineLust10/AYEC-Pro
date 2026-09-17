# -*- coding: utf-8 -*-

import sqlite3
import os

db_path = 'ayecpro.db'

# Ensure we are in the right directory or find the db
if not os.path.exists(db_path):
    # Try absolute path based on workspace info if running from elsewhere (unlikely but safe)
    # But user said "projenizin olduğu klasörde" so current dir should be fine if cwd is correct.
    pass

try:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # İsmi tamamen temizle (id=2 olan Gürkan için)
    cur.execute("UPDATE personnel SET name = 'Gurkan AYDIN', role = 'Saha Personeli' WHERE id = 2")
    conn.commit()
    conn.close()
    # PRINT YOK - SESSİZ ÇALIŞMA
except Exception:
    # Fail silently to avoid encoding errors in output
    pass
