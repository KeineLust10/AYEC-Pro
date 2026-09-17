# -*- coding: utf-8 -*-

import os
import sqlite3
import random
from datetime import datetime, timedelta
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))
try:
    from src.utils.path_helper import PathHelper
except ImportError:
    class PathHelper:
        @staticmethod
        def get_db_path(name): return os.path.join(os.getenv("LOCALAPPDATA"), "AYEC Pro", name)

def get_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

def generate_mock_data():
    db_path = PathHelper.get_db_path("ayecpro.db")
    print(f"Veritabanı bağlantısı sağlanıyor: {db_path}")
    
    if not os.path.exists(db_path):
        print("Veritabanı dosyası bulunamadı!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. GENERATE USERS (PERSONNEL)
    print("Personeller oluşturuluyor (3 adet)...")
    personnel_roles = ["Teknisyen", "Satış", "Yönetici"]
    personnel_names = ["Ahmet Yılmaz", "Mehmet Kaya", "Ayşe Demir"]
    u_cols = get_columns(cursor, "users")
    
    for i in range(3):
        data = {"username": f"user{i}"}
        if "password" in u_cols: data["password"] = "dummy_hash_not_used_here"
        if "password_hash" in u_cols: data["password_hash"] = "dummy_hash_not_used_here"
        if "full_name" in u_cols: data["full_name"] = personnel_names[i]
        elif "name" in u_cols: data["name"] = personnel_names[i]
        if "role" in u_cols: data["role"] = personnel_roles[i]
        if "status" in u_cols: data["status"] = 1
        if "active" in u_cols: data["active"] = 1
        
        cols = ", ".join(data.keys())
        places = ", ".join(["?"] * len(data))
        cursor.execute(f"INSERT OR IGNORE INTO users ({cols}) VALUES ({places})", tuple(data.values()))
    
    # 2. GENERATE CUSTOMERS
    print("Müşteriler oluşturuluyor (50 adet)...")
    first_names = ["Ali", "Veli", "Ayşe", "Fatma", "Hakan", "Burak", "Seda", "Merve", "Murat", "Can"]
    last_names = ["Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Öztürk", "Arslan", "Doğan", "Kılıç", "Çetin"]
    cities = ["İstanbul", "Ankara", "İzmir", "Bursa", "Antalya", "Adana"]
    c_cols = get_columns(cursor, "customers")
    
    customer_ids = []
    
    for i in range(50):
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        phone = f"05{random.randint(10000000, 99999999)}"
        email = f"test_{i}@ornek.com"
        address = f"Örnek Mah. Sk. No: {random.randint(1,100)} {random.choice(cities)}"
        
        data = {"name": name, "phone": phone, "email": email, "address": address, "type": "Bireysel"}
        if "identity_number" in c_cols: data["identity_number"] = f"1{random.randint(1000000000, 9999999999)}"
        if "tc_no" in c_cols: data["tc_no"] = f"1{random.randint(1000000000, 9999999999)}"
        if "tax_office" in c_cols: data["tax_office"] = ""
        if "tax_number" in c_cols: data["tax_number"] = ""
        if "tax_no" in c_cols: data["tax_no"] = ""
        if "note" in c_cols: data["note"] = "Otomatik oluşturuldu."
        if "notes" in c_cols: data["notes"] = "Otomatik oluşturuldu."
        if "balance" in c_cols: data["balance"] = 0.0
        if "created_at" in c_cols: data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cols = ", ".join(data.keys())
        places = ", ".join(["?"] * len(data))
        cursor.execute(f"INSERT INTO customers ({cols}) VALUES ({places})", tuple(data.values()))
        customer_ids.append(cursor.lastrowid)

    # 3. GENERATE STOCK ITEMS
    print("Stok parçaları oluşturuluyor (200 adet)...")
    cat1 = "Güvenlik Sistemleri"
    cat2 = "Bilgisayar Bileşenleri"
    
    security_items = ["2MP AHD Kamera", "4MP IP Kamera", "8 Kanal DVR Kayıt Cihazı", "16 Kanal NVR", "Alarm Paneli", "Hareket Sensörü (PIR)", "Manyetik Kontak", "Yangın Dedektörü", "12V 5A Adaptör", "BNC Konnektör"]
    computer_items = ["Ana Kart H61", "16GB DDR4 RAM", "8GB DDR3 RAM", "500GB NVMe SSD", "1TB SATA HDD", "Intel i5 İşlemci", "AMD Ryzen 5", "GTX 1650 Ekran Kartı", "600W Power Supply", "24 İnç Monitör"]
    p_cols = get_columns(cursor, "parts")
    
    for i in range(200):
        is_security = random.choice([True, False])
        category = cat1 if is_security else cat2
        base_name = random.choice(security_items if is_security else computer_items)
        name = f"{base_name} - Model {random.randint(100, 999)}"
        barcode = f"869{random.randint(1000000000, 9999999999)}"
        
        purchase_price = random.uniform(50.0, 1500.0)
        sale_price = purchase_price * random.uniform(1.3, 2.0)
        
        data = {"stock": random.randint(1, 50), "price": sale_price}
        if "name" in p_cols: data["name"] = name
        if "part_name" in p_cols: data["part_name"] = name
        if "barcode" in p_cols: data["barcode"] = barcode
        if "code" in p_cols: data["code"] = barcode
        if "brand" in p_cols: data["brand"] = "Hikvision" if is_security else "Asus"
        if "category" in p_cols: data["category"] = category
        if "purchase_price" in p_cols: data["purchase_price"] = purchase_price
        if "sale_price" in p_cols: data["sale_price"] = sale_price
        if "min_stock" in p_cols: data["min_stock"] = random.randint(5, 15)
        if "unit" in p_cols: data["unit"] = "Adet"
        if "note" in p_cols: data["note"] = "Otomatik oluşturulan stok."
        if "description" in p_cols: data["description"] = "Otomatik oluşturulan stok."
        if "status" in p_cols: data["status"] = 1
        if "is_deleted" in p_cols: data["is_deleted"] = 0

        cols = ", ".join(data.keys())
        places = ", ".join(["?"] * len(data))
        cursor.execute(f"INSERT INTO parts ({cols}) VALUES ({places})", tuple(data.values()))

    # 4. GENERATE DEVICES (IN SERVICE)
    print("Servisteki cihazlar oluşturuluyor (50 adet)...")
    statuses = ["Bekliyor", "Tamirde", "Parça Bekliyor", "Test Sürecinde", "Hazır", "Teslim Edildi"]
    faults = ["Açılmıyor", "Ekranda çizgi var", "Kayıt tutmuyor", "Mavi ekran hatası alıyor", "Kamerada görüntü yok"]
    d_cols = get_columns(cursor, "devices")
    
    for i in range(50):
        c_id = random.choice(customer_ids)
        cursor.execute("SELECT * FROM customers WHERE id=?", (c_id,))
        c_row = cursor.fetchone()
        
        # safely get name and phone
        c_dict = dict(zip(c_cols, c_row))
        c_name = c_dict.get("name", "")
        c_phone = c_dict.get("phone", "")
        
        is_security = random.choice([True, False])
        brand = "Dahua" if is_security else "Lenovo"
        model = f"X{random.randint(10, 99)}" if is_security else f"IdeaPad {random.randint(3,7)}"
        tracking_no = f"SRV-{random.randint(10000, 99999)}-{i}"
        
        days_ago = random.randint(0, 30)
        entry_date = (datetime.now() - timedelta(days=days_ago)).strftime("%d.%m.%Y")
        
        data = {"tracking_no": tracking_no, "status": random.choice(statuses), "entry_date": entry_date}
        if "customer_id" in d_cols: data["customer_id"] = c_id
        if "customer_name" in d_cols: data["customer_name"] = c_name
        if "customer_contact" in d_cols: data["customer_contact"] = c_phone
        if "device_brand" in d_cols: data["device_brand"] = brand
        if "device_model" in d_cols: data["device_model"] = model
        if "serial_no" in d_cols: data["serial_no"] = f"SN{random.randint(1000,9999)}"
        if "fault_description" in d_cols: data["fault_description"] = random.choice(faults)
        if "price" in d_cols: data["price"] = random.choice([0, 500, 1500, 250])
        if "technician_note" in d_cols: data["technician_note"] = "Otomaitk kayıt"
        if "device_type" in d_cols: data["device_type"] = "Güvenlik" if is_security else "Bilgisayar"

        cols = ", ".join(data.keys())
        places = ", ".join(["?"] * len(data))
        cursor.execute(f"INSERT INTO devices ({cols}) VALUES ({places})", tuple(data.values()))

    # 5. GENERATE APPOINTMENTS
    print("Randevular oluşturuluyor (10 adet)...")
    a_cols = get_columns(cursor, "appointments")
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    for i in range(10):
        c_id = random.choice(customer_ids)
        cursor.execute(f"SELECT {c_cols.index('name')}, {c_cols.index('phone')} FROM customers WHERE id=?", (c_id,))
        c_row = cursor.fetchone()
        c_name, c_phone = c_row[0], c_row[1]
        
        data = {"date": today_str, "time": f"{random.randint(9, 17):02d}:00", "description": "Otomatik Randevu", "status": "Bekliyor"}
        if "customer_id" in a_cols: data["customer_id"] = c_id
        if "customer_name" in a_cols: data["customer_name"] = c_name
        if "phone" in a_cols: data["phone"] = c_phone
        if "title" in a_cols: data["title"] = "Servis Randevusu"
        if "created_at" in a_cols: data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cols = ", ".join(data.keys())
        places = ", ".join(["?"] * len(data))
        cursor.execute(f"INSERT INTO appointments ({cols}) VALUES ({places})", tuple(data.values()))

    conn.commit()
    conn.close()
    print("VERİ OLUŞTURMA İŞLEMİ BAŞARIYLA TAMAMLANDI!")

if __name__ == "__main__":
    generate_mock_data()
