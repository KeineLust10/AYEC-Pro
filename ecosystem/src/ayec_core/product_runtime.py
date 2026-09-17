"""Shared central identity, protected session, license and durable outbox."""

import json
from pathlib import Path
import threading
import uuid

from .client import CentralApiError, CentralClient
from .outbox import DurableOutbox
from .product_license import ProductLicense
from .storage import ProtectedJsonStore


class ProductRuntime:
    def __init__(self, directory, *, product_code, hardware_id, base_url,
                 client=None, verify_signature=None, trial_started="", trial_expires=""):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.identity_store = ProtectedJsonStore(
            self.directory / "identity.dat", scope={"product_code": product_code,
                                                    "hardware_id": hardware_id})
        self.identity = self.identity_store.load()
        if not self.identity:
            self.identity = {"installation_id": str(uuid.uuid4()), "tenant_id": "", "profile": {}}
            self.identity_store.save(self.identity)
        self.client = client or CentralClient(base_url, product_code=product_code, device_id=hardware_id)
        self.client.product_code = product_code
        self.client.device_id = hardware_id
        self.client.base_url = base_url.rstrip("/")
        self.client.installation_id = self.identity["installation_id"]
        self.client.tenant_id = self.identity.get("tenant_id", "")
        self.session_path = self.directory / "session.dat"
        self.session_state = "SIGN_IN_REQUIRED"
        if hasattr(self.client, "load_session"):
            try:
                self.client.load_session(self.session_path)
                if self.authenticated:
                    self.session_state = "READY"
            except (ValueError, OSError):
                self.client.cookies.clear()
                self.session_state = "SESSION_INVALID"
        self.outbox = self._outbox()
        self.license = ProductLicense(self.directory, self.client, verify_signature=verify_signature,
                                      trial_started=trial_started, trial_expires=trial_expires)

    def _outbox(self):
        return DurableOutbox(self.directory / "outbox.db", product_code=self.client.product_code,
                             tenant_id=self.client.tenant_id or "local",
                             installation_id=self.client.installation_id)

    @property
    def authenticated(self):
        return bool(self.client.tenant_id and getattr(self.client, "cookies", {}))

    def set_profile(self, *, email="", company="", contact="", phone=""):
        with self.lock:
            self.identity["profile"] = {"requester_email": str(email).strip(),
                                        "company_name": str(company).strip(),
                                        "requester_name": str(contact).strip(),
                                        "requester_phone": str(phone).strip()}
            self.identity_store.save(self.identity)

    def _bind_tenant(self, tenant_id):
        tenant_id = str(tenant_id or "")
        existing = self.identity.get("tenant_id") or ""
        if not tenant_id or (existing and tenant_id != existing):
            raise ValueError("Tenant change requires a separate product data directory")
        self.client.tenant_id = tenant_id
        self.identity["tenant_id"] = tenant_id
        self.identity_store.save(self.identity)
        if self.outbox.scope[1] == "local":
            self.outbox.bind_tenant(tenant_id)
        self.outbox = self._outbox()
        self.license.bind_tenant()

    def login(self, identifier, password, *, tenant_id=""):
        with self.lock:
            known = self.identity.get("tenant_id") or ""
            if known and tenant_id and known != tenant_id:
                raise ValueError("This database belongs to another tenant")
            result = self.client.login(identifier, password, tenant_id or known)
            self._bind_tenant(self.client.tenant_id)
            user = result.get("user") or {}
            profile = self.identity.setdefault("profile", {})
            if not profile.get("requester_email"):
                profile["requester_email"] = str(user.get("email") or identifier)
            if not profile.get("company_name"):
                profile["company_name"] = str(user.get("company_name") or "")
            self.identity_store.save(self.identity)
            self.client.save_session(self.session_path)
            self.session_state = "READY"
            # Credentials are only used for the initial binding; never persisted.
            return self.refresh_license(identifier=identifier, password=password)

    def refresh_license(self, **extra):
        with self.lock:
            payload = dict(self.identity.get("profile") or {})
            payload.update(extra)
            if not payload.get("requester_email"):
                state = self.license.status(offline=True)
                state.update(ok=False, connectivity="identity_required")
                return state
            result = self.license.refresh(payload)
            if result.get("ok") and result.get("tenant_id"):
                self._bind_tenant(result["tenant_id"])
            return result

    def activate(self, key):
        key = str(key or "").strip()
        if not key:
            raise ValueError("License key is required")
        return self.refresh_license(license_key=key)

    def session_failed(self, error):
        if getattr(error, "status_code", None) == 401:
            self.client.clear_session(self.session_path)
            self.session_state = "SIGN_IN_REQUIRED"

    def status(self):
        return {"session": self.session_state, "tenant_id": self.identity.get("tenant_id", ""),
                "installation_id": self.client.installation_id, "hardware_id": self.client.device_id,
                "profile": dict(self.identity.get("profile") or {}), "queued": self.outbox.count_pending(),
                "license": self.license.status()}
