import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ayec_core.entitlements import EntitlementVerifier, sign_entitlement


class EntitlementTests(unittest.TestCase):
    def test_only_trusted_key_and_unchanged_payload_are_accepted(self):
        key = Ed25519PrivateKey.generate()
        pem = key.public_key().public_bytes(serialization.Encoding.PEM,
                                           serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")
        verifier = EntitlementVerifier({"test": pem})
        signed = sign_entitlement({"allowed": True, "hardware_id": "pc1"}, key, key_id="test")
        self.assertTrue(verifier(signed))
        self.assertFalse(verifier(dict(signed, hardware_id="pc2")))
        self.assertFalse(verifier(dict(signed, allowed=False)))
        self.assertFalse(verifier(dict(signed, key_id="unknown")))
        forged = sign_entitlement({"allowed": True, "hardware_id": "pc1"},
                                  Ed25519PrivateKey.generate(), key_id="test")
        self.assertFalse(verifier(forged))
