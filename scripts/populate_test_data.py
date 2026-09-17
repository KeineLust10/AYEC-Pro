# -*- coding: utf-8 -*-

import sys
import os
import random
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import Database

def populate_data():
    print("Initializing Database...")
    db = Database()
    
    # 1. Products (Cameras & Computers)
    print("\n--- Generating Products ---")
    camera_brands = ["Sony", "Samsung", "Hikvision", "Dahua", "Axis"]
    computer_brands = ["Dell", "HP", "Lenovo", "Asus", "Apple"]
    
    # Security Cameras
    print("Adding 50 Security Cameras...")
    for i in range(50):
        brand = random.choice(camera_brands)
        model = f"Cam-{random.randint(100, 999)} Pro"
        name = f"{brand} {model} Güvenlik Kamerası"
        stock = random.randint(50, 100)
        purchase_price = random.randint(500, 1500)
        sale_price = purchase_price * random.uniform(1.2, 1.5)
        
        db.add_part(
            name=name,
            category="Güvenlik Sistemleri",
            stock=stock,
            price=round(sale_price, 2),
            purchase_price=round(purchase_price, 2),
            desc=f"{brand} marka yüksek çözünürlüklü güvenlik kamerası.",
            min_stock=10,
            code=f"CAM-{1000+i}",
            shelf=f"A-{random.randint(1, 5)}"
        )
        
    # Computers
    print("Adding 50 Computers...")
    for i in range(50):
        brand = random.choice(computer_brands)
        model = f"Book {random.randint(10, 90)}"
        name = f"{brand} {model} Laptop"
        stock = random.randint(50, 100)
        purchase_price = random.randint(10000, 30000)
        sale_price = purchase_price * random.uniform(1.15, 1.4)
        
        db.add_part(
            name=name,
            category="Bilgisayar",
            stock=stock,
            price=round(sale_price, 2),
            purchase_price=round(purchase_price, 2),
            desc=f"{brand} marka iş istasyonu.",
            min_stock=5,
            code=f"PC-{1000+i}",
            shelf=f"B-{random.randint(1, 5)}"
        )

    # 2. Personnel
    print("\n--- Generating Personnel ---")
    personnel_list = [
        ("Cem Yılmaz", "Teknisyen", "05551234567", 25000),
        ("Ozan Güven", "Saha Ekibi", "05329876543", 22000)
    ]
    
    for name, role, phone, salary in personnel_list:
        if db.add_personnel(name, role, phone, salary):
            print(f"Added personnel: {name}")
        else:
            print(f"Skipped personnel (might exist): {name}")

    # 3. Customers & Transactions
    print("\n--- Generating Customers and Transactions ---")
    customer_names = [
        "Ahmet", "Mehmet", "Ayşe", "Fatma", "Ali", "Veli", "Hasan", "Hüseyin", 
        "Zeynep", "Elif", "Mustafa", "Kemal", "Yusuf", "Ömer", "İbrahim", 
        "Halil", "Murat", "Burak", "Selin", "Deniz"
    ]
    
    last_names = [
        "Yılmaz", "Kaya", "Demir", "Çelik", "Şahin", "Yıldız", "Yıldırım", "Öztürk", 
        "Aydın", "Özdemir", "Arslan", "Doğan", "Kılıç", "Aslan", "Çetin", 
        "Kara", "Koç", "Kurt", "Özkan", "Şimşek"
    ]
    
    created_customers = 0
    for i in range(20):
        full_name = f"{customer_names[i]} {last_names[i]}"
        phone = f"05{random.randint(300, 599)}{random.randint(1000000, 9999999)}"
        # Creating a dictionary for add_customer as mixin expects 'data' dict usually, 
        # but let's check mixin signature again.
        # customer_mixin: add_customer(self, data) -> Keys: name, phone, etc.
        
        customer_data = {
            "name": full_name,
            "phone": phone,
            "email": f"{full_name.lower().replace(' ', '')}@example.com",
            "address": "İstanbul, Türkiye",
            "account_type": "Bireysel"
        }
        
        c_id = db.add_customer(customer_data)
        
        if c_id:
            created_customers += 1
            print(f"Added Customer: {full_name} (ID: {c_id})")
            
            # 4. Sales Transaction (Cari)
            # "Müşteriler sadece ismi olsun, servise gelen cihaz eklemeyelim"
            # "Ayrıca servis yaptığımız da görünsün... ama servis cihazı değil, satış gibi" 
            # -> This implies we add a transaction record but NOT a device record.
            # "20 tane kamera satmışız"
            
            qty = 20
            # Let's say we sold cameras
            # Find a camera part to get price
            # We just iterate and fake it since we just need the transaction record
            # But the user said "Satışlarımız görünsün"
            
            unit_price = random.randint(1000, 2000)
            total_amount = qty * unit_price
            
            desc = f"{qty} Adet Güvenlik Kamerası Satışı\n(Projeli Montaj Dahil)"
            
            # Using add_currency_transaction from CurrencyMixin
            # transaction_type='DEBIT' for Debt/Sale (Müşteri Borçlanır)
            success = db.add_currency_transaction(
                customer_id=c_id,
                amount=total_amount,
                currency='TRY',
                transaction_type='DEBIT',
                description=desc,
                is_invoiced=1 # Faturalı varsayalım
            )
            if success:
                 print(f"  -> Added Sales Transaction: {total_amount} TRY")
        else:
            print(f"Failed to add customer: {full_name}")

    print(f"\nSummary:")
    print(f"Total Customers Added: {created_customers}")
    print("Done.")

if __name__ == "__main__":
    populate_data()
