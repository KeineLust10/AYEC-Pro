"""Register existing tenant databases missing from the AYEC registry."""

from __future__ import annotations

import shutil
import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "data" / "ayecpro.db"
TENANT_DIR = ROOT / ("Kullan" + chr(0x0131) + "c" + chr(0x0131) + "lar")


def has_users_table(path: Path) -> bool:
    try:
        with sqlite3.connect(path) as conn:
            return bool(
                conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='users'"
                ).fetchone()
            )
    except sqlite3.Error:
        return False


def company_name(path: Path) -> str:
    try:
        with sqlite3.connect(path) as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if "company_info" in tables:
                columns = {
                    row[1] for row in conn.execute('PRAGMA table_info("company_info")')
                }
                if "company_name" in columns:
                    row = conn.execute(
                        "SELECT company_name FROM company_info ORDER BY rowid LIMIT 1"
                    ).fetchone()
                    if row and str(row[0] or "").strip():
                        return str(row[0]).strip()
    except sqlite3.Error:
        pass
    return path.stem


def main() -> int:
    if not REGISTRY.is_file():
        print("ERROR: data/ayecpro.db was not found.")
        return 2
    if not TENANT_DIR.is_dir():
        print("ERROR: tenant database folder was not found.")
        return 2

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = REGISTRY.with_name(f"ayecpro.db.pre-tenant-sync-{stamp}")
    try:
        with sqlite3.connect(REGISTRY, timeout=30) as source:
            with sqlite3.connect(backup) as destination:
                source.backup(destination)
    except sqlite3.Error as error:
        print(f"ERROR: registry backup failed ({type(error).__name__}).")
        return 3

    try:
        os.environ["AYEC_DB_PATH"] = str(REGISTRY)
        os.environ["AYEC_TENANT_DIR"] = str(TENANT_DIR)
        import Main

        with Main.registry_connect() as registry:
            columns = {
                row[1]
                for row in registry.execute('PRAGMA table_info("tenants")')
            }
            required = {"id", "company_name", "db_filename", "created_at", "active"}
            if not required.issubset(columns):
                raise RuntimeError("tenant registry schema is incomplete")

            existing = {
                str(row[0] or "").replace("\\", "/").rsplit("/", 1)[-1].casefold()
                for row in registry.execute("SELECT db_filename FROM tenants")
            }
            valid_files = [
                path
                for path in sorted(TENANT_DIR.glob("*.db"))
                if has_users_table(path)
            ]
            added = 0
            for path in valid_files:
                if path.name.casefold() in existing:
                    continue
                name = company_name(path)
                tenant_id = Main._new_tenant_id(name)
                created = Main.utc_now().isoformat(timespec="seconds")
                registry.execute(
                    "INSERT INTO tenants(id,company_name,db_filename,created_at,active) "
                    "VALUES (?,?,?,?,1)",
                    (tenant_id, name, path.name, created),
                )
                existing.add(path.name.casefold())
                added += 1
            registry.commit()
            active_count = int(
                registry.execute(
                    "SELECT COUNT(*) FROM tenants WHERE COALESCE(active,1)=1"
                ).fetchone()[0]
            )
    except Exception as error:
        print(f"ERROR: tenant registry update failed ({type(error).__name__}).")
        print(f"REGISTRY_BACKUP={backup}")
        return 4

    print(f"TENANT_DATABASES_FOUND={len(valid_files)}")
    print(f"TENANTS_ADDED={added}")
    print(f"ACTIVE_TENANTS={active_count}")
    print(f"REGISTRY_BACKUP={backup}")
    if not active_count:
        print("ERROR: no active tenant records are available.")
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
