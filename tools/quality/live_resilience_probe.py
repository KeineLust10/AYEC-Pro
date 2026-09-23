"""Controlled live AYEC resilience verification gate.

The default mode is read-only and checks HTTPS/TLS plus the central catalog.
Mutation steps are deliberately opt-in and require all credentials and test
identities through environment variables. Secrets are never printed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sqlite3
import ssl
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE_URL = os.environ.get("AYEC_LIVE_BASE_URL", "https://lisans.ayecpro.com").rstrip("/")
PRODUCT = os.environ.get("AYEC_LIVE_PRODUCT_CODE", "barkod_okuyucu")
REQUIRED_MUTATION_VARS = (
    "AYEC_LIVE_CUSTOMER_EMAIL",
    "AYEC_LIVE_CUSTOMER_PASSWORD",
    "AYEC_LIVE_ADMIN_EMAIL",
    "AYEC_LIVE_ADMIN_PASSWORD",
    "AYEC_LIVE_HARDWARE_ID",
    "AYEC_LIVE_INSTALLATION_ID",
)


def _env(name: str) -> str:
    return str(os.environ.get(name) or "").strip()


def _tls_probe(host: str) -> dict:
    addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)})
    context = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=15) as raw:
        with context.wrap_socket(raw, server_hostname=host) as stream:
            certificate = stream.getpeercert()
            return {
                "host": host,
                "addresses": addresses,
                "protocol": stream.version(),
                "subject": dict(item[0] for item in certificate.get("subject", ())),
                "issuer": dict(item[0] for item in certificate.get("issuer", ())),
                "not_after": certificate.get("notAfter", ""),
            }


def _request(session: requests.Session, method: str, path: str, **kwargs):
    response = session.request(method, BASE_URL + path, timeout=30, **kwargs)
    try:
        payload = response.json()
    except ValueError:
        payload = {"raw_length": len(response.content)}
    return response, payload


def _scoped_headers(product: str, hardware: str, installation: str) -> dict:
    return {
        "X-AYEC-Product-Code": product,
        "X-AYEC-Device-ID": hardware,
        "X-AYEC-Installation-ID": installation,
    }


def _make_fixture_database() -> tuple[tempfile.TemporaryDirectory, Path]:
    holder = tempfile.TemporaryDirectory(prefix="ayec-live-")
    path = Path(holder.name) / "verification.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE verification(value TEXT NOT NULL)")
        connection.execute("INSERT INTO verification(value) VALUES (?)", ("AYEC live verification",))
        connection.commit()
    finally:
        connection.close()
    return holder, path


def _catalog(session: requests.Session) -> dict:
    response, payload = _request(session, "GET", "/api/license/catalog")
    if response.status_code != 200:
        raise RuntimeError(f"catalog HTTP {response.status_code}")
    plans = payload.get("plans") or []
    return {
        "status": response.status_code,
        "product": PRODUCT,
        "plans": [
            {key: row.get(key) for key in ("code", "duration_months", "amount_try", "currency")}
            for row in plans if isinstance(row, dict)
        ],
    }


def _mutation_preflight() -> list[str]:
    return [name for name in REQUIRED_MUTATION_VARS if not _env(name)]


def _execute_mutation_flow(session: requests.Session) -> dict:
    missing = _mutation_preflight()
    if missing:
        raise RuntimeError("Missing live mutation variables: " + ", ".join(missing))
    hardware = _env("AYEC_LIVE_HARDWARE_ID")
    installation = _env("AYEC_LIVE_INSTALLATION_ID")
    if len(hardware) < 12:
        raise RuntimeError("AYEC_LIVE_HARDWARE_ID must be at least 12 characters")

    customer_email = _env("AYEC_LIVE_CUSTOMER_EMAIL")
    customer_password = _env("AYEC_LIVE_CUSTOMER_PASSWORD")
    admin_email = _env("AYEC_LIVE_ADMIN_EMAIL")
    admin_password = _env("AYEC_LIVE_ADMIN_PASSWORD")
    order_payload = {
        "hardware_id": hardware,
        "installation_id": installation,
        "product_code": PRODUCT,
        "plan_code": _env("AYEC_LIVE_PLAN_CODE") or "monthly",
        "company_name": _env("AYEC_LIVE_COMPANY") or "AYEC Live Verification",
        "requester_name": _env("AYEC_LIVE_REQUESTER") or "AYEC Live Verification",
        "requester_email": customer_email,
        "identifier": customer_email,
        "password": customer_password,
        "payment_reported": True,
    }
    result: dict = {"product": PRODUCT, "hardware_hash": hashlib.sha256(hardware.encode()).hexdigest()[:12]}
    response, payload = _request(session, "POST", "/api/license/orders/device", json=order_payload)
    if response.status_code not in (200, 201):
        raise RuntimeError(f"license order HTTP {response.status_code}: {payload.get('error', 'unknown')}")
    order = payload.get("order") or payload
    result["order_id"] = order.get("id")
    result["request_no"] = order.get("request_no")
    tenant_id = str(order.get("tenant_id") or "")

    customer = requests.Session()
    response, payload = _request(customer, "POST", "/api/auth/login", json={
        "identifier": customer_email, "password": customer_password, "remember": True,
    })
    if response.status_code != 200:
        raise RuntimeError(f"customer login HTTP {response.status_code}")
    user = payload.get("user") or {}
    tenant_id = tenant_id or str(user.get("tenant_id") or user.get("_tenant_id") or "")
    if not tenant_id:
        raise RuntimeError("customer login did not return a tenant id")
    result["customer_login"] = True

    device_payload = {
        "requester_email": customer_email,
        "requester_name": _env("AYEC_LIVE_REQUESTER") or "AYEC Live Verification",
        "hardware_id": hardware,
        "installation_id": installation,
        "product_code": PRODUCT,
        "tenant_id": tenant_id,
    }
    response, payload = _request(customer, "POST", "/api/license/status/device",
                                 json=device_payload,
                                 headers=_scoped_headers(PRODUCT, hardware, installation))
    if response.status_code != 200:
        raise RuntimeError(f"license status before revoke HTTP {response.status_code}")
    access = payload.get("access") or {}
    result["status_before_revoke"] = {
        "http": response.status_code,
        "license_status": access.get("license_status"),
        "allowed": access.get("allowed"),
    }

    admin = requests.Session()
    response, payload = _request(admin, "POST", "/api/admin/login", json={"email": admin_email, "password": admin_password})
    if response.status_code != 200:
        raise RuntimeError(f"admin login HTTP {response.status_code}")
    result["admin_login"] = True
    result["admin_session_cookie"] = bool(admin.cookies)
    response, payload = _request(admin, "POST", f"/api/admin/license-orders/{int(order['id'])}/approve",
                                 json={"plan_code": order.get("plan_code") or _env("AYEC_LIVE_PLAN_CODE") or "monthly",
                                       "admin_note": "AYEC controlled resilience verification"})
    if response.status_code != 200:
        raise RuntimeError(f"license approval HTTP {response.status_code}: {payload.get('error', 'unknown')}")
    result["approval"] = {"http": response.status_code, "mail_sent": payload.get("mail_sent")}

    response, payload = _request(customer, "POST", "/api/license/status/device",
                                 json=device_payload,
                                 headers=_scoped_headers(PRODUCT, hardware, installation))
    if response.status_code != 200:
        raise RuntimeError(f"license status after approval HTTP {response.status_code}")
    access = payload.get("access") or {}
    result["status_after_approval"] = {
        "http": response.status_code,
        "license_status": access.get("license_status"),
        "allowed": access.get("allowed"),
    }

    holder, database = _make_fixture_database()
    try:
        raw = database.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        upload_headers = {
            **_scoped_headers(PRODUCT, hardware, installation),
            "X-AYEC-Backup-Name": "AYEC-live-verification.db",
            "X-AYEC-Program": "AYEC Live Verification",
            "Content-Type": "application/vnd.sqlite3",
            "X-AYEC-Backup-SHA256": digest,
        }
        response, payload = _request(customer, "POST", "/api/support/backups/upload",
                                     data=raw, headers=upload_headers)
        if response.status_code != 200 or payload.get("sha256") != digest:
            raise RuntimeError(f"backup upload HTTP {response.status_code}: checksum not confirmed")
        backup_id = int(payload.get("backup_id") or 0)
        result["backup_upload"] = {
            "http": response.status_code,
            "backup_id": backup_id,
            "sha256": digest,
            "size_bytes": len(raw),
            "server_sha256_match": payload.get("sha256") == digest,
        }

        response, payload = _request(admin, "GET", f"/api/admin/backups/{tenant_id}")
        if response.status_code != 200:
            raise RuntimeError(f"admin backup list HTTP {response.status_code}")
        listed = [item for item in payload.get("backups") or []
                  if int(item.get("backup_id") or 0) == backup_id]
        result["admin_backup_list"] = {"http": response.status_code, "matching_count": len(listed)}
        if not listed:
            raise RuntimeError("uploaded backup was not present in Admin backup catalog")

        response, downloaded = _request(admin, "GET", f"/api/admin/backups/{tenant_id}/download/0",
                                        params={"backup_id": backup_id})
        downloaded_raw = response.content
        result["admin_backup_download"] = {
            "http": response.status_code,
            "sha256": hashlib.sha256(downloaded_raw).hexdigest(),
            "matches_upload": hashlib.sha256(downloaded_raw).hexdigest() == digest,
        }
        if response.status_code != 200 or hashlib.sha256(downloaded_raw).hexdigest() != digest:
            raise RuntimeError("Admin backup download checksum mismatch")

        response, payload = _request(admin, "POST", f"/api/admin/backups/{tenant_id}/restore",
                                     json={"backup_index": 0, "backup_id": backup_id})
        if response.status_code != 200:
            raise RuntimeError(f"admin restore queue HTTP {response.status_code}")
        command_id = int(payload.get("command_id") or 0)
        result["restore_queue"] = {"http": response.status_code, "command_id": command_id}

        response, payload = _request(customer, "GET", "/api/support/desktop/commands",
                                     headers=_scoped_headers(PRODUCT, hardware, installation))
        commands = payload.get("commands") or []
        matching = [item for item in commands if int(item.get("id") or 0) == command_id]
        result["restore_command_poll"] = {
            "http": response.status_code,
            "matching_count": len(matching),
            "application_applied": False,
            "note": "Command delivery is proven; application restart and APPLIED/rollback require the real desktop process.",
        }
        if response.status_code != 200 or not matching:
            raise RuntimeError("restore command was not delivered to the scoped client")
    finally:
        holder.cleanup()

    response, payload = _request(admin, "POST", f"/api/admin/license-orders/{int(order['id'])}/cancel",
                                 json={"admin_note": "AYEC controlled revoke verification"})
    if response.status_code != 200:
        raise RuntimeError(f"license revoke HTTP {response.status_code}: {payload.get('error', 'unknown')}")
    result["revoke"] = {"http": response.status_code, "license_status": (payload.get("license") or {}).get("license_status")}

    response, payload = _request(customer, "POST", "/api/license/status/device",
                                 json=device_payload,
                                 headers=_scoped_headers(PRODUCT, hardware, installation))
    access = payload.get("access") or {}
    result["status_after_revoke"] = {
        "http": response.status_code,
        "license_status": access.get("license_status"),
        "allowed": access.get("allowed"),
        "revocation_verified": response.status_code == 200 and not bool(access.get("allowed")),
    }
    result["email_delivery_inbox_verified"] = False
    result["desktop_restore_applied"] = False
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Run the controlled live mutation preflight")
    parser.add_argument("--output", type=Path, help="Write redacted JSON evidence to this path")
    args = parser.parse_args(argv)
    host = BASE_URL.split("//", 1)[-1].split("/", 1)[0].split(":", 1)[0]
    evidence = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "base_url": BASE_URL, "product": PRODUCT}
    try:
        evidence["tls"] = _tls_probe(host)
        with requests.Session() as session:
            evidence["catalog"] = _catalog(session)
            if args.execute:
                evidence["mutation"] = _execute_mutation_flow(session)
            else:
                evidence["mutation"] = {"executed": False, "missing_variables": _mutation_preflight()}
        evidence["ok"] = True
    except Exception as error:
        evidence["ok"] = False
        evidence["error"] = str(error)
    rendered = json.dumps(evidence, ensure_ascii=True, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if evidence.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
