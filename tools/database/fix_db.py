# -*- coding: utf-8 -*-

import sqlite3
import sys

# Terminal çıktı kodlamasını zorla UTF-8 yapmayı dene
try:
    conn = sqlite3.connect('ayecpro.db')
    cur = conn.cursor()

    columns = [
        ('lat', 'REAL'),
        ('lng', 'REAL'),
        ('status', "TEXT DEFAULT 'Bosta'"), # 'Boşta' yerine 'Bosta'
        ('last_seen', 'TEXT')
    ]

    for col_name, col_type in columns:
        try:
            cur.execute(f'ALTER TABLE personnel ADD COLUMN {col_name} {col_type}')
            print(f'Added column: {col_name}') # Türkçe karakter kullanma
        except sqlite3.OperationalError:
            print(f'Already exists: {col_name}')

    # 'Görevde' yerine 'Gorevde' kullanarak dene (Test amaçlı)
    # Ayrıca NULL olmayanları da güncelleyelim ki veri görünsün
    cur.execute("UPDATE personnel SET lat=?, lng=?, status=? WHERE lat IS NULL OR lat = ''", 
                (39.6484, 27.8826, "Gorevde"))
    
    print(f'Updated rows: {cur.rowcount}')
    
    conn.commit()
    conn.close()
    print("Database repair completed successfully.") # Türkçe karakter yok

except Exception as e:
    print(f"Error: {str(e)}")
