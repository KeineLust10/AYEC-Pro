import re


class TaxSettings:
    SETTING_KEY = "default_vat_percent"
    DEFAULT_PERCENT = 20.0

    @classmethod
    def normalize_percent(cls, value):
        try:
            percent = float(value)
        except (TypeError, ValueError):
            percent = cls.DEFAULT_PERCENT
        if 0 < percent < 1:
            percent *= 100.0
        return max(0.0, min(percent, 100.0))

    @classmethod
    def normalize_ratio(cls, value):
        return cls.normalize_percent(value) / 100.0

    @classmethod
    def get_percent(cls, db=None):
        if db is None or not hasattr(db, "get_setting"):
            return cls.DEFAULT_PERCENT
        value = db.get_setting(cls.SETTING_KEY, cls.DEFAULT_PERCENT)
        return cls.normalize_percent(value)

    @classmethod
    def get_ratio(cls, db=None):
        return cls.get_percent(db) / 100.0

    @classmethod
    def set_percent(cls, db, value):
        percent = cls.normalize_percent(value)
        if db is None or not hasattr(db, "set_setting"):
            raise RuntimeError("Settings database is not available.")
        db.set_setting(cls.SETTING_KEY, str(percent))
        return percent

    @classmethod
    def combo_text(cls, db=None):
        percent = cls.get_percent(db)
        if percent.is_integer():
            return f"%{int(percent)}"
        return f"%{percent:g}"

    @classmethod
    def ratio_from_text(cls, value):
        raw = str(value or "").strip().replace("%", "")
        if not raw or raw.lower() in {"kdv haric", "kdv hari\u00e7"}:
            return 0.0
        match = re.search(r"-?\d+(?:[.,]\d+)?", raw)
        if not match:
            return 0.0
        try:
            return cls.normalize_percent(
                match.group(0).replace(",", ".")
            ) / 100.0
        except (TypeError, ValueError):
            return 0.0
