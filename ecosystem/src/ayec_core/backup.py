"""Consistent, validated SQLite snapshots for the central backup API."""

from contextlib import closing
from pathlib import Path
import re
import sqlite3
import tempfile


def snapshot_upload(database_path, *, product_code, program_name, database_name):
    """Return a committed snapshot and product-scoped HTTP headers."""
    if not re.fullmatch(r"[a-z][a-z0-9_]*", product_code):
        raise ValueError("Invalid product code")
    for value in (program_name, database_name):
        if not value or any(ord(char) < 32 or ord(char) > 126 for char in value):
            raise ValueError("Invalid backup header")
    if Path(database_name).name != database_name or '/' in database_name or '\\' in database_name:
        raise ValueError("Invalid database name")
    source = Path(database_path).expanduser().resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="ayec-snapshot-") as directory:
        snapshot = Path(directory) / "snapshot.db"
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=30)) as origin:
            with closing(sqlite3.connect(snapshot, timeout=30)) as target:
                origin.backup(target)
                target.execute("PRAGMA journal_mode=DELETE")
                if target.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ValueError("SQLite snapshot integrity check failed")
        payload = snapshot.read_bytes()
    return payload, {
        "Content-Type": "application/vnd.sqlite3",
        "Accept": "application/json",
        "X-AYEC-Backup-Name": database_name,
        "X-AYEC-Program": program_name,
        "X-AYEC-Product-Code": product_code,
    }
