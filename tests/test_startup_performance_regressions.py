import sqlite3
from pathlib import Path

from src.database import Database
from src.utils.currency_helper import CurrencyHelper
from src.utils.startup_profiler import StartupProfiler
from src.utils.theme_manager import ThemeManager, ThemeQSSTransformer


def test_connection_only_does_not_run_schema_bootstrap(tmp_path):
    db_path = tmp_path / "connection_only.db"
    db = Database(str(db_path), init_mode="connection_only")
    tables = {
        row[0]
        for row in db.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    db.close()

    assert "_migrations" not in tables
    assert "customers" not in tables
    assert "parts" not in tables


def test_database_connection_uses_safe_runtime_cache_pragmas(tmp_path):
    db = Database(
        str(tmp_path / "runtime_cache.db"),
        init_mode="connection_only",
    )
    try:
        assert db.cursor.execute("PRAGMA busy_timeout").fetchone()[0] == 30000
        assert db.cursor.execute("PRAGMA cache_size").fetchone()[0] == -32768
        assert db.cursor.execute("PRAGMA temp_store").fetchone()[0] == 2
    finally:
        db.close()


def test_latest_database_reopen_skips_migration_scan(tmp_path, monkeypatch):
    db_path = tmp_path / "latest.db"
    first = Database(str(db_path), init_mode="full")
    assert (
        first.cursor.execute("PRAGMA user_version").fetchone()[0]
        == Database.CURRENT_SCHEMA_VERSION
    )
    assert first.cursor.execute(
        "SELECT COUNT(*) FROM _migrations"
    ).fetchone()[0] == Database.CURRENT_SCHEMA_VERSION
    first.close()

    def fail_if_called(_self):
        raise AssertionError("Latest schema must not scan or run migrations")

    monkeypatch.setattr(
        "src.database.MigrationManager.migrate",
        fail_if_called,
    )
    reopened = Database(str(db_path), init_mode="full")
    assert (
        reopened.cursor.execute("PRAGMA user_version").fetchone()[0]
        == Database.CURRENT_SCHEMA_VERSION
    )
    reopened.close()

    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM _migrations"
        ).fetchone()[0] == Database.CURRENT_SCHEMA_VERSION


def test_theme_qss_transform_is_cached(monkeypatch):
    calls = {"count": 0}

    def fake_transform(*args, **kwargs):
        calls["count"] += 1
        return "QWidget { color: #010203; }"

    ThemeManager._qss_transform_cache.clear()
    ThemeManager._qss_transformed_values.clear()
    monkeypatch.setattr(
        ThemeQSSTransformer,
        "transform_qss",
        fake_transform,
    )

    source = "QWidget { color: @text; }"
    first = ThemeManager.transform_qss(source)
    second = ThemeManager.transform_qss(source)
    already_transformed = ThemeManager.transform_qss(first)

    assert first == second == already_transformed
    assert calls["count"] == 1


def test_connection_only_does_not_replace_currency_context(tmp_path):
    primary = Database(str(tmp_path / "primary.db"), init_mode="full")
    CurrencyHelper.register_db(primary)

    worker = Database(
        str(tmp_path / "worker.db"),
        init_mode="connection_only",
    )

    assert CurrencyHelper.get_db() is primary
    worker.close()
    primary.close()
    CurrencyHelper._db = None


def test_latest_migration_adds_activity_indexes(tmp_path):
    db = Database(str(tmp_path / "indexes.db"), init_mode="full")
    indexes = {
        row[0]
        for row in db.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    db.close()

    assert "idx_offer_items_offer_id" in indexes
    assert "idx_appointments_customer_date_status" in indexes
    assert "idx_used_parts_part_created" in indexes


def test_startup_profiler_writes_timeline(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    profiler = StartupProfiler()
    profiler.mark("test.ready", "detail=ok")
    log_path = profiler.finish()

    expected = tmp_path / "AYEC Pro" / "startup_performance.log"
    assert Path(log_path) == expected
    content = expected.read_text(encoding="utf-8")
    assert "startup_timeline" in content
    assert "test.ready" in content
    assert "startup.complete" in content


def test_main_window_keeps_assistant_import_lazy():
    source = Path("src/ui/main_window.py").read_text(encoding="utf-8")

    assert "from src.services.assistant_manager import AssistantManager" not in source
