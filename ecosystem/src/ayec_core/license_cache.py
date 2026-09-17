"""Device-bound entitlement evaluation shared by AYEC desktop products."""

import copy
from datetime import datetime, timedelta, timezone


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse(value):
    if not value:
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


class LicenseCache:
    """Only a trusted server response grants access, never a local key.

    Production adapters require signatures and provide a trusted verifier.
    Unsigned mode supports callers that authenticate the response separately.
    """

    def __init__(self, *, product_code, hardware_id, tenant_id="", installation_id="",
                 offline_days=7, safety_days=3, clock_skew_minutes=5,
                 require_signature=False):
        if not product_code or not hardware_id:
            raise ValueError("product_code and hardware_id are required")
        if not 0 <= int(offline_days) <= 365 or not 0 <= int(safety_days) <= 30:
            raise ValueError("Invalid offline policy")
        self.product_code = str(product_code)
        self.hardware_id = str(hardware_id)
        self.tenant_id = str(tenant_id or "")
        self.installation_id = str(installation_id or "")
        self.offline_days = int(offline_days)
        self.safety_days = int(safety_days)
        self.clock_skew = timedelta(minutes=int(clock_skew_minutes))
        self.require_signature = bool(require_signature)
        self.record = {}

    def _check_identity(self, access):
        for field, expected in (("product_code", self.product_code),
                                ("hardware_id", self.hardware_id),
                                ("tenant_id", self.tenant_id),
                                ("installation_id", self.installation_id)):
            if expected and access.get(field, None if self.require_signature else expected) != expected:
                raise ValueError("Entitlement {} mismatch".format(field))

    def load(self, record, *, verify_signature=None, now=None):
        """Revalidate the signed payload before trusting a persisted record."""
        self.record = {}
        if not record:
            return self.evaluate(now=now)
        candidate = copy.deepcopy(record)
        try:
            self._check_identity(candidate)
            if self.require_signature:
                access = candidate.get("entitlement") or {}
                last_success = _parse(candidate.get("last_success"))
                if not last_success:
                    raise ValueError("Missing successful check time")
                self.apply({"access": access}, now=last_success, verify_signature=verify_signature)
                self.record["last_seen"] = str(candidate.get("last_seen") or candidate["last_success"])
            else:
                self.record = candidate
            return self.transport_failure(now=now)
        except (ValueError, TypeError, KeyError):
            self.record = {}
            return self._state("INVALID", "Cached entitlement is not valid")

    def export(self):
        return copy.deepcopy(self.record)

    def apply(self, response, *, now=None, verify_signature=None):
        access = copy.deepcopy((response or {}).get("access") or {})
        if type(access.get("allowed")) is not bool:
            raise ValueError("Entitlement allowed flag is invalid")
        self._check_identity(access)
        if self.require_signature and (not access.get("signature") or not callable(verify_signature)):
            raise ValueError("A trusted entitlement signature verifier is required")
        if access.get("signature"):
            if not callable(verify_signature) or not verify_signature(access):
                raise ValueError("Entitlement signature is invalid")
        current = _parse(now) if now else _utc_now()
        server_time = _parse(access.get("server_time"))
        previous_time = _parse(self.record.get("server_time"))
        if previous_time and (not server_time or server_time < previous_time):
            raise ValueError("Entitlement predates the last server response")
        if server_time and abs(server_time - current) > self.clock_skew:
            raise ValueError("Server and local clock disagree")
        policy = access.get("offline_policy") or {}
        offline_days = int(policy.get("offline_days", self.offline_days))
        safety_days = int(policy.get("safety_days", self.safety_days))
        if not 0 <= offline_days <= 365 or not 0 <= safety_days <= 30:
            raise ValueError("Invalid central offline policy")
        status = str(access.get("license_status") or "").strip().casefold()
        reason = str(access.get("reason_code") or "").strip().casefold()
        license_type = str(access.get("license_type") or "").strip()
        start = _parse(access.get("license_start"))
        end = _parse(access.get("license_end"))
        if access["allowed"]:
            if not license_type or not start:
                raise ValueError("Entitlement dates are incomplete")
            if not end and license_type.casefold() not in {"lifetime", "sinirsiz"}:
                raise ValueError("A finite license requires an end date")
            if end and end <= start:
                raise ValueError("Entitlement end precedes start")
            if start > current + self.clock_skew:
                raise ValueError("Entitlement starts in the future")
            state = "ACTIVE_ONLINE"
        elif reason == "expired" or status in {"expired", "ended"} or (end and current >= end):
            state = "EXPIRED"
        elif reason == "revoked" or status in {"revoked", "inactive", "passive", "cancelled", "canceled"}:
            state = "REVOKED"
        else:
            state = "INACTIVE"
        self.record = {
            "state": state, "product_code": self.product_code, "hardware_id": self.hardware_id,
            "tenant_id": str(access.get("tenant_id") or self.tenant_id),
            "installation_id": self.installation_id, "license_type": license_type,
            "license_status": status, "license_start": start.isoformat() if start else "",
            "license_end": end.isoformat() if end else "", "allowed": access["allowed"],
            "last_success": current.isoformat(), "last_seen": current.isoformat(),
            "server_time": server_time.isoformat() if server_time else "",
            "offline_days": offline_days, "safety_days": safety_days,
            "message": str(access.get("message") or ""), "entitlement": access,
        }
        return self.evaluate(now=current)

    def _evaluate(self, current, offline):
        if not self.record:
            return self._state("OFFLINE", "No cached entitlement")
        if self.record.get("allowed") is False or self.record.get("state") in {"REVOKED", "INACTIVE"}:
            return self._state(self.record["state"], self.record.get("message", "License is not active"))
        last_seen = _parse(self.record.get("last_seen")) or _parse(self.record.get("last_success"))
        if last_seen and current < last_seen - self.clock_skew:
            return self._state("CLOCK_SUSPECT", "Local clock moved backwards")
        self.record["last_seen"] = max(current, last_seen or current).isoformat()
        end = _parse(self.record.get("license_end"))
        if end and current >= end:
            return self._state("EXPIRED", "Entitlement expiry has passed")
        last_success = _parse(self.record.get("last_success"))
        if not last_success:
            return self._state("OFFLINE", "No successful server check")
        age = current - last_success
        offline_days = int(self.record.get("offline_days", self.offline_days))
        safety_days = int(self.record.get("safety_days", self.safety_days))
        if age <= timedelta(days=offline_days):
            state = "ACTIVE_OFFLINE" if offline or age > timedelta(hours=6) else "ACTIVE_ONLINE"
            return self._state(state, "Using cached entitlement" if offline else "")
        if age <= timedelta(days=offline_days + safety_days):
            return self._state("RECHECK_REQUIRED", "Server check is overdue; export and backup remain available")
        return self._state("EXPIRED", "Offline allowance has passed")

    def transport_failure(self, *, now=None):
        return self._evaluate(_parse(now) if now else _utc_now(), True)

    def evaluate(self, *, now=None):
        return self._evaluate(_parse(now) if now else _utc_now(), False)

    def clock_rollback(self, *, now=None):
        return self.evaluate(now=now)

    def _state(self, state, message):
        result = {key: value for key, value in self.record.items() if key != "entitlement"}
        result.update(state=state, message=str(message or ""),
                      write_allowed=state in {"ACTIVE_ONLINE", "ACTIVE_OFFLINE"},
                      maintenance_allowed=True)
        return result
