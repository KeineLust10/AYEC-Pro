# -*- coding: utf-8 -*-

"""
İşlem İşleme Modülü
Veritabanına kayıt işlemleri
"""

from src.utils.currency_helper import CurrencyHelper


class TransactionProcessor:
    """İşlem işleme sınıfı"""
    
    def __init__(self, db):
        """
        Args:
            db: Database instance
        """
        self.db = db
    
    def save_transaction(self, customer_id, cart_items, totals, date, discount=0, pay_now=False):
        """
        İşlemi veritabanına kaydet
        
        Args:
            customer_id: Müşteri ID'si
            cart_items: Sepet kalemleri
            totals: (subtotal, discount, vat_rate, vat_amount, total) tuple
            date: İşlem tarihi
            discount: İskonto tutarı
            pay_now: Ödeme hemen alınacak mı
        
        Returns:
            tuple: (success: bool, message: str)
        """
        if not cart_items:
            return False, "Sepet boş!"
        
        # Validation
        for item in cart_items:
            if item['price'] < 0:
                return False, f"'{item['service']}' için fiyat negatif olamaz!"
        
        try:
            subtotal, discount, vat_rate, vat_amount, total = totals
            
            # 1. Her kalemi SATIŞ (Borç) olarak kaydet
            for item in cart_items:
                qty = item.get('qty', 1)
                unit_price = item['price']
                total_line = unit_price * qty
                
                desc = f"{item['service']}: {item['description']}"
                if qty > 1:
                    desc += f" ({qty} Adet x {unit_price:.2f})"
                
                # Borç kaydı (Satış)
                self.db.add_transaction_with_customer(
                    customer_id=customer_id,
                    date=item['date'],
                    description=desc,
                    amount=total_line,
                    vat_rate=int(vat_rate * 100)
                )
            
            # 2. İskonto
            if discount > 0:
                self.db.add_transaction_with_customer(
                    customer_id=customer_id,
                    date=date,
                    description=f"İskonto ({CurrencyHelper.format_try_for_display(discount, include_try_reference=False)})",
                    amount=-discount,
                    vat_rate=0
                )
            
            # 3. KDV
            if vat_amount > 0:
                self.db.add_transaction_with_customer(
                    customer_id=customer_id,
                    date=date,
                    description=f"KDV (%{int(vat_rate*100)})",
                    amount=vat_amount,
                    vat_rate=int(vat_rate * 100)
                )
            
            # 4. Ödeme Alma (Tahsilat) - Eğer hemen ödeme alınıyorsa
            if pay_now:
                self.db.add_transaction_with_customer(
                    customer_id=customer_id,
                    date=date,
                    description=f"Tahsilat (Servis Ödemesi) - {CurrencyHelper.format_try_for_display(total, include_try_reference=False)}",
                    amount=total,
                    t_type="Gelir",
                    category="Tahsilat",
                    vat_rate=0
                )
                return True, f"İşlem ve Ödeme Kaydedildi: {CurrencyHelper.format_try_for_display(total, include_try_reference=False)} ✅"
            else:
                return True, f"Servis Borç Olarak Kaydedildi: {CurrencyHelper.format_try_for_display(total, include_try_reference=False)} ⏳"
                
        except Exception as e:
            return False, f"Kayıt hatası: {e}"
