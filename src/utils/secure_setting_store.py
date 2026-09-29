import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from src.utils.config import config


class SecureSettingStore:
    """Encrypt sensitive application settings before database persistence."""

    PREFIX = "enc:v1:"

    @classmethod
    def _fernet(cls):
        material = str(config.database_key or "").encode("utf-8")
        key = base64.urlsafe_b64encode(hashlib.sha256(material).digest())
        return Fernet(key)

    @classmethod
    def get(cls, db, key, default=""):
        value = str(db.get_setting(key, "") or "")
        if not value:
            return default
        if not value.startswith(cls.PREFIX):
            # Preserve legacy values and migrate them on the first read.
            try:
                cls.set(db, key, value)
            except Exception:
                pass
            return value
        try:
            return cls._fernet().decrypt(value[len(cls.PREFIX):].encode("ascii")).decode("utf-8")
        except (InvalidToken, ValueError, TypeError):
            return default

    @classmethod
    def set(cls, db, key, value):
        text = str(value or "")
        if not text:
            return db.set_setting(key, "")
        encrypted = cls._fernet().encrypt(text.encode("utf-8")).decode("ascii")
        return db.set_setting(key, cls.PREFIX + encrypted)

    @classmethod
    def is_encrypted(cls, value):
        return str(value or "").startswith(cls.PREFIX)
