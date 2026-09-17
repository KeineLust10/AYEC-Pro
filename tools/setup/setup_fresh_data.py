# -*- coding: utf-8 -*-

"""
Güvenlik Sistemleri Test Verisi Oluşturucu
- 20 Müşteri
- 20 Güvenlik Sistemi Ürünü (Kamera, DVR, Sensör vb.)
- Temiz başlangıç
"""

import sqlite3
import random
from datetime import datetime

# Database connection
conn = sqlite3.connect(r'C:\Users\Admin\AppData\Local\AYECPro\ayecpro.db')
cursor = conn.cursor()

print("=== VERI TEMIZLEME ===")
# Clear all transactional data
tables_to_clear = [
    "currency_transactions",
    "accounting",
    "used_parts",
    "stock_movements",
    "audit_logs",
    "jarvis_notifications",
    "customers",
    "parts"
]

for table in tables_to_clear:
    try:
        cursor.execute(f"DELETE FROM {table}")
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
        print(f"[OK] {table} temizlendi")
    except Exception as e:
        print(f"[HATA] {table} temizlenemedi: {e}")

conn.commit()

print("\n=== MUSTERI EKLEME ===")
# 20 Realistic Customers
customers = [
    ("Ahmet Yilmaz", "Yilmaz Guvenlik Ltd.", "05321234567", "ahmet@yilmazguvenlik.com", "Istanbul"),
    ("Mehmet Demir", "Demir Elektronik", "05339876543", "mehmet@demirelektronik.com", "Ankara"),
    ("Ayse Kaya", "Kaya Teknoloji A.S.", "05347654321", "ayse@kayatek.com", "Izmir"),
    ("Fatma Celik", "Celik Guvenlik Sistemleri", "05356789012", "fatma@celikguvenlik.com", "Bursa"),
    ("Ali Sahin", "Sahin Insaat", "05362345678", "ali@sahininsaat.com", "Antalya"),
    ("Zeynep Arslan", "Arslan Market Zinciri", "05378901234", "zeynep@arslanmarket.com", "Adana"),
    ("Mustafa Koc", "Koc Otomotiv", "05384567890", "mustafa@kocoto.com", "Gaziantep"),
    ("Elif Yildiz", "Yildiz Otel", "05391234567", "elif@yildizhotel.com", "Mugla"),
    ("Hasan Aydin", "Aydin Fabrika", "05402345678", "hasan@aydinfabrika.com", "Kocaeli"),
    ("Selin Ozturk", "Ozturk Lojistik", "05413456789", "selin@ozturklojistik.com", "Mersin"),
    ("Burak Kilic", "Kilic Restoran", "05424567890", "burak@kilicrestoran.com", "Konya"),
    ("Deniz Sen", "Sen Eczanesi", "05435678901", "deniz@seneczane.com", "Kayseri"),
    ("Can Acar", "Acar Mobilya", "05446789012", "can@acarmobilya.com", "Eskisehir"),
    ("Ece Yurt", "Yurt Okulu", "05457890123", "ece@yurtokulu.com", "Samsun"),
    ("Onur Tas", "Tas Yapi", "05468901234", "onur@tasyapi.com", "Trabzon"),
    ("Gizem Kurt", "Kurt Cafe", "05479012345", "gizem@kurtcafe.com", "Balikesir"),
    ("Emre Polat", "Polat Spor Salonu", "05480123456", "emre@polatspor.com", "Sakarya"),
    ("Seda Aksoy", "Aksoy Kuafor", "05491234567", "seda@aksoybeauty.com", "Tekirdag"),
    ("Baris Erdogan", "Erdogan Oto Galeri", "05502345678", "baris@erdoganoto.com", "Manisa"),
    ("Ceren Yavuz", "Yavuz Veteriner Klinigi", "05513456789", "ceren@yavuzvet.com", "Denizli")
]

