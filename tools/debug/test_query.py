# -*- coding: utf-8 -*-

import sqlite3
try:
    conn = sqlite3.connect('ayec.db', timeout=10)
    cur = conn.cursor()
    cur.execute("SELECT id, type, category, amount, description, payment_method, date FROM accounting WHERE type='Gider' ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    print("Son 5 Gider İşlemi:")
    for r in rows:
        print(r)
except Exception as e:
    print("Err:", e)
