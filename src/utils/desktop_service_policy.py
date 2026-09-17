from __future__ import annotations

import os


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _enabled(value) -> bool:
    return str(value or "").strip().lower() in _TRUE_VALUES


def _environment_override(name: str) -> bool | None:
    value = os.environ.get(name)
    if value is None:
        return None
    return _enabled(value)


def _database_setting(db, key: str, default: str = "0") -> bool:
    if db is None or not hasattr(db, "get_setting"):
        return False
    try:
        return _enabled(db.get_setting(key, default))
    except Exception:
        return False


def auto_web_sync_enabled(db=None) -> bool:
    override = _environment_override("AYECPRO_ENABLE_WEB_SYNC")
    if override is not None:
        return override
    return _database_setting(db, "desktop_auto_web_sync", "1")


def local_api_enabled(db=None) -> bool:
    override = _environment_override("AYECPRO_ENABLE_LOCAL_API")
    if override is not None:
        return override
    return _database_setting(db, "desktop_local_api")


def local_api_host() -> str:
    return "127.0.0.1"
