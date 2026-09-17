#!/usr/bin/env python3
"""Verify Google nonce validation, registration and subject-based login."""
from __future__ import annotations

import sys
import tempfile
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
        Main.official_service_settings = lambda: {
            "google_client_id": "test.apps.googleusercontent.com"
        }
        Main.send_registration_emails = lambda user, event="registration": (True, "sent")
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
                "sector": "teknik_servis",
            })
            assert created["created"] is True
            assert created["user"]["email"] == "member@example.com"
            linked = Main.google_account(identity, {"mode": "login"})
            assert linked["created"] is False
            assert linked["user"]["id"] == created["user"]["id"]
            with closing(Main.registry_connect()) as conn:
                row = conn.execute("SELECT subject,tenant_id,user_id FROM google_identities").fetchone()
                assert row and row["subject"] == "google-subject-1"
        finally:
            Main.official_service_settings = original_settings
            Main.send_registration_emails = original_mail
            id_token.verify_oauth2_token = original_verify
    print("google nonce: ok, registration: ok, subject login: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
