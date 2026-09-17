"""Optional AYEC Pro desktop-to-web synchronization client.

This module deliberately uses the Python standard library only.  The desktop
application can run it in a QThread after login; if the web server is offline
the local application continues to work and the next cycle retries.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import ssl
import ctypes
from ctypes import wintypes
import urllib.error
import urllib.request
import tempfile
from datetime import datetime
from pathlib import Path


DEFAULT_WEB_SYNC_URL = "http://85.117.239.60"
WEB_SYNC_SESSION_FILE = "web_sync_session.dat"
_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
logger = logging.getLogger(__name__)


class WebSyncError(RuntimeError):
    """A user-safe synchronization error."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = int(status_code or 0)


class WebSyncClient:
    def __init__(self, base_url: str, *, verify_tls: bool = True, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cookies: dict[str, str] = {}
        self.device_id = ""
        self.sync_epoch = 1
        self.context = ssl.create_default_context() if verify_tls else ssl._create_unverified_context()

    def _request(self, path: str, method: str = "GET", payload: dict | None = None) -> dict:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json", "User-Agent": "AYEC-Pro-Desktop-Sync/1.0"}
        headers["X-AYEC-Product-Code"] = "teknik_servis"
        if self.device_id:
            headers["X-AYEC-Device-ID"] = self.device_id
        if self.cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=self.context) as response:
                from ayec_core.session import update_cookies
                update_cookies(self.cookies, response.headers)
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code in {502, 503, 504}:
                raise WebSyncError(
                    "AYEC Pro sunucu servisi kullan\u0131lam\u0131yor "
                    f"(HTTP {error.code}). Sunucuda AYEC Pro Web ve IIS "
                    "hizmetlerini yeniden ba\u015flat\u0131n.",
                    error.code,
                ) from error
            try:
                detail = json.loads(error.read().decode("utf-8"))
            except Exception:
                detail = {"error": str(error)}
            raise WebSyncError(
                str(detail.get("error") or detail), error.code
            ) from error
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            raise WebSyncError(
                f"AYEC Pro sunucusuna ba\u011flan\u0131lamad\u0131: {error}"
            ) from error
        if isinstance(result, dict) and result.get("error"):
            raise WebSyncError(str(result["error"]))
        return result

    def _request_bytes(self, path: str, method: str = "GET", payload: bytes | None = None, headers: dict | None = None) -> bytes:
        request_headers = {
            "X-AYEC-Product-Code": "teknik_servis",
            "X-AYEC-Device-ID": self.device_id,
            "Accept": "application/octet-stream,application/vnd.sqlite3",
            "User-Agent": "AYEC-Pro-Desktop-Sync/1.0",
            **(headers or {}),
        }
        if self.cookies:
            request_headers["Cookie"] = "; ".join(f"{key}={value}" for key, value in self.cookies.items())
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            headers=request_headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=max(self.timeout, 120), context=self.context) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            try:
                detail = json.loads(error.read().decode("utf-8"))
            except Exception:
                detail = {"error": str(error)}
            raise WebSyncError(str(detail.get("error") or detail)) from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise WebSyncError(f"AYEC Pro server request failed: {error}") from error

    def login(self, identifier: str, password: str, remember: bool = True, tenant_id: str | None = None) -> dict:
        payload = {"identifier": identifier, "password": password, "remember": remember}
        if tenant_id:
            payload["tenant_id"] = tenant_id
        return self._request("/api/auth/login", "POST", payload)

    def provision_desktop_tenant(self, payload: dict) -> dict:
        return self._request("/api/sync/provision", "POST", payload)

    def save_session(self, path: str | Path, metadata: dict | None = None) -> None:
        from ayec_core.session import save_session
        save_session(path, base_url=self.base_url, product_code="teknik_servis",
                     cookies=self.cookies, metadata=metadata, protect=_protect_for_current_user)

    def load_session(self, path: str | Path) -> dict:
        from ayec_core.session import load_session
        return load_session(path, base_url=self.base_url, product_code="teknik_servis",
                            cookies=self.cookies, unprotect=_unprotect_for_current_user)

    @staticmethod
    def clear_session(path: str | Path) -> None:
        Path(path).expanduser().resolve().unlink(missing_ok=True)

    def auth_status(self) -> dict:
        return self._request("/api/auth/status")

    def manifest(self) -> dict:
        return self._request("/api/sync/manifest")

    def pull(self, since: dict | None = None, tables: list[str] | None = None) -> dict:
        return self._request("/api/sync/pull", "POST", {"since": since or {}, "tables": tables or [], "limit": 5000, "sync_epoch": self.sync_epoch})

    def push(self, changes: list[dict]) -> dict:
        return self._request("/api/sync/push", "POST", {"changes": changes, "sync_epoch": self.sync_epoch})

    def wipe_tenant_data(self, password: str) -> dict:
        return self._request(
            "/api/admin/wipe-user-data",
            "POST",
            {
                "password": str(password or ""),
                "phrase": "T\u00dcM VER\u0130LER\u0130 S\u0130L",
            },
        )

    def update_sector(self, sector: str) -> dict:
        return self._request(
            "/api/company/sector",
            "POST",
            {"sector": str(sector or "").strip()},
        )

    def update_company_location(self, payload: dict) -> dict:
        return self._request("/api/company/location", "POST", dict(payload or {}))

    def pending_commands(self) -> list[dict]:
        return list(self._request("/api/support/desktop/commands").get("commands") or [])

    def complete_command(self, command_id: int, success: bool, result: dict | None = None) -> dict:
        return self._request(
            "/api/support/desktop/complete",
            "POST",
            {"command_id": int(command_id), "success": bool(success), "result": result or {}},
        )

    def download_backup(self, backup_id: int) -> bytes:
        return self._request_bytes(f"/api/support/backups/{int(backup_id)}")

    def upload_backup(self, database_path: str | Path) -> dict:
        from ayec_core.backup import snapshot_upload
        payload, headers = snapshot_upload(
            database_path, product_code="teknik_servis",
            program_name="AYEC Pro Teknik Servis", database_name="Teknik-Servis-AYEC.db",
        )
        raw = self._request_bytes(
            "/api/support/backups/upload",
            "POST",
            payload,
            headers,
        )
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as error:
            raise WebSyncError("Backup server returned an invalid response") from error

    def stage_restore_command(self, command: dict, local_db: str | Path) -> dict:
        from ayec_core.restore import stage_restore
        try:
            return stage_restore(command, local_db, self.download_backup,
                                 product_code="teknik_servis")
        except ValueError as error:
            raise WebSyncError(str(error)) from error

    def sync_sqlite(
        self,
        local_db: str | Path,
        state_file: str | Path | None = None,
        *,
        push_local: bool = True,
    ) -> dict:
        local_path = Path(local_db).expanduser().resolve()
        state_path = Path(state_file or f"{local_path}.ayec-sync.json").expanduser().resolve()
        state = {
            "since": {},
            "machine_id": secrets.token_hex(8),
            "row_hashes": {},
            "conflict_hashes": {},
        }
        recovered_state = ""
        if state_path.exists():
            try:
                loaded_state = json.loads(state_path.read_text(encoding="utf-8"))
                if not isinstance(loaded_state, dict):
                    raise ValueError("Synchronization state must be a JSON object")
                state.update(loaded_state)
            except (OSError, UnicodeError, ValueError, TypeError, json.JSONDecodeError) as error:
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                quarantine = state_path.with_name(f"{state_path.name}.corrupt-{stamp}")
                try:
                    os.replace(state_path, quarantine)
                    recovered_state = str(quarantine)
                except OSError:
                    logger.exception("Corrupt synchronization state could not be quarantined")
                    raise WebSyncError(
                        "Synchronization state is corrupt and could not be quarantined"
                    ) from error
                logger.warning(
                    "Corrupt synchronization state quarantined at %s; full reconciliation will run",
                    quarantine,
                )
        row_hashes = dict(state.get("row_hashes") or {})
        conflict_hashes = dict(state.get("conflict_hashes") or {})
        recovery_tables = (
            {"parts", "stock_movements", "accounting"}
            if int(state.get("reconciliation_version") or 0) < 2
            else set()
        )
        if recovery_tables:
            state_since = dict(state.get("since") or {})
            for table in recovery_tables:
                state_since[table] = 0
            state["since"] = state_since

        def row_digest(table_name: str, row_data: dict) -> str:
            normalized = dict(row_data)
            if table_name == "offers":
                normalized.pop("pdf_path", None)
            return hashlib.sha256(
                json.dumps(normalized, sort_keys=True, default=str).encode()
            ).hexdigest()[:16]

        self.device_id = str(state.get("machine_id") or "")
        manifest = self.manifest()
        remote_epoch = max(1, int(manifest.get("sync_epoch") or 1))
        local_epoch = max(1, int(state.get("sync_epoch") or 1))
        self.sync_epoch = remote_epoch
        tables = sorted(
            name
            for name in (manifest.get("tables") or {}).keys()
            if _SQL_IDENTIFIER.fullmatch(str(name or ""))
        )
        epoch_reset_backup = ""
        if local_epoch != remote_epoch:
            backup_dir = local_path.parent / "sync_reset_backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup_path = backup_dir / (
                f"before-sync-reset-{local_epoch}-to-{remote_epoch}-"
                f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.db"
            )
            with sqlite3.connect(local_path) as source_conn:
                with sqlite3.connect(backup_path) as destination_conn:
                    source_conn.backup(destination_conn)
                    destination_conn.commit()
            reset_tables = {
                str(name)
                for name in (manifest.get("reset_tables") or [])
                if _SQL_IDENTIFIER.fullmatch(str(name or ""))
            }
            with sqlite3.connect(local_path) as reset_conn:
                reset_conn.execute("PRAGMA foreign_keys=OFF")
                installed_tables = {
                    str(row[0])
                    for row in reset_conn.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
                for table in sorted(reset_tables & installed_tables):
                    reset_conn.execute(f'DELETE FROM "{table}"')
                    try:
                        reset_conn.execute(
                            "DELETE FROM sqlite_sequence WHERE name=?", (table,)
                        )
                    except sqlite3.OperationalError:
                        pass
                reset_conn.commit()
                reset_conn.execute("PRAGMA foreign_keys=ON")
            state["since"] = {}
            state["row_hashes"] = {}
            state["conflict_hashes"] = {}
            state["reconciliation_version"] = 2
            row_hashes = {}
            conflict_hashes = {}
            recovery_tables = set()
            epoch_reset_backup = str(backup_path)
        state["sync_epoch"] = remote_epoch
        pulled = self.pull(state.get("since", {}), tables)
        applied = 0
        preserved_conflicts: list[dict] = []
        outgoing: list[dict] = []
        pending_hashes: dict[str, str] = {}
        remote_keys: set[str] = set()
        with sqlite3.connect(local_path) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA busy_timeout=30000")
            for table, records in (pulled.get("changes") or {}).items():
                if table not in tables or not _SQL_IDENTIFIER.fullmatch(str(table or "")):
                    continue
                columns = {row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')}
                if "id" not in columns:
                    continue
                for record in records:
                    clean = {key: value for key, value in record.items() if key in columns}
                    if table == "offers":
                        # File paths are machine-local. The desktop rebuilds a
                        # synchronized offer PDF from its database payload.
                        clean.pop("pdf_path", None)
                    if clean.get("id") is None:
                        continue
                    remote_keys.add(f"{table}:{clean['id']}")
                    existing = conn.execute(f'SELECT * FROM "{table}" WHERE id=?', (clean["id"],)).fetchone()
                    key = f"{table}:{clean['id']}"
                    if existing:
                        local_row = dict(existing)
                        base_hash = str(row_hashes.get(key) or "")
                        local_hash = row_digest(table, local_row)
                        remote_hash = row_digest(table, clean)
                        if (
                            base_hash
                            and table != "offers"
                            and local_hash != base_hash
                            and local_hash != remote_hash
                        ):
                            # Keep an unsynchronized local edit. This also covers
                            # tables without updated_at, which are fully pulled on
                            # every pass so edits to existing rows stay visible.
                            preserved_conflicts.append(
                                {"table": table, "record_id": str(clean["id"])}
                            )
                            continue
                    if existing and "updated_at" in columns and clean.get("updated_at") and existing["updated_at"] and str(clean["updated_at"]) <= str(existing["updated_at"]):
                        continue
                    if existing:
                        updates = {key: value for key, value in clean.items() if key != "id"}
                        if updates:
                            setters = ",".join(f'"{key}"=?' for key in updates)
                            conn.execute(f'UPDATE "{table}" SET {setters} WHERE id=?', (*updates.values(), clean["id"]))
                    else:
                        names = ",".join(f'"{key}"' for key in clean)
                        marks = ",".join("?" for _ in clean)
                        conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({marks})', tuple(clean.values()))
                    stored = conn.execute(f'SELECT * FROM "{table}" WHERE id=?', (clean["id"],)).fetchone()
                    if stored:
                        row_hashes[key] = row_digest(table, dict(stored))
                    applied += 1
            conn.commit()
            accounting_columns = {
                row[1] for row in conn.execute('PRAGMA table_info("accounting")')
            }
            if {"amount", "original_amount", "try_equivalent", "currency", "exchange_rate"}.issubset(accounting_columns):
                conn.execute(
                    """
                    UPDATE accounting
                       SET amount = ROUND(original_amount * exchange_rate, 4),
                           try_equivalent = ROUND(original_amount * exchange_rate, 4)
                     WHERE UPPER(COALESCE(currency, 'TRY')) IN ('USD', 'EUR')
                       AND COALESCE(original_amount, 0) > 0
                       AND COALESCE(exchange_rate, 0) > 1
                       AND ABS(COALESCE(try_equivalent, 0) - (original_amount * exchange_rate)) > 0.01
                    """
                )
            for table in tables:
                columns = [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')]
                if "id" not in columns:
                    continue
                for record in conn.execute(f'SELECT * FROM "{table}" ORDER BY id DESC LIMIT 5000').fetchall():
                    row = dict(record)
                    digest = row_digest(table, row)
                    key = f"{table}:{row['id']}"
                    remote_missing = table in recovery_tables and key not in remote_keys
                    if row_hashes.get(key) == digest and not remote_missing:
                        conflict_hashes.pop(key, None)
                        continue
                    if conflict_hashes.get(key) == digest and not remote_missing:
                        continue
                    if not push_local:
                        row_hashes[key] = digest
                        continue
                    sync_row = dict(row)
                    if "updated_at" in columns:
                        # Legacy desktop save paths do not all touch updated_at.
                        # Stamp the detected local edit so timestamp-aware server
                        # reconciliation does not reject a valid hash-based push.
                        sync_row["updated_at"] = datetime.now().isoformat(
                            timespec="microseconds"
                        )
                        conn.execute(
                            f'UPDATE "{table}" SET updated_at=? WHERE id=?',
                            (sync_row["updated_at"], row["id"]),
                        )
                        digest = row_digest(table, sync_row)
                    if table == "offers":
                        sync_row.pop("pdf_path", None)
                    outgoing.append({
                        "table": table,
                        "row": sync_row,
                        "action": "upsert",
                        "base_hash": "" if table == "offers" else str(row_hashes.get(key) or ""),
                        "source_id": f"desktop:{state['machine_id']}:{table}:{row['id']}:{digest}",
                    })
                    pending_hashes[key] = digest
            conn.commit()
        pushed = self.push(outgoing) if outgoing else {"applied": 0, "skipped": 0, "errors": []}
        conflict_keys = {
            f"{item.get('table')}:{item.get('record_id')}"
            for item in (pushed.get("conflicts") or [])
            if item.get("table") and item.get("record_id") is not None
        }
        if not pushed.get("errors"):
            for key, digest in pending_hashes.items():
                if key in conflict_keys:
                    conflict_hashes[key] = digest
                    continue
                row_hashes[key] = digest
                conflict_hashes.pop(key, None)
        state["row_hashes"] = row_hashes
        state["conflict_hashes"] = conflict_hashes
        state["reconciliation_version"] = 2
        state["since"] = {
            table: (
                details.get("last_timestamp") or ""
                if "updated_at" in (details.get("columns") or [])
                else 0
            )
            for table, details in (manifest.get("tables") or {}).items()
        }
        state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_state = state_path.with_suffix(state_path.suffix + ".tmp")
        try:
            temporary_state.write_text(
                json.dumps(state, ensure_ascii=True, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary_state, state_path)
        finally:
            temporary_state.unlink(missing_ok=True)
        return {
            "ok": not pushed.get("errors"),
            "tenant_id": manifest.get("tenant_id"),
            "pulled": applied,
            "pushed": pushed,
            "preserved_conflicts": preserved_conflicts,
            "recovered_state": recovered_state,
            "sync_epoch": remote_epoch,
            "epoch_reset_backup": epoch_reset_backup,
        }


def apply_pending_restore(database_path: str | Path) -> dict:
    from ayec_core.restore import apply_pending_restore as apply_shared_restore
    try:
        return apply_shared_restore(database_path, product_code="teknik_servis")
    except ValueError as error:
        raise WebSyncError(str(error)) from error


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _blob(data: bytes):
    buffer = ctypes.create_string_buffer(data)
    return _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer


def _protect_for_current_user(data: bytes) -> bytes:
    if os.name != "nt":
        return data
    source, source_buffer = _blob(data)
    output = _DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source),
        "AYEC Pro Web Sync",
        None,
        None,
        None,
        0,
        ctypes.byref(output),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def _unprotect_for_current_user(data: bytes) -> bytes:
    if os.name != "nt":
        return data
    source, source_buffer = _blob(data)
    output = _DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(output),
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)
