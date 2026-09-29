"""Shared AYEC product catalog consumed by Admin_Konsol."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parent.parent / "ecosystem" / "products.json"

_BUILTIN_PRODUCTS = (
    {"code": "teknik_servis", "name": "AYEC Pro Teknik Servis", "active": True},
    {"code": "barkod_okuyucu", "name": "AYEC Pro Barkod Okuyucu", "active": True},
    {"code": "elek", "name": "AYEC Pro Elek", "active": True},
    {"code": "ciro", "name": "AYEC Pro Ciro", "active": True},
)


@lru_cache(maxsize=1)
def products() -> tuple[dict, ...]:
    try:
        payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        products = tuple(dict(item) for item in payload.get("products", ()) if item.get("active", True))
        if products:
            return products
    except (OSError, ValueError, TypeError):
        pass
    return tuple(dict(item) for item in _BUILTIN_PRODUCTS)


def product_names() -> tuple[str, ...]:
    return tuple(str(item["name"]) for item in products())


def product_code(product_name: str) -> str:
    wanted = str(product_name or "").strip().casefold()
    return next((str(item["code"]) for item in products() if str(item["name"]).casefold() == wanted), "")


def product_by_code(code: str) -> dict | None:
    wanted = str(code or "").strip().casefold()
    return next((dict(item) for item in products() if str(item["code"]).casefold() == wanted), None)
