# -*- coding: utf-8 -*-
"""
Input Validation Module - AYEC Pro
Kapsamlı veri tipi ve format validasyonu
"""

import re
from datetime import datetime
from typing import Any, Tuple, Optional


class ValidationError(Exception):
    """Validasyon hatası için özel exception"""
    pass


class InputValidator:
    """
    Tüm kullanıcı girişlerini doğrulayan merkezi validasyon sınıfı
    """
    
    # Regex pattern'leri
    PHONE_PATTERN = re.compile(r'^(\+90|0)?5\d{9}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    TC_PATTERN = re.compile(r'^\d{11}$')
    TAX_ID_PATTERN = re.compile(r'^\d{10}$')
    IBAN_PATTERN = re.compile(r'^TR\d{24}$')
    IMEI_PATTERN = re.compile(r'^\d{15}$')
    
    @staticmethod
    def validate_required(value: Any, field_name: str) -> Tuple[bool, str]:
        """
        Zorunlu alan kontrolü
        
        Args:
            value: Kontrol edilecek değer
            field_name: Alan adı (hata mesajı için)
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return False, f"{field_name} alanı boş bırakılamaz."
        return True, ""
    
    @staticmethod
    def validate_string(value: str, field_name: str, min_length: int = 1, 
                       max_length: int = 255, allow_empty: bool = False) -> Tuple[bool, str]:
        """
        String validasyonu
        
        Args:
            value: Kontrol edilecek string
            field_name: Alan adı
            min_length: Minimum uzunluk
            max_length: Maksimum uzunluk
            allow_empty: Boş değere izin ver
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if not allow_empty and not value:
            return False, f"{field_name} boş bırakılamaz."
        
        if value and not isinstance(value, str):
            return False, f"{field_name} metin olmalıdır."
        
        if value and len(value) < min_length:
            return False, f"{field_name} en az {min_length} karakter olmalıdır."
        
        if value and len(value) > max_length:
            return False, f"{field_name} en fazla {max_length} karakter olabilir."
        
        return True, ""
    
    @staticmethod
    def validate_integer(value: Any, field_name: str, min_value: Optional[int] = None,
                        max_value: Optional[int] = None) -> Tuple[bool, str]:
        """
        Integer validasyonu
        
        Args:
            value: Kontrol edilecek değer
            field_name: Alan adı
            min_value: Minimum değer
            max_value: Maksimum değer
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return False, f"{field_name} geçerli bir tam sayı olmalıdır."
        
        if min_value is not None and int_value < min_value:
            return False, f"{field_name} en az {min_value} olmalıdır."
        
        if max_value is not None and int_value > max_value:
            return False, f"{field_name} en fazla {max_value} olabilir."
        
        return True, ""
    
    @staticmethod
    def validate_float(value: Any, field_name: str, min_value: Optional[float] = None,
                      max_value: Optional[float] = None, decimals: int = 2) -> Tuple[bool, str]:
        """
        Float/Decimal validasyonu
        
        Args:
            value: Kontrol edilecek değer
            field_name: Alan adı
            min_value: Minimum değer
            max_value: Maksimum değer
            decimals: Ondalık basamak sayısı
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        _ = decimals
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            return False, f"{field_name} geçerli bir sayı olmalıdır."
        
        if min_value is not None and float_value < min_value:
            return False, f"{field_name} en az {min_value} olmalıdır."
        
        if max_value is not None and float_value > max_value:
            return False, f"{field_name} en fazla {max_value} olabilir."
        
        return True, ""
    
    @staticmethod
    def validate_phone(phone: str, field_name: str = "Telefon") -> Tuple[bool, str]:
        """
        Türk telefon numarası validasyonu
        
        Geçerli formatlar:
        - 05551234567
        - 5551234567
        - +905551234567
        
        Args:
            phone: Telefon numarası
            field_name: Alan adı
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if not phone:
            return False, f"{field_name} boş bırakılamaz."
        
        # Boşlukları ve tire işaretlerini temizle
        clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        if not InputValidator.PHONE_PATTERN.match(clean_phone):
            return False, f"{field_name} geçerli bir Türk telefon numarası olmalıdır (örn: 05551234567)."
        
        return True, ""
    
    @staticmethod
    def validate_email(email: str, field_name: str = "E-posta", allow_empty: bool = True) -> Tuple[bool, str]:
        """
        E-posta validasyonu
        
        Args:
            email: E-posta adresi
            field_name: Alan adı
            allow_empty: Boş değere izin ver
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if not email:
            if allow_empty:
                return True, ""
            return False, f"{field_name} boş bırakılamaz."
        
        if not InputValidator.EMAIL_PATTERN.match(email):
            return False, f"{field_name} geçerli bir e-posta adresi olmalıdır (örn: ornek@mail.com)."
        
        return True, ""
    
    @staticmethod
    def validate_tc_no(tc_no: str, field_name: str = "TC Kimlik No", allow_empty: bool = True) -> Tuple[bool, str]:
        """
        TC Kimlik No validasyonu
        
        Args:
            tc_no: TC Kimlik numarası
            field_name: Alan adı
            allow_empty: Boş değere izin ver
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if not tc_no:
            if allow_empty:
                return True, ""
            return False, f"{field_name} boş bırakılamaz."
        
        if not InputValidator.TC_PATTERN.match(tc_no):
            return False, f"{field_name} 11 haneli olmalıdır."
        
        # TC Kimlik No algoritması kontrolü
        try:
            digits = [int(d) for d in tc_no]
            
            # İlk hane 0 olamaz
            if digits[0] == 0:
                return False, f"{field_name} geçersiz (ilk hane 0 olamaz)."
            
            # 10. hane kontrolü
            sum_odd = sum(digits[0:9:2])
            sum_even = sum(digits[1:8:2])
            if (sum_odd * 7 - sum_even) % 10 != digits[9]:
                return False, f"{field_name} geçersiz."
            
            # 11. hane kontrolü
            if sum(digits[0:10]) % 10 != digits[10]:
                return False, f"{field_name} geçersiz."
            
        except Exception:
            return False, f"{field_name} geçersiz."
        
        return True, ""
    
    @staticmethod
    def validate_tax_id(tax_id: str, field_name: str = "Vergi No", allow_empty: bool = True) -> Tuple[bool, str]:
        """
        Vergi numarası validasyonu
        
        Args:
            tax_id: Vergi numarası
            field_name: Alan adı
            allow_empty: Boş değere izin ver
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if not tax_id:
            if allow_empty:
                return True, ""
            return False, f"{field_name} boş bırakılamaz."
        
        if not InputValidator.TAX_ID_PATTERN.match(tax_id):
            return False, f"{field_name} 10 haneli olmalıdır."
        
        return True, ""
    
    @staticmethod
    def validate_iban(iban: str, field_name: str = "IBAN", allow_empty: bool = True) -> Tuple[bool, str]:
        """
        IBAN validasyonu
        
        Args:
            iban: IBAN numarası
            field_name: Alan adı
            allow_empty: Boş değere izin ver
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if not iban:
            if allow_empty:
                return True, ""
            return False, f"{field_name} boş bırakılamaz."
        
        # Boşlukları temizle
        clean_iban = iban.replace(" ", "").upper()
        
        if not InputValidator.IBAN_PATTERN.match(clean_iban):
            return False, f"{field_name} geçerli bir Türk IBAN'ı olmalıdır (TR + 24 hane)."
        
        return True, ""
    
    @staticmethod
    def validate_imei(imei: str, field_name: str = "IMEI", allow_empty: bool = True) -> Tuple[bool, str]:
        """
        IMEI numarası validasyonu
        
        Args:
            imei: IMEI numarası
            field_name: Alan adı
            allow_empty: Boş değere izin ver
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if not imei:
            if allow_empty:
                return True, ""
            return False, f"{field_name} boş bırakılamaz."
        
        if not InputValidator.IMEI_PATTERN.match(imei):
            return False, f"{field_name} 15 haneli olmalıdır."
        
        return True, ""
    
    @staticmethod
    def validate_date(date_str: str, field_name: str = "Tarih", 
                     date_format: str = "%Y-%m-%d", allow_empty: bool = False) -> Tuple[bool, str]:
        """
        Tarih validasyonu
        
        Args:
            date_str: Tarih string'i
            field_name: Alan adı
            date_format: Beklenen tarih formatı
            allow_empty: Boş değere izin ver
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if not date_str:
            if allow_empty:
                return True, ""
            return False, f"{field_name} boş bırakılamaz."
        
        try:
            datetime.strptime(date_str, date_format)
            return True, ""
        except ValueError:
            return False, f"{field_name} geçerli bir tarih olmalıdır (format: {date_format})."
    
    @staticmethod
    def validate_price(price: Any, field_name: str = "Fiyat", 
                      allow_zero: bool = True, allow_negative: bool = False) -> Tuple[bool, str]:
        """
        Fiyat validasyonu
        
        Args:
            price: Fiyat değeri
            field_name: Alan adı
            allow_zero: Sıfır değere izin ver
            allow_negative: Negatif değere izin ver
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        try:
            price_value = float(price)
        except (ValueError, TypeError):
            return False, f"{field_name} geçerli bir sayı olmalıdır."
        
        if not allow_zero and price_value == 0:
            return False, f"{field_name} sıfır olamaz."
        
        if not allow_negative and price_value < 0:
            return False, f"{field_name} negatif olamaz."
        
        if price_value > 999999999:
            return False, f"{field_name} çok büyük bir değer."
        
        return True, ""
    
    @staticmethod
    def validate_stock(stock: Any, field_name: str = "Stok") -> Tuple[bool, str]:
        """
        Stok miktarı validasyonu
        
        Args:
            stock: Stok miktarı
            field_name: Alan adı
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        return InputValidator.validate_integer(stock, field_name, min_value=0, max_value=999999)
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """
        String'i temizle (XSS, SQL Injection koruması)
        
        Args:
            value: Temizlenecek string
            
        Returns:
            Temizlenmiş string
        """
        if not value:
            return ""
        
        # Tehlikeli karakterleri temizle
        dangerous_chars = ['<', '>', '"', "'", ';', '--', '/*', '*/']
        cleaned = str(value)
        
        for char in dangerous_chars:
            cleaned = cleaned.replace(char, '')
        
        return cleaned.strip()
    
    @staticmethod
    def validate_choice(value: Any, choices: list, field_name: str) -> Tuple[bool, str]:
        """
        Seçim validasyonu (dropdown, radio button vb.)
        
        Args:
            value: Seçilen değer
            choices: Geçerli seçenekler listesi
            field_name: Alan adı
            
        Returns:
            (başarılı_mı, hata_mesajı)
        """
        if value not in choices:
            return False, f"{field_name} geçersiz. Geçerli seçenekler: {', '.join(map(str, choices))}"
        
        return True, ""


# Kullanım kolaylığı için yardımcı fonksiyonlar
def validate_and_raise(is_valid: bool, error_message: str):
    """
    Validasyon başarısızsa exception fırlat
    
    Args:
        is_valid: Validasyon sonucu
        error_message: Hata mesajı
        
    Raises:
        ValidationError: Validasyon başarısızsa
    """
    if not is_valid:
        raise ValidationError(error_message)


def validate_customer_data(data: dict) -> Tuple[bool, list]:
    """
    Müşteri verisi toplu validasyonu
    
    Args:
        data: Müşteri verisi dictionary
        
    Returns:
        (başarılı_mı, hata_listesi)
    """
    errors = []
    validator = InputValidator()
    
    # Zorunlu alanlar
    is_valid, msg = validator.validate_required(data.get('name'), 'Müşteri Adı')
    if not is_valid:
        errors.append(msg)
    
    is_valid, msg = validator.validate_phone(data.get('phone', ''), 'Telefon')
    if not is_valid:
        errors.append(msg)
    
    # Opsiyonel alanlar
    if data.get('email'):
        is_valid, msg = validator.validate_email(data.get('email'), 'E-posta')
        if not is_valid:
            errors.append(msg)
    
    if data.get('tc_no'):
        is_valid, msg = validator.validate_tc_no(data.get('tc_no'), 'TC Kimlik No')
        if not is_valid:
            errors.append(msg)
    
    if data.get('tax_id'):
        is_valid, msg = validator.validate_tax_id(data.get('tax_id'), 'Vergi No')
        if not is_valid:
            errors.append(msg)
    
    return len(errors) == 0, errors


def validate_service_data(data: dict) -> Tuple[bool, list]:
    """
    Servis verisi toplu validasyonu
    
    Args:
        data: Servis verisi dictionary
        
    Returns:
        (başarılı_mı, hata_listesi)
    """
    errors = []
    validator = InputValidator()
    
    # Zorunlu alanlar
    is_valid, msg = validator.validate_required(data.get('customer_name'), 'Müşteri Adı')
    if not is_valid:
        errors.append(msg)
    
    is_valid, msg = validator.validate_required(data.get('device_brand'), 'Cihaz Markası')
    if not is_valid:
        errors.append(msg)
    
    is_valid, msg = validator.validate_required(data.get('device_model'), 'Cihaz Modeli')
    if not is_valid:
        errors.append(msg)
    
    # Fiyat kontrolü
    if data.get('price') is not None:
        is_valid, msg = validator.validate_price(data.get('price'), 'Fiyat')
        if not is_valid:
            errors.append(msg)
    
    # IMEI kontrolü
    if data.get('imei'):
        is_valid, msg = validator.validate_imei(data.get('imei'), 'IMEI')
        if not is_valid:
            errors.append(msg)
    
    return len(errors) == 0, errors


def validate_stock_data(data: dict) -> Tuple[bool, list]:
    """
    Stok verisi toplu validasyonu
    
    Args:
        data: Stok verisi dictionary
        
    Returns:
        (başarılı_mı, hata_listesi)
    """
    errors = []
    validator = InputValidator()
    
    # Zorunlu alanlar
    is_valid, msg = validator.validate_required(data.get('name'), 'Parça Adı')
    if not is_valid:
        errors.append(msg)
    
    is_valid, msg = validator.validate_stock(data.get('stock', 0), 'Stok Miktarı')
    if not is_valid:
        errors.append(msg)
    
    is_valid, msg = validator.validate_price(data.get('price', 0), 'Fiyat', allow_zero=True)
    if not is_valid:
        errors.append(msg)
    
    return len(errors) == 0, errors
