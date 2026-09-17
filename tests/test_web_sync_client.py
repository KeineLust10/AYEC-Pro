import json
import sqlite3
import hashlib
import urllib.error
from pathlib import Path

from src.utils.web_sync_client import WebSyncClient, WebSyncError


class FakeSyncClient(WebSyncClient):
    def __init__(self):
        super().__init__("http://example.invalid", verify_tls=False)
        self.pushed = []

    def manifest(self):
        return {
            "tenant_id": "tenant-test",
            "tables": {"parts": {"last_id": 2}},
        }

    def pull(self, since=None, tables=None):
        return {
            "changes": {
                "parts": [
                    {
                        "id": 2,
                        "name": "Remote camera",
                        "stock": 10,
                        "updated_at": "2026-07-18 10:00:00",
                    }
                ]
            }
        }

    def push(self, changes):
        self.pushed.extend(changes)
        return {"applied": len(changes), "skipped": 0, "errors": []}


class EpochResetSyncClient(FakeSyncClient):
    def manifest(self):
        return {
            "tenant_id": "tenant-test",
            "sync_epoch": 2,
            "reset_tables": ["parts"],
            "tables": {"parts": {"last_id": 0}},
        }

    def pull(self, since=None, tables=None):
        return {"changes": {"parts": []}}


class OfferSyncClient(FakeSyncClient):
    def manifest(self):
        return {
            "tenant_id": "tenant-test",
            "tables": {"offers": {"last_id": 1}},
        }

    def pull(self, since=None, tables=None):
        return {
            "changes": {
                "offers": [
                    {
                        "id": 1,
                        "offer_no": "PRF-WEB-1",
                        "pdf_path": "C:/server/temp/offer.pdf",
                        "updated_at": "2026-07-18 10:00:00",
                    }
                ]
            }
        }


class ConflictSyncClient(FakeSyncClient):
    def manifest(self):
        return {
            "tenant_id": "tenant-test",
            "tables": {"parts": {"last_id": 1}},
        }

    def pull(self, since=None, tables=None):
        return {
            "changes": {
                "parts": [
                    {
                        "id": 1,
                        "name": "Remote edit",
                        "stock": 3,
                        "updated_at": "2026-07-18 12:00:00",
                    }
                ]
            }
        }

    def push(self, changes):
        self.pushed.extend(changes)
        return {
            "applied": 0,
            "skipped": len(changes),
            "conflicts": [{"table": "parts", "record_id": "1"}],
            "errors": [],
        }


class CreatedAtOnlySyncClient(FakeSyncClient):
    def manifest(self):
        return {
            "tenant_id": "tenant-test",
            "tables": {
                "parts": {
                    "last_id": 1,
                    "last_timestamp": "2026-07-18 09:00:00",
                    "columns": ["id", "name", "stock", "created_at"],
                }
            },
        }

    def pull(self, since=None, tables=None):
        self.last_since = dict(since or {})
        with sqlite3.connect(self.local_path) as conn:
            remote = conn.execute(
                "SELECT id, name, stock, created_at FROM remote_parts WHERE id=1"
            ).fetchone()
        return {
            "changes": {
                "parts": [
                    {
                        "id": remote[0],
                        "name": remote[1],
                        "stock": remote[2],
                        "created_at": remote[3],
                    }
                ]
            }
        }


class MissingRemoteRowSyncClient(FakeSyncClient):
    def manifest(self):
        return {
            "tenant_id": "tenant-test",
            "tables": {
                "parts": {
                    "last_id": 0,
                    "last_timestamp": "",
                    "columns": ["id", "name", "stock", "updated_at"],
                }
            },
        }

    def pull(self, since=None, tables=None):
        self.last_since = dict(since or {})
        return {"changes": {"parts": []}}

