"""Shared protected trial and signed entitlement service for desktop adapters."""

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import threading

from .client import CentralApiError
from .connectivity import classify_error
from .entitlements import EntitlementVerifier
from .license_cache import LicenseCache, _parse
from .storage import LicenseCacheStore, ProtectedJsonStore


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProductLicense:
    def __init__(self, directory, client, *, trial_days=15, verify_signature=None,
                 trial_started="", trial_expires=""):
        self.client = client
        self.directory = Path(directory)
        self.trial_days = int(trial_days)
        self.lock = threading.RLock()
        self.verify_signature = verify_signature or self._verify
        scope = {"product_code": client.product_code, "hardware_id": client.device_id,
                 "installation_id": client.installation_id}
        self.trial_store = ProtectedJsonStore(self.directory / "trial.dat", scope=scope)
        self.load_error = ""
        try:
            self.trial = self.trial_store.load()
            if not self.trial:
                now = utc_now()
                start = min(_parse(trial_started) or now, now)
                end = min(_parse(trial_expires) or start + timedelta(days=trial_days),
                          start + timedelta(days=trial_days))
                self.trial = {"started": start.isoformat(), "expires": end.isoformat(),
                              "last_seen": now.isoformat()}
                self.trial_store.save(self.trial)
        except (OSError, ValueError, TypeError):
            self.trial = {}
            self.load_error = "Protected trial state cannot be read"
        self._load_cache()

    def _verify(self, access):
        configured = os.environ.get("AYEC_LICENSE_PUBLIC_KEYS_FILE", "")
        path = Path(configured) if configured else Path(__file__).with_name("entitlement-keys.json")
        try:
            return EntitlementVerifier.from_file(path)(access)
        except (OSError, ValueError, TypeError):
            return False

    def _load_cache(self):
        self.cache = LicenseCache(product_code=self.client.product_code,
                                  hardware_id=self.client.device_id,
                                  tenant_id=self.client.tenant_id,
                                  installation_id=self.client.installation_id,
                                  require_signature=True)
        self.store = LicenseCacheStore(self.directory / "license.dat", self.cache,
                                       base_url=self.client.base_url)
        try:
            result = self.store.restore(verify_signature=self.verify_signature)
            if result["state"] == "INVALID":
                self.load_error = result["message"]
        except (OSError, ValueError, TypeError):
            self.load_error = "Protected entitlement cannot be read"

    def status(self, *, now=None, offline=False):
        with self.lock:
            now = now or utc_now()
            if self.cache.record:
                result = (self.cache.transport_failure if offline else self.cache.evaluate)(now=now)
                try:
                    self.store.persist()
                except OSError:
                    result["storage_error"] = "License state could not be saved"
                return result
            if self.load_error or not self.trial:
                return {"state": "INVALID", "write_allowed": False, "maintenance_allowed": True,
                        "message": self.load_error or "No trial record"}
            last_seen = _parse(self.trial.get("last_seen"))
            if last_seen and now < last_seen - timedelta(minutes=5):
                return {"state": "CLOCK_SUSPECT", "write_allowed": False,
                        "maintenance_allowed": True, "message": "Local clock moved backwards"}
            end = _parse(self.trial["expires"])
            self.trial["last_seen"] = max(now, last_seen or now).isoformat()
            try:
                self.trial_store.save(self.trial)
            except OSError:
                return {"state": "INVALID", "write_allowed": False,
                        "maintenance_allowed": True, "message": "Trial state could not be saved"}
            allowed = now < end
            return {"state": "TRIAL" if allowed else "EXPIRED", "write_allowed": allowed,
                    "maintenance_allowed": True, "license_type": "trial",
                    "license_start": self.trial["started"], "license_end": end.isoformat(),
                    "days": max(0, (end - now).days), "message": ""}

    def refresh(self, payload):
        # Network I/O must not hold the lock used by UI status readers.
        try:
            response = self.client.status_for_device(payload)
        except (CentralApiError, OSError, TimeoutError, RuntimeError) as error:
            result = self.status(offline=True)
            result.update(ok=False, connectivity=classify_error(error))
            return result
        with self.lock:
            try:
                state = self.cache.apply(response, verify_signature=self.verify_signature)
                self.store.persist()
                self.load_error = ""
                state["ok"] = True
                state["tenant_id"] = str((response.get("tenant") or {}).get("id")
                                         or state.get("tenant_id") or "")
                return state
            except (ValueError, TypeError, KeyError, OSError) as error:
                result = self.status(offline=True)
                result.update(ok=False, connectivity="invalid_entitlement", error=str(error))
                return result

    def bind_tenant(self):
        """Re-scope an accepted cache after the initial tenant has been verified."""
        with self.lock:
            previous = self.cache.export()
            if previous.get("tenant_id") and previous["tenant_id"] != self.client.tenant_id:
                raise ValueError("Cannot transfer an entitlement to another tenant")
            self.cache.tenant_id = self.client.tenant_id
            self.store = LicenseCacheStore(self.directory / "license.dat", self.cache,
                                           base_url=self.client.base_url)
            if previous:
                self.store.persist()
