#!/usr/bin/env python3
"""Remove expired per-visitor AYEC Pro demo tenants from the isolated demo host."""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


SESSION_NAME = re.compile(r"^Demo Session ([0-9a-f]{16})$")


def within(path: Path, root: Path) -> bool:
    resolved = path.expanduser().resolve()
    return resolved != root and root in resolved.parents


def parse_time(value: str) -> datetime | None:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if result.tzinfo is None:
        result = result.replace(tzinfo=timezone.utc)
    return result.astimezone(timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean expired demo-only workspaces")
    parser.add_argument("--age-hours", type=float, default=3.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.age_hours < 2:
        parser.error("--age-hours must be at least 2")

    root_text = os.environ.get("AYEC_DEMO_ROOT", "").strip()
    db_text = os.environ.get("AYEC_DB_PATH", "").strip()
    tenant_text = os.environ.get("AYEC_TENANT_DIR", "").strip()
    if not root_text or not db_text or not tenant_text:
        print("AYEC_DEMO_ROOT, AYEC_DB_PATH and AYEC_TENANT_DIR are required", file=sys.stderr)
        return 2

    root = Path(root_text).expanduser().resolve()
    registry_path = Path(db_text).expanduser().resolve()
    tenant_root = Path(tenant_text).expanduser().resolve()
    if not (root / ".ayec-demo-sandbox").is_file():
        print("Demo sandbox marker is missing; refusing cleanup", file=sys.stderr)
        return 2
    if not within(registry_path, root) or not within(tenant_root, root):
        print("Configured database paths are outside the demo root; refusing cleanup", file=sys.stderr)
        return 2
    if not registry_path.is_file():
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(hours=args.age_hours)
    removed = 0
    with sqlite3.connect(registry_path, timeout=15) as registry:
        registry.row_factory = sqlite3.Row
        registry.execute("PRAGMA busy_timeout=15000")
        registry.execute("PRAGMA foreign_keys=OFF")
        try:
            rows = registry.execute(
                "SELECT id,company_name,db_filename,created_at FROM tenants"
            ).fetchall()
        except sqlite3.Error as error:
            print("Demo registry is unavailable: " + str(error), file=sys.stderr)
            return 2

        for row in rows:
            tenant_id = str(row["id"] or "")
            company_name = str(row["company_name"] or "")
            match = SESSION_NAME.fullmatch(company_name)
            created_at = parse_time(row["created_at"])
            filename = str(row["db_filename"] or "")
            if not match or not created_at or created_at > cutoff:
                continue
            expected_name = company_name + ".db"
            if filename != expected_name:
                continue
            tenant_db = (tenant_root / filename).resolve()
            if tenant_db.parent != tenant_root or not within(tenant_db, root):
                continue
            if args.dry_run:
                print("Would remove " + company_name)
                removed += 1
                continue

            if tenant_db.is_file():
                try:
                    with sqlite3.connect(tenant_db, timeout=15) as tenant_conn:
                        tenant_conn.execute("PRAGMA busy_timeout=15000")
                        tenant_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except sqlite3.Error:
                    pass
                tenant_db.unlink(missing_ok=True)

            tables = [
                str(item[0])
                for item in registry.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ]
            for table in tables:
                columns = {
                    str(item[1])
                    for item in registry.execute('PRAGMA table_info("' + table.replace('"', '""') + '")')
                }
                for column in ("tenant_id", "target_tenant_id", "created_by_tenant_id"):
                    if column in columns and table != "tenants":
                        registry.execute(
                            'DELETE FROM "' + table.replace('"', '""') + '" WHERE "' + column + '"=?',
                            (tenant_id,),
                        )
            registry.execute("DELETE FROM tenants WHERE id=?", (tenant_id,))
            registry.commit()
            removed += 1

    backup_root = root / "backups"
    if not args.dry_run and backup_root.is_dir() and backup_root.resolve().parent == root:
        for item in backup_root.iterdir():
            if item.is_file() and datetime.fromtimestamp(item.stat().st_mtime, timezone.utc) <= cutoff:
                item.unlink(missing_ok=True)
    print(("Would remove " if args.dry_run else "Removed ") + str(removed) + " expired demo workspace(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
