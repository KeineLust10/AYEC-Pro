# -*- coding: utf-8 -*-

import unittest
import sys
import os

# Yolu ayarla
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.input_validator import InputValidator

class TestInputValidatorComprehensive(unittest.TestCase):
    
    def setUp(self):
        self.validator = InputValidator()

    def test_phone_validation(self):
        # Geçerli Numaralar
        self.assertTrue(self.validator.validate_phone("0555 123 45 67")[0])
        self.assertTrue(self.validator.validate_phone("5551234567")[0])
        self.assertTrue(self.validator.validate_phone("+905551234567")[0])
        
        # Geçersiz Numaralar
        self.assertFalse(self.validator.validate_phone("123")[0])
        self.assertFalse(self.validator.validate_phone("abc")[0])
        self.assertFalse(self.validator.validate_phone(None)[0])

    def test_email_validation(self):
        # Geçerli
        self.assertTrue(self.validator.validate_email("test@example.com")[0])
        self.assertTrue(self.validator.validate_email("user.name@domain.co.uk")[0])
        
        # Geçersiz
        self.assertFalse(self.validator.validate_email("test")[0])
        self.assertFalse(self.validator.validate_email("test@")[0])
        self.assertFalse(self.validator.validate_email("@test.com")[0])

    def test_tc_validation(self):
        # validate_tc_no metodunu test et
        self.assertFalse(self.validator.validate_tc_no("123")[0])
        self.assertFalse(self.validator.validate_tc_no("a"*11)[0])
        self.assertFalse(self.validator.validate_tc_no("01234567890")[0]) # 0 ile başlayamaz

    def test_text_sanitization(self):
        # sanitize_string metodunu test et
        dirty_input = "<script>alert('xss')</script>"
        clean_input = self.validator.sanitize_string(dirty_input)
        self.assertNotIn("<script>", clean_input)
        
        sql_input = "DROP TABLE users; --"
        clean_sql = self.validator.sanitize_string(sql_input)
        # Sadece özel karakterlerin temizlendiğini kontrol edelim, SQL parser değiliz
        self.assertNotIn("--", clean_sql)
        self.assertNotIn(";", clean_sql)

    def test_price_validation(self):
        self.assertTrue(self.validator.validate_price("100")[0])
        self.assertTrue(self.validator.validate_price("100.50")[0])
        self.assertTrue(self.validator.validate_price(500)[0])
        
        self.assertFalse(self.validator.validate_price("-100")[0])
        self.assertFalse(self.validator.validate_price("abc")[0])

if __name__ == '__main__':
    unittest.main()
