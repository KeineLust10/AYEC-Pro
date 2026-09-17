"""
AYEC Pro Admin Konsol - API Client
Sunucu ile t\u00fcm HTTP iletisimini y\u00f6netir.
Super Admin token'i oturum boyunca bellekte saklanir.
"""
import json
import threading
import requests
from typing import Any, Optional

import config

_lock = threading.Lock()
_session_token: Optional[str] = None


def _headers() -> dict:
    h = {"Content-Type": "application/json"}
    if _session_token:
        h["Cookie"] = f"ayec_session={_session_token}"
    return h


def _url(path: str) -> str:
    return config.server_url() + path


def _parse(resp: requests.Response) -> dict:
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Sunucu gecersiz yanit verdi ({resp.status_code}): {resp.text[:200]}")
    if not resp.ok:
        raise RuntimeError(data.get("error") or f"Hata ({resp.status_code})")
    return data


# -------------------------------------------------------
# Auth
# -------------------------------------------------------

def login(email: str, password: str) -> dict:
    """Super Admin girisi. Basarili olursa session cookie saklanir."""
    global _session_token
    resp = requests.post(
        _url("/api/admin/login"),
        json={"email": email, "password": password},
        timeout=config.timeout(),
    )
    data = _parse(resp)
    # Cookie'den token al
    cookie = resp.headers.get("Set-Cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("ayec_session="):
            with _lock:
                _session_token = part.split("=", 1)[1]
            break
    return data


def logout() -> None:
    global _session_token
    try:
        requests.post(_url("/api/auth/logout"), headers=_headers(), json={}, timeout=5)
    except Exception:
        pass
    with _lock:
        _session_token = None


# -------------------------------------------------------
# Dashboard
# -------------------------------------------------------

def dashboard() -> dict:
    resp = requests.get(_url("/api/admin/dashboard"), headers=_headers(), timeout=config.timeout())
    return _parse(resp)


# -------------------------------------------------------
# Companies
# -------------------------------------------------------

def companies(search: str = "", product_code: str = "") -> list:
    params = {}
    if search:
        params["q"] = search
    if product_code:
        params["product_code"] = product_code
    resp = requests.get(_url("/api/admin/companies"), headers=_headers(), params=params, timeout=config.timeout())
    return _parse(resp).get("companies", [])


def company_detail(tenant_id: str) -> dict:
    resp = requests.get(_url(f"/api/admin/companies/{tenant_id}"), headers=_headers(), timeout=config.timeout())
    return _parse(resp)


def update_company(tenant_id: str, data: dict) -> dict:
    resp = requests.post(_url(f"/api/admin/companies/{tenant_id}"), headers=_headers(), json=data, timeout=config.timeout())
    return _parse(resp)


def delete_company(tenant_id: str) -> dict:
    resp = requests.post(
        _url(f"/api/admin/companies/{tenant_id}/delete"),
        headers=_headers(),
        json={},
        timeout=config.timeout(),
    )
    return _parse(resp)


def refresh_company_locations() -> dict:
    resp = requests.post(
        _url("/api/admin/companies/locations/refresh"),
        headers=_headers(),
        json={},
        timeout=max(config.timeout(), 120),
    )
    return _parse(resp)


def update_company_sector(tenant_id: str, sector: str) -> dict:
    payload = {"sector": sector}
    resp = requests.post(
        _url(f"/api/admin/companies/{tenant_id}"),
        headers=_headers(),
        json=payload,
        timeout=config.timeout(),
    )
    try:
        return _parse(resp)
    except RuntimeError as admin_error:
        fallback = requests.post(
            _url("/api/control/tenant"),
            headers=_headers(),
            json={"tenant_id": tenant_id, "sector": sector},
            timeout=config.timeout(),
        )
        try:
            return _parse(fallback)
        except RuntimeError as fallback_error:
            raise RuntimeError(
                f"Sektor guncellenemedi. Admin API: {admin_error}; "
                f"Yonetim Merkezi API: {fallback_error}"
            ) from fallback_error


# -------------------------------------------------------
# Users
# -------------------------------------------------------

def company_users(tenant_id: str) -> list:
    resp = requests.get(_url(f"/api/admin/companies/{tenant_id}/users"), headers=_headers(), timeout=config.timeout())
    return _parse(resp).get("users", [])


def repair_company_users(tenant_id: str) -> dict:
    resp = requests.post(
        _url(f"/api/admin/companies/{tenant_id}/repair-users"),
        headers=_headers(),
        json={},
        timeout=max(config.timeout(), 120),
    )
    return _parse(resp)


def reset_user_password(tenant_id: str, user_id: int, new_password: str) -> dict:
    resp = requests.post(
        _url(f"/api/admin/users/{user_id}/reset-password"),
        headers=_headers(),
        json={"tenant_id": tenant_id, "new_password": new_password},
        timeout=config.timeout(),
    )
    return _parse(resp)


def create_password_reset_link(tenant_id: str, user_id: int) -> dict:
    resp = requests.post(
        _url("/api/control/password-reset"),
        headers=_headers(),
        json={"tenant_id": tenant_id, "user_id": int(user_id)},
        timeout=config.timeout(),
    )
    return _parse(resp)


# -------------------------------------------------------
# Backups
# -------------------------------------------------------

def backups(tenant_id: str) -> list:
    resp = requests.get(_url(f"/api/admin/backups/{tenant_id}"), headers=_headers(), timeout=config.timeout())
    return _parse(resp).get("backups", [])


def download_backup(tenant_id: str, backup_index: int, backup_id: int = 0) -> bytes:
    resp = requests.get(
        _url(f"/api/admin/backups/{tenant_id}/download/{backup_index}"),
        headers=_headers(),
        params={"backup_id": int(backup_id)} if backup_id else None,
        timeout=60,
    )
    if not resp.ok:
        raise RuntimeError(f"Yedek indirilemedi ({resp.status_code})")
    return resp.content


def restore_backup(tenant_id: str, backup_index: int, backup_id: int = 0) -> dict:
    resp = requests.post(
        _url(f"/api/admin/backups/{tenant_id}/restore"),
        headers=_headers(),
        json={"backup_index": backup_index, "backup_id": int(backup_id)},
        timeout=config.timeout(),
    )
    return _parse(resp)


# -------------------------------------------------------
# Licenses
# -------------------------------------------------------

def licenses(product_code: str = "") -> list:
    resp = requests.get(_url("/api/admin/licenses"), headers=_headers(), params={"product_code": product_code} if product_code else None, timeout=config.timeout())
    return _parse(resp).get("licenses", [])


def update_license(tenant_id: str, data: dict) -> dict:
    resp = requests.post(_url(f"/api/admin/licenses/{tenant_id}"), headers=_headers(), json=data, timeout=config.timeout())
    return _parse(resp)


def license_orders(status: str = "", product_code: str = "") -> list:
    params = {k: v for k, v in (("status", status), ("product_code", product_code)) if v} or None
    resp = requests.get(
        _url("/api/admin/license-orders"),
        headers=_headers(),
        params=params,
        timeout=config.timeout(),
    )
    return _parse(resp).get("orders", [])


def approve_license_order(order_id: int, admin_note: str = "", plan_code: str = "") -> dict:
    resp = requests.post(
        _url(f"/api/admin/license-orders/{int(order_id)}/approve"),
        headers=_headers(),
        json={"admin_note": admin_note, "plan_code": plan_code},
        timeout=config.timeout(),
    )
    return _parse(resp)


def reject_license_order(order_id: int, admin_note: str = "") -> dict:
    resp = requests.post(
        _url(f"/api/admin/license-orders/{int(order_id)}/reject"),
        headers=_headers(),
        json={"admin_note": admin_note},
        timeout=config.timeout(),
    )
    return _parse(resp)


def cancel_license_order(order_id: int, admin_note: str = "") -> dict:
    resp = requests.post(
        _url(f"/api/admin/license-orders/{int(order_id)}/cancel"),
        headers=_headers(),
        json={"admin_note": admin_note},
        timeout=config.timeout(),
    )
    return _parse(resp)


def provision_invites() -> dict:
    resp = requests.get(
        _url("/api/control/provision-invites"),
        headers=_headers(),
        timeout=config.timeout(),
    )
    return _parse(resp)


def create_provision_invite(expires_in_hours: int = 72, max_uses: int = 1) -> dict:
    resp = requests.post(
        _url("/api/control/provision-invite"),
        headers=_headers(),
        json={"expires_in_hours": int(expires_in_hours), "max_uses": int(max_uses)},
        timeout=config.timeout(),
    )
    return _parse(resp)


def revoke_provision_invite(invite_id: int) -> dict:
    resp = requests.post(
        _url("/api/control/provision-invite/revoke"),
        headers=_headers(),
        json={"invite_id": int(invite_id)},
        timeout=config.timeout(),
    )
    return _parse(resp)



# -------------------------------------------------------
# Notifications
# -------------------------------------------------------

def send_notification(target: str, title: str, body: str, icon: str = "info", popup: bool = True) -> dict:
    resp = requests.post(
        _url("/api/admin/notifications/send"),
        headers=_headers(),
        json={"target": target, "title": title, "body": body, "icon": icon, "popup": popup},
        timeout=config.timeout(),
    )
    return _parse(resp)


# -------------------------------------------------------
# Error Logs
# -------------------------------------------------------

def error_logs(tenant_id: str = "", limit: int = 100) -> list:
    params: dict[str, Any] = {"limit": limit}
    if tenant_id:
        params["tenant_id"] = tenant_id
    resp = requests.get(_url("/api/admin/logs"), headers=_headers(), params=params, timeout=config.timeout())
    return _parse(resp).get("logs", [])


def audit_logs(tenant_id: str = "", limit: int = 200) -> list:
    params: dict[str, Any] = {"limit": limit}
    if tenant_id:
        params["tenant_id"] = tenant_id
    resp = requests.get(
        _url("/api/admin/audit-logs"),
        headers=_headers(),
        params=params,
        timeout=config.timeout(),
    )
    return _parse(resp).get("logs", [])


def readonly_query(tenant_id: str, sql: str) -> dict:
    resp = requests.post(
        _url(f"/api/admin/companies/{tenant_id}/query"),
        headers=_headers(),
        json={"sql": sql},
        timeout=config.timeout(),
    )
    return _parse(resp)


# -------------------------------------------------------
# Server Status
# -------------------------------------------------------

def server_status() -> dict:
    resp = requests.get(_url("/api/admin/server-status"), headers=_headers(), timeout=config.timeout())
    return _parse(resp)


# -------------------------------------------------------
# Live Status
# -------------------------------------------------------

def live_status() -> list:
    resp = requests.get(_url("/api/admin/live-status"), headers=_headers(), timeout=config.timeout())
    return _parse(resp).get("companies", [])


# -------------------------------------------------------
# Updates
# -------------------------------------------------------

def deploy_update(
    version: str,
    targets: list,
    changelog: str,
    channel: str = "pilot",
) -> dict:
    resp = requests.post(
        _url("/api/admin/updates/deploy"),
        headers=_headers(),
        json={
            "version": version,
            "targets": targets,
            "changelog": changelog,
            "channel": channel,
        },
        timeout=config.timeout(),
    )
    return _parse(resp)
