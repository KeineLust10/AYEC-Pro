from datetime import datetime, timedelta
import unittest

from ayec_core.license_cache import LicenseCache


class LicenseCacheTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 16, 12, 0, 0)
        self.cache = LicenseCache(product_code="elek", hardware_id="pc-1")
        self.base = {
            "allowed": True, "product_code": "elek", "hardware_id": "pc-1",
            "license_type": "one_year",
            "license_start": "2026-01-01T00:00:00",
            "license_end": "2027-01-01T00:00:00",
        }

    def test_transport_failure_uses_cache_then_safety_window(self):
        self.cache.apply({"access": self.base}, now=self.now)
        self.assertEqual(self.cache.transport_failure(now=self.now + timedelta(days=6))["state"], "ACTIVE_OFFLINE")
        self.assertEqual(self.cache.transport_failure(now=self.now + timedelta(days=8))["state"], "RECHECK_REQUIRED")
        self.assertEqual(self.cache.transport_failure(now=self.now + timedelta(days=11))["state"], "EXPIRED")

    def test_only_verified_denial_revokes(self):
        self.cache.apply({"access": self.base}, now=self.now)
        denied = dict(self.base, allowed=False, license_status="revoked", message="revoked by admin")
        self.assertEqual(self.cache.apply({"access": denied}, now=self.now)["state"], "REVOKED")
        self.assertEqual(self.cache.transport_failure(now=self.now + timedelta(days=30))["state"], "REVOKED")

    def test_expired_denial_is_not_reported_as_revocation(self):
        self.cache.apply({"access": self.base}, now=self.now)
        denied = dict(self.base, allowed=False, license_status="expired", message="License suresi doldu")
        self.assertEqual(self.cache.apply({"access": denied}, now=self.now)["state"], "EXPIRED")
        self.assertEqual(self.cache.transport_failure(now=self.now + timedelta(days=1))["state"], "EXPIRED")

    def test_identity_dates_and_clock_are_checked(self):
        with self.assertRaises(ValueError):
            self.cache.apply({"access": dict(self.base, hardware_id="other")}, now=self.now)
        with self.assertRaises(ValueError):
            self.cache.apply({"access": dict(self.base, license_end="2025-01-01T00:00:00")}, now=self.now)
        self.cache.apply({"access": self.base}, now=self.now)
        self.assertEqual(self.cache.clock_rollback(now=self.now - timedelta(hours=1))["state"], "CLOCK_SUSPECT")

    def test_signature_can_be_required(self):
        strict = LicenseCache(product_code="elek", hardware_id="pc-1", require_signature=True)
        with self.assertRaises(ValueError):
            strict.apply({"access": self.base}, now=self.now)
        signed = dict(self.base, signature="fixture")
        with self.assertRaises(ValueError):
            strict.apply({"access": signed}, now=self.now)
        self.assertEqual(strict.apply({"access": signed}, now=self.now,
                                      verify_signature=lambda access: True)["state"], "ACTIVE_ONLINE")

    def test_finite_license_cannot_become_lifetime(self):
        with self.assertRaises(ValueError):
            self.cache.apply({"access": dict(self.base, license_end="")}, now=self.now)

    def test_expiry_has_no_offline_extension(self):
        end = self.now + timedelta(minutes=1)
        self.cache.apply({"access": dict(self.base, license_end=end.isoformat())}, now=self.now)
        self.assertEqual(self.cache.transport_failure(now=end)["state"], "EXPIRED")

    def test_policy_and_last_seen_survive_restart(self):
        access = dict(self.base, offline_policy={"offline_days": 2, "safety_days": 1})
        self.cache.apply({"access": access}, now=self.now)
        observed = self.now + timedelta(days=1)
        self.cache.evaluate(now=observed)
        clone = LicenseCache(product_code="elek", hardware_id="pc-1")
        self.assertEqual(clone.load(self.cache.export(), now=observed)["state"], "ACTIVE_OFFLINE")
        self.assertEqual(clone.evaluate(now=observed - timedelta(hours=1))["state"], "CLOCK_SUSPECT")
        self.assertEqual(clone.evaluate(now=self.now + timedelta(days=2, hours=1))["state"], "RECHECK_REQUIRED")
        self.assertEqual(clone.evaluate(now=self.now + timedelta(days=4))["state"], "EXPIRED")

    def test_invalid_signature_does_not_replace_accepted_entitlement(self):
        self.cache.apply({"access": self.base}, now=self.now)
        previous = self.cache.export()
        with self.assertRaises(ValueError):
            self.cache.apply({"access": dict(self.base, signature="fake")}, now=self.now,
                             verify_signature=lambda access: False)
        self.assertEqual(self.cache.export(), previous)

    def test_generic_denial_is_inactive_not_revoked(self):
        denied = dict(self.base, allowed=False, license_status="unknown")
        self.assertEqual(self.cache.apply({"access": denied}, now=self.now)["state"], "INACTIVE")

    def test_older_server_response_cannot_undo_revocation(self):
        revoked = dict(self.base, allowed=False, license_status="revoked",
                       server_time=self.now.isoformat())
        self.cache.apply({"access": revoked}, now=self.now)
        with self.assertRaises(ValueError):
            self.cache.apply({"access": dict(self.base, server_time=(self.now - timedelta(seconds=1)).isoformat())},
                             now=self.now)
        self.assertEqual(self.cache.evaluate(now=self.now)["state"], "REVOKED")
