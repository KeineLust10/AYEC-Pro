# -*- coding: utf-8 -*-

import sqlite3
import os

def sunucu_veritabanini_onar():
    db_path = 'ayecpro.db'
    if not os.path.exists(db_path):
        print("Hata: ayecpro.db dosyası bulunamadı!")
        return

    try:
        conn = sqlite3.connect(db_path)
        # Karakter hatalarını görmezden gelerek bağlantı kur
        conn.text_factory = lambda b: b.decode('utf-8', errors='replace')
        c = conn.cursor()

        print("--- Karakter Onarımı Başlatılıyor ---")
        # Personel tablosundaki bozuk karakterleri otomatik düzelt
        c.execute("UPDATE personnel SET status='Bosta' WHERE status LIKE 'Bo%'")
        c.execute("UPDATE personnel SET status='Gorevde' WHERE status LIKE 'G%'")
        
        # Loglardaki bozuk yazıları temizle
        # Check if audit_logs table exists first
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
        if c.fetchone():
            c.execute("UPDATE audit_logs SET details = REPLACE(details, 'arYivlendi', 'arsivlendi')")
        
        conn.commit()
        print("✅ Karakterler ve durumlar başarıyla onarıldı.")
        
        # Tablo şemasını kontrol et
        c.execute("PRAGMA table_info(personnel)")
        cols = [row[1] for row in c.fetchall()]
        print(f"Mevcut Kolonlar: {cols}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Bir hata oluştu: {e}")

if __name__ == "__main__":
    sunucu_veritabanini_onar()
