# -*- coding: utf-8 -*-


import sqlite3
import os
import json
from datetime import datetime

# DB Yolu
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ayecpro.db"))
print(f"Veritabanı: {DB_PATH}")

def run_simulation():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        print("\n1. MÜŞTERİ KONTROLÜ...")
        cur.execute("SELECT id, name FROM customers LIMIT 1")
        cust = cur.fetchone()
        
        if not cust:
            print("   -> Müşteri yok, oluşturuluyor...")
            cur.execute("INSERT INTO customers (name, phone) VALUES (?, ?)", ("Test Müşteri", "5551234567"))
            cust_id = cur.lastrowid
            cust_name = "Test Müşteri"
        else:
            cust_id = cust['id']
            cust_name = cust['name']
            print(f"   -> Müşteri bulundu: ID={cust_id}, İsim={cust_name}")

        print("\n2. CİHAZ/SERVİS KAYDI SİMÜLASYONU...")
        
        # main.py'deki mantığın aynısı
        cur.execute("SELECT MAX(id) as max_id FROM devices")
        row = cur.fetchone()
        max_id = row['max_id'] if row and row['max_id'] else 0
        tracking_no = f"SRV{max_id + 1:05d}"
        print(f"   -> Yeni Takip No: {tracking_no}")
        
        process_date = datetime.now().strftime("%Y-%m-%d")
        desc_str = "Test Hizmeti (1x)"
        
        # KRİTİK NOKTA: INSERT SQL
        print("   -> INSERT SQL çalıştırılıyor...")
        
        try:
            # Önce customer_id ile deniyoruz
            cur.execute("""
                INSERT INTO devices (
                    tracking_no, customer_name, device_brand, device_model,
                    fault_description, urgency, entry_date, status, customer_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tracking_no, cust_name, "Hızlı İşlem", "Genel Hizmet",
                f"Sihirbaz Kaydı: {desc_str}", "Normal", process_date, "Yeni Kayıt", cust_id
            ))
            print("   ✅ INSERT BAŞARILI (customer_id sütunu var)")
            
        except sqlite3.OperationalError as e:
            print(f"   ⚠️ HATA (customer_id ile): {e}")
            print("   -> Fallback deneniyor (customer_id olmadan)...")
            
            cur.execute("""
                INSERT INTO devices (
                    tracking_no, customer_name, device_brand, device_model,
                    fault_description, urgency, entry_date, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tracking_no, cust_name, "Hızlı İşlem", "Genel Hizmet",
                f"Sihirbaz Kaydı: {desc_str}", "Normal", process_date, "Yeni Kayıt"
            ))
            print("   ✅ INSERT BAŞARILI (Fallback ile)")

        service_id = cur.lastrowid
        print(f"   -> Servis ID: {service_id}")

        print("\n3. KULLANILAN PARÇA (Adisyon) KAYDI...")
        # used_parts tablosu
        cur.execute("""
            INSERT INTO used_parts (tracking_no, part_name, price, quantity, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (tracking_no, "Test Parça", 100.0, 1, datetime.now().isoformat()))
        print("   ✅ Parça Eklendi.")
        
        # Rollback yapıyoruz ki veritabanı kirlenmesin, sadece test ettik
        conn.rollback() 
        print("\n✅ TEST TAMAMLANDI: HATA YOK (Rollback yapıldı)")

    except Exception as e:
        print(f"\n❌ KRİTİK HATA OLUŞTU:\n{e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    run_simulation()

