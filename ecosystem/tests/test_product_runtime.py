from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
import threading

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ayec_core.client import CentralApiError, CentralClient
from ayec_core.entitlements import EntitlementVerifier, sign_entitlement
from ayec_core.product_runtime import ProductRuntime


class FixtureClient(CentralClient):
    def __init__(self, key):
        super().__init__("https://example.test", product_code="ciro", device_id="pc1")
        self.key = key
        self.offline = False
        self.revoked = False
        self.last_payload = {}

    def _request(self, path, method="GET", payload=None, **kwargs):
        if self.offline:
            raise CentralApiError("offline") from TimeoutError()
        if path == "/api/auth/login":
            self.cookies["ayec_session"] = "test-session"
            return {"user": {"tenant_id": "tenant1", "email": "test@example.test"}}
        self.last_payload = dict(payload)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        access = {
            "allowed": not self.revoked, "license_status": "revoked" if self.revoked else "active",
            "product_code": self.product_code, "hardware_id": self.device_id,
            "tenant_id": "tenant1", "installation_id": self.installation_id,
            "license_type": "monthly", "license_start": (now - timedelta(days=1)).isoformat(),
            "license_end": (now + timedelta(days=29)).isoformat(), "server_time": now.isoformat(),
        }
        return {"tenant": {"id": "tenant1"}, "access": sign_entitlement(access, self.key, key_id="test")}


class ProductRuntimeTests(unittest.TestCase):
    def make(self, directory, key):
        pem = key.public_key().public_bytes(serialization.Encoding.PEM,
                                           serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")
        return ProductRuntime(directory, product_code="ciro", hardware_id="pc1",
                              base_url="https://example.test", client=FixtureClient(key),
                              verify_signature=EntitlementVerifier({"test": pem}))

    def test_login_binds_queue_and_restart_loads_same_session_and_entitlement(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Ed25519PrivateKey.generate()
            runtime = self.make(directory, key)
            runtime.outbox.enqueue("backup_upload", {"path": "fixture.db"}, now=0)
            result = runtime.login("test@example.test", "temporary-password")
            self.assertTrue(result["ok"])
            self.assertEqual(result["state"], "ACTIVE_ONLINE")
            self.assertEqual(runtime.outbox.scope[1], "tenant1")
            self.assertEqual(runtime.outbox.count_pending(), 1)
            reopened = self.make(directory, key)
            self.assertTrue(reopened.authenticated)
            self.assertEqual(reopened.client.tenant_id, "tenant1")
            reopened.client.offline = True
            state = reopened.refresh_license()
            self.assertEqual(state["state"], "ACTIVE_OFFLINE")
            self.assertEqual(state["connectivity"], "timeout")
            reopened.client.offline = False
            reopened.client.revoked = True
            self.assertEqual(reopened.refresh_license()["state"], "REVOKED")
            self.assertEqual(self.make(directory, key).license.status()["state"], "REVOKED")
            self.assertNotIn(b"temporary-password", (Path(directory) / "outbox.db").read_bytes())

    def test_session_expiry_keeps_queue_and_valid_license(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.make(directory, Ed25519PrivateKey.generate())
            runtime.login("test@example.test", "temporary-password")
            runtime.outbox.enqueue("backup_upload", {"path": "fixture.db"})
            runtime.session_failed(CentralApiError("expired", status_code=401))
            self.assertFalse(runtime.authenticated)
            self.assertEqual(runtime.outbox.count_pending(), 1)
            self.assertTrue(runtime.license.status()["write_allowed"])
            self.assertFalse(runtime.session_path.exists())

    def test_trial_cannot_be_extended_by_recreating_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Ed25519PrivateKey.generate()
            runtime = self.make(directory, key)
            first = runtime.license.status()
            self.assertEqual(first["state"], "TRIAL")
            self.assertEqual(self.make(directory, key).license.status()["license_end"], first["license_end"])
            with self.assertRaises(ValueError):
                runtime._bind_tenant("")
            runtime._bind_tenant("tenant1")
            with self.assertRaises(ValueError):
                runtime._bind_tenant("tenant2")

    def test_ui_status_does_not_wait_for_a_slow_license_request(self):
        with tempfile.TemporaryDirectory() as directory:
            runtime = self.make(directory, Ed25519PrivateKey.generate())
            runtime.set_profile(email="test@example.test")
            started = threading.Event()
            release = threading.Event()
            finished = threading.Event()
            def slow(_payload):
                started.set()
                release.wait(2)
                raise TimeoutError()
            runtime.client.status_for_device = slow
            network = threading.Thread(target=runtime.refresh_license)
            network.start()
            self.assertTrue(started.wait(1))
            reader = threading.Thread(target=lambda: (runtime.license.status(), finished.set()))
            reader.start()
            try:
                self.assertTrue(finished.wait(0.5), "UI status waited for network")
            finally:
                release.set()
                network.join()
                reader.join()
