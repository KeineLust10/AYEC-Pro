#!/usr/bin/env python3
"""End-to-end checks for AYEC web sessions, authorization and Wipe All."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

from backup_database import backup_database


ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main() -> int:
    source = ROOT / "data" / "ayecpro.db"
    with tempfile.TemporaryDirectory(prefix="ayec-auth-test-", ignore_cleanup_errors=True) as temporary:
        temporary_path = Path(temporary)
        database = temporary_path / "auth-test.db"
        backup_database(source, database)
        with sqlite3.connect(database) as connection:
            if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                connection.execute(
                    "INSERT INTO users (username,password,email,role,full_name,active,interface_edit_access) "
                    "VALUES (?,?,?,?,?,?,?)",
                    (
                        "admin",
                        hashlib.sha256(b"admin123").hexdigest(),
                        "admin@ayecpro.local",
                        "Admin",
                        "Admin",
                        1,
                        1,
                    ),
                )
            if connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
                connection.execute(
                    "INSERT INTO customers (name,phone,type,is_deleted) VALUES (?,?,?,0)",
                    ("Wipe Test Customer", "0000000000", "Bireysel"),
                )
            if connection.execute("SELECT COUNT(*) FROM parts").fetchone()[0] == 0:
                connection.execute(
                    "INSERT INTO parts (name,part_name,stock,price,purchase_price,currency,code,is_deleted) "
                    "VALUES (?,?,?,?,?,?,?,0)",
                    ("Wipe Test Part", "Wipe Test Part", 1, 10, 5, "TRY", "WIPE-001"),
                )
                connection.commit()

        port = free_port()
        base = f"http://127.0.0.1:{port}"
        environment = dict(os.environ)
        environment["AYEC_BACKUP_DIR"] = str(temporary_path / "backups")
        environment["AYEC_TENANT_DIR"] = str(temporary_path / "Kullanıcılar")
        process = subprocess.Popen(
            [sys.executable, "Main.py", "--host", "127.0.0.1", "--port", str(port), "--db", str(database)],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            for _ in range(80):
                try:
                    with build_opener().open(base + "/api/desktop/health", timeout=1) as response:
                        if json.loads(response.read()).get("ok"):
                            break
                except Exception:
                    time.sleep(0.1)
            else:
                raise RuntimeError("Test sunucusu başlamadı.")

            jar = CookieJar()
            client = build_opener(HTTPCookieProcessor(jar))

            def call(path: str, method: str = "GET", body=None, origin: str | None = None):
                payload = json.dumps(body).encode() if body is not None else None
                headers = {"Content-Type": "application/json"}
                if origin:
                    headers["Origin"] = origin
                request = Request(base + path, data=payload, headers=headers, method=method)
                try:
                    with client.open(request, timeout=20) as response:
                        return response.status, json.loads(response.read())
                except HTTPError as error:
                    return error.code, json.loads(error.read())

            checks = [
                ("status anonymous", *call("/api/auth/status")),
                ("bootstrap blocked", *call("/api/desktop/bootstrap")),
                ("bad login", *call("/api/auth/login", "POST", {"identifier": "admin", "password": "wrong"})),
                ("legacy login", *call("/api/auth/login", "POST", {"identifier": "  ADMIN  ", "password": "admin123", "remember": True})),
                ("users redacted", *call("/api/desktop/table/users")),
                ("bootstrap allowed", *call("/api/desktop/bootstrap")),
                ("cross origin blocked", *call("/api/desktop/table/internal_settings", "POST", {"key": "bad", "value": "1"}, "http://evil.example")),
                ("same origin write", *call("/api/desktop/table/internal_settings", "POST", {"key": "auth_test", "value": "1"}, base)),
                ("register member", *call("/api/auth/register", "POST", {"username": "member", "full_name": "Member", "email": "member@example.com", "password": "Member123!"})),
                ("logout admin", *call("/api/auth/logout", "POST", {}, base)),
                ("member login", *call("/api/auth/login", "POST", {"identifier": "member", "password": "Member123!"})),
                ("member users blocked", *call("/api/desktop/table/users")),
                ("member settings blocked", *call("/api/desktop/table/settings", "POST", {"key": "forbidden", "value": "1"}, base)),
                ("logout member", *call("/api/auth/logout", "POST", {}, base)),
                ("admin relogin", *call("/api/auth/login", "POST", {"identifier": "admin", "password": "admin123", "remember": True})),
                ("wipe wrong password", *call("/api/admin/wipe-user-data", "POST", {"password": "wrong", "phrase": "TÜM VERİLERİ SİL"}, base)),
                ("wipe operational data", *call("/api/admin/wipe-user-data", "POST", {"password": "admin123", "phrase": "TÜM VERİLERİ SİL"}, base)),
                ("status remembered", *call("/api/auth/status")),
                ("logout", *call("/api/auth/logout", "POST", {}, base)),
                ("bootstrap after logout", *call("/api/desktop/bootstrap")),
            ]
            expected = [200, 401, 401, 200, 200, 200, 403, 200, 201, 200, 200, 403, 403, 200, 200, 403, 200, 200, 200, 401]
            actual = [item[1] for item in checks]
            for name, status, payload in checks:
                print(f"{name}: HTTP {status} {json.dumps(payload, ensure_ascii=False)[:240]}")
            if actual != expected:
                raise AssertionError((actual, expected))
            user_payload = checks[4][2]
            if "password" in user_payload.get("columns", []) or any(
                "password" in row for row in user_payload.get("rows", [])
            ):
                raise AssertionError("Kullanıcı parola alanı API yanıtında maskelenmedi.")
            if checks[16][2].get("deleted_rows", 0) <= 0:
                raise AssertionError("Wipe All hiçbir satır silmedi.")

            tenant_files = sorted((temporary_path / "Kullanıcılar").glob("*.db"))
            if not tenant_files:
                raise AssertionError("Firma veritabanı oluşturulmadı.")
            with sqlite3.connect(tenant_files[0]) as connection:
                users = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                customers = connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
                parts = connection.execute("SELECT COUNT(*) FROM parts").fetchone()[0]
                stored_password = connection.execute("SELECT password FROM users WHERE username='admin'").fetchone()[0]
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            print(
                f"after wipe: users={users} customers={customers} parts={parts} "
                f"password_scheme={stored_password.split('$', 1)[0]} integrity={integrity}"
            )
            if not (
                users == 2
                and customers == 0
                and parts == 0
                and stored_password.startswith("pbkdf2_sha256$")
                and integrity == "ok"
            ):
                raise AssertionError("Wipe/auth veritabanı sonucu beklenen durumda değil.")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            stdout, stderr = process.communicate()
            if stdout:
                print(stdout.strip())
            if stderr:
                print(stderr.strip(), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
