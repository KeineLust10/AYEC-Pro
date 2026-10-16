import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from src.ui.pages.reminders_page import RemindersPage


def test_reminder_rows_map_legacy_column_names_instead_of_schema_positions():
    columns = [
        "id", "tracking_no", "message", "due_date", "is_read", "created_at",
        "title", "personnel", "date", "description", "status",
    ]
    row = (1, "SRV-1", "Legacy reminder", "2026-10-21", 1, "2026-10-16 10:00:00", None, None, None, None, None)

    assert RemindersPage._reminder_table_values(columns, row) == [
        "1", "Legacy reminder", "", "2026-10-21", "Legacy reminder", "Okundu",
    ]


def test_reminder_rows_map_modern_columns_by_name():
    columns = [
        "id", "tracking_no", "message", "due_date", "is_read", "created_at",
        "title", "personnel", "date", "description", "status",
    ]
    row = (2, None, None, None, 0, "2026-10-16 10:00:00", "QA Reminder", "QA Tech", "2026-10-20", "QA notes", "Aktif")

    assert RemindersPage._reminder_table_values(columns, row) == [
        "2", "QA Reminder", "QA Tech", "2026-10-20", "QA notes", "Aktif",
    ]
