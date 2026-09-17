from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


REQUIRED_TABLES = {"settings"}


def app_data_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not available")
    return Path(local_app_data) / "AYEC Pro"


def latest_backup(backups_dir: Path) -> Path:
    backups = sorted(
        backups_dir.glob("*.db"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not backups:
        raise FileNotFoundError(f"No SQLite backup found in {backups_dir}")
    return backups[0]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def table_counts(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()
    counts: dict[str, int] = {}
    for (name,) in rows:
        escaped = str(name).replace('"', '""')
        counts[str(name)] = int(
            connection.execute(f'SELECT COUNT(*) FROM "{escaped}"').fetchone()[0]
        )
    return counts


def validate_database(path: Path) -> dict[str, object]:
    uri = f"{path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as connection:
        integrity = str(
            connection.execute("PRAGMA integrity_check").fetchone()[0]
        )
        foreign_key_issues = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        counts = table_counts(connection)
    return {
        "integrity": integrity,
        "foreign_key_issue_count": len(foreign_key_issues),
        "table_counts": counts,
    }


def run_drill(source: Path, output_root: Path) -> dict[str, object]:
    source = source.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)

    source_result = validate_database(source)
    if source_result["integrity"] != "ok":
        raise RuntimeError("Source backup integrity check failed")

    source_tables = set(source_result["table_counts"])
    missing_required = sorted(REQUIRED_TABLES - source_tables)
    if missing_required:
        raise RuntimeError(
            f"Source backup is missing required tables: {missing_required}"
        )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    drill_dir = output_root.resolve() / timestamp
    drill_dir.mkdir(parents=True, exist_ok=False)
    restored_path = drill_dir / "restored.db"
    report_path = drill_dir / "restore_drill_report.json"

    source_uri = f"{source.as_uri()}?mode=ro"
    with sqlite3.connect(source_uri, uri=True) as source_connection:
        with sqlite3.connect(restored_path) as restored_connection:
            source_connection.backup(restored_connection)

    restored_result = validate_database(restored_path)
    counts_match = (
        source_result["table_counts"] == restored_result["table_counts"]
    )
    passed = (
        restored_result["integrity"] == "ok"
        and restored_result["foreign_key_issue_count"] == 0
        and counts_match
    )
    report = {
        "status": "passed" if passed else "failed",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "source_sha256": sha256_file(source),
        "restored": str(restored_path),
        "restored_sha256": sha256_file(restored_path),
        "source_validation": source_result,
        "restored_validation": restored_result,
        "table_counts_match": counts_match,
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    report["report"] = str(report_path)
    if not passed:
        raise RuntimeError(f"Restore drill failed: {report_path}")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an isolated SQLite backup restore drill."
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Backup database path. Defaults to the latest local backup.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Drill output folder. Defaults to local app data.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base = app_data_dir()
    source = args.source or latest_backup(base / "backups")
    output_root = args.output_root or base / "restore_drills"
    report = run_drill(source, output_root)
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": report["report"],
                "restored": report["restored"],
                "table_count": len(
                    report["restored_validation"]["table_counts"]
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
