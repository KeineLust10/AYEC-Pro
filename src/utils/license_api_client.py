"""Independent AYEC Pro licensing API client."""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request


DEFAULT_LICENSE_API_URL = "https://lisans.ayecpro.com"


class LicenseApiError(RuntimeError):
    def __init__(self, message, *, status_code=0):
        super().__init__(message)
        self.status_code = int(status_code or 0)


ELEK_PRODUCT_CODE = "elek"


def configured_license_api_url() -> str:
    return str(
        os.environ.get("AYEC_LICENSE_API_URL") or DEFAULT_LICENSE_API_URL
    ).strip().rstrip("/")


class LicenseApiClient:
    def __init__(self, base_url="", *, timeout=20, verify_tls=True):
        self.base_url = str(base_url or configured_license_api_url()).rstrip("/")
        self.timeout = int(timeout)
        self.context = (
            ssl.create_default_context()
            if verify_tls
            else ssl._create_unverified_context()
        )

    def _request(self, path, method="GET", payload=None):
        body = None
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "AYEC-Pro-License/1.0",
        }
        request = urllib.request.Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=self.context,
            ) as response:
                raw = response.read().decode("utf-8")
                try:
                    result = json.loads(raw)
                except json.JSONDecodeError as error:
                    raise LicenseApiError(
                        "Lisans servisi guncel bir JSON yaniti vermedi."
                    ) from error
        except urllib.error.HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8"))
            except Exception:
                detail = {"error": str(error)}
            raise LicenseApiError(
                str(detail.get("error") or detail),
                status_code=getattr(error, "code", 0),
            ) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise LicenseApiError(
                f"AYEC Pro lisans servisine baglanilamadi: {error}"
            ) from error
        if not isinstance(result, dict):
            raise LicenseApiError("Lisans servisi gecersiz yanit verdi.")
        if result.get("error"):
            raise LicenseApiError(str(result["error"]))
        return result

    def catalog(self):
        return self._request("/api/license/catalog")

    def create_order(self, payload):
        data = dict(payload or {})
        data.setdefault("product_code", ELEK_PRODUCT_CODE)
        return self._request("/api/license/orders/device", "POST", data)

    def status_for_device(self, payload):
        return self._request("/api/license/status/device", "POST", payload)

    def status_for_credentials(self, identifier, password, tenant_id=""):
        return self._request(
            "/api/license/status/public",
            "POST",
            {
                "identifier": identifier,
                "password": password,
                "tenant_id": tenant_id,
            },
        )

    def activate_invitation(self, identifier, password, invitation_code):
        return self._request(
            "/api/license/activate",
            "POST",
            {
                "identifier": str(identifier or "").strip(),
                "password": str(password or ""),
                "invitation_code": str(invitation_code or "").strip(),
            },
        )
