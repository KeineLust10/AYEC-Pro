import sqlite3
import threading

from src.db.mixins.settings_mixin import SettingsMixin


class CountingCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.select_count = 0

    def execute(self, sql, params=()):
        if str(sql).lstrip().upper().startswith("SELECT"):
            self.select_count += 1
        self._cursor.execute(sql, params)
        return self

    def fetchall(self):
        return self._cursor.fetchall()

    def fetchone(self):
        return self._cursor.fetchone()


class CachedSettingsDb(SettingsMixin):
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = CountingCursor(self.conn.cursor())
        self.lock = threading.RLock()
        self.cursor.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        self.cursor.execute(
            "CREATE TABLE internal_settings (key TEXT PRIMARY KEY, value TEXT)"
        )
        self.conn.commit()


def test_settings_are_loaded_once_and_reused_from_memory():
    db = CachedSettingsDb()
    db.set_setting("company_name", "AYEC Pro")
    db.cursor.select_count = 0
    db.invalidate_settings_cache("settings")

    assert db.get_setting("company_name") == "AYEC Pro"
    assert db.get_setting("company_name") == "AYEC Pro"
    assert db.get_setting("missing", "fallback") == "fallback"
    assert db.cursor.select_count == 1


def test_setting_write_updates_cache_and_notifies_listener():
    db = CachedSettingsDb()
    events = []
    db.subscribe_setting_changes(
        lambda key, value, internal: events.append((key, value, internal))
    )

    db.set_setting("nav_mode", "ust_bar")

    assert db.get_setting("nav_mode") == "ust_bar"
    assert events == [("nav_mode", "ust_bar", False)]


def test_internal_setting_cache_uses_same_runtime_contract():
    db = CachedSettingsDb()
    events = []
    db.subscribe_setting_changes(
        lambda key, value, internal: events.append((key, value, internal))
    )

    db._set_cached_setting_value("internal_settings", "current_sector", "otomotiv")

    assert (
        db._get_cached_setting_value("internal_settings", "current_sector")
        == "otomotiv"
    )
    assert events == [("current_sector", "otomotiv", True)]


def test_direct_transaction_write_can_refresh_loaded_cache():
    db = CachedSettingsDb()
    db.set_setting("payment_number_next", "1")
    assert db.get_setting("payment_number_next") == "1"

    db.cursor.execute(
        "UPDATE settings SET value=? WHERE key=?",
        ("2", "payment_number_next"),
    )
    db.conn.commit()
    db.update_settings_cache_entry("settings", "payment_number_next", "2")

    assert db.get_setting("payment_number_next") == "2"
