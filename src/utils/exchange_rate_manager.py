# -*- coding: utf-8 -*-

"""
Exchange Rate Manager - TCMB API Integration
Türkiye Cumhuriyet Merkez Bankası'ndan güncel döviz kurlarını çeker
"""

import requests
from datetime import datetime

from defusedxml import ElementTree as ET
from src.utils.logger import logger

class ExchangeRateManager:
    """TCMB API ile döviz kuru yönetimi"""
    
    TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"
    SUPPORTED_CURRENCIES = ['USD', 'EUR', 'GBP']
    
    _rates_cache = {}  # Önbellek: {'USD': 30.56, 'EUR': 33.12}
    _last_cache_update = None
    
    @staticmethod
    def fetch_tcmb_rates():
        """
        TCMB'den güncel kurları çek
        Returns: dict {'USD': {'buying': 30.12, 'selling': 30.56}, ...}
        """
        try:
            response = requests.get(ExchangeRateManager.TCMB_URL, timeout=2)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            rates = {}
            
            for currency_elem in root.findall('Currency'):
                code = currency_elem.get('CurrencyCode')
                if code in ExchangeRateManager.SUPPORTED_CURRENCIES:
                    buying = currency_elem.find('ForexBuying')
                    selling = currency_elem.find('ForexSelling')
                    
                    if buying is not None and selling is not None:
                        rates[code] = {
                            'buying': float(buying.text),
                            'selling': float(selling.text),
                            'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
            
            logger.info(f"TCMB rates fetched successfully: {rates}")
            return rates
            
        except requests.exceptions.RequestException as e:
            logger.error(f"TCMB API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Exchange rate parsing error: {e}")
            return None
    
    @staticmethod
    def save_rates_to_db(db, rates, source="TCMB"):
        """Kurları veritabanına kaydet"""
        if not rates:
            return False
            
        try:
            cursor = db.conn.cursor()
            for currency, data in rates.items():
                cursor.execute("""
                    INSERT INTO exchange_rates (currency, buying_rate, selling_rate, effective_date, source, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    currency,
                    data['buying'],
                    data['selling'],
                    data['date'],
                    str(source or "TCMB"),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))
            db.conn.commit()
            ExchangeRateManager._rates_cache.clear()
            ExchangeRateManager._last_cache_update = None
            logger.info("Exchange rates saved to database")
            return True
        except Exception as e:
            logger.error(f"Error saving rates to DB: {e}")
            return False

    @staticmethod
    def save_manual_rates(db, rates):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        payload = {}
        for currency, rate in dict(rates or {}).items():
            code = str(currency or "").strip().upper()
            if code not in ExchangeRateManager.SUPPORTED_CURRENCIES:
                continue
            try:
                numeric_rate = float(rate)
            except (TypeError, ValueError):
                continue
            if numeric_rate <= 0:
                continue
            payload[code] = {
                "buying": numeric_rate,
                "selling": numeric_rate,
                "date": now,
            }
        return ExchangeRateManager.save_rates_to_db(
            db,
            payload,
            source="MANUAL",
        )
    
    @staticmethod
    def get_current_rate(db, currency, rate_type='selling'):
        """
        Veritabanından veya önbellekten güncel kuru getir
        """
        # 1. Önbelleği kontrol et (Bugün güncellendiyse)
        today = datetime.now().strftime("%Y-%m-%d")
        if ExchangeRateManager._last_cache_update == today:
            if currency in ExchangeRateManager._rates_cache:
                return ExchangeRateManager._rates_cache[currency]
        
        try:
            cursor = db.conn.cursor()
            column = 'buying_rate' if rate_type == 'buying' else 'selling_rate'
            
            # Bugünün kurunu al
            result = cursor.execute("""
                SELECT {column} FROM exchange_rates
                WHERE currency = ? AND DATE(effective_date) = DATE(?)
                ORDER BY created_at DESC
                LIMIT 1
            """.format(column=column), (currency, today)).fetchone()
            
            rate = None
            if result:
                rate = result[0]
            else:
                # Bugünün kuru yoksa, en son kuru al
                result = cursor.execute("""
                    SELECT {column} FROM exchange_rates
                    WHERE currency = ?
                    ORDER BY created_at DESC
                    LIMIT 1
                """.format(column=column), (currency,)).fetchone()
                rate = result[0] if result else None

            # Önbelleği güncelle
            if rate:
                ExchangeRateManager._rates_cache[currency] = rate
                ExchangeRateManager._last_cache_update = today
                
            return rate
            
        except Exception as e:
            logger.error(f"Error getting current rate: {e}")
            return None
    
    @staticmethod
    def convert_to_try(amount, currency, exchange_rate):
        """
        Dövizi TL'ye çevir
        Args:
            amount: Döviz miktarı
            currency: Para birimi
            exchange_rate: Kur
        Returns: TL karşılığı
        """
        if currency == 'TRY':
            return amount
        return amount * exchange_rate
    
    @staticmethod
    def convert_from_try(try_amount, currency, exchange_rate):
        """
        TL'yi dövize çevir
        Args:
            try_amount: TL miktarı
            currency: Hedef para birimi
            exchange_rate: Kur
        Returns: Döviz karşılığı
        """
        if currency == 'TRY':
            return try_amount
        if exchange_rate == 0:
            return 0
        return try_amount / exchange_rate
    
    @staticmethod
    def update_rates_if_needed(db):
        """Kurlar güncel değilse TCMB'den çek ve kaydet"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            cursor = db.conn.cursor()
            # Bugünün kuru var mı kontrol et
            result = cursor.execute("""
                SELECT COUNT(*) FROM exchange_rates
                WHERE DATE(effective_date) = DATE(?)
            """, (today,)).fetchone()
            
            if result[0] == 0:
                # Bugünün kuru yok, TCMB'den çek
                logger.info("No rates for today, fetching from TCMB...")
                rates = ExchangeRateManager.fetch_tcmb_rates()
                if rates:
                    ExchangeRateManager.save_rates_to_db(db, rates)
                    return True
                else:
                    logger.warning("Could not fetch rates from TCMB")
                    return False
            return True
        except Exception as e:
            logger.error(f"Error updating rates: {e}")
            return False
