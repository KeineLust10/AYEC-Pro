import sqlite3
import shutil
import sys
import tempfile
import threading
import types
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


def test_cloud_restore_aborts_if_local_safety_backup_fails(monkeypatch, tmp_path):
    current_db = tmp_path / "current.db"
    current_db.write_bytes(b"local-database")
    downloaded = tmp_path / "server_sync_download.db"
    messages = []
    copies = []

    class Confirmation:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return True

    class Provider:
        def download(self, remote_name, destination):
            assert remote_name == "server_sync.db"
            Path(destination).write_bytes(b"remote-database")
            return True

    class Manager:
        providers = {"remote": Provider()}

    def fail_copy(*args):
        copies.append(args)
        raise OSError("disk full")

    confirmation_module = types.ModuleType("src.ui.dialogs.simple_confirm")
    confirmation_module.SimpleConfirmDialog = Confirmation
    monkeypatch.setitem(sys.modules, "src.ui.dialogs.simple_confirm", confirmation_module)
    monkeypatch.setattr(backup_page.PathHelper, "get_db_path", lambda: str(current_db))
    monkeypatch.setattr(backup_page, "get_cloud_backup_manager", lambda _path: Manager())
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(shutil, "copy2", fail_copy)
    monkeypatch.setattr(backup_page, "show_info", lambda *args: messages.append("info"))
    monkeypatch.setattr(backup_page, "show_error", lambda _page, message: messages.append(message))
    monkeypatch.setattr(backup_page, "show_warning", lambda *args: messages.append("warning"))
    monkeypatch.setattr(backup_page, "show_success", lambda *args: messages.append("success"))

    class Page:
        pass

    backup_page.BackupPage.restore_cloud_backup(Page())

    assert current_db.read_bytes() == b"local-database"
    assert not downloaded.exists()
    assert len(copies) == 1
    assert len(messages) == 2
    assert messages[0] == "info"
    assert "sunucu geri y" in messages[1]


def test_cloud_restore_rolls_back_if_remote_database_replace_fails(monkeypatch, tmp_path):
    current_db = tmp_path / "current.db"
    current_db.write_bytes(b"local-database")
    downloaded = tmp_path / "server_sync_download.db"
    copies = []
    messages = []

    class Confirmation:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return True

    class Provider:
        def download(self, _remote_name, destination):
            Path(destination).write_bytes(b"remote-database")
            return True

    class Manager:
        providers = {"remote": Provider()}

    def copy_with_remote_failure(source, destination):
        source_path = Path(source)
        destination_path = Path(destination)
        copies.append((source_path, destination_path))
        if source_path == downloaded:
            destination_path.write_bytes(b"partial-remote-database")
            raise OSError("disk full")
        destination_path.write_bytes(source_path.read_bytes())

    confirmation_module = types.ModuleType("src.ui.dialogs.simple_confirm")
    confirmation_module.SimpleConfirmDialog = Confirmation
    monkeypatch.setitem(sys.modules, "src.ui.dialogs.simple_confirm", confirmation_module)
    monkeypatch.setattr(backup_page.PathHelper, "get_db_path", lambda: str(current_db))
    monkeypatch.setattr(backup_page, "get_cloud_backup_manager", lambda _path: Manager())
    monkeypatch.setattr(tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(shutil, "copy2", copy_with_remote_failure)
    monkeypatch.setattr(backup_page, "show_info", lambda *_args: messages.append("info"))
    monkeypatch.setattr(backup_page, "show_error", lambda _page, message: messages.append(message))
    monkeypatch.setattr(backup_page, "show_warning", lambda *_args: messages.append("warning"))
    monkeypatch.setattr(backup_page, "show_success", lambda *_args: messages.append("success"))

    class Page:
        pass

    backup_page.BackupPage.restore_cloud_backup(Page())

    assert current_db.read_bytes() == b"local-database"
    assert not downloaded.exists()
    assert len(copies) == 3
    assert messages[0] == "info"
    assert "yerel yedek geri y" in messages[-1]


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
