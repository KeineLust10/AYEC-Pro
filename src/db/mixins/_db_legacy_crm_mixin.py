# -*- coding: utf-8 -*-

from src.utils.logger import logger

class DBLegacyCRMMixin:
    """Legacy CRM methods for managing Quick Notes and Fast Notes."""

    def get_quick_notes(self, group_name=None):
        if group_name:
            self.cursor.execute("SELECT * FROM quick_notes WHERE group_name=? ORDER BY id", (group_name,))
        else:
            self.cursor.execute("SELECT * FROM quick_notes ORDER BY group_name, id")
        return self.cursor.fetchall()

    def add_quick_note(self, group_name, label, category="Genel"):
        self.cursor.execute("INSERT INTO quick_notes (group_name, label, is_active, category) VALUES (?, ?, 1, ?)", (group_name, label, category))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_quick_note(self, note_id, label, is_active, category):
        self.cursor.execute("UPDATE quick_notes SET label=?, is_active=?, category=? WHERE id=?", (label, is_active, category, note_id))
        self.conn.commit()

    def delete_quick_note(self, note_id):
        self.cursor.execute("DELETE FROM quick_notes WHERE id=?", (note_id,))
        self.conn.commit()

    def get_fast_notes(self, category=None):
        query = "SELECT * FROM fast_notes"
        params = []
        if category:
            query += " WHERE category=?"
            params.append(category)
        query += " ORDER BY display_order ASC"
        return self.cursor.execute(query, params).fetchall()

    def add_fast_note(self, category, label, is_active=1, order=0):
        self.cursor.execute("INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, ?, ?)", (category, label, is_active, order))
        self.conn.commit()

    def update_fast_note(self, note_id, label, is_active, category, order=0):
        self.cursor.execute("UPDATE fast_notes SET label=?, is_active=?, category=?, display_order=? WHERE id=?", (label, is_active, category, order, note_id))
        self.conn.commit()

    def delete_fast_note(self, note_id):
        self.cursor.execute("DELETE FROM fast_notes WHERE id=?", (note_id,))
        self.conn.commit()
