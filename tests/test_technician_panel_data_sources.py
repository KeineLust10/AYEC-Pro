import sqlite3
from types import SimpleNamespace

from src.ui.dialogs.device_selection_dialog import DeviceSelectionDialog
from src.ui.dialogs._tp_operations import _TpOperations
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


def test_silent_close_save_uses_notes_page_and_preserves_unrelated_device_fields():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE devices(tracking_no TEXT PRIMARY KEY,internal_notes TEXT,accessories TEXT,repair_details TEXT,status TEXT)")
    original = ("CURRENT", "Original private note", "Original accessories", "Original public note", "Waiting")
    other = ("OTHER", "Other private note", "Other accessories", "Other public note", "In progress")
    cursor.executemany("INSERT INTO devices VALUES (?,?,?,?,?)", (original, other))
    conn.commit()
    panel = SimpleNamespace(
        db=SimpleNamespace(conn=conn, cursor=cursor),
        tracking_no="CURRENT",
        read_only=False,
        device_dict={"internal_notes": original[1]},
        wizard_page1=SimpleNamespace(get_data=lambda: {"accessories": "Actual selected charger"}),
        wizard_page2=SimpleNamespace(get_data=lambda: {"internal_notes": "Actual edited private note"}),
    )
    try:
        _TpOperations._perform_silent_save(panel)
        assert cursor.execute("SELECT * FROM devices WHERE tracking_no='CURRENT'").fetchone() == ("CURRENT", "Actual edited private note", "Actual selected charger", "Original public note", "Waiting")
        assert cursor.execute("SELECT * FROM devices WHERE tracking_no='OTHER'").fetchone() == other
        panel.read_only = True
        changes = conn.total_changes
        panel.wizard_page1.get_data = lambda: (_ for _ in ()).throw(AssertionError("Read-only close must not collect mutating fields"))
        _TpOperations._perform_silent_save(panel)
        assert conn.total_changes == changes
    finally:
        conn.close()


def test_silent_close_without_notes_page_keeps_original_private_note():
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE devices(tracking_no TEXT PRIMARY KEY,internal_notes TEXT,accessories TEXT)")
    cursor.execute("INSERT INTO devices VALUES ('CURRENT','Actual original note','Original charger')")
    conn.commit()
    panel = SimpleNamespace(db=SimpleNamespace(conn=conn, cursor=cursor), tracking_no="CURRENT", read_only=False, device_dict={"internal_notes": "Actual original note"}, wizard_page1=SimpleNamespace(get_data=lambda: {"accessories": "Selected charger"}))
    try:
        _TpOperations._perform_silent_save(panel)
        assert cursor.execute("SELECT internal_notes,accessories FROM devices").fetchone() == ("Actual original note", "Selected charger")
    finally:
        conn.close()
