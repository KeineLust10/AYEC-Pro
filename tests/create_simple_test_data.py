# -*- coding: utf-8 -*-
"""
Basitlestirilmis Test Verisi Olusturma Scripti
Mevcut veritabani yapisina uygun test verileri olusturur
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta
import random

def create_test_data():
    """Mevcut veritabani yapisina uygun test verileri olustur"""
    print("\n" + "="*70)
    print("TEST VERILERI OLUSTURMA BASLIYOR")
    print("="*70 + "\n")
    
    conn = sqlite3.connect("ayecpro.db")
    cursor = conn.cursor()
    
    customer_ids = []
    personnel_names = ["Ahmet Yilmaz", "Mehmet Demir", "Ayse Kaya"]
    
    # 1. Musteriler ekle
    print("[1/4] Musteri kayitlari olusturuluyor...")
    customers_data = [
        ("Zeynep Yildiz", "0541 111 2233", "zeynep.yildiz@gmail.com", "Ataturk Cad. No:15 Kadikoy/Istanbul", "11111111111", "", ""),
        ("Teknoloji A.S.", "0212 444 5566", "info@teknoloji.com.tr", "Buyukdere Cad. Plaza No:100 Sisli/Istanbul", "", "1234567890", "Sisli Vergi Dairesi"),
        ("Can Ozturk", "0542 222 3344", "can.ozturk@hotmail.com", "Bagdat Cad. No:250 Maltepe/Istanbul", "22222222222", "", ""),
        ("Egitim Kurumlari Ltd.", "0216 333 4455", "bilgi@egitim.com", "Kozyatagi Mah. Okul Sok. No:5 Kadikoy/Istanbul", "", "9876543210", "Kadikoy Vergi Dairesi"),
        ("Elif Arslan", "0543 444 5566", "elif.arslan@yahoo.com", "Istiklal Cad. No:88 Beyoglu/Istanbul", "33333333333", "", ""),
        ("Saglik Merkezi A.S.", "0212 555 6677", "destek@saglik.com.tr", "Nisantasi Mah. Saglik Sok. No:12 Sisli/Istanbul", "", "5555555555", "Besiktas Vergi Dairesi"),
        ("Burak Kilic", "0544 666 7788", "burak.kilic@gmail.com", "Camlica Mah. Yesil Sok. No:7 Uskudar/Istanbul", "44444444444", "", ""),
        ("Mimarlik Ofisi", "0216 777 8899", "info@mimarlik.com", "Suadiye Mah. Tasarim Cad. No:45 Kadikoy/Istanbul", "", "7777777777", "Kadikoy Vergi Dairesi"),
        ("Deniz Aydin", "0545 888 9900", "deniz.aydin@outlook.com", "Fenerbahce Mah. Sahil Yolu No:23 Kadikoy/Istanbul", "55555555555", "", ""),
        ("Medya Produksiyon Ltd.", "0212 999 0011", "contact@medya.com.tr", "Levent Mah. Medya Plaza No:78 Besiktas/Istanbul", "", "9999999999", "Besiktas Vergi Dairesi"),
    ]
    
    for customer in customers_data:
        try:
            cursor.execute("""
                INSERT INTO customers (name, phone, email, address, tc_no, tax_no, tax_office)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, customer)
            customer_ids.append(cursor.lastrowid)
            print(f"  [OK] {customer[0]} eklendi")
        except Exception as e:
            print(f"  [UYARI] {customer[0]} eklenirken hata: {str(e)}")
    
    conn.commit()
    print(f"[TAMAMLANDI] {len(customer_ids)} musteri kaydi olusturuldu\n")
    
    # 2. Randevular ekle
    print("[2/4] Randevu kayitlari olusturuluyor...")
    appointment_count = 0
    
    for i in range(15):  # 15 gun
        date = datetime.now() + timedelta(days=i)
        for _ in range(random.randint(2, 4)):  # Her gun 2-4 randevu
            try:
                hour = random.randint(9, 17)
                minute = random.choice([0, 30])
                customer_idx = random.randint(0, len(customer_ids) - 1)
                personnel = random.choice(personnel_names)
                
                cursor.execute("""
                    INSERT INTO appointments 
                    (customer_name, phone, date, time, description, status, personnel, 
                     customer_id, personnel_id, type, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    customers_data[customer_idx][0],  # customer_name
                    customers_data[customer_idx][1],  # phone
                    date.strftime("%Y-%m-%d"),  # date
                    f"{hour:02d}:{minute:02d}",  # time
                    "Genel bakim ve kontrol",  # description
                    random.choice(["Bekliyor", "Onaylandi", "Tamamlandi"]),  # status
                    personnel,  # personnel
                    customer_ids[customer_idx],  # customer_id
                    random.randint(1, 5),  # personnel_id
                    random.choice(["Bakim", "Onarim", "Danismanlik"]),  # type
                    "Test randevusu"  # notes
                ))
                appointment_count += 1
            except Exception as e:
                print(f"  [UYARI] Randevu eklenirken hata: {str(e)}")
    
    conn.commit()
    print(f"[TAMAMLANDI] {appointment_count} randevu kaydi olusturuldu\n")
    
    # 3. Muhasebe kayitlari ekle
    print("[3/4] Muhasebe kayitlari olusturuluyor...")
    accounting_count = 0
    
    for i in range(60):  # Son 60 gun
        date = datetime.now() - timedelta(days=i)
        for _ in range(random.randint(1, 3)):  # Her gun 1-3 islem
            try:
                transaction_type = random.choice(["Gelir", "Gider"])
                
                if transaction_type == "Gelir":
                    category = random.choice(["Servis Ucreti", "Urun Satisi", "Bakim Sozlesmesi"])
                    amount = random.randint(500, 10000)
                    customer_id = random.choice(customer_ids) if customer_ids else None
                else:
                    category = random.choice(["Kira", "Maas", "Stok Alimi", "Elektrik"])
                    amount = random.randint(1000, 15000)
                    customer_id = None
                
                cursor.execute("""
                    INSERT INTO accounting 
                    (date, type, category, amount, customer_id, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    date.strftime("%Y-%m-%d"),
                    transaction_type,
                    category,
                    amount,
                    customer_id,
                    f"{category} - {date.strftime('%B %Y')}"
                ))
                accounting_count += 1
            except Exception as e:
                print(f"  [UYARI] Muhasebe kaydi eklenirken hata: {str(e)}")
    
    conn.commit()
    print(f"[TAMAMLANDI] {accounting_count} muhasebe kaydi olusturuldu\n")
    
    # 4. Bakim sozlesmeleri ekle
    print("[4/4] Bakim sozlesmeleri olusturuluyor...")
    contracts_count = 0
    
    contracts_data = [
        (customer_ids[1] if len(customer_ids) > 1 else None, "2024-01-01", "2024-12-31", 5000, "Aylik bakim, oncelikli destek", "Aktif"),
        (customer_ids[3] if len(customer_ids) > 3 else None, "2024-03-01", "2025-02-28", 3500, "Okul bilgisayarlari bakimi", "Aktif"),
        (customer_ids[5] if len(customer_ids) > 5 else None, "2024-06-01", "2025-05-31", 4500, "7/24 destek, sunucu bakimi", "Aktif"),
    ]
    
    for contract in contracts_data:
        if contract[0]:  # customer_id varsa
            try:
                cursor.execute("""
                    INSERT INTO contracts 
                    (customer_id, start_date, end_date, monthly_fee, services_included, status)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, contract)
                contracts_count += 1
                print(f"  [OK] Musteri #{contract[0]} - {contract[3]} TL/ay - {contract[5]}")
            except Exception as e:
                print(f"  [UYARI] Sozlesme eklenirken hata: {str(e)}")
    
    conn.commit()
    print(f"[TAMAMLANDI] {contracts_count} bakim sozlesmesi olusturuldu\n")
    
    # Istatistikler
    print("\n" + "="*70)
    print("TEST VERILERI ISTATISTIKLERI")
    print("="*70)
    
    cursor.execute("SELECT COUNT(*) FROM customers")
    print(f"Toplam Musteri: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(*) FROM stock")
    product_count = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(quantity * price) FROM stock")
    stock_value = cursor.fetchone()[0] or 0
    print(f"Toplam Urun Cesidi: {product_count}")
    print(f"Toplam Stok Degeri: {stock_value:,.2f} TL")
    
    cursor.execute("SELECT COUNT(*) FROM appointments")
    print(f"Toplam Randevu: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT SUM(amount) FROM accounting WHERE type='Gelir'")
    total_income = cursor.fetchone()[0] or 0
    cursor.execute("SELECT SUM(amount) FROM accounting WHERE type='Gider'")
    total_expense = cursor.fetchone()[0] or 0
    print(f"Toplam Gelir: {total_income:,.2f} TL")
    print(f"Toplam Gider: {total_expense:,.2f} TL")
    print(f"Net Kar: {(total_income - total_expense):,.2f} TL")
    
    cursor.execute("SELECT COUNT(*) FROM contracts WHERE status='Aktif'")
    print(f"Aktif Sozlesmeler: {cursor.fetchone()[0]}")
    
    print("="*70 + "\n")
    
    conn.close()
    
    print("="*70)
    print("TUM TEST VERILERI BASARIYLA OLUSTURULDU!")
    print("="*70 + "\n")
    
    print("Sonraki Adimlar:")
    print("  1. Uygulamayi calistirin: python ModernDesktopApp.py")
    print("  2. Giris yapin: admin / admin")
    print("  3. Tum modulleri test edin:")
    print("     - Musteriler sayfasinda yeni musterileri gorun")
    print("     - Randevular sayfasinda randevulari kontrol edin")
    print("     - Stok sayfasinda urunleri inceleyin")
    print("     - Muhasebe sayfasinda gelir-gider raporlarini gorun")
    print("     - Sozlesmeler sayfasinda bakim sozlesmelerini kontrol edin")
    print("  4. Raporlari olusturun ve yazdirin")
    print("  5. Yedekleme sistemini test edin\n")

if __name__ == "__main__":
    create_test_data()
