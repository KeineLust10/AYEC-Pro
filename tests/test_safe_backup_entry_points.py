import sqlite3
import threading
from pathlib import Path

from PyQt6.QtCore import QCoreApplication

from src.ui.pages import backup_page
from src.db.mixins.schema_mixin import SchemaMixin
from src.utils.backup_scheduler import BackupScheduler
from src.utils.path_helper import PathHelper


class _SchedulerDb:
    def __init__(self, target):
        self.target = Path(target)
        self.calls = []

    def get_setting(self, key, default=""):
        if key == "company_name":
            return "AYEC Pro"
        return default

    def backup_database(self, target_name=None):
        self.calls.append(target_name)
        self.target.write_bytes(b"validated-backup")
        return str(self.target)


def test_scheduler_uses_validated_database_backup_api(tmp_path):
    app = QCoreApplication.instance() or QCoreApplication([])
    db = _SchedulerDb(tmp_path / "scheduled.db")
    scheduler = BackupScheduler(db)
    events = []
    scheduler.backup_completed.connect(lambda kind, value: events.append((kind, value)))

    try:
        assert scheduler.perform_backup("test") is True
        app.processEvents()
    finally:
        scheduler.timer.stop()

    assert len(db.calls) == 1
    assert db.calls[0].startswith("AYEC Pro_")
    assert events == [("success", str(db.target))]


def test_local_restore_uses_validated_database_restore_api(monkeypatch, tmp_path):
    source = tmp_path / "backup.db"
    source.write_bytes(b"backup")
    calls = []

    class Db:
        def restore_database(self, path):
            calls.append(path)
            return True

    class Page:
        db = Db()

    messages = []
    monkeypatch.setattr(
        backup_page.QFileDialog,
        "getOpenFileName",
        lambda *args, **kwargs: (str(source), ""),
    )
    monkeypatch.setattr(
        backup_page, "show_success", lambda *args: messages.append("success")
    )
    monkeypatch.setattr(
        backup_page, "show_error", lambda *args: messages.append("error")
    )

    backup_page.BackupPage.restore_local_backup(Page())

    assert calls == [str(source)]
    assert messages == ["success"]


def test_validated_backup_restore_round_trip_and_rejects_corruption(
    monkeypatch, tmp_path
):
    import src.database as database_module

    db_path = tmp_path / "live.db"
    app_data = tmp_path / "app-data"
    app_data.mkdir()

    monkeypatch.setattr(database_module, "sqlite3", sqlite3)
    monkeypatch.setattr(database_module, "SQLCIPHER_AVAILABLE", False)
    monkeypatch.setattr(PathHelper, "get_app_data_dir", lambda: str(app_data))
    monkeypatch.setattr(
        PathHelper, "get_db_path", lambda db_name=None: str(db_path)
    )

    class Db(SchemaMixin):
        pass

    db = Db()
    db._db_name = "live.db"
    db.lock = threading.RLock()
    db.conn = sqlite3.connect(db_path)
    db.cursor = db.conn.cursor()
    db.cursor.execute("CREATE TABLE sample (value TEXT NOT NULL)")
    db.cursor.execute("INSERT INTO sample(value) VALUES ('original')")
    db.conn.commit()

    try:
        backup = db.backup_database(target_name="round-trip.db")
        assert backup is not None

        db.cursor.execute("UPDATE sample SET value = 'changed'")
        db.conn.commit()
        assert db.restore_database(backup) is True
        assert db.cursor.execute("SELECT value FROM sample").fetchone()[0] == "original"

        corrupted = tmp_path / "corrupted.db"
        corrupted.write_bytes(b"not-a-database")
        assert db.restore_database(corrupted) is False
        assert db.cursor.execute("SELECT value FROM sample").fetchone()[0] == "original"
    finally:
        db.conn.close()
