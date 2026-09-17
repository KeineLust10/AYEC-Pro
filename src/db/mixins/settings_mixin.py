# -*- coding: utf-8 -*-

"""Runtime-cached application settings and configuration methods."""


class SettingsMixin:
    """Database methods for settings, templates, and quick notes."""

    _SETTING_TABLES = frozenset({"settings", "internal_settings"})

    def _ensure_settings_runtime(self):
        if not hasattr(self, "_settings_runtime_cache"):
            self._settings_runtime_cache = {
                "settings": {},
                "internal_settings": {},
            }
            self._settings_runtime_loaded = set()
            self._settings_runtime_listeners = []

    def _load_settings_runtime_table(self, table_name):
        if table_name not in self._SETTING_TABLES:
            raise ValueError(f"Unsupported settings table: {table_name}")
        self._ensure_settings_runtime()
        if table_name in self._settings_runtime_loaded:
            return
        rows = self.cursor.execute(
            f'SELECT "key", "value" FROM "{table_name}"'
        ).fetchall()
        self._settings_runtime_cache[table_name] = {
            str(row[0]): row[1] for row in rows
        }
        self._settings_runtime_loaded.add(table_name)

    def _get_cached_setting_value(self, table_name, key, default=None):
        cache_key = str(key)
        lock = getattr(self, "lock", None)
        if lock is None:
            self._load_settings_runtime_table(table_name)
            return self._settings_runtime_cache[table_name].get(cache_key, default)
        with lock:
            self._load_settings_runtime_table(table_name)
            return self._settings_runtime_cache[table_name].get(cache_key, default)

    def _set_cached_setting_value(self, table_name, key, value):
        if table_name not in self._SETTING_TABLES:
            raise ValueError(f"Unsupported settings table: {table_name}")
        cache_key = str(key)
        stored_value = None if value is None else str(value)
        lock = getattr(self, "lock", None)

        def _write():
            self._ensure_settings_runtime()
            table_was_loaded = table_name in self._settings_runtime_loaded
            self.cursor.execute(
                f'INSERT OR REPLACE INTO "{table_name}" ("key", "value") '
                "VALUES (?, ?)",
                (cache_key, stored_value),
            )
            self.conn.commit()
            self._settings_runtime_cache[table_name][cache_key] = stored_value
            if table_was_loaded:
                self._settings_runtime_loaded.add(table_name)
            else:
                self._settings_runtime_loaded.discard(table_name)

        if lock is None:
            _write()
        else:
            with lock:
                _write()
        self._notify_setting_changed(
            cache_key,
            stored_value,
            internal=table_name == "internal_settings",
        )
        return True

    def preload_settings_cache(self):
        """Load both settings tables in two queries during idle startup."""
        for table_name in self._SETTING_TABLES:
            try:
                self._load_settings_runtime_table(table_name)
            except Exception:
                continue

    def invalidate_settings_cache(self, table_name=None):
        """Discard cached values after restore, sync, or direct SQL writes."""
        self._ensure_settings_runtime()
        tables = self._SETTING_TABLES if table_name is None else {table_name}
        for name in tables:
            if name not in self._SETTING_TABLES:
                continue
            self._settings_runtime_cache[name] = {}
            self._settings_runtime_loaded.discard(name)

    def update_settings_cache_entry(
        self,
        table_name,
        key,
        value,
        notify=False,
    ):
        """Mirror a direct transactional SQL write into an already loaded cache."""
        if table_name not in self._SETTING_TABLES:
            raise ValueError(f"Unsupported settings table: {table_name}")
        self._ensure_settings_runtime()
        if table_name not in self._settings_runtime_loaded:
            return
        cache_key = str(key)
        stored_value = None if value is None else str(value)
        self._settings_runtime_cache[table_name][cache_key] = stored_value
        if notify:
            self._notify_setting_changed(
                cache_key,
                stored_value,
                internal=table_name == "internal_settings",
            )

    def subscribe_setting_changes(self, callback):
        """Subscribe to runtime setting writes made through this database."""
        self._ensure_settings_runtime()
        if callable(callback) and callback not in self._settings_runtime_listeners:
            self._settings_runtime_listeners.append(callback)

    def unsubscribe_setting_changes(self, callback):
        self._ensure_settings_runtime()
        self._settings_runtime_listeners = [
            listener
            for listener in self._settings_runtime_listeners
            if listener != callback
        ]

    def _notify_setting_changed(self, key, value, internal=False):
        self._ensure_settings_runtime()
        for listener in tuple(self._settings_runtime_listeners):
            try:
                listener(str(key), value, bool(internal))
            except Exception:
                continue

    def get_setting(self, key, default=""):
        """Return an application setting from the runtime cache."""
        return self._get_cached_setting_value("settings", key, default)

    def set_setting(self, key, value):
        """Persist an application setting and refresh runtime listeners."""
        return self._set_cached_setting_value("settings", key, value)

    def get_templates(self):
        self.cursor.execute("SELECT * FROM whatsapp_templates")
        return self.cursor.fetchall()

    def add_template(self, name, content):
        self.cursor.execute(
            "INSERT INTO whatsapp_templates (name, content) VALUES (?, ?)",
            (name, content),
        )
        self.conn.commit()

    def delete_template(self, template_id):
        self.cursor.execute(
            "DELETE FROM whatsapp_templates WHERE id=?",
            (template_id,),
        )
        self.conn.commit()

    def get_quick_notes(self, group_name=None):
        if group_name:
            self.cursor.execute(
                "SELECT * FROM quick_notes WHERE group_name=?",
                (group_name,),
            )
        else:
            self.cursor.execute("SELECT * FROM quick_notes")
        return self.cursor.fetchall()

    def add_quick_note(self, group_name, label, category="Genel"):
        self.cursor.execute(
            "INSERT INTO quick_notes (group_name, label, category) "
            "VALUES (?, ?, ?)",
            (group_name, label, category),
        )
        self.conn.commit()

    def update_quick_note(self, note_id, label, is_active, category):
        self.cursor.execute(
            "UPDATE quick_notes SET label=?, is_active=?, category=? WHERE id=?",
            (label, is_active, category, note_id),
        )
        self.conn.commit()

    def delete_quick_note(self, note_id):
        self.cursor.execute("DELETE FROM quick_notes WHERE id=?", (note_id,))
        self.conn.commit()

    def get_fast_notes(self, category=None):
        if category:
            self.cursor.execute(
                "SELECT * FROM fast_notes WHERE category=? ORDER BY display_order",
                (category,),
            )
        else:
            self.cursor.execute("SELECT * FROM fast_notes ORDER BY display_order")
        return self.cursor.fetchall()

    def add_fast_note(self, category, label, is_active=1, order=0):
        self.cursor.execute(
            "INSERT INTO fast_notes "
            "(category, label, is_active, display_order) VALUES (?, ?, ?, ?)",
            (category, label, is_active, order),
        )
        self.conn.commit()

    def update_fast_note(self, note_id, label, is_active, category, order=0):
        self.cursor.execute(
            "UPDATE fast_notes "
            "SET label=?, is_active=?, category=?, display_order=? WHERE id=?",
            (label, is_active, category, order, note_id),
        )
        self.conn.commit()

    def delete_fast_note(self, note_id):
        self.cursor.execute("DELETE FROM fast_notes WHERE id=?", (note_id,))
        self.conn.commit()
