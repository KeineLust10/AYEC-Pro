"""Compatibility verification for issued AYEC HWID-bound license keys."""
import hashlib
import hmac


def verify_legacy_key(input_key, hardware_id):
    """Verify existing keys; server entitlement still owns paid duration."""
    if not isinstance(input_key, str) or not isinstance(hardware_id, str) or not hardware_id:
        return False
    digest = hashlib.sha256((hardware_id + "BULUT_TEKNIK_SERVIS_2026_SECURE_SALT_!@#").encode()).hexdigest().upper()[:25]
    expected = "-".join(digest[index:index + 5] for index in range(0, 25, 5))
    return hmac.compare_digest(input_key.encode(), expected.encode())
