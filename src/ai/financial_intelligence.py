# -*- coding: utf-8 -*-

"""
Financial Intelligence Module for AI Assistant.
AI asistanın finansal verilere erişimi ve konuşma template sistemi.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger


class FinancialIntelligence:
    """
    AI asistan için finansal zeka modülü.
    - Template-based responses
    - Database integration
    - Placeholder substitution
    """

    def __init__(self, db):
        self.db = db
        self.templates = self._load_templates()

    def _amount_in_words(self, amount, currency="TRY"):
        try:
            val = float(amount or 0)
        except Exception:
            val = 0.0
            
        sign = "eksi " if val < 0 else ""
        val = round(abs(val), 2)
        whole = int(val)
        fraction = int(round((val - whole) * 100))
        
        def number_to_tr(n):
            if n == 0: return "sıfır"
            birler = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
            onlar = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
            def chunk(num):
                s = ""
                h = num // 100
                if h > 0: s += (birler[h] if h > 1 else "") + "yüz "
                o = (num % 100) // 10
                if o > 0: s += onlar[o] + " "
                b = num % 10
                if b > 0: s += birler[b] + " "
                return s.strip()
            words = []
            for scale_val, scale_name in [(1000000000, "milyar"), (1000000, "milyon"), (1000, "bin")]:
                if n >= scale_val:
                    c = n // scale_val
                    if scale_name == "bin" and c == 1: words.append("bin")
                    else: words.extend([chunk(c), scale_name])
                    n %= scale_val
            if n > 0: words.append(chunk(n))
            return " ".join(w for w in words if w).strip()
            
        words = f"{number_to_tr(whole)} Türk Lirası"
        if fraction > 0:
            words += f" {number_to_tr(fraction)} kuruş"
        return sign + words

    def _fmt_try(self, amount, include_try_reference=False):
        return self._amount_in_words(amount)

    def _load_templates(self):
        """JSON şablonlarını yükle."""
        template_path = Path(__file__).parent / "financial_templates.json"
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Finans Şablonlar? yüklenemedi: %s", e)
            return {}

    def get_financial_summary(self, user_name="Kullanıcı"):
        """
        Finansal Özet cümlesi döndürür.
        Trigger: "Finansal durum nedir?", "Krediler"
        """
        summary = self._get_summary_data()
        templates = self.templates.get("financial_summary", {}).get("general", [])
        if not templates:
            return "Finansal veriler hazırlanıyor..."

        template = random.choice(templates)
        return template.format(
            user_name=user_name,
            total_balance=self._fmt_try(summary['total_balance']),
            upcoming_debt=self._fmt_try(summary['upcoming_debt']),
            upcoming_count=summary["upcoming_count"],
            overdue_count=summary["overdue_count"],
        )

    def get_morning_greeting_with_finance(self, user_name="Kullanıcı"):
        """Günaydın mesajına finansal bilgi ekler."""
        today = datetime.now()
        day_names = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

        from src.utils.date_utils import format_turkish_date

        today_str = today.strftime("%Y-%m-%d")
        tomorrow_str = (today + timedelta(days=1)).strftime("%Y-%m-%d")

        today_loans = self.db.get_loan_installments_by_date(today_str)
        tomorrow_loans = self.db.get_loan_installments_by_date(tomorrow_str)
        today_checks = self._get_checks_by_date(today_str)
        tomorrow_checks = self._get_checks_by_date(tomorrow_str)

        has_finance = any([today_loans, tomorrow_loans, today_checks])

        if has_finance:
            templates = self.templates.get("morning_greeting", {}).get("with_finance", [])
            template = random.choice(templates) if templates else "Günaydın!"
            bank_name = tomorrow_loans[0]["bank_name"] if tomorrow_loans else "Banka"
            return template.format(
                user_name=user_name,
                date=format_turkish_date(today, "short"),
                day_name=day_names[today.weekday()],
                weather="Açık",
                bank_name=bank_name,
                today_payments=len(today_loans) + len(today_checks),
                tomorrow_payments=len(tomorrow_loans) + len(tomorrow_checks),
                today_amount=sum(l["total_amount"] for l in today_loans),
                upcoming_count=len(tomorrow_loans),
            )

        templates = self.templates.get("morning_greeting", {}).get("no_finance", [])
        template = random.choice(templates) if templates else "Günaydın!"
        return template.format(
            user_name=user_name,
            date=format_turkish_date(today, "short"),
            day_name=day_names[today.weekday()],
        )

    def get_critical_cash_warning(self, user_name="Kullanıcı"):
        """
        Kritik kasa uyarısı üretir.
        Eğer mevcut bakiye 3 günlük borçtan düşükse uyar? verir.
        """
        summary = self._get_summary_data()
        upcoming_3days = self._get_upcoming_debt(days=3)

        if summary["total_balance"] < upcoming_3days:
            templates = self.templates.get("financial_summary", {}).get("critical_cash_warning", [])
            template = random.choice(templates) if templates else "Nakit uyarısı!"
            return template.format(
                user_name=user_name,
                total_balance=self._fmt_try(summary['total_balance']),
                upcoming_debt=self._fmt_try(summary['upcoming_debt']),
                upcoming_3days=self._fmt_try(upcoming_3days),
            )

        return None

    def get_loan_reminder_message(self, installment, days_until_due=0):
        """
        Kredi taksit hatırlatma mesaj?.
        days_until_due: 0=bugün, 1=yarın, -X=X gün gecikmiş
        """
        if days_until_due == 1:
            category = "loan_t_minus_1"
        elif days_until_due == 0:
            category = "loan_t_0"
        else:
            category = "loan_overdue"

        templates = self.templates.get("financial_reminders", {}).get(category, [])
        template = random.choice(templates) if templates else "Kredi hatırlatmas?"
        return template.format(
            user_name="Kullanıcı",
            bank_name=installment.get("bank_name", "Banka"),
            amount=self._fmt_try(installment.get('total_amount', 0)),
            days_overdue=abs(days_until_due) if days_until_due < 0 else 0,
        )

    def get_check_reminder_message(self, check, days_until_due=0):
        """Çek/senet hatırlatma mesaj?."""
        if days_until_due == 1:
            category = "check_t_minus_1"
        elif days_until_due == 0:
            category = "check_t_0"
        else:
            category = "check_overdue"

        templates = self.templates.get("financial_reminders", {}).get(category, [])
        template = random.choice(templates) if templates else "Çek hatırlatmas?"
        return template.format(
            user_name="Kullanıcı",
            customer_name=check.get("issuer") or check.get("recipient", "Firma"),
            amount=self._fmt_try(check.get('amount', 0)),
            check_type=check.get("type", "Çek"),
            check_no=check.get("check_no", "N/A"),
            days_overdue=abs(days_until_due) if days_until_due < 0 else 0,
            due_date=check.get("due_date", ""),
        )

    def _get_summary_data(self):
        """Finansal Özet verileri topla."""
        try:
            total_balance = 0
            upcoming = self.db.get_upcoming_installments(days=7)
            upcoming_debt = sum(i["total_amount"] for i in upcoming)
            overdue = self.db.get_overdue_installments()
            return {
                "total_balance": total_balance,
                "upcoming_debt": upcoming_debt,
                "upcoming_count": len(upcoming),
                "overdue_count": len(overdue),
            }
        except Exception as e:
            logger.error("Summary data error: %s", e)
            return {
                "total_balance": 0,
                "upcoming_debt": 0,
                "upcoming_count": 0,
                "overdue_count": 0,
            }

    def _get_upcoming_debt(self, days=3):
        """Önümüzdeki X günlük toplam borç."""
        try:
            upcoming = self.db.get_upcoming_installments(days=days)
            return sum(i["total_amount"] for i in upcoming)
        except Exception as e:
            logger.debug("Upcoming debt fallback used: %s", e)
            return 0

    def _get_checks_by_date(self, target_date):
        """Belirli tarihteki Çek/senetler."""
        try:
            all_checks = self.db.get_checks_notes(status_filter="Portföyde")
            return [c for c in all_checks if c["due_date"] == target_date]
        except Exception as e:
            logger.debug("Checks by date fallback used: %s", e)
            return []


if __name__ == "__main__":
    class MockDB:
        def get_upcoming_installments(self, days):
            return [{"total_amount": 5000}, {"total_amount": 3000}]

        def get_overdue_installments(self):
            return [{"total_amount": 2000}]

        def get_loan_installments_by_date(self, date):
            return [{"bank_name": "Garanti", "total_amount": 3923}]

        def get_checks_notes(self, status_filter):
            return []

    fi = FinancialIntelligence(MockDB())
    logger.info("Finansal Özet: %s", fi.get_financial_summary("Engin"))
    logger.info("Günaydın mesaj?: %s", fi.get_morning_greeting_with_finance("Engin"))
    warning = fi.get_critical_cash_warning("Engin")
    if warning:
        logger.info("Kritik uyar?: %s", warning)
