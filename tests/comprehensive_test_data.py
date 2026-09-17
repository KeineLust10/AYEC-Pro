# -*- coding: utf-8 -*-
"""
Kapsamli Test Verisi Olusturma Scripti
AYEC Pro uygulamasini gercek dunya senaryolariyla test etmek icin
detayli test verileri olusturur.
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Proje kok dizinini Python path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database import Database

class ComprehensiveTestDataGenerator:
    def __init__(self):
        self.db = Database("ayecpro.db")
        self.customer_ids = []
        self.personnel_ids = []
        self.product_ids = []
        self.device_ids = []
        
    def create_personnel(self):
        """Personel kayitlari olustur"""
        print("\n[PERSONEL] Personel Kayitlari Olusturuluyor...")
        
        personnel_data = [
            {
                "name": "Ahmet Yilmaz",
                "role": "Teknisyen",
                "phone": "0532 111 2233",
                "salary": 15000,
                "commission": 10,
                "tc": "12345678901",
                "email": "ahmet.yilmaz@ayecpro.com",
                "dept": "Teknik Servis",
                "password": "ahmet123"
            },
            {
                "name": "Mehmet Demir",
                "role": "Teknisyen",
                "phone": "0533 222 3344",
                "salary": 14000,
                "commission": 8,
                "tc": "23456789012",
                "email": "mehmet.demir@ayecpro.com",
                "dept": "Teknik Servis",
                "password": "mehmet123"
            },
            {
                "name": "Ayse Kaya",
                "role": "Muhasebe",
                "phone": "0534 333 4455",
                "salary": 12000,
                "commission": 0,
                "tc": "34567890123",
                "email": "ayse.kaya@ayecpro.com",
                "dept": "Muhasebe",
                "password": "ayse123"
            },
            {
                "name": "Fatma Sahin",
                "role": "Satis Danismani",
                "phone": "0535 444 5566",
                "salary": 11000,
                "commission": 15,
                "tc": "45678901234",
                "email": "fatma.sahin@ayecpro.com",
                "dept": "Satis",
                "password": "fatma123"
            },
            {
                "name": "Ali Celik",
                "role": "Yonetici",
                "phone": "0536 555 6677",
                "salary": 20000,
                "commission": 5,
                "tc": "56789012345",
                "email": "ali.celik@ayecpro.com",
                "dept": "Yonetim",
                "password": "ali123"
            }
        ]
        
        for person in personnel_data:
            try:
                # Önce kullanici hesabi olustur
                self.db.add_user(person["email"], person["password"], person["role"])
                
                # Sonra personel kaydi ekle
                self.db.cursor.execute("""
                    INSERT INTO personnel (name, role, phone, salary, commission, tc_no, email, department)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (person["name"], person["role"], person["phone"], person["salary"], 
                      person["commission"], person["tc"], person["email"], person["dept"]))
                
                self.personnel_ids.append(self.db.cursor.lastrowid)
                print(f"  [OK] {person['name']} - {person['role']} eklendi")
            except Exception as e:
                print(f"  [UYARI] {person['name']} eklenirken hata (zaten var olabilir): {str(e)}")
        
        self.db.conn.commit()
        print(f"[TAMAMLANDI] {len(personnel_data)} personel kaydi olusturuldu\n")
        
    def create_customers(self):
        """Musteri kayitlari olustur"""
        print("\n[MUSTERI] Musteri Kayitlari Olusturuluyor...")
        
        customers_data = [
            {
                "name": "Zeynep Yildiz",
                "phone": "0541 111 2233",
                "email": "zeynep.yildiz@gmail.com",
                "address": "Ataturk Cad. No:15 Kadikoy/Istanbul",
                "tc": "11111111111",
                "tax_no": "",
                "tax_office": "",
                "notes": "Kurumsal musteri, aylik bakim sozlesmesi var"
            },
            {
                "name": "Teknoloji A.S.",
                "phone": "0212 444 5566",
                "email": "info@teknoloji.com.tr",
                "address": "Buyukdere Cad. Plaza No:100 Sisli/Istanbul",
                "tc": "",
                "tax_no": "1234567890",
                "tax_office": "Sisli Vergi Dairesi",
                "notes": "Kurumsal musteri, 50+ cihaz bakimi yapiliyor"
            },
            {
                "name": "Can Ozturk",
                "phone": "0542 222 3344",
                "email": "can.ozturk@hotmail.com",
                "address": "Bagdat Cad. No:250 Maltepe/Istanbul",
                "tc": "22222222222",
                "tax_no": "",
                "tax_office": "",
                "notes": "Sadik musteri, yillik 3-4 servis geliyor"
            },
            {
                "name": "Egitim Kurumlari Ltd.",
                "phone": "0216 333 4455",
                "email": "bilgi@egitim.com",
                "address": "Kozyatagi Mah. Okul Sok. No:5 Kadikoy/Istanbul",
                "tc": "",
                "tax_no": "9876543210",
                "tax_office": "Kadikoy Vergi Dairesi",
                "notes": "Okul bilgisayarlari ve projeksiyon cihazlari bakimi"
            },
            {
                "name": "Elif Arslan",
                "phone": "0543 444 5566",
                "email": "elif.arslan@yahoo.com",
                "address": "Istiklal Cad. No:88 Beyoglu/Istanbul",
                "tc": "33333333333",
                "tax_no": "",
                "tax_office": "",
                "notes": "Grafik tasarimci, yuksek performansli PC kullaniyor"
            },
            {
                "name": "Saglik Merkezi A.S.",
                "phone": "0212 555 6677",
                "email": "destek@saglik.com.tr",
                "address": "Nisantasi Mah. Saglik Sok. No:12 Sisli/Istanbul",
                "tc": "",
                "tax_no": "5555555555",
                "tax_office": "Besiktas Vergi Dairesi",
                "notes": "Tibbi cihaz yazilimlari ve sunucu bakimi"
            },
            {
                "name": "Burak Kilic",
                "phone": "0544 666 7788",
                "email": "burak.kilic@gmail.com",
                "address": "Camlica Mah. Yesil Sok. No:7 Uskudar/Istanbul",
                "tc": "44444444444",
                "tax_no": "",
                "tax_office": "",
                "notes": "Oyuncu, gaming PC ve ekipman bakimi"
            },
            {
                "name": "Mimarlik Ofisi",
                "phone": "0216 777 8899",
                "email": "info@mimarlik.com",
                "address": "Suadiye Mah. Tasarim Cad. No:45 Kadikoy/Istanbul",
                "tc": "",
                "tax_no": "7777777777",
                "tax_office": "Kadikoy Vergi Dairesi",
                "notes": "CAD is istasyonlari ve render sunuculari"
            },
            {
                "name": "Deniz Aydin",
                "phone": "0545 888 9900",
                "email": "deniz.aydin@outlook.com",
                "address": "Fenerbahce Mah. Sahil Yolu No:23 Kadikoy/Istanbul",
                "tc": "55555555555",
                "tax_no": "",
                "tax_office": "",
                "notes": "Ev ofis kullanicisi, duzenli bakim istiyor"
            },
            {
                "name": "Medya Produksiyon Ltd.",
                "phone": "0212 999 0011",
                "email": "contact@medya.com.tr",
                "address": "Levent Mah. Medya Plaza No:78 Besiktas/Istanbul",
                "tc": "",
                "tax_no": "9999999999",
                "tax_office": "Besiktas Vergi Dairesi",
                "notes": "Video editing workstation'lari ve storage sistemleri"
            }
        ]
        
        for customer in customers_data:
            try:
                data = {
                    "name": customer["name"],
                    "phone": customer["phone"],
                    "email": customer["email"],
                    "address": customer["address"],
                    "tc_no": customer["tc"],
                    "tax_no": customer["tax_no"],
                    "tax_office": customer["tax_office"],
                    "notes": customer["notes"]
                }
                self.db.add_customer(data)
                self.customer_ids.append(self.db.cursor.lastrowid)
                print(f"  [OK] {customer['name']} eklendi")
            except Exception as e:
                print(f"  [UYARI] {customer['name']} eklenirken hata: {str(e)}")
        
        self.db.conn.commit()
        print(f"[TAMAMLANDI] {len(customers_data)} musteri kaydi olusturuldu\n")
        
    def create_products(self):
        """Urun ve stok kayitlari olustur"""
        print("\n[STOK] Urun ve Stok Kayitlari Olusturuluyor...")
        
        products_data = [
            {"name": "Samsung SSD 1TB", "category": "Donanim", "stock": 25, "price": 2500, "barcode": "8806090123456"},
            {"name": "Kingston RAM 16GB DDR4", "category": "Donanim", "stock": 40, "price": 1200, "barcode": "7406090234567"},
            {"name": "Logitech MX Master 3", "category": "Aksesuar", "stock": 15, "price": 1800, "barcode": "9706090345678"},
            {"name": "Dell UltraSharp 27\" Monitor", "category": "Donanim", "stock": 8, "price": 8500, "barcode": "8846090456789"},
            {"name": "Windows 11 Pro Lisans", "category": "Yazilim", "stock": 50, "price": 3500, "barcode": "8906090567890"},
            {"name": "Microsoft Office 2021", "category": "Yazilim", "stock": 30, "price": 2800, "barcode": "8906090678901"},
            {"name": "Corsair PSU 750W", "category": "Donanim", "stock": 12, "price": 2200, "barcode": "8436090789012"},
            {"name": "TP-Link WiFi Router", "category": "Ag", "stock": 20, "price": 850, "barcode": "6935364090123"},
            {"name": "Seagate HDD 4TB", "category": "Donanim", "stock": 18, "price": 3200, "barcode": "7636090234567"},
            {"name": "NVIDIA RTX 4060", "category": "Donanim", "stock": 5, "price": 18000, "barcode": "8943090345678"},
            {"name": "AMD Ryzen 7 5800X", "category": "Donanim", "stock": 10, "price": 12000, "barcode": "7306090456789"},
            {"name": "ASUS ROG Anakart", "category": "Donanim", "stock": 7, "price": 8500, "barcode": "4719090567890"},
            {"name": "Cooler Master Kasa", "category": "Donanim", "stock": 15, "price": 2500, "barcode": "4719090678901"},
            {"name": "Arctic Liquid Cooler", "category": "Sogutma", "stock": 12, "price": 1800, "barcode": "4895090789012"},
            {"name": "Thermal Paste Premium", "category": "Aksesuar", "stock": 50, "price": 150, "barcode": "4895090890123"},
            {"name": "HDMI Kablo 2m", "category": "Aksesuar", "stock": 60, "price": 120, "barcode": "6935090901234"},
            {"name": "USB-C Hub 7 Port", "category": "Aksesuar", "stock": 25, "price": 450, "barcode": "6935091012345"},
            {"name": "Mekanik Klavye RGB", "category": "Aksesuar", "stock": 18, "price": 1500, "barcode": "6935091123456"},
            {"name": "Webcam 1080p", "category": "Aksesuar", "stock": 22, "price": 950, "barcode": "9706091234567"},
            {"name": "Antivirus 1 Yillik", "category": "Yazilim", "stock": 100, "price": 350, "barcode": "8906091345678"}
        ]
        
        for product in products_data:
            try:
                self.db.cursor.execute("""
                    INSERT INTO stock (product_name, category, quantity, price, barcode)
                    VALUES (?, ?, ?, ?, ?)
                """, (product["name"], product["category"], product["stock"], 
                      product["price"], product["barcode"]))
                
                self.product_ids.append(self.db.cursor.lastrowid)
                print(f"  [OK] {product['name']} - Stok: {product['stock']} - Fiyat: {product['price']} TL")
            except Exception as e:
                print(f"  [UYARI] {product['name']} eklenirken hata: {str(e)}")
        
        self.db.conn.commit()
        print(f"[TAMAMLANDI] {len(products_data)} urun kaydi olusturuldu\n")
        
    def create_devices_and_services(self):
        """Cihaz kayitlari ve servis islemleri olustur"""
        print("\n[SERVIS] Cihaz ve Servis Kayitlari Olusturuluyor...")
        
        if not self.customer_ids or not self.personnel_ids:
            print("  [UYARI] Once musteri ve personel kayitlari olusturulmali!")
            return
        
        devices_data = [
            {
                "customer_idx": 0,
                "brand": "Dell",
                "model": "Latitude 5420",
                "serial": "DL2023ABC123",
                "device_type": "Laptop",
                "problem": "Acilmiyor, fan sesi geliyor",
                "status": "Tamamlandi",
                "cost": 850,
                "notes": "Anakart temizlendi, termal macun yenilendi"
            },
            {
                "customer_idx": 1,
                "brand": "HP",
                "model": "ProDesk 600 G5",
                "serial": "HP2023XYZ456",
                "device_type": "Masaustu PC",
                "problem": "Yavas calisiyor, donmalar oluyor",
                "status": "Tamamlandi",
                "cost": 1200,
                "notes": "SSD upgrade yapildi, RAM 16GB'a yukseltildi"
            },
            {
                "customer_idx": 2,
                "brand": "Lenovo",
                "model": "ThinkPad X1 Carbon",
                "serial": "LN2023QWE789",
                "device_type": "Laptop",
                "problem": "Ekran kirik",
                "status": "Beklemede",
                "cost": 3500,
                "notes": "Ekran paneli siparis edildi, geldiginde degistirilecek"
            },
            {
                "customer_idx": 3,
                "brand": "Apple",
                "model": "iMac 27\" 2020",
                "serial": "AP2023RTY012",
                "device_type": "Masaustu PC",
                "problem": "Ses gelmiyor",
                "status": "Tamamlandi",
                "cost": 650,
                "notes": "Ses karti surucusu guncellendi"
            },
            {
                "customer_idx": 4,
                "brand": "Asus",
                "model": "ROG Strix G15",
                "serial": "AS2023UIO345",
                "device_type": "Laptop",
                "problem": "Oyunlarda FPS dusukugu",
                "status": "Devam Ediyor",
                "cost": 0,
                "notes": "GPU testi yapiliyor, termal sorun olabilir"
            },
            {
                "customer_idx": 5,
                "brand": "Dell",
                "model": "PowerEdge R740",
                "serial": "DL2023SRV678",
                "device_type": "Sunucu",
                "problem": "RAID hatasi",
                "status": "Tamamlandi",
                "cost": 4500,
                "notes": "Arizali disk degistirildi, RAID yeniden yapilandirildi"
            },
            {
                "customer_idx": 6,
                "brand": "MSI",
                "model": "Trident X",
                "serial": "MS2023GAM901",
                "device_type": "Masaustu PC",
                "problem": "Ekran karti arizali",
                "status": "Tamamlandi",
                "cost": 18500,
                "notes": "RTX 4060 ile degistirildi"
            },
            {
                "customer_idx": 7,
                "brand": "HP",
                "model": "Z4 Workstation",
                "serial": "HP2023WRK234",
                "device_type": "Is Istasyonu",
                "problem": "Render sirasinda kapaniyor",
                "status": "Tamamlandi",
                "cost": 2800,
                "notes": "PSU yetersizdi, 850W ile degistirildi"
            },
            {
                "customer_idx": 8,
                "brand": "Acer",
                "model": "Aspire 5",
                "serial": "AC2023ASP567",
                "device_type": "Laptop",
                "problem": "Klavye bazi tuslar calismiyor",
                "status": "Tamamlandi",
                "cost": 450,
                "notes": "Klavye degistirildi"
            },
            {
                "customer_idx": 9,
                "brand": "Dell",
                "model": "Precision 7920",
                "serial": "DL2023PRE890",
                "device_type": "Is Istasyonu",
                "problem": "Storage doldu, yedekleme lazim",
                "status": "Tamamlandi",
                "cost": 5500,
                "notes": "4TB HDD eklendi, RAID 1 yapilandirmasi yapildi"
            }
        ]
        
        for device in devices_data:
            try:
                customer_id = self.customer_ids[device["customer_idx"]]
                personnel_id = random.choice(self.personnel_ids[:2])  # Teknisyenlerden biri
                
                # Cihaz kaydi ekle
                self.db.cursor.execute("""
                    INSERT INTO services 
                    (customer_id, device_brand, device_model, serial_number, device_type, 
                     problem_description, status, cost, notes, personnel_id, entry_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (customer_id, device["brand"], device["model"], device["serial"],
                      device["device_type"], device["problem"], device["status"],
                      device["cost"], device["notes"], personnel_id,
                      (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S")))
                
                self.device_ids.append(self.db.cursor.lastrowid)
                print(f"  [OK] {device['brand']} {device['model']} - {device['status']} - {device['cost']} TL")
            except Exception as e:
                print(f"  [UYARI] Cihaz eklenirken hata: {str(e)}")
        
        self.db.conn.commit()
        print(f"[TAMAMLANDI] {len(devices_data)} cihaz ve servis kaydi olusturuldu\n")
        
    def create_appointments(self):
        """Randevu kayitlari olustur"""
        print("\n[RANDEVU] Randevu Kayitlari Olusturuluyor...")
        
        if not self.customer_ids or not self.personnel_ids:
            print("  [UYARI] Once musteri ve personel kayitlari olusturulmali!")
            return
        
        appointments_count = 0
        
        # Gelecek 2 hafta icin randevular
        for i in range(15):
            date = datetime.now() + timedelta(days=i)
            # Her gun 2-4 randevu
            for _ in range(random.randint(2, 4)):
                hour = random.randint(9, 17)
                minute = random.choice([0, 30])
                
                try:
                    customer_id = random.choice(self.customer_ids)
                    personnel_id = random.choice(self.personnel_ids)
                    service_type = random.choice([
                        "Genel Bakim",
                        "Donanim Onarimi",
                        "Yazilim Kurulumu",
                        "Veri Kurtarma",
                        "Upgrade",
                        "Danismanlik"
                    ])
                    
                    self.db.cursor.execute("""
                        INSERT INTO appointments 
                        (customer_id, personnel_id, appointment_date, appointment_time, 
                         service_type, notes, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (customer_id, personnel_id, date.strftime("%Y-%m-%d"), 
                          f"{hour:02d}:{minute:02d}", service_type, 
                          "Test randevusu", "Bekliyor"))
                    
                    appointments_count += 1
                except Exception as e:
                    print(f"  [UYARI] Randevu eklenirken hata: {str(e)}")
        
        self.db.conn.commit()
        print(f"[TAMAMLANDI] {appointments_count} randevu kaydi olusturuldu\n")
        
    def generate_statistics(self):
        """Test verileri istatistikleri"""
        print("\n" + "="*70)
        print("TEST VERILERI ISTATISTIKLERI")
        print("="*70)
        
        try:
            # Musteri sayisi
            self.db.cursor.execute("SELECT COUNT(*) FROM customers")
            customer_count = self.db.cursor.fetchone()[0]
            print(f"Toplam Musteri: {customer_count}")
            
            # Personel sayisi
            self.db.cursor.execute("SELECT COUNT(*) FROM personnel")
            personnel_count = self.db.cursor.fetchone()[0]
            print(f"Toplam Personel: {personnel_count}")
            
            # Urun sayisi ve toplam stok degeri
            self.db.cursor.execute("SELECT COUNT(*), SUM(quantity * price) FROM stock")
            product_count, stock_value = self.db.cursor.fetchone()
            print(f"Toplam Urun Cesidi: {product_count}")
            print(f"Toplam Stok Degeri: {stock_value:,.2f} TL")
            
            # Servis kayitlari
            self.db.cursor.execute("SELECT COUNT(*) FROM services")
            service_count = self.db.cursor.fetchone()[0]
            print(f"Toplam Servis Kaydi: {service_count}")
            
            # Tamamlanan servisler
            self.db.cursor.execute("SELECT COUNT(*), SUM(cost) FROM services WHERE status='Tamamlandi'")
            completed_count, completed_revenue = self.db.cursor.fetchone()
            print(f"Tamamlanan Servisler: {completed_count}")
            if completed_revenue:
                print(f"Servis Geliri: {completed_revenue:,.2f} TL")
            
            # Randevular
            self.db.cursor.execute("SELECT COUNT(*) FROM appointments")
            appointment_count = self.db.cursor.fetchone()[0]
            print(f"Toplam Randevu: {appointment_count}")
            
        except Exception as e:
            print(f"[UYARI] Istatistik hesaplanirken hata: {str(e)}")
        
        print("="*70 + "\n")
        
    def run_all(self):
        """Tum test verilerini olustur"""
        print("\n" + "="*70)
        print("KAPSAMLI TEST VERISI OLUSTURMA BASLIYOR")
        print("="*70 + "\n")
        
        start_time = datetime.now()
        
        # Sirayla tum verileri olustur
        self.create_personnel()
        self.create_customers()
        self.create_products()
        self.create_devices_and_services()
        self.create_appointments()
        
        # Istatistikleri goster
        self.generate_statistics()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("="*70)
        print(f"TUM TEST VERILERI BASARIYLA OLUSTURULDU!")
        print(f"Toplam Sure: {duration:.2f} saniye")
        print("="*70 + "\n")
        
        print("Sonraki Adimlar:")
        print("  1. Uygulamayi calistirin: python ModernDesktopApp.py")
        print("  2. Giris yapin (admin/admin veya personel e-postalari)")
        print("  3. Tum modulleri test edin")
        print("  4. Raporlari kontrol edin")
        print("  5. Yedekleme sistemini test edin\n")


if __name__ == "__main__":
    generator = ComprehensiveTestDataGenerator()
    generator.run_all()
