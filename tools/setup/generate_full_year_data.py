# -*- coding: utf-8 -*-

import sqlite3
import random
import datetime
import os
import sys

# Proje dizinini sys.path'e ekle
sys.path.append(os.getcwd())

from src.utils.path_helper import PathHelper

def add_col(cursor, table, col, ddl):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ddl}")
    except:
        pass

def generate_data():
    db_path = PathHelper.get_db_path()
    print(f"Generating stress test data in: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Ensure columns exist
    add_col(cursor, "accounting", "is_deleted", "INTEGER DEFAULT 0")
    add_col(cursor, "accounting", "fiscal_year_id", "INTEGER")
    add_col(cursor, "devices", "is_archived", "INTEGER DEFAULT 0")
    add_col(cursor, "parts", "is_deleted", "INTEGER DEFAULT 0")

    # 1. Fiscal Year 2024
    cursor.execute("INSERT OR IGNORE INTO fiscal_years (id, year_name, start_date, end_date, is_active) VALUES (2, '2024', '2024-01-01 00:00:00', '2024-12-31 23:59:59', 1)")
    fy_id = 2
    
    # 2. Customers (300+)
    print("Generating 300 customers...")
    names = ["Ahmet", "Mehmet", "Ayşe", "Fatma", "Mustafa", "Ali", "Hüseyin", "Zeynep", "Elif", "Murat", "Hakan", "Deniz", "Ebru", "Okan", "Serkan", "Emre", "Bülent", "Canan", "Derya", "Gökhan"]
    surnames = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aydın", "Öztürk", "Güneş", "Kocaman", "Bakır"]
    companies = ["Teknoloji", "Bilişim", "İnşaat", "Gıda", "Lojistik", "Teknik", "Servis", "Market", "Eczane", "Kuyumcu", "Mühendislik", "Pazarlama"]
    
    customer_ids = []
    for i in range(300):
        full_name = f"{random.choice(names)} {random.choice(surnames)}"
        company = f"{random.choice(companies)} {random.choice(['A.Ş.', 'Ltd. Şti.', 'Ticaret'])}"
        phone = f"05{random.randint(10, 99)}{random.randint(100, 999)}{random.randint(10, 99)}{random.randint(10, 99)}"
        email = f"cust{i}@example.com"
        cursor.execute("INSERT INTO customers (name, company_name, phone, email, is_deleted) VALUES (?, ?, ?, ?, 0)",
                       (full_name, company, phone, email))
        customer_ids.append((cursor.lastrowid, full_name))

    # 3. Stock Items / Parts (1500+)
    print("Generating 1500 stock items...")
    categories = ["Laptop", "Telefon", "Tablet", "Yazıcı", "Monitör", "Klavye", "Mouse", "Anakart", "İşlemci", "RAM", "SSD", "HDD"]
    brands = ["Apple", "Samsung", "HP", "Dell", "Lenovo", "Asus", "Acer", "MSI", "Gigabyte", "Intel", "AMD", "Western Digital", "Seagate"]
    
    part_ids = []
    for i in range(1500):
        category = random.choice(categories)
        brand = random.choice(brands)
        part_name = f"{brand} {category} {random.randint(100, 999)}"
        code = f"{category[:3].upper()}{random.randint(10000, 99999)}"
        purchase_price = random.randint(100, 5000)
        price = purchase_price * 1.3
        
        cursor.execute("INSERT INTO parts (name, part_name, brand, category, purchase_price, price, stock, code, is_deleted) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
                       (part_name, part_name, brand, category, purchase_price, price, random.randint(10, 100), code))
        part_ids.append(cursor.lastrowid)

    # 4. Bank Accounts
    print("Generating bank accounts...")
    for bank in ["Ziraat", "Garanti", "İşBank"]:
        cursor.execute("INSERT INTO bank_accounts (bank_name, account_holder, currency, current_balance, is_active) VALUES (?, ?, 'TRY', 0, 1)",
                       (bank, "AYEC Pro İşletme"))

    # 5. Service Records (600+)
    print("Generating 600 service records (devices)...")
    for i in range(600):
        cid, cname = random.choice(customer_ids)
        tracking_no = f"TRK24{i:04d}"
        date = f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d} 10:00:00"
        cursor.execute("""
            INSERT INTO devices (tracking_no, customer_id, customer_name, device_brand, status, entry_date, created_at, price, is_archived)
            VALUES (?, ?, ?, ?, 'Teslim Edildi', ?, ?, ?, 0)
        """, (tracking_no, cid, cname, random.choice(brands), date, date, random.randint(500, 3000)))

    # 6. Accounting Transactions (2500+)
    print("Generating 2500 accounting transactions...")
    for i in range(2500):
        t_type = random.choice(["Gelir", "Gider"])
        amount = random.randint(100, 10000) if t_type == "Gelir" else -random.randint(50, 5000)
        date = f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d} 11:00:00"
        cursor.execute("""
            INSERT INTO accounting (type, amount, try_equivalent, currency, exchange_rate, description, date, created_at, fiscal_year_id, is_deleted)
            VALUES (?, ?, ?, 'TRY', 1.0, 'Test İşlemi', ?, ?, ?, 0)
        """, (t_type, amount, amount, date, date, fy_id))

    # 7. Set current_fiscal_year
    cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('current_fiscal_year', '2024')")
    
    conn.commit()
    conn.close()
    print("Stress test data generation completed successfully!")

if __name__ == "__main__":
    generate_data()
