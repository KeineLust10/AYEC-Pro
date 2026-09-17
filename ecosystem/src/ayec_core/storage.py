"""Atomic protected persistence for central identity and entitlement state."""

import json
import os
from pathlib import Path
import secrets

from .session import protect_current_user, unprotect_current_user


class ProtectedJsonStore:
    def __init__(self, path, *, scope, protect=protect_current_user, unprotect=unprotect_current_user):
        self.path = Path(path).expanduser().resolve()
        self.scope = dict(scope)
        self.protect = protect
        self.unprotect = unprotect

    def load(self):
        if not self.path.exists():
            return {}
        raw = self.path.read_bytes()
        if len(raw) > 2_000_000:
            raise ValueError("Protected record is too large")
        envelope = json.loads(self.unprotect(raw).decode("utf-8"))
        if not isinstance(envelope, dict) or envelope.get("scope") != self.scope:
            raise ValueError("Protected record scope mismatch")
        value = envelope.get("value")
        if not isinstance(value, dict):
            raise ValueError("Invalid protected record")
        return value

    def save(self, value):
        raw = json.dumps({"version": 1, "scope": self.scope, "value": value},
                         ensure_ascii=True, sort_keys=True).encode("utf-8")
        protected = self.protect(raw)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + "." + secrets.token_hex(8) + ".tmp")
        try:
            with temporary.open("xb") as handle:
                handle.write(protected)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            temporary.unlink(missing_ok=True)


class LicenseCacheStore(ProtectedJsonStore):
    def __init__(self, path, cache, *, base_url, **kwargs):
        self.cache = cache
        super().__init__(path, scope={
            "base_url": str(base_url).rstrip("/"), "product_code": cache.product_code,
            "tenant_id": cache.tenant_id, "installation_id": cache.installation_id,
            "hardware_id": cache.hardware_id,
        }, **kwargs)

    def restore(self, *, verify_signature=None, now=None):
        return self.cache.load(super().load(), verify_signature=verify_signature, now=now)

    def persist(self):
        self.save(self.cache.export())
