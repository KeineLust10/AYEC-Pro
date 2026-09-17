"""Helpers for consistent role checks across the UI and database layers."""

import re
import unicodedata


_TURKISH_ASCII_MAP = str.maketrans(
    {
        "\u00c7": "C",
        "\u00d6": "O",
        "\u00dc": "U",
        "\u011e": "G",
        "\u0130": "I",
        "\u015e": "S",
        "\u00e7": "c",
        "\u00f6": "o",
        "\u00fc": "u",
        "\u011f": "g",
        "\u0131": "i",
        "\u015f": "s",
    }
)

_ADMIN_ROLE_KEYS = {
    "admin",
    "administrator",
    "superadmin",
    "super admin",
    "super administrator",
    "master admin",
    "platform admin",
    "system admin",
    "company admin",
    "yonetici",
    "sistem yoneticisi",
    "firma yoneticisi",
    "firma sahibi",
    "owner",
    "tenant owner",
    "en yetkili",
    "en yetkili kisi",
}


def role_key(role):
    value = str(role or "").strip().translate(_TURKISH_ASCII_MAP)
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def normalize_role(role):
    key = role_key(role)
    if key == "master":
        return "Master"
    if key in _ADMIN_ROLE_KEYS:
        return "Admin"
    aliases = {
        "teknisyen": "Teknisyen",
        "technician": "Teknisyen",
        "muhasebe": "Muhasebe",
        "accounting": "Muhasebe",
        "personel": "Personel",
        "personnel": "Personel",
        "satis": "Sat\u0131\u015f",
        "sales": "Sat\u0131\u015f",
    }
    return aliases.get(key, str(role or "").strip())


def is_admin_role(role):
    return role_key(role) == "master" or role_key(role) in _ADMIN_ROLE_KEYS