def _create_database(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE parts ("
            "id INTEGER PRIMARY KEY, name TEXT, stock INTEGER, updated_at TEXT)"
        )
        conn.execute(
            "INSERT INTO parts (id, name, stock, updated_at) VALUES (1, ?, 1, ?)",
            ("Local default", "2026-07-18 09:00:00"),
        )


def test_initial_remote_link_is_pull_only(tmp_path):
    db_path = tmp_path / "desktop.db"
    state_path = tmp_path / "sync-state.json"
    _create_database(db_path)
    client = FakeSyncClient()

    result = client.sync_sqlite(db_path, state_path, push_local=False)

    assert result["ok"] is True
    assert result["pulled"] == 1
    assert client.pushed == []
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "parts:1" in state["row_hashes"]
    assert "parts:2" in state["row_hashes"]


def test_epoch_change_clears_old_local_rows_before_push(tmp_path):
    db_path = tmp_path / "desktop.db"
    state_path = tmp_path / "sync-state.json"
    _create_database(db_path)
    state_path.write_text(
        json.dumps({"machine_id": "old-device", "sync_epoch": 1}),
        encoding="utf-8",
    )
    client = EpochResetSyncClient()

    result = client.sync_sqlite(db_path, state_path)

    assert result["sync_epoch"] == 2
    assert result["epoch_reset_backup"]
    assert Path(result["epoch_reset_backup"]).is_file()
    assert client.pushed == []
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM parts").fetchone()[0] == 0
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["sync_epoch"] == 2


def test_later_local_change_is_pushed(tmp_path):
    db_path = tmp_path / "desktop.db"
    state_path = tmp_path / "sync-state.json"
    _create_database(db_path)
    client = FakeSyncClient()
    client.sync_sqlite(db_path, state_path, push_local=False)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE parts SET stock=7, updated_at=? WHERE id=1",
            ("2026-07-18 11:00:00",),
        )

    result = client.sync_sqlite(db_path, state_path)

    assert result["ok"] is True
    assert len(client.pushed) == 1
    assert client.pushed[0]["table"] == "parts"
    assert client.pushed[0]["row"]["stock"] == 7


def test_offer_pdf_path_remains_machine_local(tmp_path):
    db_path = tmp_path / "desktop.db"
    state_path = tmp_path / "sync-state.json"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE offers ("
            "id INTEGER PRIMARY KEY, offer_no TEXT, pdf_path TEXT, updated_at TEXT)"
        )
    client = OfferSyncClient()

    client.sync_sqlite(db_path, state_path, push_local=False)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT offer_no, pdf_path FROM offers WHERE id=1").fetchone()
        assert row == ("PRF-WEB-1", None)
        conn.execute(
            "UPDATE offers SET pdf_path=?, updated_at=? WHERE id=1",
            ("C:/desktop/cache/offer.pdf", "2026-07-18 11:00:00"),
        )

    client.sync_sqlite(db_path, state_path)

    assert len(client.pushed) == 1
    assert client.pushed[0]["table"] == "offers"
    assert "pdf_path" not in client.pushed[0]["row"]


