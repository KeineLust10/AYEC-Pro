from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ayec_core.license_cache import LicenseCache
from ayec_core.storage import LicenseCacheStore, ProtectedJsonStore


class StorageTests(unittest.TestCase):
    def test_replace_failure_preserves_last_good_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protected"
            store = ProtectedJsonStore(path, scope={"product": "ciro"})
            store.save({"value": 1})
            with patch("ayec_core.storage.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    store.save({"value": 2})
            self.assertEqual(store.load(), {"value": 1})
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_foreign_scope_and_corruption_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "protected"
            first = ProtectedJsonStore(path, scope={"product": "ciro"})
            first.save({"value": 1})
            foreign = ProtectedJsonStore(path, scope={"product": "elek"})
            with self.assertRaises(ValueError):
                foreign.load()
            path.write_bytes(b"broken")
            with self.assertRaises((ValueError, OSError)):
                first.load()

    def test_signed_cache_roundtrip_and_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            now = datetime(2026, 9, 17, 12)
            cache = LicenseCache(product_code="ciro", hardware_id="pc-1", tenant_id="t1",
                                 installation_id="i1", require_signature=True)
            access = dict(product_code="ciro", hardware_id="pc-1", tenant_id="t1",
                          installation_id="i1", allowed=True, license_type="monthly",
                          license_start="2026-09-01", license_end="2026-10-01", signature="test-only")
            verifier = lambda value: value.get("signature") == "test-only"
            cache.apply({"access": access}, now=now, verify_signature=verifier)
            store = LicenseCacheStore(Path(directory) / "cache", cache, base_url="https://example.test")
            store.persist()
            self.assertEqual(store.restore(now=now + timedelta(days=1), verify_signature=verifier)["state"],
                             "ACTIVE_OFFLINE")
            self.assertEqual(store.restore(now=now, verify_signature=lambda value: False)["state"], "INVALID")
            foreign = LicenseCacheStore(store.path, cache, base_url="https://other.test")
            with self.assertRaises(ValueError):
                foreign.restore(now=now, verify_signature=verifier)
