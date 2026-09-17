# -*- coding: utf-8 -*-

import sqlite3
import os

db_path = "ayecpro.db"
if not os.path.exists(db_path):
    print("Database not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Check and add columns
cursor.execute("PRAGMA table_info(currency_transactions)")
cols = [c[1] for c in cursor.fetchall()]

if 'current_balance' not in cols:
    print("Adding current_balance column...")
    cursor.execute('ALTER TABLE currency_transactions ADD COLUMN current_balance REAL DEFAULT 0.0')

if 'is_invoiced' not in cols:
    print("Adding is_invoiced column...")
    cursor.execute('ALTER TABLE currency_transactions ADD COLUMN is_invoiced INTEGER DEFAULT 0')

# 2. Recalculate balances ordered by date
print("Recalculating balances...")
cursor.execute('SELECT id, transaction_type, try_equivalent FROM currency_transactions ORDER BY created_at ASC')
rows = cursor.fetchall()
bakiye = 0.0

for row in rows:
    t_id, t_type, amount = row
    if t_type == 'DEBIT': # Satış / Gelir
        bakiye += amount
    elif t_type == 'CREDIT': # Tahsilat / Gider
        bakiye -= amount
    
    cursor.execute('UPDATE currency_transactions SET current_balance = ? WHERE id = ?', (round(bakiye, 2), t_id))

conn.commit()
conn.close()
print('Sistem Türkiye standartlarına başarıyla güncellendi!')
