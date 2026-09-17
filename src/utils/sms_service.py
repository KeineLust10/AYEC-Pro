# -*- coding: utf-8 -*-

import requests
import logging

logger = logging.getLogger("AYECProLogger")

class SMSService:
    """SMS Gönderim Servisi (Mock/Placeholder)"""
    
    API_URL = "https://api.ornek-sms-saglayici.com/v1/send"
    API_KEY = "YOUR_API_KEY"
    
    @staticmethod
    def send_sms(phone, message):
        """SMS gönder (Şimdilik sadece loglar)"""
        try:
            # Gerçek entegrasyon için buraya API isteği eklenebilir
            # payload = {"phone": phone, "message": message, "key": SMSService.API_KEY}
            # requests.post(SMSService.API_URL, json=payload)
            
            logger.info(f"SMS GÖNDERİLDİ -> {phone}: {message}")
            logger.debug(f"[SMS SIMULATION] To: {phone} | Msg: {message}")
            return True
        except Exception as e:
            logger.error(f"SMS Error: {e}")
            return False
