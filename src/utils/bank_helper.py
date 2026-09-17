# -*- coding: utf-8 -*-

"""
Bank Helper Utility
Türkiye bankalarını yönetir, IBAN doğrular ve banka kodları sağlar
"""
import json
import os
from typing import Optional, Dict, List, Tuple

from src.utils.logger import logger


class BankHelper:
    """Banka verileri ve IBAN validasyonu için yardımcı sınıf"""
    
    _instance = None
    _banks_cache = None
    
    def __new__(cls):
        """Singleton pattern - tek instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Constructor - ilk çağrıda bankaları yükle"""
        if BankHelper._banks_cache is None:
            BankHelper._banks_cache = self._load_banks_from_file()
    
    def _load_banks_from_file(self) -> List[Dict]:
        """banks.json dosyasından banka listesini yükle"""
        try:
            # Get path relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, '..', 'data', 'banks.json')
            json_path = os.path.normpath(json_path)
            
            if not os.path.exists(json_path):
                logger.warning("banks.json not found at %s", json_path)
                return self._get_fallback_banks()
            
            with open(json_path, 'r', encoding='utf-8') as f:
                banks = json.load(f)
            
            return banks
        except Exception as e:
            logger.error("Error loading banks.json: %s", e)
            return self._get_fallback_banks()
    
    def _get_fallback_banks(self) -> List[Dict]:
        """JSON yüklenemezse fallback banka listesi"""
        return [
            {"id": 1, "name": "T.C. Ziraat Bankası", "shortName": "Ziraat", "eftCode": "0010", "swift": "TCZITR2A", "type": "Kamu Mevduat"},
            {"id": 2, "name": "Türkiye İş Bankası", "shortName": "İş Bankası", "eftCode": "0064", "swift": "ISBKTRIS", "type": "Özel Mevduat"},
            {"id": 3, "name": "Akbank", "shortName": "Akbank", "eftCode": "0046", "swift": "AKBKTRIS", "type": "Özel Mevduat"},
            {"id": 4, "name": "Garanti BBVA", "shortName": "Garanti", "eftCode": "0062", "swift": "TGBATRIS", "type": "Özel Mevduat"},
            {"id": 5, "name": "Yapı ve Kredi Bankası", "shortName": "Yapı Kredi", "eftCode": "0067", "swift": "YKTRTRIS", "type": "Özel Mevduat"},
            {"id": 6, "name": "Türkiye Halk Bankası", "shortName": "Halkbank", "eftCode": "0012", "swift": "THALTR2A", "type": "Kamu Mevduat"},
            {"id": 7, "name": "Türkiye Vakıflar Bankası", "shortName": "VakıfBank", "eftCode": "0015", "swift": "TVBATR2A", "type": "Kamu Mevduat"},
        ]
    
    def get_all_banks(self) -> List[Dict]:
        """Tüm bankaları döndür"""
        return BankHelper._banks_cache or []
    
    def get_bank_by_eft_code(self, eft_code: str) -> Optional[Dict]:
        """EFT koduna göre banka bul"""
        eft_code = str(eft_code).strip()
        for bank in self.get_all_banks():
            if bank.get('eftCode') == eft_code:
                return bank
        return None
    
    def get_bank_by_name(self, name: str) -> Optional[Dict]:
        """İsme göre banka bul (case-insensitive)"""
        name_lower = name.lower().strip()
        for bank in self.get_all_banks():
            if name_lower in bank.get('name', '').lower() or name_lower in bank.get('shortName', '').lower():
                return bank
        return None
    
    def extract_bank_code_from_iban(self, iban: str) -> Optional[str]:
        """
        IBAN'dan banka kodunu çıkar
        TR dışındaki IBAN'lar için None döner
        
        Türk IBAN formatı: TR + 2 digit check + 4 digit bank code + ...
        Örnek: TR12 0046 0000 1234... -> "0046"
        """
        iban = iban.replace(" ", "").replace("-", "").strip().upper()
        
        # Türk IBAN kontrolü
        if not iban.startswith("TR"):
            return None
        
        # En az 9 karakter olmalı (TR + 2 check + 4 bank + 1)
        if len(iban) < 9:
            return None
        
        # Position 4-7 (0-indexed) = bank code
        bank_code = iban[4:8]
        
        # Numeric check
        if not bank_code.isdigit():
            return None
        
        return bank_code
    
    def validate_iban(self, iban: str, expected_bank_eft_code: str = None) -> Tuple[bool, str]:
        """
        IBAN doğrula
        
        Args:
            iban: Doğrulanacak IBAN
            expected_bank_eft_code: Beklenen banka EFT kodu (opsiyonel)
        
        Returns:
            (is_valid, message) tuple
        """
        iban = iban.replace(" ", "").replace("-", "").strip().upper()
        
        # Boş kontrol
        if not iban:
            return False, "IBAN boş olamaz"
        
        # Türk IBAN kontrolü
        if not iban.startswith("TR"):
            return False, "IBAN 'TR' ile başlamalı"
        
        # Uzunluk kontrolü (Türk IBAN: 26 karakter)
        if len(iban) != 26:
            return False, f"Türk IBAN 26 karakter olmalı (Girilen: {len(iban)})"
        
        # Banka kodu çıkar
        bank_code = self.extract_bank_code_from_iban(iban)
        
        if not bank_code:
            return False, "IBAN formatı hatalı"
        
        # Banka kodunu veritabanında ara
        bank = self.get_bank_by_eft_code(bank_code)
        
        if not bank:
            return False, f"Bilinmeyen banka kodu: {bank_code}"
        
        # Eğer beklenen kod verilmişse karşılaştır
        if expected_bank_eft_code:
            expected_bank_eft_code = str(expected_bank_eft_code).strip()
            if bank_code != expected_bank_eft_code:
                expected_bank = self.get_bank_by_eft_code(expected_bank_eft_code)
                expected_name = expected_bank['shortName'] if expected_bank else expected_bank_eft_code
                return False, f"IBAN {bank['shortName']} bankasına ait, seçilen banka {expected_name}"
        
        return True, f"✓ {bank['shortName']} bankası doğrulandı"
    
    def format_iban(self, iban: str) -> str:
        """IBAN'ı düzenli formatta döndür (4'lü gruplar)"""
        iban = iban.replace(" ", "").replace("-", "").strip().upper()
        if len(iban) < 4:
            return iban
        
        # 4'lü gruplara böl
        formatted = ' '.join([iban[i:i+4] for i in range(0, len(iban), 4)])
        return formatted


# Singleton instance
_bank_helper_instance = None

def get_bank_helper() -> BankHelper:
    """Global BankHelper instance'ını döndür"""
    global _bank_helper_instance
    if _bank_helper_instance is None:
        _bank_helper_instance = BankHelper()
    return _bank_helper_instance
