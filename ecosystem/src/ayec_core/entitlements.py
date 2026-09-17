"""Ed25519 entitlement signatures with deployment-managed trust anchors.

Only public keys belong in a desktop package. The private key is loaded by the
server from its protected deployment directory and is never sent to clients.
"""

import base64
import copy
import json
from pathlib import Path


def canonical_payload(access):
    return json.dumps({key: value for key, value in access.items() if key != "signature"},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def sign_entitlement(access, private_key, *, key_id):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    if not isinstance(private_key, Ed25519PrivateKey) or not key_id:
        raise ValueError("An Ed25519 signing key and key ID are required")
    result = copy.deepcopy(access)
    result.update(signature_algorithm="Ed25519", key_id=str(key_id))
    result["signature"] = base64.b64encode(private_key.sign(canonical_payload(result))).decode("ascii")
    return result


class EntitlementVerifier:
    def __init__(self, public_keys):
        self.public_keys = dict(public_keys)

    @classmethod
    def from_file(cls, path):
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("version") != 1 or not isinstance(payload.get("keys"), dict):
            raise ValueError("Invalid entitlement trust store")
        return cls(payload["keys"])

    def __call__(self, access):
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        try:
            if access.get("signature_algorithm") != "Ed25519":
                return False
            public_pem = self.public_keys[str(access["key_id"])]
            key = serialization.load_pem_public_key(public_pem.encode("ascii"))
            if not isinstance(key, Ed25519PublicKey):
                return False
            signature = base64.b64decode(access["signature"], validate=True)
            key.verify(signature, canonical_payload(access))
            return True
        except (KeyError, ValueError, TypeError, InvalidSignature):
            return False
