# -*- coding: utf-8 -*-


import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "ayecpro.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def clear_tables(conn):
    """Optional: Clear existing data to avoid duplicates or messy state?"""
    # For now, let's just append or maybe clear if user asked? 
    # User said "Test verisi oluştururmusun", usually implies a fresh start or heavy seed.
    # I'll suppress clearing to respect existing data, but I'll add unique checks or just let them pile up for stress testing.
    pass

def seed_personnel(conn):
    cursor = conn.cursor()
    roles = ["Saha Teknisyeni", "Ofis Müdürü", "Satış Temsilcisi", "Muhasebe", "Admin"]
    names = [
        ("Ahmet Yılmaz", "Saha Teknisyeni"),
        ("Ayşe Demir", "Ofis Müdürü"),
        ("Mehmet Kaya", "Satış Temsilcisi"),
        ("Fatma Çelik", "Muhasebe"),
        ("Ali Vural", "Saha Teknisyeni Admin")
    ]
    
    print("Adding Personnel...")
    for name, role in names:
        phone = f"05{random.randint(100,999)}{random.randint(1000000,9999999)}"
        salary = random.randint(25, 45) * 1000
        cursor.execute("""
            INSERT INTO personnel (name, role, phone, salary, commission, created_at, active)
            VALUES (?, ?, ?, ?, 0, ?, 1)
        """, (name, role, phone, salary, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()

def seed_stock(conn):
    cursor = conn.cursor()
    print("Adding Security Stock...")
    
    security_products = [
        ("Hikvision 2MP Bullet Kamera", "Kamera", 45.0),
        ("Hikvision 5MP Dome Kamera", "Kamera", 65.0),
        ("Dahua 4 Kanal NVR", "Kayıt Cihazı", 120.0),
        ("Dahua 8 Kanal DVR", "Kayıt Cihazı", 180.0),
        ("Seagate Skyhawk 1TB HDD", "Depolama", 55.0),
        ("WD Purple 2TB HDD", "Depolama", 75.0),
        ("Hikvision 4MP IP Kamera", "Kamera", 85.0),
        ("Paradox Hırsız Alarm Paneli", "Alarm", 150.0),
        ("Paradox Hareket Sensörü (PIR)", "Alarm", 15.0),
        ("Manyetik Kontak", "Alarm", 3.0),
        ("12V 10A Adaptör", "Aksesuar", 20.0),
        ("BNC Konnektör (100'lü)", "Aksesuar", 25.0),
        ("CCTV Kablosu 2+1 (100m)", "Kablo", 35.0),
        ("Cat6 Kablo (305m)", "Kablo", 110.0),
        ("Yangın Dedektörü", "Yangın", 25.0),
        ("Duman Sensörü", "Yangın", 22.0),
        ("Akıllı Kilit Sistemi", "Kilit", 200.0),
        ("RFID Kart Okuyucu", "Geçiş Kontrol", 45.0),
        ("Biometrik Parmak İzi Okuyucu", "Geçiş Kontrol", 120.0),
        ("UPS Kesintisiz Güç Kaynağı 1kVA", "Enerji", 180.0)
    ]
    
    for name, cat, price_usd in security_products:
        price_try = price_usd * 36.5 # Mock rate
        stock = random.randint(5, 100)
        cursor.execute("""
            INSERT INTO parts (name, category, stock, price, purchase_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, cat, stock, price_try, price_try * 0.7, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()

def seed_customers(conn):
    cursor = conn.cursor()
    print("Adding 20 Customers...")
    first_names = ["Mustafa", "Emre", "Selin", "Kemal", "Zeynep", "Burak", "Esra", "Murat", "Hakan", "Elif"]
    last_names = ["Yıldız", "Öztürk", "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", "Kara"]
    
    customers = []
    for _ in range(20):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        phone = f"05{random.randint(300,599)} {random.randint(100,999)} {random.randint(10,99)} {random.randint(10,99)}"
        customers.append(name)
        cursor.execute("""
            INSERT INTO customers (name, phone, type, created_at)
            VALUES (?, ?, 'Bireysel', ?)
        """, (name, phone, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    return customers

def seed_finance(conn, customers):
    cursor = conn.cursor()
    print("Adding Finance (Loans & Checks)...")
    
    today = datetime.now()
    tomorrow = today + timedelta(days=1)
    
    # --- LOANS ---
    # 1. Loan due today
    cursor.execute("INSERT INTO loans (bank_name, amount, description, status) VALUES (?, ?, ?, 'Aktif')", 
                   ("Garanti BBVA", 100000, "Demo Kredi 1"))
    lid1 = cursor.lastrowid
    cursor.execute("""
        INSERT INTO loan_installments (loan_id, installment_no, due_date, total_amount, principal_part, interest_part, status)
        VALUES (?, 1, ?, 10000, 8000, 2000, 'Bekliyor')
    """, (lid1, today.strftime("%Y-%m-%d")))
    
    # 2. Loan due tomorrow
    cursor.execute("INSERT INTO loans (bank_name, amount, description, status) VALUES (?, ?, ?, 'Aktif')", 
                   ("Akbank", 50000, "Demo Kredi 2"))
    lid2 = cursor.lastrowid
    cursor.execute("""
        INSERT INTO loan_installments (loan_id, installment_no, due_date, total_amount, principal_part, interest_part, status)
        VALUES (?, 1, ?, 5000, 4000, 1000, 'Bekliyor')
    """, (lid2, tomorrow.strftime("%Y-%m-%d")))

    # 3. Random active loan
    cursor.execute("INSERT INTO loans (bank_name, amount, description, status) VALUES (?, ?, ?, 'Aktif')", 
                   ("Yapı Kredi", 200000, "Demo Kredi 3"))
    
    # --- CHECKS ---
    # 1. Check due tomorrow
    cursor.execute("""
        INSERT INTO checks_notes (type, direction, amount, due_date, issuer, status)
        VALUES ('Çek', 'Giriş', 15000, ?, 'Test Müşteri Ltd', 'Portföyde')
    """, (tomorrow.strftime("%Y-%m-%d"),))
    
    # 4 random checks
    for _ in range(4):
        days = random.randint(5, 60)
        d_date = (today + timedelta(days=days)).strftime("%Y-%m-%d")
        amt = random.randint(10, 100) * 1000
        cursor.execute("""
            INSERT INTO checks_notes (type, direction, amount, due_date, issuer, status)
            VALUES ('Çek', 'Giriş', ?, ?, ?, 'Portföyde')
        """, (amt, d_date, f"{random.choice(customers)}"))
        
    conn.commit()

def seed_devices(conn, customers):
    cursor = conn.cursor()
    print("Adding Service Devices...")
    brands = ["Samsung", "iPhone", "Huawei", "Xiaomi", "Dell", "HP", "Asus"]
    problems = ["Ekran Kırık", "Şarj Almıyor", "Kapanıyor", "Sıvı Teması", "Yavaş Çalışıyor"]
    
    for i in range(10):
        cust = random.choice(customers)
        brand = random.choice(brands)
        status = random.choice(["Beklemede", "İşlemde", "Tamamlandı", "Teslim Edildi"])
        
        cursor.execute("""
            INSERT INTO devices (tracking_no, customer_name, device_brand, fault_description, status, entry_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (f"SRV-{random.randint(10000,99999)}", cust, brand, random.choice(problems), status, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()

if __name__ == "__main__":
    try:
        conn = get_conn()
        seed_personnel(conn)
        seed_stock(conn)
        custs = seed_customers(conn) # returns list of names
        seed_finance(conn, custs)
        seed_devices(conn, custs)
        print("Test Data Generation Complete!")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")
