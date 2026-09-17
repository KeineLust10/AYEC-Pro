# -*- coding: utf-8 -*-
"""
Input Validation Tests - AYEC Pro
Validasyon modülü testleri
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.input_validator import (
    InputValidator, ValidationError,
    validate_customer_data, validate_service_data
)


class ValidationTests:
    """Validasyon test sınıfı"""
    
    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
        self.validator = InputValidator()
    
    def test_phone_validation(self):
        """Telefon numarası validasyon testleri"""
        print("\n[TEST] Telefon Validasyonu")
        print("-" * 60)
        
        test_cases = [
            ("05551234567", True, "Geçerli telefon (0 ile)"),
            ("5551234567", True, "Geçerli telefon (0 sız)"),
            ("+905551234567", True, "Geçerli telefon (+90 ile)"),
            ("555 123 45 67", True, "Geçerli telefon (boşluklu)"),
            ("0555-123-45-67", True, "Geçerli telefon (tire ile)"),
            ("123", False, "Geçersiz (çok kısa)"),
            ("05551234", False, "Geçersiz (eksik hane)"),
            ("abc", False, "Geçersiz (harf)"),
            ("", False, "Geçersiz (boş)"),
        ]
        
        for phone, should_pass, description in test_cases:
            is_valid, msg = self.validator.validate_phone(phone)
            
            if (is_valid and should_pass) or (not is_valid and not should_pass):
                self.results["passed"].append(f"Telefon: {description}")
                print(f"  [✓] {description}: '{phone}'")
            else:
                self.results["failed"].append(f"Telefon: {description} - Beklenen: {should_pass}, Gerçek: {is_valid}")
                print(f"  [✗] {description}: '{phone}' - {msg}")
    
    def test_email_validation(self):
        """E-posta validasyon testleri"""
        print("\n[TEST] E-posta Validasyonu")
        print("-" * 60)
        
        test_cases = [
            ("test@example.com", True, "Geçerli e-posta"),
            ("user.name@domain.co.uk", True, "Geçerli e-posta (noktalı)"),
            ("user+tag@example.com", True, "Geçerli e-posta (+ ile)"),
            ("invalid@", False, "Geçersiz (domain eksik)"),
            ("@example.com", False, "Geçersiz (kullanıcı eksik)"),
            ("notanemail", False, "Geçersiz (@ yok)"),
            ("", True, "Boş (allow_empty=True)"),
        ]
        
        for email, should_pass, description in test_cases:
            is_valid, msg = self.validator.validate_email(email, allow_empty=True)
            
            if (is_valid and should_pass) or (not is_valid and not should_pass):
                self.results["passed"].append(f"E-posta: {description}")
                print(f"  [✓] {description}: '{email}'")
            else:
                self.results["failed"].append(f"E-posta: {description}")
                print(f"  [✗] {description}: '{email}' - {msg}")
    
    def test_tc_validation(self):
        """TC Kimlik No validasyon testleri"""
        print("\n[TEST] TC Kimlik No Validasyonu")
        print("-" * 60)
        
        test_cases = [
            ("12345678901", False, "Geçersiz TC (algoritma hatası)"),
            ("00000000000", False, "Geçersiz TC (ilk hane 0)"),
            ("123", False, "Geçersiz TC (çok kısa)"),
            ("", True, "Boş (allow_empty=True)"),
        ]
        
        for tc, should_pass, description in test_cases:
            is_valid, msg = self.validator.validate_tc_no(tc, allow_empty=True)
            
            if (is_valid and should_pass) or (not is_valid and not should_pass):
                self.results["passed"].append(f"TC: {description}")
                print(f"  [✓] {description}: '{tc}'")
            else:
                self.results["failed"].append(f"TC: {description}")
                print(f"  [✗] {description}: '{tc}' - {msg}")
    
    def test_price_validation(self):
        """Fiyat validasyon testleri"""
        print("\n[TEST] Fiyat Validasyonu")
        print("-" * 60)
        
        test_cases = [
            (100, True, "Geçerli fiyat (pozitif)"),
            (0, True, "Geçerli fiyat (sıfır, allow_zero=True)"),
            (99.99, True, "Geçerli fiyat (ondalıklı)"),
            (-50, False, "Geçersiz fiyat (negatif)"),
            ("abc", False, "Geçersiz fiyat (harf)"),
            (1000000000, False, "Geçersiz fiyat (çok büyük)"),
        ]
        
        for price, should_pass, description in test_cases:
            is_valid, msg = self.validator.validate_price(price, allow_zero=True, allow_negative=False)
            
            if (is_valid and should_pass) or (not is_valid and not should_pass):
                self.results["passed"].append(f"Fiyat: {description}")
                print(f"  [✓] {description}: {price}")
            else:
                self.results["failed"].append(f"Fiyat: {description}")
                print(f"  [✗] {description}: {price} - {msg}")
    
    def test_integer_validation(self):
        """Integer validasyon testleri"""
        print("\n[TEST] Integer Validasyonu")
        print("-" * 60)
        
        test_cases = [
            (10, 0, 100, True, "Geçerli (aralıkta)"),
            (0, 0, 100, True, "Geçerli (minimum)"),
            (100, 0, 100, True, "Geçerli (maksimum)"),
            (-5, 0, 100, False, "Geçersiz (minimum altında)"),
            (150, 0, 100, False, "Geçersiz (maksimum üstünde)"),
            ("abc", 0, 100, False, "Geçersiz (harf)"),
            (50.5, 0, 100, True, "Geçerli (float'tan int'e dönüşüm)"),
        ]
        
        for value, min_val, max_val, should_pass, description in test_cases:
            is_valid, msg = self.validator.validate_integer(value, "Test", min_value=min_val, max_value=max_val)
            
            if (is_valid and should_pass) or (not is_valid and not should_pass):
                self.results["passed"].append(f"Integer: {description}")
                print(f"  [✓] {description}: {value}")
            else:
                self.results["failed"].append(f"Integer: {description}")
                print(f"  [✗] {description}: {value} - {msg}")
    
    def test_string_validation(self):
        """String validasyon testleri"""
        print("\n[TEST] String Validasyonu")
        print("-" * 60)
        
        test_cases = [
            ("Test", 1, 10, True, "Geçerli (aralıkta)"),
            ("A", 1, 10, True, "Geçerli (minimum)"),
            ("1234567890", 1, 10, True, "Geçerli (maksimum)"),
            ("", 1, 10, False, "Geçersiz (boş)"),
            ("12345678901", 1, 10, False, "Geçersiz (çok uzun)"),
        ]
        
        for value, min_len, max_len, should_pass, description in test_cases:
            is_valid, msg = self.validator.validate_string(value, "Test", min_length=min_len, max_length=max_len)
            
            if (is_valid and should_pass) or (not is_valid and not should_pass):
                self.results["passed"].append(f"String: {description}")
                print(f"  [✓] {description}: '{value}'")
            else:
                self.results["failed"].append(f"String: {description}")
                print(f"  [✗] {description}: '{value}' - {msg}")
    
    def test_sanitize(self):
        """String sanitization testleri"""
        print("\n[TEST] String Sanitization")
        print("-" * 60)
        
        test_cases = [
            ("<script>alert('xss')</script>", "scriptalert('xss')/script", "XSS temizleme"),
            ("'; DROP TABLE users; --", " DROP TABLE users ", "SQL Injection temizleme"),
            ("Normal text", "Normal text", "Normal metin (değişmez)"),
            ("Test /* comment */ data", "Test  comment  data", "SQL comment temizleme"),
        ]
        
        for input_str, expected_contains, description in test_cases:
            result = self.validator.sanitize_string(input_str)
            
            if expected_contains in result or (not expected_contains and not result):
                self.results["passed"].append(f"Sanitize: {description}")
                print(f"  [✓] {description}")
            else:
                self.results["failed"].append(f"Sanitize: {description}")
                print(f"  [✗] {description}: '{result}'")
    
    def test_customer_data_validation(self):
        """Müşteri verisi toplu validasyon"""
        print("\n[TEST] Müşteri Verisi Validasyonu")
        print("-" * 60)
        
        # Geçerli müşteri
        valid_customer = {
            "name": "Ahmet Yılmaz",
            "phone": "05551234567",
            "email": "ahmet@example.com"
        }
        
        is_valid, errors = validate_customer_data(valid_customer)
        if is_valid:
            self.results["passed"].append("Müşteri: Geçerli veri")
            print("  [✓] Geçerli müşteri verisi")
        else:
            self.results["failed"].append(f"Müşteri: Geçerli veri başarısız - {errors}")
            print(f"  [✗] Geçerli müşteri verisi başarısız: {errors}")
        
        # Geçersiz müşteri (telefon eksik)
        invalid_customer = {
            "name": "Mehmet Demir",
            "phone": "123",  # Geçersiz
            "email": "invalid-email"  # Geçersiz
        }
        
        is_valid, errors = validate_customer_data(invalid_customer)
        if not is_valid and len(errors) > 0:
            self.results["passed"].append("Müşteri: Geçersiz veri yakalandı")
            print(f"  [✓] Geçersiz müşteri verisi yakalandı: {len(errors)} hata")
        else:
            self.results["failed"].append("Müşteri: Geçersiz veri yakalanmadı")
            print("  [✗] Geçersiz müşteri verisi yakalanmadı")
    
    def generate_report(self):
        """Test raporu oluştur"""
        print("\n" + "=" * 80)
        print("VALIDASYON TEST RAPORU")
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
        
        # Raporu dosyaya kaydet
        report_file = f"validation_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"VALIDASYON TEST RAPORU - {datetime.now()}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Başarı Oranı: {success_rate:.1f}%\n\n")
            
            f.write(f"BAŞARILI TESTLER ({len(self.results['passed'])}):\n")
            for test in self.results["passed"]:
                f.write(f"  ✓ {test}\n")
            
            if self.results["failed"]:
                f.write(f"\nBAŞARISIZ TESTLER ({len(self.results['failed'])}):\n")
                for test in self.results["failed"]:
                    f.write(f"  ✗ {test}\n")
        
        print(f"\n📄 Rapor kaydedildi: {report_file}")
        print("=" * 80)
        
        return success_rate >= 90


def main():
    print("=" * 80)
    print("  PREMIUM BULUT - VALIDASYON TEST SİSTEMİ")
    print("=" * 80)
    
    tester = ValidationTests()
    
    try:
        tester.test_phone_validation()
        tester.test_email_validation()
        tester.test_tc_validation()
        tester.test_price_validation()
        tester.test_integer_validation()
        tester.test_string_validation()
        tester.test_sanitize()
        tester.test_customer_data_validation()
        
        success = tester.generate_report()
        
        if success:
            print("\n✅ VALIDASYON TESTLERİ BAŞARILI!")
            return 0
        else:
            print("\n⚠️ BAZI TESTLER BAŞARISIZ!")
            return 1
            
    except Exception as e:
        print(f"\n❌ KRITIK HATA: {str(e)}")
        import traceback
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    sys.exit(main())
