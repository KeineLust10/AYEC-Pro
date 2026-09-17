#!/usr/bin/env python3
"""Verify first-run setup and the two-recipient registration mail flow."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
import Main


class FakeSMTP:
    sent = []

    def __init__(self, host, port, timeout=20):
        self.host = host
        self.port = port

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def ehlo(self):
        return None

    def starttls(self, context=None):
        return None

    def login(self, username, password):
        assert username == "info@ayecpro.com"
        assert password == "application-password"

    def send_message(self, message):
        self.sent.append(message)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ayec-mail-test-") as temporary:
        Main.DB_PATH = Path(temporary) / "mail-test.db"
        Main.TENANT_ROOT = Path(temporary) / "tenants"
        Main.DEMO_TEMPLATE_PATH = Path(temporary) / "no-demo.db"
        Main._SCHEMA_READY_PATH = ""
        original_smtp = Main.smtplib.SMTP
        original_official_settings = Main.official_service_settings
        Main.official_service_settings = lambda: {"smtp_host": "smtp.example.com", "smtp_port": 587, "smtp_password": "application-password"}
        Main.smtplib.SMTP = FakeSMTP
        try:
            setup = Main.setup_application(
                {
                    "sector": "teknik_servis",
                    "company_name": "AYEC Test",
                    "company_email": "company@example.com",
                    "phone": "5550000000",
                    "company_address": "Test adresi",
                    "currency": "TRY",
                    "full_name": "System Admin",
                    "username": "sysadmin",
                    "email": "admin@example.com",
                    "password": "Admin123!",
                    "smtp_server": "smtp.example.com",
                    "smtp_port": "587",
                    "smtp_email": "mailer@example.com",
                    "smtp_password": "application-password",
                    "admin_email": "owner@example.com",
                }
            )
            assert setup["mail_sent"] is True
            assert setup["user"]["role"] == "User"
            assert setup["user"]["is_control_admin"] is False
            assert len(FakeSMTP.sent) == 2
            assert {str(message["To"]) for message in FakeSMTP.sent} == {
                "admin@example.com",
                "destek@ayecpro.com",
            }

            registration = Main.register_account(
                {
                    "full_name": "New Member",
                    "username": "member",
                    "email": "member@example.com",
                    "password": "Member123!",
                }
            )
            assert registration["mail_sent"] is True
            assert len(FakeSMTP.sent) == 4
            assert {str(message["To"]) for message in FakeSMTP.sent[2:]} == {
                "member@example.com",
                "destek@ayecpro.com",
            }
            with closing(Main.db_connect()) as conn:
                assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
                assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                conn.execute("UPDATE users SET role='Admin',interface_edit_access=1 WHERE email=?", ("member@example.com",))
                conn.commit()
            Main.ensure_control_owner()
            with closing(Main.db_connect()) as conn:
                role, interface_edit_access = conn.execute(
                    "SELECT role,interface_edit_access FROM users WHERE email=?",
                    ("member@example.com",),
                ).fetchone()
            assert role == "User"
            assert interface_edit_access == 0
            assert all(str(message["From"]) == "info@ayecpro.com" for message in FakeSMTP.sent)
            assert all(str(message["Reply-To"]) == "destek@ayecpro.com" for message in FakeSMTP.sent)
            sent, _ = Main.send_license_email("", "customer@example.com", "License approved", "Your license is active.")
            assert sent and str(FakeSMTP.sent[-1]["From"]) == "info@ayecpro.com"
            assert "https://www.ayecpro.com" in FakeSMTP.sent[-1].get_content()
            Main.official_service_settings = lambda: {}
            sent, _ = Main.send_license_email("", "customer@example.com", "License approved", "Test")
            assert not sent
        finally:
            Main.smtplib.SMTP = original_smtp
            Main.official_service_settings = original_official_settings

    print("setup mail: 2/2, registration mail: 2/2, integrity: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
