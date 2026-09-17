#!/usr/bin/env python3
"""Repair an existing AYEC SQLite file without deleting operational data."""

from __future__ import annotations

import argparse
import json
import sys
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def repair_database(database: Path) -> dict:
    import Main

    database = database.expanduser().resolve()
    Main.DB_PATH = database
    Main._SCHEMA_READY_PATH = ""
    backup = ""
    if database.is_file():
        backup = str(Main.create_database_backup("pre-schema-repair"))

    with closing(Main.db_connect()) as conn:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]

    return {
        "ok": integrity == "ok",
        "database": str(database),
        "backup": backup,
        "tables": len(tables),
        "has_customers": "customers" in tables,
        "has_devices": "devices" in tables,
        "has_parts": "parts" in tables,
        "missing_required": sorted(Main.REQUIRED_OPERATIONAL_TABLES.difference(tables)),
        "integrity": integrity,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=Path)
    args = parser.parse_args()
    result = repair_database(args.database)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] and not result["missing_required"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
