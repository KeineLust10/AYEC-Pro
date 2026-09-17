# -*- coding: utf-8 -*-

"""
Fiyat Hesaplama Modülü
Toplam, KDV, iskonto hesaplamaları
"""

from src.utils.currency_helper import CurrencyHelper


class PriceCalculator:
    """Fiyat hesaplama sınıfı"""
    
    @staticmethod
    def calculate_subtotal(cart_items):
        """
        Ara toplamı hesapla (KDV ve iskonto hariç)
        
        Args:
            cart_items: Sepet kalemleri listesi
        
        Returns:
            float: Ara toplam
        """
        return sum(item['price'] * item.get('qty', 1) for item in cart_items)
    
    @staticmethod
    def calculate_vat_rate(vat_percentage):
        """
        KDV yüzdesini oran'a çevir
        
        Args:
            vat_percentage: KDV yüzdesi string'i (örn: "18%") veya int
        
        Returns:
            float: KDV oranı (0.18 gibi)
        """
        if isinstance(vat_percentage, str):
            vat_text = vat_percentage.replace("%", "").strip()
            try:
                return int(vat_text) / 100
            except ValueError:
                return 0.0
        elif isinstance(vat_percentage, (int, float)):
            return float(vat_percentage) / 100
        return 0.0
    
    @staticmethod
    def calculate_totals(cart_items, discount=0, vat_rate=0):
        """
        Toplamları hesapla
        
        Args:
            cart_items: Sepet kalemleri
            discount: İskonto tutarı
            vat_rate: KDV oranı (0.18 gibi, %18 için)
        
        Returns:
            tuple: (subtotal, discount, vat_rate, vat_amount, total)
                - subtotal: Ara toplam
                - discount: İskonto
                - vat_rate: KDV oranı
                - vat_amount: KDV tutarı
                - total: Genel toplam
        """
        subtotal = PriceCalculator.calculate_subtotal(cart_items)
        
        # Net (iskonto sonrası)
        net = subtotal - discount
        
        # KDV
        if isinstance(vat_rate, str):
            vat_rate = PriceCalculator.calculate_vat_rate(vat_rate)
        
        vat_amount = net * vat_rate
        total = net + vat_amount
        
        return subtotal, discount, vat_rate, vat_amount, total
    
    @staticmethod
    def format_price(amount):
        """
        Fiyatı formatla
        
        Args:
            amount: Tutar
        
        Returns:
            str: Formatlanmış fiyat (örn: "1.234,56 ₺")
        """
        return CurrencyHelper.format_try_for_display(amount, include_try_reference=False)
