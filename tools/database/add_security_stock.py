# -*- coding: utf-8 -*-


import sys
import os
import random
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

from src.database import Database

def add_security_products():
    print("Initializing Database Connection for Security Stock...")
    db = Database()
    
    # List of 20 Security System Products
    # Format: (Name, Category, Stock, Sale Price, Purchase Price, Code, Shelf)
    products = [
        ("Hikvision 2MP Dome IP Kamera", "Kamera", 50, 1250.00, 850.00, "HIK-DOME-001", "RAF-A1"),
        ("Hikvision 4MP Bullet IP Kamera", "Kamera", 40, 1650.00, 1100.00, "HIK-BULL-002", "RAF-A1"),
        ("Dahua 5MP Motorize Lens Kamera", "Kamera", 20, 2400.00, 1750.00, "DAH-MOTO-003", "RAF-A2"),
        ("Neutron 8 Kanal NVR Kayıt Cihazı", "Kayıt Cihazı", 15, 3500.00, 2600.00, "NEU-NVR-008", "RAF-B1"),
        ("Neutron 16 Kanal NVR Kayıt Cihazı", "Kayıt Cihazı", 10, 5200.00, 3900.00, "NEU-NVR-016", "RAF-B1"),
        ("WD Purple 4TB 7/24 Güvenlik Diski", "Depolama", 25, 4100.00, 3200.00, "WD-PURP-004", "RAF-B2"),
        ("Seagate Skyhawk 8TB Güvenlik Diski", "Depolama", 10, 7800.00, 6100.00, "SEA-SKY-008", "RAF-B2"),
        ("CCTV Kablosu 2+1 (100m Top)", "Kablo", 100, 850.00, 550.00, "CBL-21-100", "RAF-C1"),
        ("CAT6 Halogen Free Kablo (305m)", "Kablo", 30, 3200.00, 2400.00, "CBL-CAT6-305", "RAF-C2"),
        ("12V 10A Metal Kasa Adaptör", "Güç Kaynağı", 40, 450.00, 280.00, "PWR-12V-10A", "RAF-D1"),
        ("12V 20A Fanlı Adaptör", "Güç Kaynağı", 25, 750.00, 480.00, "PWR-12V-20A", "RAF-D1"),
        ("BNC Konnektör (Vidalı)", "Aksesuar", 500, 15.00, 5.00, "ACC-BNC-001", "RAF-E1"),
        ("Power Jack (Erkek)", "Aksesuar", 500, 10.00, 3.00, "ACC-JACK-M", "RAF-E1"),
        ("Paradox Kablolu Hareket Sensörü", "Sensör", 60, 450.00, 290.00, "PAR-PIR-001", "RAF-F1"),
        ("Kablosuz Manyetik Kapı Kontağı", "Sensör", 40, 350.00, 220.00, "SENS-MAG-W", "RAF-F1"),
        ("Desi Alarm Paneli (Anakart)", "Alarm", 12, 2800.00, 1900.00, "DESI-MAIN", "RAF-G1"),
        ("Harici Siren (Ledli/Flaşörlü)", "Siren", 30, 650.00, 420.00, "SIR-EXT-01", "RAF-G2"),
        ("Kamera Montaj Buatı (Su Geçirmez)", "Montaj", 150, 45.00, 25.00, "MNT-BOX-01", "RAF-E2"),
        ("RJ45 Konnektör (100'lü Paket)", "Aksesuar", 50, 250.00, 120.00, "ACC-RJ45-PCK", "RAF-E2"),
        ("PoE Switch 8 Port (Gigabit)", "Network", 15, 1850.00, 1350.00, "NET-POE-008", "RAF-H1")
    ]
    
    count = 0
    for item in products:
        name, cat, stock, market_price, buy_price, code, shelf = item
        
        # add_part(name, category, stock, price, desc, min_stock, code, shelf, purchase_price)
        result = db.add_part(
            name=name,
            category=cat,
            stock=stock,
            price=market_price,
            desc="Guvenlik Sistemleri Stok Girisi",
            min_stock=5,
            code=code,
            shelf=shelf,
            purchase_price=buy_price
        )
        
        if result:
            print(f"Added: {name} ({cat})")
            count += 1
        else:
            print(f"Failed: {name}")

    print(f"\nCompleted! {count} stock items added successfully.")

if __name__ == "__main__":
    add_security_products()
