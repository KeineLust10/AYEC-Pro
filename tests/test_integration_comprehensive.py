# -*- coding: utf-8 -*-
"""
Kapsamlı Entegrasyon Test Suite - AYEC Pro
Tüm program işlevlerini test eder
"""

import sys
import os
import re
from datetime import datetime
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer
from src.database import Database


def _safe_identifier(name: str) -> str:
    text = str(name or "").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return text


class IntegrationTestSuite:
    """Kapsamlı entegrasyon test sınıfı"""
    
    def __init__(self):
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
        
        self.db = Database()
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": [],
            "skipped": []
        }
        self.start_time = datetime.now()
    
    def test_1_menu_navigation(self):
        """1. Menü ve Alt Menü Testleri"""
        print("\n" + "="*80)
        print("TEST 1: MENÜ VE ALT MENÜ NAVİGASYONU")
        print("="*80)
        
        try:
            from src.ui.main_window import MainWindow
            
            # Test kullanıcı verisi oluştur
            test_user = {
                'id': 1,
                'username': 'test_admin',
                'role': 'Admin'
            }
            
            print("\n[1.1] Ana pencere oluşturuluyor...")
            window = MainWindow(self.db, test_user)
            window.show()
            QTest.qWait(500)  # Pencere açılsın
            
            self.results["passed"].append("Ana pencere başarıyla oluşturuldu")
            print("  ✓ Ana pencere açıldı")
            
            # Menü öğelerini test et
            menu_items = [
                ("Dashboard", 0),
                ("Müşteriler", 1),
                ("Servisler", 2),
                ("Stok", 3),
                ("Finans", 4),
                ("Personel", 5),
                ("Ayarlar", 6)
            ]
            
            print("\n[1.2] Menü öğeleri test ediliyor...")
            for menu_name, index in menu_items:
                try:
                    if hasattr(window, 'sidebar') and hasattr(window.sidebar, 'list_widget'):
                        window.sidebar.list_widget.setCurrentRow(index)
                        QTest.qWait(200)  # Sayfa yüklensin
                        
                        self.results["passed"].append(f"Menü: {menu_name}")
                        print(f"  ✓ {menu_name} menüsü açıldı")
                    else:
                        self.results["warnings"].append(f"Menü: {menu_name} - Sidebar yapısı farklı")
                        print(f"  ! {menu_name} - Sidebar bulunamadı")
                except Exception as e:
                    self.results["failed"].append(f"Menü: {menu_name} - {str(e)}")
                    print(f"  ✗ {menu_name} hatası: {str(e)[:50]}")
            
            window.close()
            QTest.qWait(200)
            
        except Exception as e:
            self.results["failed"].append(f"Menü testi: {str(e)}")
            print(f"\n✗ Menü testi başarısız: {str(e)}")
    
    def test_2_user_authentication(self):
        """2. Kullanıcı Bilgileri Testleri"""
        print("\n" + "="*80)
        print("TEST 2: KULLANICI KİMLİK DOĞRULAMA")
        print("="*80)
        
        print("\n[2.1] Geçerli kullanıcı girişi test ediliyor...")
        
        # Admin kullanıcısı test
        admin_user = self.db.authenticate_user("admin", "admin123")
        if admin_user:
            self.results["passed"].append("Admin girişi başarılı")
            print("  ✓ Admin kullanıcısı doğrulandı")
        else:
            self.results["failed"].append("Admin girişi başarısız")
            print("  ✗ Admin kullanıcısı doğrulanamadı")
        
        print("\n[2.2] Geçersiz kullanıcı girişi test ediliyor...")
        
        # Geçersiz şifre
        invalid_user = self.db.authenticate_user("admin", "wrongpassword")
        if not invalid_user:
            self.results["passed"].append("Geçersiz şifre reddedildi")
            print("  ✓ Geçersiz şifre doğru şekilde reddedildi")
        else:
            self.results["failed"].append("Geçersiz şifre kabul edildi!")
            print("  ✗ GÜVENLİK AÇIĞI: Geçersiz şifre kabul edildi!")
        
        # Olmayan kullanıcı
        nonexistent = self.db.authenticate_user("nonexistent_user", "password")
        if not nonexistent:
            self.results["passed"].append("Olmayan kullanıcı reddedildi")
            print("  ✓ Olmayan kullanıcı doğru şekilde reddedildi")
        else:
            self.results["failed"].append("Olmayan kullanıcı kabul edildi!")
            print("  ✗ GÜVENLİK AÇIĞI: Olmayan kullanıcı kabul edildi!")
    
    def test_3_service_forms(self):
        """3. Servis Formları Testleri"""
        print("\n" + "="*80)
        print("TEST 3: SERVİS FORMLARI VE VALİDASYON")
        print("="*80)
        
        from src.utils.input_validator import validate_service_data
        
        print("\n[3.1] Geçerli servis verisi test ediliyor...")
        
        valid_service = {
            "customer_name": "Test Müşteri",
            "device_brand": "Apple",
            "device_model": "iPhone 13",
            "price": 1500.00,
            "imei": "123456789012345"
        }
        
        is_valid, errors = validate_service_data(valid_service)
        if is_valid:
            self.results["passed"].append("Geçerli servis verisi kabul edildi")
            print("  ✓ Geçerli servis verisi doğrulandı")
        else:
            self.results["failed"].append(f"Geçerli servis verisi reddedildi: {errors}")
            print(f"  ✗ Geçerli servis verisi reddedildi: {errors}")
        
        print("\n[3.2] Geçersiz servis verisi test ediliyor...")
        
        invalid_service = {
            "customer_name": "",  # Boş - geçersiz
            "device_brand": "Apple",
            "device_model": "",  # Boş - geçersiz
            "price": -100,  # Negatif - geçersiz
            "imei": "123"  # Kısa - geçersiz
        }
        
        is_valid, errors = validate_service_data(invalid_service)
        if not is_valid and len(errors) > 0:
            self.results["passed"].append(f"Geçersiz servis verisi reddedildi ({len(errors)} hata)")
            print(f"  ✓ Geçersiz servis verisi doğru şekilde reddedildi")
            print(f"    Tespit edilen hatalar: {len(errors)}")
        else:
            self.results["failed"].append("Geçersiz servis verisi kabul edildi!")
            print("  ✗ Geçersiz servis verisi kabul edildi!")
    
    def test_4_dialogs(self):
        """4. Açılır Pencere Testleri"""
        print("\n" + "="*80)
        print("TEST 4: AÇILIR PENCERELER (DIALOGS)")
        print("="*80)
        
        print("\n[4.1] Dialog import testleri...")
        
        dialogs_to_test = [
            ("add_customer_dialog", "AddCustomerDialog"),
            ("add_device_dialog", "AddDeviceDialog"),
            ("new_service_dialog", "NewServiceDialog"),
        ]
        
        for module_name, class_name in dialogs_to_test:
            try:
                module = __import__(f"src.ui.dialogs.{module_name}", fromlist=[class_name])
                dialog_class = getattr(module, class_name)
                
                self.results["passed"].append(f"Dialog: {class_name}")
                print(f"  ✓ {class_name} import edildi")
            except Exception as e:
                self.results["failed"].append(f"Dialog: {class_name} - {str(e)}")
                print(f"  ✗ {class_name} import hatası: {str(e)[:50]}")
    
    def test_5_program_startup(self):
        """5. Program Başlatma Testleri"""
        print("\n" + "="*80)
        print("TEST 5: PROGRAM BAŞLATMA VE İNİTİALİZASYON")
        print("="*80)
        
        print("\n[5.1] Veritabanı bağlantısı test ediliyor...")
        
        try:
            # Veritabanı bağlantısı
            test_db = Database()
            self.results["passed"].append("Veritabanı bağlantısı başarılı")
            print("  ✓ Veritabanı bağlantısı kuruldu")
            
            # Tablo varlık kontrolü
            tables = ["customers", "devices", "personnel", "parts", "accounting", "services"]
            print("\n[5.2] Veritabanı tabloları kontrol ediliyor...")
            
            for table in tables:
                try:
                    test_db.cursor.execute(
                        "SELECT COUNT(*) FROM {table}".format(table=_safe_identifier(table))
                    )
                    count = test_db.cursor.fetchone()[0]
                    self.results["passed"].append(f"Tablo: {table} ({count} kayıt)")
                    print(f"  ✓ {table} tablosu mevcut ({count} kayıt)")
                except Exception as e:
                    self.results["failed"].append(f"Tablo: {table} - {str(e)}")
                    print(f"  ✗ {table} tablosu hatası: {str(e)[:50]}")
            
            test_db.conn.close()
            
        except Exception as e:
            self.results["failed"].append(f"Veritabanı: {str(e)}")
            print(f"  ✗ Veritabanı hatası: {str(e)}")
        
        print("\n[5.3] Kritik modüller test ediliyor...")
        
        critical_modules = [
            "src.database",
            "src.utils.input_validator",
            "src.utils.toast_notification",
            "src.utils.security_manager",
            "src.utils.theme_manager"
        ]
        
        for module_name in critical_modules:
            try:
                __import__(module_name)
                self.results["passed"].append(f"Modül: {module_name}")
                print(f"  ✓ {module_name} yüklendi")
            except Exception as e:
                self.results["failed"].append(f"Modül: {module_name} - {str(e)}")
                print(f"  ✗ {module_name} hatası: {str(e)[:50]}")
    
    def test_6_foreign_key_constraints(self):
        """6. Foreign Key Constraints Testi"""
        print("\n" + "="*80)
        print("TEST 6: FOREIGN KEY CONSTRAINTS")
        print("="*80)
        
        print("\n[6.1] Foreign key durumu kontrol ediliyor...")
        
        try:
            self.db.cursor.execute("PRAGMA foreign_keys")
            fk_status = self.db.cursor.fetchone()[0]
            
            if fk_status == 1:
                self.results["passed"].append("Foreign key constraints aktif")
                print("  ✓ Foreign key constraints AKTİF")
            else:
                self.results["failed"].append("Foreign key constraints pasif!")
                print("  ✗ Foreign key constraints PASİF!")
        except Exception as e:
            self.results["failed"].append(f"Foreign key kontrolü: {str(e)}")
            print(f"  ✗ Foreign key kontrolü hatası: {str(e)}")
    
    def test_7_toast_notification(self):
        """7. Toast Notification Sistemi Testi"""
        print("\n" + "="*80)
        print("TEST 7: TOAST NOTIFICATION SİSTEMİ")
        print("="*80)
        
        print("\n[7.1] Toast notification modülü test ediliyor...")
        
        try:
            from src.utils.toast_notification import (
                show_success, show_error, show_warning, show_info,
                ToastNotification
            )
            
            self.results["passed"].append("Toast notification modülü import edildi")
            print("  ✓ Toast notification modülü yüklendi")
            
            # Toast sınıfı oluşturma testi
            from PyQt6.QtWidgets import QWidget
            test_widget = QWidget()
            
            toast = ToastNotification(test_widget, "Test mesajı", "success", 1000)
            self.results["passed"].append("Toast notification oluşturuldu")
            print("  ✓ Toast notification nesnesi oluşturuldu")
            
            test_widget.close()
            
        except Exception as e:
            self.results["failed"].append(f"Toast notification: {str(e)}")
            print(f"  ✗ Toast notification hatası: {str(e)}")
    
    def generate_report(self):
        """Test raporu oluştur"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        print("\n" + "="*80)
        print("KAPSAMLI ENTEGRASYON TEST RAPORU")
        print("="*80)
        
        total = len(self.results["passed"]) + len(self.results["failed"]) + \
                len(self.results["warnings"]) + len(self.results["skipped"])
        success_rate = (len(self.results["passed"]) / total * 100) if total > 0 else 0
        
        print(f"\nTest Başlangıç: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test Bitiş:     {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Toplam Süre:    {duration:.2f} saniye")
        
        print(f"\nToplam Test: {total}")
        print(f"  ✓ Başarılı: {len(self.results['passed'])} ({success_rate:.1f}%)")
        print(f"  ✗ Başarısız: {len(self.results['failed'])}")
        print(f"  ! Uyarı: {len(self.results['warnings'])}")
        print(f"  - Atlanan: {len(self.results['skipped'])}")
        
        if self.results["failed"]:
            print(f"\n❌ BAŞARISIZ TESTLER:")
            for fail in self.results["failed"]:
                print(f"  • {fail}")
        
        if self.results["warnings"]:
            print(f"\n⚠️ UYARILAR:")
            for warn in self.results["warnings"]:
                print(f"  • {warn}")
        
        # Raporu dosyaya kaydet
        report_file = f"integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"KAPSAMLI ENTEGRASYON TEST RAPORU - {datetime.now()}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Test Süresi: {duration:.2f} saniye\n")
            f.write(f"Başarı Oranı: {success_rate:.1f}%\n\n")
            
            f.write(f"BAŞARILI TESTLER ({len(self.results['passed'])}):\n")
            f.write("-" * 80 + "\n")
            for test in self.results["passed"]:
                f.write(f"  ✓ {test}\n")
            
            if self.results["failed"]:
                f.write(f"\nBAŞARISIZ TESTLER ({len(self.results['failed'])}):\n")
                f.write("-" * 80 + "\n")
                for test in self.results["failed"]:
                    f.write(f"  ✗ {test}\n")
            
            if self.results["warnings"]:
                f.write(f"\nUYARILAR ({len(self.results['warnings'])}):\n")
                f.write("-" * 80 + "\n")
                for test in self.results["warnings"]:
                    f.write(f"  ! {test}\n")
        
        print(f"\n📄 Detaylı rapor kaydedildi: {report_file}")
        print("=" * 80)
        
        return success_rate >= 85


def main():
    print("=" * 80)
    print("  PREMIUM BULUT - KAPSAMLI ENTEGRASYON TEST SİSTEMİ")
    print("=" * 80)
    print("\nTüm program işlevleri test edilecek...")
    print("Bu işlem birkaç dakika sürebilir.\n")
    
    tester = IntegrationTestSuite()
    
    try:
        # Tüm testleri çalıştır
        tester.test_5_program_startup()  # Önce başlatma testleri
        tester.test_6_foreign_key_constraints()
        tester.test_7_toast_notification()
        tester.test_2_user_authentication()
        tester.test_3_service_forms()
        tester.test_4_dialogs()
        tester.test_1_menu_navigation()  # En son UI testleri
        
        success = tester.generate_report()
        
        if success:
            print("\n✅ ENTEGRASYON TESTLERİ BAŞARILI!")
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