def test_concurrent_row_is_preserved_and_not_retried(tmp_path):
    db_path = tmp_path / "desktop.db"
    state_path = tmp_path / "sync-state.json"
    _create_database(db_path)
    base_row = {
        "id": 1,
        "name": "Local default",
        "stock": 1,
        "updated_at": "2026-07-18 09:00:00",
    }
    base_hash = hashlib.sha256(
        json.dumps(base_row, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    state_path.write_text(
        json.dumps(
            {
                "machine_id": "desktop-test",
                "row_hashes": {"parts:1": base_hash},
                "since": {},
            }
        ),
        encoding="utf-8",
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE parts SET name=?, stock=?, updated_at=? WHERE id=1",
            ("Local edit", 7, "2026-07-18 11:00:00"),
        )
    client = ConflictSyncClient()

    result = client.sync_sqlite(db_path, state_path)

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT name, stock FROM parts WHERE id=1").fetchone() == (
            "Local edit",
            7,
        )
    assert result["preserved_conflicts"] == [{"table": "parts", "record_id": "1"}]
    assert client.pushed[0]["base_hash"] == base_hash
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["conflict_hashes"]["parts:1"]

    client.sync_sqlite(db_path, state_path)

    assert len(client.pushed) == 1


def test_created_at_only_table_is_fully_reconciled_without_losing_local_edit(tmp_path):
    db_path = tmp_path / "desktop.db"
    state_path = tmp_path / "sync-state.json"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE parts (id INTEGER PRIMARY KEY, name TEXT, stock INTEGER, created_at TEXT)"
        )
        conn.execute(
            "INSERT INTO parts VALUES (1, 'Shared part', 1, '2026-07-18 09:00:00')"
        )
        conn.execute(
            "CREATE TABLE remote_parts (id INTEGER PRIMARY KEY, name TEXT, stock INTEGER, created_at TEXT)"
        )
        conn.execute(
            "INSERT INTO remote_parts VALUES (1, 'Shared part', 1, '2026-07-18 09:00:00')"
        )
    client = CreatedAtOnlySyncClient()
    client.local_path = db_path

    client.sync_sqlite(db_path, state_path, push_local=False)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["since"]["parts"] == 0

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE parts SET stock=7 WHERE id=1")
    result = client.sync_sqlite(db_path, state_path)

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT stock FROM parts WHERE id=1").fetchone()[0] == 7
    assert result["preserved_conflicts"] == [{"table": "parts", "record_id": "1"}]
    assert client.pushed[-1]["row"]["stock"] == 7


def test_upgrade_repushes_row_missing_from_remote_database(tmp_path):
    db_path = tmp_path / "desktop.db"
    state_path = tmp_path / "sync-state.json"
    _create_database(db_path)
    with sqlite3.connect(db_path) as conn:
        row = dict(
            zip(
                ("id", "name", "stock", "updated_at"),
                conn.execute("SELECT * FROM parts WHERE id=1").fetchone(),
            )
        )
    digest = hashlib.sha256(
        json.dumps(row, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    state_path.write_text(
        json.dumps(
            {
                "machine_id": "desktop-test",
                "row_hashes": {"parts:1": digest},
                "since": {"parts": "2026-07-18 09:00:00"},
                "reconciliation_version": 1,
            }
        ),
        encoding="utf-8",
    )
    client = MissingRemoteRowSyncClient()

    result = client.sync_sqlite(db_path, state_path)

    assert result["ok"] is True
    assert client.last_since["parts"] == 0
    assert client.pushed[-1]["table"] == "parts"
    assert client.pushed[-1]["row"]["id"] == 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["reconciliation_version"] == 2


def test_corrupt_state_is_quarantined_and_reconciled(tmp_path):
    db_path = tmp_path / "desktop.db"
    state_path = tmp_path / "sync-state.json"
    _create_database(db_path)
    state_path.write_text("{broken-json", encoding="utf-8")
    client = FakeSyncClient()

    result = client.sync_sqlite(db_path, state_path)

    assert result["ok"] is True
    assert result["recovered_state"]
    assert not Path(result["recovered_state"]).samefile(state_path)
    assert Path(result["recovered_state"]).read_text(encoding="utf-8") == "{broken-json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert "machine_id" in state
    assert "parts:1" in state["row_hashes"]


def test_gateway_error_has_server_recovery_message(monkeypatch):
    def unavailable(*_args, **_kwargs):
        raise urllib.error.HTTPError("http://server", 502, "Bad Gateway", {}, None)

    monkeypatch.setattr("urllib.request.urlopen", unavailable)
    client = WebSyncClient("http://server", verify_tls=False)

    try:
        client.manifest()
    except WebSyncError as error:
        assert error.status_code == 502
        assert "IIS" in str(error)
    else:
        raise AssertionError("Expected a gateway error")
