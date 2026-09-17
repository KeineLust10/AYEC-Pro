import sqlite3

from src.ui.dialogs.device_selection_dialog import DeviceSelectionDialog
from src.utils.automotive_defaults import (
    AUTOMOTIVE_PRESET,
    ensure_automotive_fast_notes,
)


class _SelectionDb:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE devices (
                id INTEGER PRIMARY KEY,
                tracking_no TEXT,
                customer_name TEXT,
                device_brand TEXT,
                device_model TEXT,
                serial_no TEXT,
                status TEXT,
                entry_date TEXT,
                is_deleted INTEGER DEFAULT 0,
                is_archived INTEGER DEFAULT 0
            )
            """
        )

    def _get_table_columns(self, table):
        return [row[1] for row in self.cursor.execute(f"PRAGMA table_info({table})")]


class _SelectionHarness:
    _row_value = staticmethod(DeviceSelectionDialog._row_value)

    def __init__(self, db):
        self.db = db


class _FastNotesDb:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE fast_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                label TEXT,
                is_active INTEGER DEFAULT 1,
                display_order INTEGER DEFAULT 0
            )
            """
        )

    def get_fast_notes(self, category):
        return self.cursor.execute(
            "SELECT * FROM fast_notes WHERE category=? ORDER BY display_order",
            (category,),
        ).fetchall()


def test_device_selector_includes_unicode_active_status_and_excludes_closed():
    db = _SelectionDb()
    db.cursor.executemany(
        """
        INSERT INTO devices (
            id, tracking_no, customer_name, device_brand, device_model,
            serial_no, status, entry_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                1,
                "SRV1",
                "Customer",
                "Audi",
                "A4",
                "10NG227",
                "Test S\u00fcrecinde",
                "2026-07-26",
            ),
            (
                2,
                "SRV2",
                "Closed",
                "Ford",
                "Focus",
                "10NG228",
                "Teslim Edildi",
                "2026-07-25",
            ),
        ],
    )
    db.conn.commit()

    rows = DeviceSelectionDialog._get_active_devices(_SelectionHarness(db))

    assert [row["tracking_no"] for row in rows] == ["SRV1"]


def test_automotive_note_seed_fills_missing_categories_without_overwrite():
    db = _FastNotesDb()
    first_category = next(iter(AUTOMOTIVE_PRESET))
    db.cursor.execute(
        """
        INSERT INTO fast_notes (category, label, is_active, display_order)
        VALUES (?, ?, 1, 0)
        """,
        (first_category, "CUSTOM"),
    )
    db.conn.commit()

    inserted = ensure_automotive_fast_notes(db)

    assert inserted > 0
    assert [row["label"] for row in db.get_fast_notes(first_category)] == ["CUSTOM"]
    for category in AUTOMOTIVE_PRESET:
        assert db.get_fast_notes(category)
    assert ensure_automotive_fast_notes(db) == 0
