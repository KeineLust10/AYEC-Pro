import sqlite3
from pathlib import Path

from Web_Arayuzu.Main import _ensure_path_schema, ensure_operational_schema


def _fast_note_columns(conn):
    return {row[1] for row in conn.execute('PRAGMA table_info("fast_notes")')}


def test_fresh_web_schema_supports_desktop_fast_note_fields():
    conn = sqlite3.connect(":memory:")
    ensure_operational_schema(conn)

    assert {"display_category", "title"}.issubset(_fast_note_columns(conn))
    conn.execute(
        "INSERT INTO fast_notes "
        "(category, label, is_active, display_order, display_category, title) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("Ariza Notu", "Check scope", 1, 4, "Clinic", "Repair macro"),
    )
    row = conn.execute(
        "SELECT category, label, is_active, display_order, display_category, title "
        "FROM fast_notes"
    ).fetchone()
    assert row == ("Ariza Notu", "Check scope", 1, 4, "Clinic", "Repair macro")


def test_existing_web_fast_notes_gain_desktop_fields_without_losing_rows(tmp_path):
    db_path = tmp_path / "tenant.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE fast_notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, label TEXT, "
        "is_active INTEGER DEFAULT 1, display_order INTEGER DEFAULT 0)"
    )
    conn.execute(
        "INSERT INTO fast_notes (category, label, is_active, display_order) "
        "VALUES (?, ?, ?, ?)",
        ("Ariza Notu", "Existing note", 1, 2),
    )
    _ensure_path_schema(conn, Path(db_path))

    assert {"display_category", "title"}.issubset(_fast_note_columns(conn))
    assert conn.execute(
        "SELECT category, label, is_active, display_order FROM fast_notes"
    ).fetchone() == ("Ariza Notu", "Existing note", 1, 2)
