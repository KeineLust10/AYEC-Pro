# -*- coding: utf-8 -*-
import sqlite3
import sys
import os

# Encoding fix for Windows console
if sys.platform == 'win32':
    import codecs
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        pass

def fix_data():
    db_path = os.path.join(os.getcwd(), 'ayecpro.db')
    print(f"Veritabani baglaniliyor: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. DEVICES TABLE FIX & POPULATE
    try:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='devices'")
        if not cursor.fetchone():
            print("Devices tablosu olusturuluyor...")
            cursor.execute("""
                CREATE TABLE devices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tracking_no TEXT UNIQUE,
                    customer_name TEXT,
                    brand TEXT,
                    model TEXT,
                    serial_no TEXT,
                    device_type TEXT,
                    problem_description TEXT,
                    status TEXT,
                    cost REAL,
                    notes TEXT,
                    personnel_id INTEGER,
                    entry_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completion_date TIMESTAMP
                )
            """)
        
        # Populate if empty
        cursor.execute("SELECT COUNT(*) FROM devices")
        count = cursor.fetchone()[0]
        if count == 0:
            print("Cihaz kayitlari ekleniyor...")
            devices = [
                ("TR-1001", "Zeynep Yildiz", "Dell", "Latitude 5420", "SN001", "Laptop", "Acilmiyor", "Tamirde", 0, "Anakart arizasi suphesi", 1),
                ("TR-1002", "Teknoloji A.S.", "HP", "ProDesk 400", "SN002", "PC", "Yavas", "Hazır", 500, "SSD takildi ve formatlandi", 2),
                ("TR-1003", "Can Ozturk", "Apple", "MacBook Air", "SN003", "Laptop", "Ekran Kirik", "Parça Bekliyor", 0, "Ekran siparis edildi", 1),
                ("TR-1004", "Egitim Kurumlari", "Epson", "Projeksiyon", "SN004", "Diger", "Goruntu yok", "Bekliyor", 0, "Lamba degisecek", 3),
                ("TR-1005", "Elif Arslan", "Lenovo", "ThinkPad", "SN005", "Laptop", "Klavye arizasi", "Teslim Edildi", 450, "Klavye degisti", 1),
                ("TR-1006", "Saglik Merkezi", "Dell", "Server T40", "SN006", "Server", "RAID hatasi", "Tamirde", 0, "Disk rebuild ediliyor", 2),
                ("TR-1007", "Burak Kilic", "Asus", "ROG Strix", "SN007", "Laptop", "Isinma sorunu", "Test Sürecinde", 0, "Termal macun yenilendi", 1),
                ("TR-1008", "Mimarlik Ofisi", "HP", "ZBook", "SN008", "Laptop", "Mavi ekran", "Bekliyor", 0, "RAM testi yapilacak", 2),
                ("TR-1009", "Deniz Aydin", "Samsung", "Tablet S8", "SN009", "Tablet", "Sarj olmuyor", "Hazır", 300, "Soket temizlendi", 1),
                ("TR-1010", "Medya Prod.", "Apple", "iMac 27", "SN010", "PC", "Yavas", "Teslim Edildi", 0, "Bakim yapildi", 2),
            ]
            
            for d in devices:
                try:
                    cursor.execute("""
                        INSERT INTO devices (tracking_no, customer_name, brand, model, serial_no, device_type, problem_description, status, cost, notes, personnel_id, entry_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '-3 days'))
                    """, d)
                except Exception as e:
                    print(f"Insert hatasi {d[0]}: {e}")
            print(f"{len(devices)} cihaz eklendi.")
        else:
            print(f"Devices tablosunda {count} kayit var.")

    except Exception as e:
        print(f"Devices islem hatasi: {e}")

    # 2. CONTRACTS SCHEMA FIX & POPULATE
    try:
        cursor.execute("PRAGMA table_info(contracts)")
        cols = [c[1] for c in cursor.fetchall()]
        
        if 'monthly_fee' not in cols:
            cursor.execute("ALTER TABLE contracts ADD COLUMN monthly_fee REAL DEFAULT 0")
            print("Contracts: monthly_fee kolonu eklendi.")
            
        if 'services_included' not in cols:
            cursor.execute("ALTER TABLE contracts ADD COLUMN services_included TEXT")
            print("Contracts: services_included kolonu eklendi.")
            
        # Populate contracts
        cursor.execute("SELECT COUNT(*) FROM contracts")
        if cursor.fetchone()[0] == 0:
            print("Sozlesme kayitlari ekleniyor...")
            cursor.execute("SELECT id FROM customers LIMIT 5")
            c_ids = [r[0] for r in cursor.fetchall()]
            
            if c_ids:
                contracts_data = [
                    (c_ids[0], '2024-01-01', '2025-01-01', 5000, 'Tam Bakim', 'Aktif'),
                    (c_ids[1] if len(c_ids)>1 else c_ids[0], '2024-03-01', '2025-03-01', 3000, 'Uzak Destek', 'Aktif'),
                    (c_ids[2] if len(c_ids)>2 else c_ids[0], '2024-06-01', '2025-06-01', 7500, 'VIP Destek', 'Aktif'),
                ]
                
                for cd in contracts_data:
                    try:
                        cursor.execute("INSERT INTO contracts (customer_id, start_date, end_date, monthly_fee, services_included, status) VALUES (?, ?, ?, ?, ?, ?)", cd)
                    except Exception as e:
                        print(f"Contract insert error: {e}")
                print("Sozlesmeler eklendi.")
                
    except Exception as e:
        print(f"Contracts islem hatasi: {e}")

    # 3. KB ARTICLES POPULATE
    try:
        cursor.execute("CREATE TABLE IF NOT EXISTS kb_articles (id INTEGER PRIMARY KEY, title TEXT, content TEXT, tags TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("SELECT COUNT(*) FROM kb_articles")
        if cursor.fetchone()[0] == 0:
            print("KB makaleleri ekleniyor...")
            kbs = [
                ("Windows 11 Kurulumu", "Windows 11 temiz kurulum adimlari...", "windows,format",),
                ("Yazici Baglantisi", "Ag yazicisi nasil tanitilir...", "network,printer",),
                ("Outlook Ayarlari", "IMAP ve POP3 ayarlari...", "email,outlook",),
                ("Yedekleme Proseduru", "Gunluk ve haftalik yedekleme...", "backup,security",),
                ("Virus Temizleme", "Malwarebytes kullanimi...", "security,virus",)
            ]
            for cb in kbs:
                cursor.execute("INSERT INTO kb_articles (title, content, tags) VALUES (?, ?, ?)", cb)
            print("KB makaleleri eklendi.")
    except Exception as e:
        print(f"KB islem hatasi: {e}")

    conn.commit()
    conn.close()
    print("Tum veri islemleri tamamlandi.")

if __name__ == "__main__":
    fix_data()
