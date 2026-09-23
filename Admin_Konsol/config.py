"""
AYEC Pro Admin Konsol - Konfig\u00fcrasyon
Sunucu adresi, port ve yerel ayarlar bu mod\u00fclde y\u00f6netilir.
"""
import json
import os
from pathlib import Path

APP_NAME = "AYEC Pro Y\u00f6netim Konsolu"
APP_VERSION = "1.0.0"

_CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "AYECAdmin"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

_DEFAULTS = {
    "server_url": "https://lisans.ayecpro.com",
    "timeout": 15,
    "remember_last_user": True,
    "last_email": "",
    "theme": "dark",
}


def load() -> dict:
    """Yerel config dosyas\u0131n\u0131 y\u00fckle. Eksik anahtarlar\u0131 varsay\u0131lanlarla tamamla."""
    try:
        if _CONFIG_FILE.exists():
            data = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            merged = {**_DEFAULTS, **data}
            return merged
    except Exception:
        pass
    return dict(_DEFAULTS)


def save(cfg: dict) -> None:
    """Config s\u00f6zl\u00fc\u011f\u00fcn\u00fc diske kaydet."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


_current: dict = load()


def get(key: str, default=None):
    return _current.get(key, default)


def set(key: str, value) -> None:
    _current[key] = value
    save(_current)


def normalize_server_url(value: str) -> str:
    """Keep only the server origin; API paths are added by api_client."""
    value = str(value or "").strip().rstrip("/")
    for suffix in ("/api/admin/login", "/api/admin", "/api"):
        if value.casefold().endswith(suffix):
            value = value[: -len(suffix)].rstrip("/")
            break
    return value


def server_url() -> str:
    value = normalize_server_url(_current.get("server_url", _DEFAULTS["server_url"]))
    if value != _current.get("server_url"):
        _current["server_url"] = value
        save(_current)
    return value


def timeout() -> int:
    return int(_current.get("timeout", 15))
