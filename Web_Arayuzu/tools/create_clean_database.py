#!/usr/bin/env python3
"""Create a first-run AYEC deployment database without user-entered records."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from backup_database import backup_database


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FACTORY_TABLES = {
    "app_labels",
    "automotive_maintenance_template_items",
    "automotive_maintenance_templates",
    "device_brands",
    "product_bank_mappings",
    "sector_presets",
}


def create_clean_database(source: Path, target: Path) -> dict:
    backup_result = backup_database(source, target)

    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    import Main  # Imported after the deployment copy exists.

    Main.DB_PATH = target.expanduser().resolve()
    Main._SCHEMA_READY_PATH = ""
    with closing(Main.db_connect()) as conn:
        conn.execute("SELECT 1")

    deleted: dict[str, int] = {}
    preserved: dict[str, int] = {}
    with closing(sqlite3.connect(target)) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        conn.execute("BEGIN IMMEDIATE")
        try:
            for table in tables:
                count = int(conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])
                if table in FACTORY_TABLES:
                    preserved[table] = count
                    continue
                if count:
                    deleted[table] = count
                conn.execute(f'DELETE FROM "{table}"')
            if "sqlite_sequence" in {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }:
                marks = ",".join("?" for _ in FACTORY_TABLES)
                conn.execute(
                    f"DELETE FROM sqlite_sequence WHERE name NOT IN ({marks})",
                    tuple(sorted(FACTORY_TABLES)),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        conn.execute("VACUUM")
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        setup_required = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0

    if integrity != "ok" or not setup_required:
        raise RuntimeError(
            f"Temiz veritabanı doğrulanamadı (integrity={integrity}, setup_required={setup_required})."
        )
    return {
        "ok": True,
        "source": backup_result["source"],
        "recovered_from": backup_result.get("recovered_from", ""),
        "target": str(target.resolve()),
        "integrity": integrity,
        "setup_required": setup_required,
        "deleted_rows": sum(deleted.values()),
        "deleted_tables": deleted,
        "preserved_factory_rows": preserved,
        "bytes": target.stat().st_size,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(json.dumps(create_clean_database(args.source, args.target), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
