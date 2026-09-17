"""Validated restart-only restore with an atomic journal and rollback."""

from contextlib import closing
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3


def _validate(path, required_tables=()):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as conn:
        if conn.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("Backup integrity check failed")
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not set(required_tables).issubset(tables):
            raise ValueError("Backup schema does not match this product")


def _atomic_json(path, payload):
    temporary = path.with_name(path.name + "." + secrets.token_hex(6) + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _checksum(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_scope(payload, *, product_code=None, tenant_id="", hardware_id="", installation_id=""):
    for field, expected in (("product_code", product_code), ("tenant_id", tenant_id),
                            ("hardware_id", hardware_id), ("installation_id", installation_id)):
        if expected and payload.get(field, expected if field == "product_code" else None) != expected:
            raise ValueError("Restore belongs to another {}".format(field.replace("_", " ")))


def stage_restore(command, local_db, download, *, product_code, required_tables=(),
                  tenant_id="", hardware_id="", installation_id="", require_confirmation=False,
                  confirmed=False):
    payload = dict(command.get("payload") or {})
    backup_id = int(payload.get("backup_id") or 0)
    if command.get("command_type") != "restore_backup" or backup_id <= 0:
        raise ValueError("Unsupported restore command")
    _check_scope(payload, product_code=product_code, tenant_id=tenant_id,
                 hardware_id=hardware_id, installation_id=installation_id)
    if require_confirmation and not confirmed:
        raise PermissionError("Local restore confirmation is required")
    if (tenant_id or hardware_id or installation_id) and (
        len(str(payload.get("sha256") or "")) != 64 or not payload.get("size_bytes")
    ):
        raise ValueError("Remote restore requires checksum and size metadata")
    target = Path(local_db).expanduser().resolve()
    staged = target.with_suffix(target.suffix + ".pending-restore")
    marker = target.with_suffix(target.suffix + ".pending-restore.json")
    if marker.exists():
        previous = json.loads(marker.read_text(encoding="utf-8"))
        if previous.get("command_id") == int(command.get("id") or 0):
            if not staged.exists() or _checksum(staged) != previous.get("sha256"):
                raise ValueError("Pending restore checksum mismatch")
            return {"backup_id": backup_id, "restart_required": True, "state": "STAGED"}
        raise ValueError("Another restore is already awaiting restart")
    raw = download(backup_id)
    if not raw.startswith(b"SQLite format 3\x00"):
        raise ValueError("Backup is not a SQLite database")
    digest = hashlib.sha256(raw).hexdigest()
    if payload.get("sha256") and not secrets.compare_digest(digest, str(payload["sha256"])):
        raise ValueError("Downloaded backup checksum mismatch")
    if payload.get("size_bytes") and int(payload["size_bytes"]) != len(raw):
        raise ValueError("Downloaded backup size mismatch")
    temporary = staged.with_name(staged.name + "." + secrets.token_hex(6) + ".tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        _validate(temporary, required_tables)
        os.replace(temporary, staged)
    finally:
        temporary.unlink(missing_ok=True)
    metadata = {"command_id": int(command.get("id") or 0), "backup_id": backup_id,
                "sha256": digest, "size_bytes": len(raw), "staged_path": str(staged),
                "product_code": product_code, "tenant_id": tenant_id,
                "hardware_id": hardware_id, "installation_id": installation_id, "state": "STAGED"}
    _atomic_json(marker, metadata)
    return {"backup_id": backup_id, "sha256": digest, "restart_required": True, "state": "STAGED"}


def _replace_snapshot(source, target):
    """Retain the journal source until post-replacement validation succeeds."""
    temporary = target.with_name(target.name + "." + secrets.token_hex(6) + ".replace")
    try:
        with source.open("rb") as origin, temporary.open("xb") as destination:
            shutil.copyfileobj(origin, destination)
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def read_restore_result(database_path):
    target = Path(database_path).expanduser().resolve()
    path = target.with_suffix(target.suffix + ".restore-result.json")
    if not path.exists():
        return {}
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Invalid restore result")
    return result


def apply_pending_restore(database_path, *, product_code=None, required_tables=(),
                          tenant_id="", hardware_id="", installation_id="", health_check=None):
    """Call before any application writer opens the database.

    A REPLACING journal left by process termination is rolled back on startup.
    Failed migration/health callbacks also restore the validated old snapshot.
    """
    target = Path(database_path).expanduser().resolve()
    marker = target.with_suffix(target.suffix + ".pending-restore.json")
    if not marker.exists():
        return {"applied": False}
    metadata = json.loads(marker.read_text(encoding="utf-8"))
    _check_scope(metadata, product_code=product_code, tenant_id=tenant_id,
                 hardware_id=hardware_id, installation_id=installation_id)
    staged = target.with_suffix(target.suffix + ".pending-restore")
    if Path(str(metadata.get("staged_path") or "")).resolve() != staged:
        raise ValueError("Pending restore file is unavailable")
    result_path = target.with_suffix(target.suffix + ".restore-result.json")

    def finish(state, before, error=""):
        result = {"applied": state == "APPLIED", "state": state, "error": error,
                  "command_id": int(metadata.get("command_id") or 0),
                  "backup_id": int(metadata.get("backup_id") or 0),
                  "before_backup": str(before) if before else "",
                  "sha256": _checksum(target), "product_code": metadata.get("product_code"),
                  "tenant_id": metadata.get("tenant_id", ""),
                  "hardware_id": metadata.get("hardware_id", ""),
                  "installation_id": metadata.get("installation_id", "")}
        _atomic_json(result_path, result)
        marker.unlink(missing_ok=True)
        staged.unlink(missing_ok=True)
        return result

    def rollback(before, error):
        if not before or before.parent != target.parent or not before.name.startswith(target.stem + ".before-remote-restore-"):
            raise ValueError("Restore rollback snapshot is unavailable")
        if _checksum(before) != metadata.get("before_sha256"):
            raise ValueError("Rollback snapshot checksum mismatch")
        _validate(before, required_tables)
        for suffix in ("-wal", "-shm"):
            Path(str(target) + suffix).unlink(missing_ok=True)
        _replace_snapshot(before, target)
        _validate(target, required_tables)
        return finish("ROLLED_BACK", before, error)

    if metadata.get("state") == "REPLACING":
        return rollback(Path(metadata.get("before_backup", "")).resolve(), "Interrupted restore recovered")
    if not staged.is_file() or not secrets.compare_digest(_checksum(staged), str(metadata.get("sha256") or "")):
        raise ValueError("Pending restore checksum validation failed")
    _validate(staged, required_tables)
    if not target.exists():
        raise ValueError("Current database is unavailable for preservation")
    before = target.with_name("{}{}.db".format(
        target.stem + ".before-remote-restore-", datetime.now().strftime("%Y%m%d-%H%M%S-%f")))
    with closing(sqlite3.connect(target, timeout=10)) as origin:
        checkpoint = origin.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        if checkpoint and checkpoint[0]:
            raise ValueError("Database is busy; restore requires all connections closed")
        with closing(sqlite3.connect(before, timeout=10)) as destination:
            origin.backup(destination)
            destination.commit()
    _validate(before, required_tables)
    metadata.update(state="REPLACING", before_backup=str(before), before_sha256=_checksum(before))
    _atomic_json(marker, metadata)
    try:
        for suffix in ("-wal", "-shm"):
            Path(str(target) + suffix).unlink(missing_ok=True)
        _replace_snapshot(staged, target)
        _validate(target, required_tables)
        if health_check is not None and health_check(target) is False:
            raise ValueError("Post-restore health check failed")
        _validate(target, required_tables)
        return finish("APPLIED", before)
    except Exception as error:
        return rollback(before, str(error)[:250])
