
import sqlite3
import os

DB_PATH = 'ayecpro.db'

TABLES_TO_CLEAR = [
    'customers',
    'devices',
    'parts',
    'stock',
    'stock_movements',
    'used_parts',
    'service_logs',
    'appointments',
    'reminders',
    'device_tests',
    'accounting',
    'personnel',
    'tickets',
    'kb_articles',
    'audit_logs',
    'sms_log',
    'contracts',
    'announcements',
    'active_devices',
    'jarvis_notifications',
    'external_warranty_tracking',
    'customer_notes',
    'customer_services'
]

def clean_database():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Disable foreign keys to allow deletion order independence
        cursor.execute("PRAGMA foreign_keys = OFF")
        
        print("Starting cleanup...")
        
        for table in TABLES_TO_CLEAR:
            try:
                # Check if table exists first
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
                if cursor.fetchone():
                    cursor.execute(f"DELETE FROM {table}")
                    # Reset auto-increment
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                    print(f"[OK] Cleared: {table}")
                else:
                    print(f"- Skipped (Not found): {table}")
            except Exception as e:
                print(f"[X] Error clearing {table}: {e}")

        # Commit changes
        conn.commit()
        
        # Verify services
        cursor.execute("SELECT COUNT(*) FROM services")
        svc_count = cursor.fetchone()[0]
        print(f"\nCleanup completed successfully.")
        print(f"Services table count: {svc_count} (Preserved)")
        print("Kept tables: services, Settings, Users, etc.")
        
    except Exception as e:
        print(f"Critical Error: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    clean_database()
