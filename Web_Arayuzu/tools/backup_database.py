#!/usr/bin/env python3
"""Create a consistent SQLite deployment backup while AYEC is running."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


def backup_database(source: Path, target: Path) -> dict:
    requested_source = source.expanduser().resolve()
    source = requested_source
    target = target.expanduser().resolve()
    recovery_directory = None
    recovered_from = ""
    if not source.is_file():
        backup_file = Path(f"{source}.bak")
        if not backup_file.is_file():
            raise FileNotFoundError(f"Kaynak veritabanı bulunamadı: {source}")
        recovery_directory = tempfile.TemporaryDirectory(
            prefix="ayec-db-recovery-", ignore_cleanup_errors=True
        )
        recovery_root = Path(recovery_directory.name)
        source = recovery_root / requested_source.name
        shutil.copy2(backup_file, source)
        for suffix in ("-wal", "-shm"):
            journal = Path(f"{requested_source}{suffix}")
            if journal.is_file():
                shutil.copy2(journal, recovery_root / f"{requested_source.name}{suffix}")
        recovered_from = str(backup_file)

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f"{target.name}.tmp")
    temporary.unlink(missing_ok=True)

    try:
        with closing(sqlite3.connect(source, timeout=30)) as source_db:
            with closing(sqlite3.connect(temporary)) as target_db:
                source_db.backup(target_db, pages=256, sleep=0.05)
                integrity = target_db.execute("PRAGMA integrity_check").fetchone()[0]
                table_count = target_db.execute(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                ).fetchone()[0]
                if integrity != "ok":
                    raise RuntimeError(f"SQLite bütünlük kontrolü başarısız: {integrity}")
                target_db.commit()
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
        if recovery_directory is not None:
            recovery_directory.cleanup()

    return {
        "ok": True,
        "source": str(requested_source),
        "recovered_from": recovered_from,
        "target": str(target),
        "bytes": target.stat().st_size,
        "tables": table_count,
        "integrity": integrity,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(json.dumps(backup_database(args.source, args.target), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
