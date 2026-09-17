# -*- coding: utf-8 -*-


import sqlite3
import os

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ayecpro.db"))

def reset_and_seed():
    print(f"Veritabanı yolu: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Tabloyu Sil ve Yeniden Oluştur (Temiz Kurulum)
    cur.execute("DROP TABLE IF EXISTS service_definitions")
    print("Eski tablo silindi.")

    cur.execute("""
        CREATE TABLE service_definitions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            category TEXT,
            price REAL,
            duration INTEGER DEFAULT 60,
            description TEXT
        )
    """)
    print("Yeni tablo oluşturuldu.")

    # 2. Örnek Verileri Hazırla
    services = [
        ("ADRESE TESLİM (0-30 KM)", "Lojistik", 1200.00, "0-30 Km'ye kadar servis bedeli"),
        ("ADRESE TESLİM (30-50 KM)", "Lojistik", 1450.00, "30-50 Km'ye kadar servis bedeli"),
        ("ARIZA TESPİT", "Servis", 725.00, "Tamirin yapılmaması durumunda tavsiye edilen bedel"),
        ("BİLGİ KURTARMA", "Veri", 2450.00, "Elektronik Devre Değişimi"),
        ("DONANIM YÜKSELTME", "Servis", 950.00, "Sabit Disk, RAM İşlemci vb. Montajı (Parça hariç)"),
        ("DOT-MATRIX YAZICI ONARIMI", "Onarım", 1160.00, "Nokta Vuruşlu Yazıcı Tamir/Bakım"),
        ("DİSK BİLGİ YENİLEME", "Veri", 1200.00, "Eski işletim sistemi ve verilerin aktarımı"),
        ("E-POSTA SUNUCUSU KURULUMU", "Sunucu", 12095.00, "Sunucu kurulumu ve teslimi"),
        ("EĞİTİM (ALINAN ÜRÜN)", "Eğitim", 2177.00, "1 Saatlik Sistem ve Donanım Eğitimi"),
        ("GÜVENLİK DUVARI (FW)", "Güvenlik", 12095.00, "İstemci tarafı kurulum ve konfigürasyon"),
        ("INKJET YAZICI BAKIM", "Onarım", 845.00, "Inkjet Yazıcı Tamir/Bakım (Parça Hariç)"),
        ("KAMERA MONTAJ", "Montaj", 1250.00, "Adet Fiyatı (Kamera hariç)"),
        ("FORMAT / KURULUM", "Yazılım", 1200.00, "Yeni bilgisayarın çalışır duruma getirilmesi"),
        ("LASER YAZICI ONARIMI", "Onarım", 1016.00, "Laser Yazıcı Tamir/Bakım (Parça Hariç)"),
        ("MODEM KURULUM", "Ağ", 725.00, "ADSL Modem Kurulumu (Kablo Hariç)")
    ]

    # 3. Verileri Ekle
    count = 0
    for name, cat, price, desc in services:
        cur.execute("""
            INSERT INTO service_definitions (service_name, category, price, duration, description)
            VALUES (?, ?, ?, ?, ?)
        """, (name, cat, price, 60, desc))
        count += 1
    
    conn.commit()
    conn.close()
    print(f"İşlem tamamlandı. {count} hizmet eklendi.")

if __name__ == "__main__":
    reset_and_seed()

