# -*- coding: utf-8 -*-

from src.database import Database
from src.utils.exchange_rate_manager import ExchangeRateManager


class CurrencyHelper:
    """Currency display and conversion helpers based on application settings."""

    _db = None
    SUPPORTED_CHOICES = (
        ("TRY", "TRY - Türk Lirası (₺)"),
        ("USD", "USD - Amerikan Doları ($)"),
        ("EUR", "EUR - Euro (€)"),
    )

    @staticmethod
    def register_db(db):
        if db is not None and hasattr(db, "get_setting"):
            CurrencyHelper._db = db
        return CurrencyHelper._db

    @staticmethod
    def get_db():
        if CurrencyHelper._db is None:
            CurrencyHelper._db = Database()
        return CurrencyHelper._db

    @staticmethod
    def parse_currency_code(setting_value):
        text = str(setting_value or "").upper()
        if "USD" in text or "$" in text:
            return "USD"
        if "EUR" in text or "\u20ac" in text:
            return "EUR"
        return "TRY"

    @staticmethod
    def normalize_code(setting_value):
        return CurrencyHelper.parse_currency_code(setting_value)

    @staticmethod
    def persist_code(db, setting_value):
        code = CurrencyHelper.normalize_code(setting_value)
        try:
            db = db or CurrencyHelper.get_db()
            db.set_setting("currency", code)
            db.set_setting("default_currency", code)
        except Exception:
            pass
        return code

    @staticmethod
    def get_choice_texts():
        return [label for _, label in CurrencyHelper.SUPPORTED_CHOICES]

    @staticmethod
    def get_supported_codes():
        return [code for code, _ in CurrencyHelper.SUPPORTED_CHOICES]

    @staticmethod
    def set_combo_to_code(combo, code):
        target = (code or "TRY").upper()
        for idx, (choice_code, _) in enumerate(CurrencyHelper.SUPPORTED_CHOICES):
            if choice_code == target:
                combo.setCurrentIndex(idx)
                return
        combo.setCurrentIndex(0)

    @staticmethod
    def combo_to_code(combo):
        text = combo.currentText() if combo else "TRY"
        return CurrencyHelper.normalize_code(text)

    @staticmethod
    def get_code(db=None):
        try:
            db = db or CurrencyHelper.get_db()
            setting = db.get_setting("currency", "") or db.get_setting(
                "default_currency", "TRY"
            )
            return CurrencyHelper.normalize_code(setting)
        except Exception:
            return "TRY"

    @staticmethod
    def get_symbol(db=None, currency_code=None):
        code = (currency_code or CurrencyHelper.get_code(db)).upper()
        if code == "USD":
            return "$"
        if code == "EUR":
            return "\u20ac"
        return "\u20ba"

    @staticmethod
    def get_label(currency_code=None, db=None):
        code = (currency_code or CurrencyHelper.get_code(db)).upper()
        if code == "TRY":
            return "TL"
        return code

    @staticmethod
    def _get_rate(db, currency_code):
        code = (currency_code or "TRY").upper()
        if code == "TRY":
            return 1.0
        try:
            db = db or CurrencyHelper.get_db()
            return float(
                ExchangeRateManager.get_current_rate(db, code, "selling") or 1.0
            )
        except Exception:
            return 1.0

    @staticmethod
    def convert_amount(db, amount, from_currency="TRY", to_currency=None):
        try:
            value = float(amount or 0)
        except Exception:
            return 0.0

        src = (from_currency or "TRY").upper()
        dst = (to_currency or CurrencyHelper.get_code(db)).upper()
        if src == dst:
            return value

        if src == "TRY":
            try_amount = value
        else:
            try_amount = value * CurrencyHelper._get_rate(db, src)

        if dst == "TRY":
            return try_amount

        dst_rate = CurrencyHelper._get_rate(db, dst)
        if not dst_rate:
            return try_amount
        return try_amount / dst_rate

    @staticmethod
    def get_precision(db=None):
        """Veritabanından para birimi hassasiyetini al (ondalık basamak sayısı)"""
        try:
            db = db or CurrencyHelper.get_db()
            precision_str = db.get_setting("currency_precision", "2")
            precision = int(precision_str)
            if precision < 0:
                precision = 0
            elif precision > 3:
                precision = 3
            return precision
        except Exception:
            return 2  # Varsayılan 2 basamak

    @staticmethod
    def format_amount(amount, db=None, currency_code=None):
        code = (currency_code or CurrencyHelper.get_code(db)).upper()
        symbol = CurrencyHelper.get_symbol(db, code)
        try:
            value = float(amount or 0)
        except (ValueError, TypeError):
            value = 0.0
        # Hassasiyet ayarını al
        precision = CurrencyHelper.get_precision(db)
        # Format string oluştur (:,.2f gibi)
        format_str = f"{{:,.{precision}f}}"
        return f"{format_str.format(value)} {symbol}"

    @staticmethod
    def format_from_try(amount_try, db=None, currency_code=None):
        code = (currency_code or CurrencyHelper.get_code(db)).upper()
        converted = CurrencyHelper.convert_amount(db, amount_try, "TRY", code)
        return CurrencyHelper.format_amount(converted, db=db, currency_code=code)

    @staticmethod
    def format_try_for_display(amount_try, db=None, include_try_reference=True):
        code = CurrencyHelper.get_code(db)
        primary = CurrencyHelper.format_from_try(amount_try, db=db, currency_code=code)
        if code == "TRY" or not include_try_reference:
            return primary
        return f"{primary} | {CurrencyHelper.format_amount(amount_try, db=db, currency_code='TRY')}"

    @staticmethod
    def format_original_and_try(amount, currency_code, db=None):
        code = (currency_code or "TRY").upper()
        if code == "TRY":
            return CurrencyHelper.format_amount(amount, db=db, currency_code="TRY")
        primary = CurrencyHelper.format_amount(amount, db=db, currency_code=code)
        try_equivalent = CurrencyHelper.convert_amount(db, amount, code, "TRY")
        return f"{primary} ({CurrencyHelper.format_amount(try_equivalent, db=db, currency_code='TRY')})"
