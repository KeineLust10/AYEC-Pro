# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime


logger = logging.getLogger(__name__)

class InvoiceMapper:
    """
    E-Fatura Veri Dönüştürücü (JSON Engine)
    Verilen Python sözlüğünü (Dict) entegratörün beklediği JSON formatına çevirir.
    Ayrıca Tevkifat ve KDV hesaplamalarını yapar.
    """

    @staticmethod
    def calculate_withholding(amount, vat_rate, withholding_code):
        """
        Tevkifat Hesaplama Motoru
        Örn: 5/10 Tevkifat -> KDV'nin yarısı alıcı tarafından ödenir.
        """
        vat_amount = amount * (vat_rate / 100.0)
        
        # Tevkifat Oranları (GİB Standart Kodları)
        # Örnek: 601 -> Yapım İşleri ile Bu İşlerle Birlikte İfa Edilen Mühendislik... (4/10 idi eskiden, güncel değişebilir)
        # Biz prompt'taki örneklere sadık kalacağız veya genel bir mapping yapacağız.
        # Basitlik için oranları koddan çıkaracağız veya manuel mapping yapacağız.
        
        rates = {
            "601": 0.5, # Örn 5/10 (Varsayım) -> Prompt'ta 5/10 veya 9/10 denmiş. 
            # İnşaat işleri genelde 4/10 veya duruma göre değişir.
            # Kodun esnek olması için oranı parametre olarak da alabiliriz veya mapleyebiliriz.
            # Şimdilik kullanıcıdan "5/10" texti gelirse onu parse edelim.
        }
        
        # Eğer withholding_code bir kesir ise (örn "5/10")
        withheld_amount = 0.0
        rate_str = ""
        
        if "/" in str(withholding_code):
            try:
                num, den = map(int, withholding_code.split('/'))
                ratio = num / den
                withheld_amount = vat_amount * ratio
                rate_str = withholding_code
            except (TypeError, ValueError) as exc:
                logger.warning("Invalid withholding ratio '%s': %s", withholding_code, exc)
        elif withholding_code in rates:
            withheld_amount = vat_amount * rates[withholding_code]
            rate_str = f"{int(rates[withholding_code]*10)}/10"
            
        return {
            "vat_amount": round(vat_amount, 2),
            "withheld_amount": round(withheld_amount, 2),
            "payable_vat": round(vat_amount - withheld_amount, 2),
            "rate_display": rate_str
        }

    def to_json(self, invoice_data):
        """
        Ana Dönüştürme Fonksiyonu
        """
        # 1. Zorunlu Alan Kontrolü
        required = ['receiver', 'items', 'currency']
        for r in required:
            if r not in invoice_data:
                raise ValueError(f"Eksik Veri: {r} alanı zorunludur.")

        receiver = invoice_data['receiver']
        items = invoice_data['items']
        
        # 2. Kalem Hesaplamaları
        json_items = []
        total_service = 0.0
        total_vat = 0.0
        total_withheld = 0.0
        
        for item in items:
            qty = float(item.get('quantity', 1))
            price = float(item.get('unit_price', 0))
            amount = qty * price
            vat_rate = float(item.get('vat_rate', 20))
            wh_code = item.get('withholding_code', "") # "5/10" gibi gelebilir
            
            calc = self.calculate_withholding(amount, vat_rate, wh_code)
            
            total_service += amount
            total_vat += calc['vat_amount']
            total_withheld += calc['withheld_amount']
            
            json_items.append({
                "urun_adi": item.get('name', 'Hizmet'),
                "miktar": qty,
                "birim": item.get('unit', 'Adet'),
                "birim_fiyat": price,
                "kdv_orani": vat_rate,
                "tevkifat_kodu": wh_code if wh_code else "", 
                "tevkifat_orani": calc['rate_display'],
                "satir_toplami": round(amount, 2)
            })

        # 3. Genel Toplamlar
        grand_total = total_service + total_vat - total_withheld
        
        # 4. JSON Yapısı (Prompt'taki Yapı)
        payload = {
            "fatura_bilgileri": {
                "seri_no": invoice_data.get('serial', ''), # API üretebilir ama biz taslak gönderiyoruz
                "tarih": datetime.now().strftime("%Y-%m-%d"),
                "tip": invoice_data.get('type', 'SATIS'), 
                "para_birimi": invoice_data.get('currency', 'TRY')
            },
            "alici_bilgileri": {
                "unvan": receiver.get('name', ''),
                "vkn_tckn": receiver.get('tax_id', ''),
                "adres": receiver.get('address', ''),
                "eposta": receiver.get('email', '')
            },
            "kalemler": json_items,
            "toplamlar": {
                "ara_toplam": round(total_service, 2),
                "toplam_kdv": round(total_vat, 2),
                "toplam_tevkifat": round(total_withheld, 2),
                "genel_toplam": round(grand_total, 2)
            }
        }
        
        return payload

    def validate_vkn(self, vkn):
        """Basit VKN/TCKN Uzunluk Kontrolü"""
        s = str(vkn).strip()
        return len(s) in [10, 11] and s.isdigit()
