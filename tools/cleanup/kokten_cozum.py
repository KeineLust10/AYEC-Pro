# -*- coding: utf-8 -*-

import sqlite3
import sys

def fix_text(text):
    """Bozuk karakterleri temizler ve ASCII dostu hale getirir."""
    if text is None:
        return ""
    # Türkçe karakterleri standart karakterlere dönüştürür
    char_map = {
        'ğ': 'g', 'Ğ': 'G', 'ç': 'c', 'Ç': 'C', 'ş': 's', 'Ş': 'S',
        'ü': 'u', 'Ü': 'U', 'ö': 'o', 'Ö': 'O', 'ı': 'i', 'İ': 'I'
    }
    for tr, eng in char_map.items():
        text = text.replace(tr, eng)
    # Geriye kalan tanımlanamayan bozuk karakterleri siler
    return text.encode('ascii', 'ignore').decode('ascii')

try:
    conn = sqlite3.connect('ayecpro.db')
    cur = conn.cursor()

    # 1. Mevcut tüm verileri çek
    cur.execute("SELECT id, name, role, status FROM personnel")
    rows = cur.fetchall()

    print("--- Veritabanı Temizliği Başlatıldı ---")

    for row in rows:
        user_id, name, role, status = row
        
        # Karakterleri temizle
        new_name = fix_text(name)
        new_role = fix_text(role)
        new_status = fix_text(status) if status else "Bosta"

        # 2. Veritabanını temizlenmiş haliyle güncelle
        cur.execute("""
            UPDATE personnel 
            SET name = ?, role = ?, status = ? 
            WHERE id = ?
        """, (new_name, new_role, new_status, user_id))
        
        print(f"ID {user_id}: '{fix_text(name)}' -> '{new_name}' olarak guncellendi.")

    conn.commit()
    
    # 3. Şema Kontrolü (Eksik sütun varsa ekle)
    expected_cols = [('lat', 'REAL'), ('lng', 'REAL'), ('last_seen', 'TEXT')]
    for col_name, col_type in expected_cols:
        try:
            cur.execute(f"ALTER TABLE personnel ADD COLUMN {col_name} {col_type}")
            print(f"Sutun eklendi: {col_name}")
        except sqlite3.OperationalError:
            pass

    conn.close()
    print("--- Islem Basariyla Tamamlandi ---")
    print("Agent artik ciktiyi okurken cokmeyecek.")

except Exception as e:
    # Hata mesajını bile temizleyerek yazdır ki Agent burada da çökmesin
    error_msg = fix_text(str(e))
    print(f"Hata olustu: {error_msg}")
    sys.exit(1)
