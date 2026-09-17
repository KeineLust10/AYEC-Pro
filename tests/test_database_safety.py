import sqlite3
import threading

import pytest

from src.db.mixins._db_legacy_maintenance_mixin import DBLegacyMaintenanceMixin
from src.db.mixins.schema_mixin import SchemaMixin
from src.repositories.base_repository import BaseRepository, RepositoryError
from src.utils.path_helper import PathHelper


class ExampleRepository(BaseRepository):
    def _get_table_name(self):
        return "records"


class DatabaseHarness(SchemaMixin, DBLegacyMaintenanceMixin):
    def __init__(self, connection, db_name):
        self.conn = connection
        self.cursor = connection.cursor()
        self.lock = threading.RLock()
        self._db_name = db_name


def test_repository_pagination_uses_validated_integer_values():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE records (id INTEGER PRIMARY KEY, is_deleted INTEGER DEFAULT 0)"
    )
    connection.executemany(
        "INSERT INTO records (id) VALUES (?)",
        [(1,), (2,), (3,)],
    )
    repository = ExampleRepository(connection)

    assert [row["id"] for row in repository.get_all(limit=2, offset=1)] == [2, 1]
    with pytest.raises(RepositoryError):
        repository.get_all(limit="1; DROP TABLE records")
    assert connection.execute("SELECT COUNT(*) FROM records").fetchone()[0] == 3


def test_wal_backup_and_restore_are_complete(tmp_path, monkeypatch):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    db_name = "live.db"
    db_path = app_dir / db_name
    monkeypatch.setattr(PathHelper, "get_app_data_dir", lambda: str(app_dir))
    monkeypatch.setattr(
        PathHelper,
        "get_db_path",
        lambda name="ayecpro.db": str(app_dir / name),
    )

    connection = sqlite3.connect(str(db_path))
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE records (id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO records (value) VALUES ('from-backup')")
    connection.commit()
    harness = DatabaseHarness(connection, db_name)

    backup_path = harness.backup_database(target_name="wal-test.db")
    assert backup_path
    with sqlite3.connect(backup_path) as backup_conn:
        assert backup_conn.execute("SELECT value FROM records").fetchone()[0] == "from-backup"

    connection.execute("UPDATE records SET value='changed-after-backup'")
    connection.commit()
    assert harness.restore_database(backup_path) is True
    assert connection.execute("SELECT value FROM records").fetchone()[0] == "from-backup"
    assert list((app_dir / "backups").glob("before_restore_*.db"))
    connection.close()


def test_wipe_preserves_identity_tables_and_clears_user_data():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
    connection.execute("CREATE TABLE internal_settings (key TEXT PRIMARY KEY, value TEXT)")
    connection.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT)")
    connection.execute(
        "CREATE TABLE customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)"
    )
    connection.execute("INSERT INTO users VALUES (1, 'admin')")
    connection.execute("INSERT INTO customers (name) VALUES ('Example')")
    connection.commit()
    harness = DatabaseHarness(connection, ":memory:")

    assert harness.wipe_all_user_data() is True
    assert connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    connection.close()
