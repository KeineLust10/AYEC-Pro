"""Deployment configuration for signed desktop license responses."""

import json
import os
from pathlib import Path

from ayec_core.entitlements import sign_entitlement


def sign_access(access):
    key_path = os.environ.get("AYEC_LICENSE_SIGNING_KEY_FILE", "")
    key_id = os.environ.get("AYEC_LICENSE_SIGNING_KEY_ID", "")
    if not key_path or not key_id:
        raise RuntimeError("Configure the server signing key and distribute its public key")
    from cryptography.hazmat.primitives import serialization
    try:
        private_key = serialization.load_pem_private_key(Path(key_path).read_bytes(), password=None)
    except (OSError, ValueError, TypeError) as error:
        raise RuntimeError("Entitlement signing key cannot be loaded") from error
    policy = {"offline_days": 7, "safety_days": 3}
    catalog_path = Path(__file__).resolve().parent.parent / "ecosystem" / "products.json"
    if not catalog_path.exists():
        catalog_path = Path(__file__).resolve().parent / "ecosystem" / "products.json"
    try:
        products = json.loads(catalog_path.read_text(encoding="utf-8")).get("products", [])
        product = next(item for item in products if item["code"] == access["product_code"])
        policy.update(product.get("offline_policy") or {})
    except (OSError, ValueError, KeyError, StopIteration):
        pass
    return sign_entitlement(dict(access, offline_policy=policy), private_key, key_id=key_id)
