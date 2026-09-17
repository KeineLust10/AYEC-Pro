# -*- coding: utf-8 -*-

import os
import sqlite3
import sys
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
try:
    from src.utils.path_helper import PathHelper
    db_path = PathHelper.get_db_path("ayecpro.db")
except ImportError:
    db_path = os.path.join(os.getenv("LOCALAPPDATA"), "AYEC Pro", "ayecpro.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name, stock, purchase_price FROM parts")
parts = cursor.fetchall()

added_count = 0
for name, stock, purchase_price in parts:
    try:
        s = float(stock or 0)
        p = float(purchase_price or 0)
        total_cost = s * p
        if total_cost > 0:
            desc = f"Otomatik Stok Alımı: {s} x {name}"
            cursor.execute("SELECT id FROM accounting WHERE description=?", (desc,))
            if not cursor.fetchone():
                today = datetime.now()
                cursor.execute("""
                    INSERT INTO accounting (type, category, amount, description, payment_method, date, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, ("Gider", "Stok Alımı", total_cost, desc, "Nakit", today.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d %H:%M:%S")))
                added_count += 1
    except Exception as e:
        print(f"Error for {name}: {e}")

conn.commit()
conn.close()
print(f"Başarıyla {added_count} adet eksik stok gider kaydı Finans modülüne işlendi.")
