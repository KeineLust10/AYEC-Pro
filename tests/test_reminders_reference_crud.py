from src.database import Database


def test_add_reminder_uses_columns_available_in_current_schema(tmp_path):
    db = Database(str(tmp_path / "reminders_reference.db"))
    try:
        assert db.add_reminder("Call customer", None, "2026-10-20", "Follow up")
        row = db.cursor.execute(
            "SELECT title, personnel, date, description, status, is_read "
            "FROM reminders ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert tuple(row) == ("Call customer", "", "2026-10-20", "Follow up", "Aktif", 0)
    finally:
        db.close()
