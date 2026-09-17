# -*- coding: utf-8 -*-

import sqlite3
import os
import sys

# Terminalin karakter hatası vermemesi için çıktı kodlamasını düzeltiyoruz
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def sunucu_veritabanini_onar():
    db_path = 'ayecpro.db'
    if not os.path.exists(db_path):
        print("Hata: ayecpro.db dosyasi bulunamadi!")
        return

    try:
        # Bağlantıyı başlat
        conn = sqlite3.connect(db_path)
        # Karakter hatalarını görmezden gelerek oku
        conn.text_factory = lambda b: b.decode('utf-8', errors='replace')
        c = conn.cursor()

        print("--- Veritabani Onarimi Baslatiliyor ---")
        
        # 1. Personel durumlarındaki karakter bozukluklarını düzelt (Emoji kullanmadan)
        c.execute("UPDATE personnel SET status='Bosta' WHERE status LIKE 'Bo%'")
        c.execute("UPDATE personnel SET status='Gorevde' WHERE status LIKE 'G%'")
        
        # 2. Loglardaki bozuk yazıları temizle
        c.execute("UPDATE audit_logs SET details = REPLACE(details, 'arYivlendi', 'arsivlendi')")
        
        conn.commit()
        print("[OK] Karakterler ve durumlar basariyla onarildi.")
        
        # 3. Tablo yapısını kontrol et (Doğrulama)
        c.execute("PRAGMA table_info(personnel)")
        cols = [row[1] for row in c.fetchall()]
        print(f"Mevcut Kolonlar: {cols}")
        
        conn.close()
    except Exception as e:
        # Hata mesajındaki bozuk karakterleri de temizleyerek yazdır
        print(f"[HATA] Bir sorun olustu: {str(e).encode('ascii', 'ignore').decode()}")

if __name__ == "__main__":
    sunucu_veritabanini_onar()
