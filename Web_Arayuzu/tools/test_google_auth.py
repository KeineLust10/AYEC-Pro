#!/usr/bin/env python3
"""Verify Google nonce validation, registration and subject-based login."""
from __future__ import annotations

import sys
import tempfile
import base64
import hashlib
import secrets
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import Main


def main() -> int:
    from google.oauth2 import id_token

    with tempfile.TemporaryDirectory(prefix="ayec-google-test-") as temporary:
        test_root = Path(temporary)
        Main.DB_PATH = test_root / "registry.db"
        Main.TENANT_ROOT = test_root / "tenants"
        Main.DEMO_TEMPLATE_PATH = test_root / "no-demo.db"
        Main._SCHEMA_READY_PATHS.clear()
        Main._GOOGLE_NONCES.clear()
        original_settings = Main.official_service_settings
        original_verify = id_token.verify_oauth2_token
        original_mail = Main.send_registration_emails
        original_location = Main.resolve_installation_location
        Main.official_service_settings = lambda: {
            "google_client_id": "test.apps.googleusercontent.com"
        }
        Main.send_registration_emails = lambda user, event="registration": (True, "sent")
        Main.resolve_installation_location = lambda address: (39.6484, 27.8826)
        try:
            challenge = Main.google_challenge()
            assert challenge["enabled"] is True
            expected = {
                "sub": "google-subject-1",
                "email": "member@example.com",
                "email_verified": True,
                "name": "Google Member",
                "nonce": challenge["nonce"],
            }
            id_token.verify_oauth2_token = lambda credential, request, client_id: expected
            identity = Main.verify_google_identity("signed-token", challenge["nonce"])
            assert identity["sub"] == "google-subject-1"
            try:
                Main.verify_google_identity("signed-token", challenge["nonce"])
                raise AssertionError("Google nonce was accepted twice")
            except ValueError:
                pass

            created = Main.google_account(identity, {
                "mode": "register",
                "username": "googlemember",
                "password": "Secure123!",
                "company_name": "Google Test Company",
                "company_address": "Test Street 1, Balikesir",
                "sector": "teknik_servis",
            })
            assert created["created"] is True
            assert created["user"]["email"] == "member@example.com"
            linked = Main.google_account(identity, {"mode": "login"})
            assert linked["created"] is False
            assert linked["user"]["id"] == created["user"]["id"]
            verifier = secrets.token_urlsafe(64)
            challenge_text = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
            transaction = Main.google_desktop_start(challenge_text)
            try:
                Main.google_desktop_claim(transaction, secrets.token_urlsafe(64))
                raise AssertionError("A mismatched PKCE verifier was accepted")
            except PermissionError:
                pass
            assert Main.google_desktop_claim(transaction, verifier) is None
            try:
                Main.google_desktop_approve(
                    transaction,
                    {"id": created["user"]["id"] + 1000, "_tenant_id": created["user"]["_tenant_id"]},
                )
                raise AssertionError("An unlinked account approved desktop access")
            except PermissionError:
                pass
            Main.google_desktop_approve(transaction, created["user"])
            claimed = Main.google_desktop_claim(transaction, verifier)
            assert claimed["id"] == created["user"]["id"]
            try:
                Main.google_desktop_claim(transaction, verifier)
                raise AssertionError("Desktop authorization was accepted twice")
            except ValueError:
                pass
            with closing(Main.registry_connect()) as conn:
                row = conn.execute("SELECT subject,tenant_id,user_id FROM google_identities").fetchone()
                assert row and row["subject"] == "google-subject-1"

            session, _max_age = Main.create_session(
                int(created["user"]["id"]), False, "test", "127.0.0.1",
                created["user"]["_tenant_id"],
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), Main.AYECRequestHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://127.0.0.1:{server.server_port}"

                def post(path, payload, extra_headers=None):
                    headers = {"Content-Type": "application/json"}
                    headers.update(extra_headers or {})
                    request = urllib.request.Request(
                        base + path,
                        data=json.dumps(payload).encode("utf-8"),
                        headers=headers,
                        method="POST",
                    )
                    with urllib.request.urlopen(request, timeout=5) as response:
                        return response.status, json.loads(response.read()), response.headers

                verifier = secrets.token_urlsafe(64)
                challenge_text = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
                code, started, _headers = post(
                    "/api/auth/google/desktop/start",
                    {"code_challenge": challenge_text},
                    {"X-AYEC-Product-Code": "teknik_servis"},
                )
                assert code == 201 and started["ok"] is True
                transaction = started["transaction_id"]
                code, pending, _headers = post(
                    "/api/auth/google/desktop/poll",
                    {"transaction_id": transaction, "code_verifier": verifier},
                    {"X-AYEC-Product-Code": "teknik_servis"},
                )
                assert code == 202 and pending["pending"] is True
                code, approved, _headers = post(
                    "/api/auth/google/desktop/approve",
                    {"transaction_id": transaction},
                    {"Origin": base, "Cookie": f"{Main.SESSION_COOKIE}={session}"},
                )
                assert code == 200 and approved["ok"] is True
                code, claimed, headers = post(
                    "/api/auth/google/desktop/poll",
                    {"transaction_id": transaction, "code_verifier": verifier},
                    {"X-AYEC-Product-Code": "teknik_servis"},
                )
                assert code == 200 and claimed["user"]["id"] == created["user"]["id"]
                assert f"{Main.SESSION_COOKIE}=" in headers.get("Set-Cookie", "")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
        finally:
            Main.official_service_settings = original_settings
            Main.send_registration_emails = original_mail
            Main.resolve_installation_location = original_location
            id_token.verify_oauth2_token = original_verify
    print("google nonce: ok, registration: ok, subject login: ok, desktop handoff: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
