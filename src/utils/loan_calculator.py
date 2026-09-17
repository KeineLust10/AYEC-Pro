# -*- coding: utf-8 -*-

"""
Kredi Hesaplama Motoru (Loan Calculator)
Annuity formülü ile sabit taksitli kredi hesaplaması
"""
from datetime import datetime, timedelta
import logging
from typing import List, Dict
from dateutil.relativedelta import relativedelta

logger = logging.getLogger("AYECProLogger")


class LoanCalculator:
    """
    Kredi taksit hesaplama ve ödeme planı oluşturma sınıfı
    """
    
    @staticmethod
    def calculate_monthly_installment(principal: float, annual_rate: float, months: int) -> float:
        """
        Sabit taksitli kredinin aylık ödemesini hesaplar (Annuity Formula)
        
        Formül: Taksit = P × [r(1+r)^n] / [(1+r)^n - 1]
        
        Args:
            principal: Ana para (TL)
            annual_rate: Yıllık faiz oranı (örn: 24.0 = %24)
            months: Taksit sayısı
            
        Returns:
            Aylık taksit tutarı (TL)
        """
        if months == 0 or principal == 0:
            return 0.0
            
        # Yıllık faizi aylığa çevir
        monthly_rate = (annual_rate / 100) / 12
        
        if monthly_rate == 0:
            # Faizsiz kredi
            return principal / months
        
        # Annuity formülü
        numerator = monthly_rate * ((1 + monthly_rate) ** months)
        denominator = ((1 + monthly_rate) ** months) - 1
        
        monthly_payment = principal * (numerator / denominator)
        return round(monthly_payment, 2)
    
    @staticmethod
    def calculate_taxes(interest_amount: float, kkdf_rate: float, bsmv_rate: float) -> Dict[str, float]:
        """
        Faiz üzerinden KKDF ve BSMV vergilerini hesaplar
        
        Args:
            interest_amount: Faiz tutarı
            kkdf_rate: KKDF oranı (örn: 0.15 = %0.15)
            bsmv_rate: BSMV oranı (örn: 0.10 = %0.10)
            
        Returns:
            Dict with 'kkdf' and 'bsmv' amounts
        """
        kkdf = round(interest_amount * (kkdf_rate / 100), 2)
        bsmv = round(interest_amount * (bsmv_rate / 100), 2)
        
        return {
            'kkdf': kkdf,
            'bsmv': bsmv,
            'total_tax': kkdf + bsmv
        }
    
    @staticmethod
    def generate_payment_plan(
        principal: float,
        annual_rate: float,
        months: int,
        start_date: datetime,
        kkdf_rate: float = 0.0,
        bsmv_rate: float = 0.0
    ) -> List[Dict]:
        """
        Tüm taksit planını detaylı olarak oluşturur
        
        Args:
            principal: Ana para
            annual_rate: Yıllık faiz oranı
            months: Taksit sayısı
            start_date: Başlangıç tarihi
            kkdf_rate: KKDF oranı (%)
            bsmv_rate: BSMV oranı (%)
            
        Returns:
            List of installment details with breakdown
        """
        monthly_payment = LoanCalculator.calculate_monthly_installment(
            principal, annual_rate, months
        )
        
        monthly_rate = (annual_rate / 100) / 12
        remaining_principal = principal
        
        payment_plan = []
        
        for i in range(1, months + 1):
            # Faiz kısmı
            interest_part = round(remaining_principal * monthly_rate, 2)
            
            # Ana para kısmı
            principal_part = round(monthly_payment - interest_part, 2)
            
            # Son taksitte yuvarlama farkını düzelt
            if i == months:
                principal_part = remaining_principal
                monthly_payment = principal_part + interest_part
            
            # Vergiler
            taxes = LoanCalculator.calculate_taxes(interest_part, kkdf_rate, bsmv_rate)
            
            # Toplam ödeme (Taksit + Vergiler)
            total_payment = monthly_payment + taxes['total_tax']
            
            # Vade tarihi
            due_date = start_date + relativedelta(months=i)
            
            installment = {
                'installment_number': i,
                'due_date': due_date.strftime('%Y-%m-%d'),
                'total_amount': round(total_payment, 2),
                'principal_part': round(principal_part, 2),
                'interest_part': round(interest_part, 2),
                'kkdf_amount': taxes['kkdf'],
                'bsmv_amount': taxes['bsmv'],
                'remaining_principal': round(remaining_principal - principal_part, 2),
                'status': 'Bekliyor'
            }
            
            payment_plan.append(installment)
            remaining_principal -= principal_part
        
        return payment_plan
    
    @staticmethod
    def calculate_total_cost(principal: float, annual_rate: float, months: int, 
                            kkdf_rate: float = 0.0, bsmv_rate: float = 0.0) -> Dict[str, float]:
        """
        Kredinin toplam maliyetini hesaplar
        
        Returns:
            Dict with total_payment, total_interest, total_tax
        """
        monthly_payment = LoanCalculator.calculate_monthly_installment(principal, annual_rate, months)
        total_payment_without_tax = monthly_payment * months
        total_interest = total_payment_without_tax - principal
        
        # Toplam vergi (kaba tahmin - her taksitteki faiz üzerinden)
        avg_interest_per_month = total_interest / months
        monthly_tax = LoanCalculator.calculate_taxes(avg_interest_per_month, kkdf_rate, bsmv_rate)
        total_tax = monthly_tax['total_tax'] * months
        
        return {
            'total_payment': round(total_payment_without_tax + total_tax, 2),
            'total_interest': round(total_interest, 2),
            'total_tax': round(total_tax, 2),
            'monthly_installment': round(monthly_payment, 2)
        }


# Test kodu
if __name__ == "__main__":
    # Örnek: 100,000 TL, %24 faiz, 36 ay, KKDF %0.15, BSMV %0.10
    calc = LoanCalculator()
    
    # Aylık taksit
    monthly = calc.calculate_monthly_installment(100000, 24, 36)
    logger.info("Aylık Taksit: %,.2f TL", monthly)
    # Toplam maliyet
    cost = calc.calculate_total_cost(100000, 24, 36, 0.15, 0.10)
    logger.info("Toplam ?deme: %,.2f TL", cost["total_payment"])
    logger.info("Toplam Faiz: %,.2f TL", cost["total_interest"])
    logger.info("Toplam Vergi: %,.2f TL", cost["total_tax"])
    
    # İlk 3 taksit detayı
    plan = calc.generate_payment_plan(
        principal=100000,
        annual_rate=24,
        months=36,
        start_date=datetime.now(),
        kkdf_rate=0.15,
        bsmv_rate=0.10
    )
    logger.info("?lk 3 Taksit:")
    for inst in plan[:3]:
        logger.info("Taksit #%s: %,.2f TL (Ana: %,.2f, Faiz: %,.2f, Vergi: %.2f)", inst["installment_number"], inst["total_amount"], inst["principal_part"], inst["interest_part"], inst["kkdf_amount"] + inst["bsmv_amount"])
