import sqlite3
import os

def wipe_data():
    db_path = "ayecpro.db"
    if not os.path.exists(db_path):
        print(f"Error: {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tables to completely truncate
    tables_to_clear = [
        "devices",
        "customers",
        "accounting",
        "appointments",
        "stock_movements",
        "used_parts",
        "logs",
        "audit_log",
        "sms_log",
        "customer_notes",
        "jarvis_notifications"
    ]

    try:
        print("Starting data truncation...")

        # 1. Clear transaction tables
        for table in tables_to_clear:
            try:
                cursor.execute(f"DELETE FROM {table}")
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                print(f"Table {table} cleared.")
            except sqlite3.OperationalError as e:
                print(f"Warning: Table {table} does not exist or error: {e}")

        # 2. Reset stock counts in parts but keep the definitions
        try:
            cursor.execute("UPDATE parts SET stock = 0")
            print("Stock levels reset to 0 in 'parts' table.")
        except sqlite3.OperationalError as e:
            print(f"Warning: Could not reset stock in parts: {e}")

        # 3. Clean up orphans or related data if any (optional but safer)
        # We are keeping personnel, settings, quick_notes, license_info as requested.

        conn.commit()
        print("\nSUCCESS: All user-entered data has been removed.")
        print("PRESERVED: Service definitions (parts), Personnel, Settings, and Activation.")
        
    except Exception as e:
        print(f"CRITICAL ERROR during truncation: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    wipe_data()
