# -*- coding: utf-8 -*-


import sqlite3
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

def fix_db():
    from src.database import Database
    print("Fixing Database Schema...")
    
    # Use the app's database connection logic to ensure we hit the right file
    db = Database()
    cursor = db.cursor
    
    # 1. Add purchase_price to parts if missing
    print("Checking 'parts' table for purchase_price...")
    try:
        cursor.execute("SELECT purchase_price FROM parts LIMIT 1")
    except:
        print("Column 'purchase_price' missing. Adding it...")
        try:
            cursor.execute("ALTER TABLE parts ADD COLUMN purchase_price REAL DEFAULT 0")
        except Exception as e:
            print(f"Error adding column: {e}")
            
    # 2. Re-create used_parts table correctly
    print("Recreating 'used_parts' table...")
    try:
        cursor.execute("DROP TABLE IF EXISTS used_parts")
        cursor.execute("""
            CREATE TABLE used_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_no TEXT,
                part_id INTEGER,
                quantity INTEGER,
                purchase_price_snapshot REAL,
                used_at TEXT,
                FOREIGN KEY(part_id) REFERENCES parts(id)
            )
        """)
        print("used_parts table recreated.")
    except Exception as e:
        print(f"Error recreating table: {e}")
        
    db.conn.commit()
    
    # 3. Update Purchase Prices for Security Stock (Hardcoded fix for the 20 items added)
    print("Updating Purchase Prices for Stock Items...")
    updates = {
        "Hikvision 2MP Dome IP Kamera": 35.0 * 34, # Approx USD conversion or direct TL
        "Hikvision 4MP Bullet IP Kamera": 45.0 * 34,
        "Dahua 5MP Motorize Lens Kamera": 60.0 * 34,
        "Neutron 8 Kanal NVR Kayıt Cihazı": 120.0 * 34,
        "Neutron 16 Kanal NVR Kayıt Cihazı": 180.0 * 34,
        "WD Purple 4TB 7/24 Güvenlik Diski": 110.0 * 34,
        "Seagate Skyhawk 8TB Güvenlik Diski": 190.0 * 34,
        "CCTV Kablosu 2+1 (100m Top)": 15.0 * 34,
        "CAT6 Halogen Free Kablo (305m)": 80.0 * 34,
        "12V 10A Metal Kasa Adaptör": 12.0 * 34,
        "12V 20A Fanlı Adaptör": 18.0 * 34,
        "BNC Konnektör (Vidalı)": 0.5 * 34,
        "Power Jack (Erkek)": 0.3 * 34,
        "Paradox Kablolu Hareket Sensörü": 15.0 * 34,
        "Kablosuz Manyetik Kapı Kontağı": 8.0 * 34,
        "Desi Alarm Paneli (Anakart)": 80.0 * 34,
        "Harici Siren (Ledli/Flaşörlü)": 25.0 * 34,
        "Kamera Montaj Buatı (Su Geçirmez)": 2.0 * 34,
        "RJ45 Konnektör (100'lü Paket)": 5.0 * 34,
        "PoE Switch 8 Port (Gigabit)": 45.0 * 34,
        # Previous Test Data
        "iPhone 11 Ekran": 800,
        "Samsung S20 Batarya": 500,
        "iPhone Şarj Soketi": 100,
        "Termal Macun": 80,
        "500GB SSD": 1100,
        "8GB DDR4 RAM": 700,
        "Kılıf (Universal)": 40,
        "Ekran Koruyucu Cam": 10,
        "iPhone 13 Kamera": 1800,
        "Samsung A50 Ekran": 600
    }
    
    for name, price in updates.items():
        try:
            cursor.execute("UPDATE parts SET purchase_price=? WHERE name LIKE ?", (price, f"{name}%"))
        except Exception as e:
            print(f"Failed to update {name}: {e}")
            
    db.conn.commit()
    print("Database Fix Completed!")

if __name__ == "__main__":
    fix_db()
