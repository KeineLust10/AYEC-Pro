"""Reset the deployed AYEC platform owner password.

Set AYEC_ADMIN_RESET_PASSWORD before running. The password is never printed.
"""
from __future__ import annotations

import hashlib
import os
import secrets
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
EMAIL = str(os.environ.get("AYEC_ADMIN_EMAIL") or "ayecpro@gmail.com").strip().lower()
PASSWORD = str(os.environ.get("AYEC_ADMIN_RESET_PASSWORD") or "").strip()
ITERATIONS = 310_000


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def locate_registry() -> Path:
    for candidate in (BASE / "data" / "ayecpro.db", BASE / "ayecpro.db"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Registry database not found")


def locate_tenant_roots() -> list[Path]:
    candidates = []
    configured = str(os.environ.get("AYEC_TENANT_DIR") or "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    tenant_name = "Kullan\u0131c\u0131lar"
    candidates.extend((BASE / tenant_name, BASE.parent / tenant_name, Path("/Web_Arayuzu") / tenant_name))
    roots = []
    for candidate in candidates:
        if candidate.is_dir() and candidate not in roots:
            roots.append(candidate)
    return roots


def tenant_databases(registry: sqlite3.Connection, roots: list[Path]) -> list[Path]:
    paths = []
    for root in roots:
        paths.extend(root.glob("*.db"))
    try:
        rows = registry.execute("SELECT db_filename FROM tenants WHERE COALESCE(db_filename,'')<>''").fetchall()
    except sqlite3.Error:
        rows = []
    for row in rows:
        raw = Path(str(row[0]))
        candidates = [raw, BASE / raw, BASE.parent / raw]
        for candidate in candidates:
            if candidate.is_file():
                paths.append(candidate)
                break
    unique = []
    seen = set()
    for path in paths:
        resolved = path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return sorted(unique)


def main() -> int:
    if not PASSWORD or len(PASSWORD) < 8:
        print("ERROR: set AYEC_ADMIN_RESET_PASSWORD to a password of at least 8 characters.")
        return 2
    registry_path = locate_registry()
    registry_backup = registry_path.with_name(registry_path.name + ".pre-admin-reset")
    if not registry_backup.exists():
        shutil.copy2(registry_path, registry_backup)
    hashed = password_hash(PASSWORD)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    updated = 0
    with sqlite3.connect(registry_path) as registry:
        registry.row_factory = sqlite3.Row
        registry.execute("CREATE TABLE IF NOT EXISTS control_admins (tenant_id TEXT NOT NULL, product_code TEXT NOT NULL DEFAULT 'teknik_servis', user_id INTEGER NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY (tenant_id, user_id))")
        control_columns = {row[1] for row in registry.execute('PRAGMA table_info("control_admins")')}
        if "product_code" not in control_columns:
            registry.execute("ALTER TABLE control_admins ADD COLUMN product_code TEXT NOT NULL DEFAULT 'teknik_servis'")
        if "created_at" not in control_columns:
            registry.execute("ALTER TABLE control_admins ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
        registry.commit()
        roots = locate_tenant_roots()
        tenant_paths = tenant_databases(registry, roots)
        if not tenant_paths:
            print("WARNING: no tenant directory was found; checking the registry database itself.")
            tenant_paths = [registry_path]
        tenant_rows = []
        try:
            tenant_rows = registry.execute("SELECT id, db_filename FROM tenants WHERE COALESCE(active,1)=1 ORDER BY created_at, id").fetchall()
        except sqlite3.Error:
            pass
        for tenant_path in tenant_paths:
            with sqlite3.connect(tenant_path) as tenant:
                tenant.row_factory = sqlite3.Row
                tables = {row[0] for row in tenant.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if "users" not in tables:
                    continue
                columns = {row[1] for row in tenant.execute('PRAGMA table_info("users")')}
                if "active" not in columns:
                    tenant.execute('ALTER TABLE users ADD COLUMN "active" INTEGER DEFAULT 1')
                if "must_change_password" not in columns:
                    tenant.execute('ALTER TABLE users ADD COLUMN "must_change_password" INTEGER DEFAULT 0')
                if "temporary_password_expires_at" not in columns:
                    tenant.execute('ALTER TABLE users ADD COLUMN "temporary_password_expires_at" TEXT')
                user = tenant.execute("SELECT id FROM users WHERE lower(trim(COALESCE(email,'')))=? OR lower(trim(COALESCE(username,'')))=?", (EMAIL, EMAIL.split("@", 1)[0])).fetchone()
                if user:
                    user_id = int(user["id"])
                    tenant.execute("UPDATE users SET password=?, active=1, role='Admin', interface_edit_access=1, must_change_password=0, temporary_password_expires_at=NULL, remember_token=NULL, auto_login=0 WHERE id=?", (hashed, user_id))
                else:
                    target = tenant_rows[0] if tenant_rows else None
                    if target and Path(str(target["db_filename"])).name.casefold() != tenant_path.name.casefold():
                        continue
                    cursor = tenant.execute("INSERT INTO users (username,password,email,role,created_at,full_name,active,interface_edit_access,must_change_password,temporary_password_expires_at) VALUES (?,?,?,?,?,?,?,?,0,NULL)", (EMAIL.split("@", 1)[0], hashed, EMAIL, "Admin", now, "AYEC Platform Owner", 1, 1))
                    user_id = int(cursor.lastrowid)
                    print(f"Created missing platform owner account in {tenant_path.name}.")
                tenant.commit()
                tenant_row = registry.execute("SELECT id FROM tenants WHERE lower(db_filename)=lower(?)", (tenant_path.name,)).fetchone()
                if tenant_row:
                    registry.execute("INSERT OR IGNORE INTO control_admins(tenant_id, product_code, user_id, created_at) VALUES (?,?,?,?)", (tenant_row["id"], "teknik_servis", user_id, now))
                updated += 1
                print(f"Admin account ready in {tenant_path.name} (user id {user_id}).")
        registry.commit()
    if not updated:
        print(f"ERROR: no user matching {EMAIL} was found.")
        print(f"Registry backup retained at {registry_backup}")
        return 1
    print(f"Completed {updated} account update(s).")
    print(f"Registry backup retained at {registry_backup}")
    print("Restart the web service if it caches database connections.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
