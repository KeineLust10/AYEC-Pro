import hashlib
import unittest
from ayec_core.licensing import verify_legacy_key


class LicenseCompatibilityTests(unittest.TestCase):
    def test_issued_key_and_wrong_device(self):
        device = "FIXTURE-DEVICE"
        raw = hashlib.sha256((device + "BULUT_TEKNIK_SERVIS_2026_SECURE_SALT_!@#").encode()).hexdigest().upper()[:25]
        key = "-".join(raw[i:i + 5] for i in range(0, 25, 5))
        self.assertTrue(verify_legacy_key(key, device))
        self.assertFalse(verify_legacy_key(key, "OTHER-DEVICE"))
        self.assertFalse(verify_legacy_key("ABCDE-ABCDE-ABCDE-ABCDE-ABCDE", device))
        self.assertFalse(verify_legacy_key(None, device))