for name, company, phone, email, city in customers:
    cursor.execute("""
        INSERT INTO customers (name, company_name, phone, email, address)
        VALUES (?, ?, ?, ?, ?)
    """, (name, company, phone, email, city))
    print(f"[OK] {name} - {company}")

conn.commit()

print("\n=== STOK EKLEME (Guvenlik Sistemleri) ===")
# 20 Security System Products
products = [
    ("Hikvision 2MP IP Kamera", 2500, 4500, 15, "A1", "HIK-2MP-001"),
    ("Dahua 4MP Dome Kamera", 3200, 5800, 12, "A2", "DAH-4MP-002"),
    ("Uniview 5MP Bullet Kamera", 3800, 6500, 10, "A3", "UNV-5MP-003"),
    ("8 Kanal DVR Kayit Cihazi", 4500, 7500, 8, "B1", "DVR-8CH-001"),
    ("16 Kanal NVR IP Kayit", 7500, 12000, 5, "B2", "NVR-16CH-002"),
    ("PIR Hareket Sensoru", 450, 850, 25, "C1", "PIR-SENSOR-001"),
    ("Manyetik Kapi Sensoru", 280, 550, 30, "C2", "DOOR-SENSOR-002"),
    ("Kablosuz Alarm Paneli", 3500, 6000, 6, "D1", "ALARM-PANEL-001"),
    ("Siren (Dis Mekan)", 850, 1500, 18, "D2", "SIREN-OUT-001"),
    ("12V 5A Adaptor", 320, 650, 40, "E1", "ADAPTER-12V-5A"),
    ("RG59 Koaksiyel Kablo (100m)", 1200, 2200, 8, "E2", "CABLE-RG59-100M"),
    ("CAT6 Network Kablosu (305m)", 1800, 3200, 6, "E3", "CABLE-CAT6-305M"),
    ("4 Port PoE Switch", 2800, 4800, 10, "F1", "POE-SWITCH-4P"),
    ("8 Port PoE Switch", 4500, 7500, 7, "F2", "POE-SWITCH-8P"),
    ("2TB Surveillance HDD", 3200, 5500, 9, "G1", "HDD-2TB-SURV"),
    ("4TB Surveillance HDD", 5500, 9000, 5, "G2", "HDD-4TB-SURV"),
    ("Akilli Kilit Sistemi", 4800, 8500, 4, "H1", "SMART-LOCK-001"),
    ("Parmak Izi Okuyucu", 3500, 6500, 6, "H2", "FINGERPRINT-001"),
    ("Yuz Tanima Terminali", 12000, 18000, 3, "H3", "FACE-RECOG-001"),
    ("Arac Plaka Tanima Kamera", 15000, 24000, 2, "I1", "LPR-CAMERA-001")
]

for name, purchase_price, sale_price, stock, shelf, code in products:
    cursor.execute("""
        INSERT INTO parts (name, stock, price, purchase_price, code, min_stock)
        VALUES (?, ?, ?, ?, ?, 5)
    """, (name, stock, sale_price, purchase_price, code))
    print(f"[OK] {name} - Stok: {stock}, Alis: {purchase_price} TL, Satis: {sale_price} TL")

conn.commit()

print("\n=== OZET ===")
cursor.execute("SELECT COUNT(*) FROM customers")
customer_count = cursor.fetchone()[0]
print(f"Toplam Musteri: {customer_count}")

cursor.execute("SELECT COUNT(*) FROM parts")
product_count = cursor.fetchone()[0]
print(f"Toplam Urun: {product_count}")

cursor.execute("SELECT SUM(stock * purchase_price) FROM parts")
total_inventory_value = cursor.fetchone()[0]
print(f"Toplam Stok Degeri (Alis): {total_inventory_value:,.2f} TL")

conn.close()

print("\n[BASARILI] Test verisi hazir! Artik manuel satis yapabilirsiniz.")
print("[NOT] Dolar satislari otomatik olarak Gelir/Gider raporlarina dahil edilecek.")

