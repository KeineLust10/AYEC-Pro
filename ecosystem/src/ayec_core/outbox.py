"""Durable, product-scoped queue for retryable central operations."""

import json
import hashlib
import random
import sqlite3
import time
import uuid
from pathlib import Path
from contextlib import contextmanager


RETRY_DELAYS = (60, 300, 900, 1800, 3600, 21600)


class DurableOutbox:
    def __init__(self, path, *, product_code, tenant_id, installation_id):
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.scope = (str(product_code), str(tenant_id), str(installation_id))
        if not all(self.scope):
            raise ValueError("Outbox scope fields are required")
        self._initialize()

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self):
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS outbox (
                    id TEXT PRIMARY KEY, product_code TEXT NOT NULL,
                    tenant_id TEXT NOT NULL, installation_id TEXT NOT NULL,
                    operation TEXT NOT NULL, payload TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL UNIQUE, state TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL,
                    created_at REAL NOT NULL, last_error TEXT NOT NULL DEFAULT ''
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS command_journal (
                    command_id TEXT PRIMARY KEY, result TEXT NOT NULL,
                    created_at REAL NOT NULL
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS outbox_due ON outbox(state, next_attempt)"
            )

    def enqueue(self, operation, payload, *, idempotency_key=None, now=None):
        created = float(time.time() if now is None else now)
        item_id = str(uuid.uuid4())
        raw_key = str(idempotency_key or item_id)
        key = self._scoped_key(raw_key)
        serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT id FROM outbox WHERE idempotency_key IN (?,?) "
                "AND product_code=? AND tenant_id=? AND installation_id=?",
                (key, raw_key, *self.scope),
            ).fetchone()
            if existing:
                return existing["id"]
            connection.execute(
                """INSERT INTO outbox
                (id, product_code, tenant_id, installation_id, operation, payload,
                 idempotency_key, state, next_attempt, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?)""",
                (item_id, *self.scope, str(operation), serialized, key, created, created),
            )
        return item_id

    def due(self, *, now=None, limit=25):
        current = float(time.time() if now is None else now)
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT * FROM outbox WHERE state IN ('queued', 'retry')
                AND next_attempt <= ? AND product_code = ? AND tenant_id = ?
                AND installation_id = ? ORDER BY created_at LIMIT ?""",
                (current, *self.scope, int(limit)),
            ).fetchall()
        return [self._decode(row) for row in rows]

    def mark_done(self, item_id):
        self._set_state(item_id, "done", 0, "")

    def mark_retry(self, item_id, error, *, now=None, jitter=True, retry_after=None):
        current = float(time.time() if now is None else now)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT attempts FROM outbox WHERE id = ? AND product_code = ? AND tenant_id = ? AND installation_id = ?",
                (str(item_id), *self.scope),
            ).fetchone()
            if not row:
                raise KeyError(item_id)
            attempts = int(row["attempts"]) + 1
            delay = RETRY_DELAYS[min(attempts - 1, len(RETRY_DELAYS) - 1)]
            if retry_after is not None:
                try:
                    # Honor the server's minimum wait while keeping an outage
                    # from pinning the queue indefinitely.
                    delay = max(delay, min(float(retry_after), RETRY_DELAYS[-1]))
                except (TypeError, ValueError):
                    pass
            if jitter:
                delay *= random.uniform(0.85, 1.15)
            connection.execute(
                "UPDATE outbox SET state = 'retry', attempts = ?, next_attempt = ?, last_error = ? WHERE id = ?",
                (attempts, current + delay, str(error)[:500], str(item_id)),
            )

    def quarantine(self, item_id, error):
        self._set_state(item_id, "quarantined", 0, str(error)[:500])

    def get(self, item_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM outbox WHERE id = ? AND product_code = ? AND tenant_id = ? AND installation_id = ?",
                (str(item_id), *self.scope),
            ).fetchone()
        return self._decode(row) if row else None

    def count_pending(self):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM outbox WHERE state IN ('queued', 'retry') AND product_code = ? AND tenant_id = ? AND installation_id = ?",
                self.scope,
            ).fetchone()
        return int(row["count"])

    def command_result(self, command_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT result FROM command_journal WHERE command_id = ?",
                (self._scoped_key(str(command_id)),),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["result"])

    def record_command_result(self, command_id, result, *, now=None):
        created = float(time.time() if now is None else now)
        serialized = json.dumps(result or {}, ensure_ascii=True,
                                sort_keys=True, separators=(",", ":"))
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO command_journal(command_id,result,created_at) VALUES(?,?,?)",
                (self._scoped_key(str(command_id)), serialized, created),
            )
        return self.command_result(command_id)

    def _scoped_key(self, value):
        scope_hash = hashlib.sha256(json.dumps(self.scope).encode("utf-8")).hexdigest()
        return scope_hash + ":" + str(value)

    def bind_tenant(self, tenant_id):
        """Adopt locally queued backups only at the first verified sign-in."""
        if self.scope[1] != "local" or not tenant_id or tenant_id == "local":
            raise ValueError("Only unbound local outbox items may be adopted")
        product, _, installation = self.scope
        new_scope = (product, str(tenant_id), installation)
        prefix = hashlib.sha256(json.dumps(new_scope).encode("utf-8")).hexdigest() + ":"
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id,idempotency_key FROM outbox WHERE product_code=? AND tenant_id=? AND installation_id=?",
                self.scope,
            ).fetchall()
            for row in rows:
                old_key = str(row["idempotency_key"])
                raw_key = old_key.split(":", 1)[1] if old_key.startswith(self._scoped_key("")) else old_key
                connection.execute("UPDATE outbox SET tenant_id=?,idempotency_key=? WHERE id=?",
                                   (str(tenant_id), prefix + raw_key, row["id"]))
        self.scope = new_scope

    def _set_state(self, item_id, state, next_attempt, error):
        with self._connect() as connection:
            cursor = connection.execute(
                """UPDATE outbox SET state = ?, next_attempt = ?, last_error = ?
                WHERE id = ? AND product_code = ? AND tenant_id = ? AND installation_id = ?""",
                (state, float(next_attempt), error, str(item_id), *self.scope),
            )
            if cursor.rowcount != 1:
                raise KeyError(item_id)

    @staticmethod
    def _decode(row):
        result = dict(row)
        result["payload"] = json.loads(result["payload"])
        return result
