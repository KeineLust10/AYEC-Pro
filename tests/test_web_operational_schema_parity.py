import sqlite3

from Web_Arayuzu import Main as web_main
from src.database import Database


def _table_names(connection):
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }


def test_web_operational_schema_matches_fresh_desktop_database():
    web_connection = sqlite3.connect(":memory:")
    web_main.ensure_operational_schema(web_connection)
    web_main.ensure_web_schema(web_connection)
    desktop = Database(":memory:", init_mode="full")

    try:
        desktop.create_device_brands_table()
        desktop.create_device_model_catalog_table()
        desktop.ensure_stock_location_schema()
        desktop.ensure_appointment_montage_schema()
        desktop_connection = desktop.conn
        web_tables = _table_names(web_connection)
        desktop_tables = _table_names(desktop_connection)
        common_tables = web_tables & desktop_tables

        assert desktop_tables - web_tables == {"_migrations"}
        assert web_tables - desktop_tables == {
            "error_telemetry",
            "global_notifications",
            "service_tracking_access",
            "staged_updates",
            "sync_conflicts",
            "sync_events",
            "web_sessions",
        }

        web_only_columns = set()
        desktop_only_columns = set()
        metadata_differences = set()
        for table in common_tables:
            web_columns = {
                row[1]: row
                for row in web_connection.execute(f'PRAGMA table_info("{table}")')
            }
            desktop_columns = {
                row[1]: row
                for row in desktop_connection.execute(f'PRAGMA table_info("{table}")')
            }
            for column in web_columns.keys() - desktop_columns.keys():
                web_only_columns.add((table, column))
            for column in desktop_columns.keys() - web_columns.keys():
                desktop_only_columns.add((table, column))
            for column in web_columns.keys() & desktop_columns.keys():
                web_info = web_columns[column]
                desktop_info = desktop_columns[column]
                if (web_info[2], web_info[3], web_info[4], web_info[5]) != (
                    desktop_info[2],
                    desktop_info[3],
                    desktop_info[4],
                    desktop_info[5],
                ):
                    metadata_differences.add((table, column))

        assert web_only_columns == {
            ("customer_notes", "note_type"),
            ("users", "phone"),
            ("users", "temporary_password_expires_at"),
        }
        assert not desktop_only_columns
        assert not metadata_differences
    finally:
        desktop.close()
        web_connection.close()
