# -*- coding: utf-8 -*-

import logging

from src.utils.exchange_rate_manager import ExchangeRateManager


logger = logging.getLogger(__name__)


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
            from src.database import Database

            CurrencyHelper._db = Database(init_mode="connection_only")
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
            logger.exception("Currency settings could not be persisted")
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
            logger.exception("Currency setting could not be read; using TRY")
            return "TRY"

    @staticmethod
    def get_symbol(db=None, currency_code=None):
        code = (currency_code or CurrencyHelper.get_code(db)).upper()

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
            rate = float(
                ExchangeRateManager.get_current_rate(db, code, "selling") or 0.0
            )
            if rate <= 0:
                fallback = 47.5736 if code == "USD" else (51.50 if code == "EUR" else 1.0)
                logger.warning("No DB selling rate for %s; using fallback: %s", code, fallback)
                return fallback
            return rate
        except Exception:
            fallback = 47.5736 if code == "USD" else (51.50 if code == "EUR" else 1.0)
            logger.exception("Currency rate lookup failed for %s; using fallback %s", code, fallback)
            return fallback

    @staticmethod
    def require_rate(db, currency_code):
        code = (currency_code or "TRY").upper()
        rate = float(CurrencyHelper._get_rate(db, code) or 0.0)
        if rate <= 0:
            raise ValueError(f"Exchange rate unavailable: {code}")
        return rate

    @staticmethod
    def convert_amount(db, value, from_currency, to_currency):
        src = (from_currency or "TRY").upper()
        dst = (to_currency or CurrencyHelper.get_code(db)).upper()
        if src == dst:
            return value

        if src == "TRY":
            try_amount = value
        else:
            try_amount = value * CurrencyHelper.require_rate(db, src)

        if dst == "TRY":
            return try_amount

        dst_rate = CurrencyHelper.require_rate(db, dst)
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
    def format_from_try(amount_try, db=None, currency_code=None, **kwargs):
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
