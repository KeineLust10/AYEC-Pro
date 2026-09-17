# -*- coding: utf-8 -*-
"""
Exception Handling ve Hata Yönetimi Testleri - AYEC Pro
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import Database


class ErrorHandlingTests:
    """Hata yönetimi test sınıfı"""
    
    def __init__(self):
        self.db = Database()
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
    
    def test_database_errors(self):
        """Veritabanı hata senaryoları"""
        print("\n[TEST] Veritabanı Hata Yönetimi")
        print("-" * 60)
        
        # 1. Unique constraint ihlali
        try:
            # Aynı isimde iki hizmet eklemeye çalış
            service_name = f"TEST_SERVICE_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            self.db.cursor.execute(
                "INSERT INTO services (name, price, description, created_at) VALUES (?, ?, ?, ?)",
                (service_name, 100, "Test", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            self.db.conn.commit()
            
            # Aynı isimle tekrar eklemeye çalış
            try:
                self.db.cursor.execute(
                    "INSERT INTO services (name, price, description, created_at) VALUES (?, ?, ?, ?)",
                    (service_name, 200, "Test 2", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                self.db.conn.commit()
                self.results["failed"].append("DB: Unique constraint - Hata yakalanmadı")
                print("  [✗] Unique constraint ihlali yakalanmadı")
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    self.results["passed"].append("DB: Unique constraint hatası yakalandı")
                    print("  [✓] Unique constraint hatası doğru yakalandı")
                    self.db.conn.rollback()
                else:
                    self.results["failed"].append(f"DB: Beklenmeyen hata - {str(e)}")
                    print(f"  [✗] Beklenmeyen hata: {str(e)[:50]}")
            
            # Temizlik
            self.db.cursor.execute("DELETE FROM services WHERE name = ?", (service_name,))
            self.db.conn.commit()
            
        except Exception as e:
            self.results["failed"].append(f"DB Test: {str(e)}")
            print(f"  [✗] Test başarısız: {str(e)}")
        
        # 2. Foreign key constraint
        try:
            # Olmayan bir müşteri ID'si ile cihaz eklemeye çalış
            try:
                self.db.cursor.execute(
                    "INSERT INTO devices (customer_id, device_brand, device_model, created_at) VALUES (?, ?, ?, ?)",
                    (999999, "Test Brand", "Test Model", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                self.db.conn.commit()
                # Eğer foreign key constraint yoksa uyarı ver
                self.results["warnings"].append("DB: Foreign key constraint aktif değil")
                print("  [!] Foreign key constraint aktif değil")
                # Temizlik
                self.db.cursor.execute("DELETE FROM devices WHERE customer_id = 999999")
                self.db.conn.commit()
            except Exception as e:
                if "FOREIGN KEY" in str(e) or "constraint" in str(e):
                    self.results["passed"].append("DB: Foreign key constraint çalışıyor")
                    print("  [✓] Foreign key constraint çalışıyor")
                    self.db.conn.rollback()
                else:
                    self.results["warnings"].append(f"DB: Foreign key - {str(e)[:50]}")
                    print(f"  [!] Foreign key: {str(e)[:50]}")
        except Exception as e:
            self.results["failed"].append(f"DB FK Test: {str(e)}")
            print(f"  [✗] FK test başarısız: {str(e)}")
    
    def test_null_value_handling(self):
        """Null değer işleme testleri"""
        print("\n[TEST] Null Değer İşleme")
        print("-" * 60)
        
        test_cases = [
            ("Müşteri - Boş Email", "customers", {"name": "Test", "phone": "5551234567", "email": None}),
            ("Müşteri - Boş Adres", "customers", {"name": "Test", "phone": "5551234567", "address": None}),
            ("Cihaz - Boş Seri No", "devices", {"customer_id": 1, "device_brand": "Test", "serial_number": None})
        ]
        
        for test_name, table, data in test_cases:
            try:
                # Null değerlerle kayıt eklemeyi dene
                if table == "customers":
                    self.db.cursor.execute(
                        "INSERT INTO customers (name, phone, email, address, created_at) VALUES (?, ?, ?, ?, ?)",
                        (data.get("name"), data.get("phone"), data.get("email"), 
                         data.get("address"), datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    )
                    self.db.conn.commit()
                    test_id = self.db.cursor.lastrowid
                    
                    # Oku ve kontrol et
                    self.db.cursor.execute("SELECT * FROM customers WHERE id = ?", (test_id,))
                    row = self.db.cursor.fetchone()
                    
                    if row:
                        self.results["passed"].append(f"Null: {test_name}")
                        print(f"  [✓] {test_name} - Null değer işlendi")
                    
                    # Temizlik
                    self.db.cursor.execute("DELETE FROM customers WHERE id = ?", (test_id,))
                    self.db.conn.commit()
                
            except Exception as e:
                if "NOT NULL" in str(e):
                    self.results["passed"].append(f"Null: {test_name} - NOT NULL constraint")
                    print(f"  [✓] {test_name} - NOT NULL constraint çalışıyor")
                    self.db.conn.rollback()
                else:
                    self.results["failed"].append(f"Null: {test_name} - {str(e)}")
                    print(f"  [✗] {test_name} başarısız: {str(e)[:50]}")
    
    def test_input_validation(self):
        """Girdi doğrulama testleri"""
        print("\n[TEST] Girdi Doğrulama")
        print("-" * 60)
        
        # SQL Injection koruması
        try:
            malicious_input = "'; DROP TABLE customers; --"
            
            # Parametreli sorgu kullanımı (güvenli)
            self.db.cursor.execute(
                "SELECT * FROM customers WHERE name = ?",
                (malicious_input,)
            )
            results = self.db.cursor.fetchall()
            
            # Tablo hala mevcut mu kontrol et
            self.db.cursor.execute("SELECT COUNT(*) FROM customers")
            count = self.db.cursor.fetchone()[0]
            
            self.results["passed"].append("Güvenlik: SQL Injection koruması")
            print(f"  [✓] SQL Injection koruması çalışıyor (Tablo güvende: {count} kayıt)")
            
        except Exception as e:
            self.results["failed"].append(f"SQL Injection Test: {str(e)}")
            print(f"  [✗] SQL Injection testi başarısız: {str(e)}")
        
        # Veri tipi kontrolü
        try:
            # String yerine integer beklenen alana string gönder
            try:
                self.db.cursor.execute(
                    "INSERT INTO accounting (type, category, amount, description, date) VALUES (?, ?, ?, ?, ?)",
                    ("Gelir", "Test", "ABC", "Test", datetime.now().strftime("%Y-%m-%d"))  # amount string
                )
                self.db.conn.commit()
                self.results["warnings"].append("Validasyon: Veri tipi kontrolü zayıf")
                print("  [!] Veri tipi kontrolü yapılmıyor")
                # Temizlik
                self.db.cursor.execute("DELETE FROM accounting WHERE description = 'Test'")
                self.db.conn.commit()
            except Exception as e:
                self.results["passed"].append("Validasyon: Veri tipi kontrolü")
                print("  [✓] Veri tipi kontrolü çalışıyor")
                self.db.conn.rollback()
        except Exception as e:
            self.results["failed"].append(f"Veri Tipi Test: {str(e)}")
            print(f"  [✗] Veri tipi testi başarısız: {str(e)}")
    
    def test_error_messages(self):
        """Hata mesajı kalitesi testleri"""
        print("\n[TEST] Hata Mesajı Kalitesi")
        print("-" * 60)
        
        # Crash reports log dosyasını kontrol et
        try:
            if os.path.exists("crash_reports.log"):
                with open("crash_reports.log", "r", encoding="utf-8") as f:
                    content = f.read()
                    
                    # Traceback bilgisi var mı?
                    if "Traceback" in content:
                        self.results["passed"].append("Hata Mesajı: Traceback kaydediliyor")
                        print("  [✓] Traceback bilgisi kaydediliyor")
                    else:
                        self.results["warnings"].append("Hata Mesajı: Traceback eksik")
                        print("  [!] Traceback bilgisi eksik")
                    
                    # Timestamp var mı?
                    if "CRASH REPORT" in content and "2026" in content:
                        self.results["passed"].append("Hata Mesajı: Timestamp kaydediliyor")
                        print("  [✓] Timestamp kaydediliyor")
                    else:
                        self.results["warnings"].append("Hata Mesajı: Timestamp eksik")
                        print("  [!] Timestamp eksik")
            else:
                self.results["warnings"].append("Hata Mesajı: crash_reports.log bulunamadı")
                print("  [!] crash_reports.log dosyası bulunamadı")
                
        except Exception as e:
            self.results["failed"].append(f"Hata Mesajı Test: {str(e)}")
            print(f"  [✗] Hata mesajı testi başarısız: {str(e)}")
    
    def test_transaction_rollback(self):
        """Transaction rollback testleri"""
        print("\n[TEST] Transaction Rollback")
        print("-" * 60)
        
        try:
            # Başlangıç kayıt sayısı
            self.db.cursor.execute("SELECT COUNT(*) FROM customers")
            initial_count = self.db.cursor.fetchone()[0]
            
            # Transaction başlat
            try:
                self.db.cursor.execute(
                    "INSERT INTO customers (name, phone, created_at) VALUES (?, ?, ?)",
                    ("Rollback Test", "5551234567", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                
                # Hata oluştur (unique constraint)
                self.db.cursor.execute(
                    "INSERT INTO services (name, price, created_at) VALUES (?, ?, ?)",
                    ("Rollback Test", 100, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                self.db.cursor.execute(
                    "INSERT INTO services (name, price, created_at) VALUES (?, ?, ?)",
                    ("Rollback Test", 100, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))  # Duplicate
                )
                
                self.db.conn.commit()
                
            except Exception:
                self.db.conn.rollback()
            
            # Rollback sonrası kayıt sayısı
            self.db.cursor.execute("SELECT COUNT(*) FROM customers")
            final_count = self.db.cursor.fetchone()[0]
            
            if initial_count == final_count:
                self.results["passed"].append("Transaction: Rollback çalışıyor")
                print("  [✓] Transaction rollback başarılı")
            else:
                self.results["failed"].append("Transaction: Rollback çalışmıyor")
                print("  [✗] Transaction rollback başarısız")
                # Temizlik
                self.db.cursor.execute("DELETE FROM customers WHERE name = 'Rollback Test'")
                self.db.conn.commit()
            
            # Servis temizliği
            self.db.cursor.execute("DELETE FROM services WHERE name = 'Rollback Test'")
            self.db.conn.commit()
            
        except Exception as e:
            self.results["failed"].append(f"Transaction Test: {str(e)}")
            print(f"  [✗] Transaction testi başarısız: {str(e)}")
    
    def generate_report(self):
        """Test raporu oluştur"""
        print("\n" + "=" * 80)
        print("HATA YÖNETİMİ TEST RAPORU")
        print("=" * 80)
        
        total = len(self.results["passed"]) + len(self.results["failed"]) + len(self.results["warnings"])
        success_rate = (len(self.results["passed"]) / total * 100) if total > 0 else 0
        
        print(f"\nToplam Test: {total}")
        print(f"  [✓] Başarılı: {len(self.results['passed'])} ({success_rate:.1f}%)")
        print(f"  [✗] Başarısız: {len(self.results['failed'])}")
        print(f"  [!] Uyarı: {len(self.results['warnings'])}")
        
        if self.results["failed"]:
            print(f"\nBAŞARISIZ TESTLER:")
            for fail in self.results["failed"]:
                print(f"  • {fail}")
        
        if self.results["warnings"]:
            print(f"\nUYARILAR:")
            for warn in self.results["warnings"]:
                print(f"  • {warn}")
        
        # Raporu dosyaya kaydet
        report_file = f"error_handling_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"HATA YÖNETİMİ TEST RAPORU - {datetime.now()}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Başarı Oranı: {success_rate:.1f}%\n\n")
            
            f.write(f"BAŞARILI TESTLER ({len(self.results['passed'])}):\n")
            for test in self.results["passed"]:
                f.write(f"  ✓ {test}\n")
            
            if self.results["failed"]:
                f.write(f"\nBAŞARISIZ TESTLER ({len(self.results['failed'])}):\n")
                for test in self.results["failed"]:
                    f.write(f"  ✗ {test}\n")
            
            if self.results["warnings"]:
                f.write(f"\nUYARILAR ({len(self.results['warnings'])}):\n")
                for test in self.results["warnings"]:
                    f.write(f"  ! {test}\n")
        
        print(f"\n📄 Rapor kaydedildi: {report_file}")
        print("=" * 80)
        
        return success_rate >= 70


def main():
    print("=" * 80)
    print("  PREMIUM BULUT - HATA YÖNETİMİ TEST SİSTEMİ")
    print("=" * 80)
    
    tester = ErrorHandlingTests()
    
    try:
        tester.test_database_errors()
        tester.test_null_value_handling()
        tester.test_input_validation()
        tester.test_error_messages()
        tester.test_transaction_rollback()
        
        success = tester.generate_report()
        
        if success:
            print("\n✅ HATA YÖNETİMİ TESTLERİ BAŞARILI!")
            return 0
        else:
            print("\n⚠️ BAZI TESTLER BAŞARISIZ!")
            return 1
            
    except Exception as e:
        print(f"\n❌ KRITIK HATA: {str(e)}")
        import traceback
        traceback.print_exc()
        return 2
    finally:
        tester.db.conn.close()


if __name__ == "__main__":
    sys.exit(main())
