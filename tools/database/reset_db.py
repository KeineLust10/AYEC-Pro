import os
import sqlite3
import sys

# Ensure UTF-8 output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def reset_database():
    db_path = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')), 'AYECPro', 'ayecpro.db')
    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tables to completely clear (TRUNCATE/DELETE)
    tables_to_clear = [
        'devices',
        'stock_movements',
        'used_parts',
        'service_logs',
        'appointments',
        'reminders',
        'device_tests',
        'accounting',
        'customers',
        'tickets',
        'kb_articles',
        'audit_logs',
        'sms_log',
        'bank_accounts',
        'contracts',
        'announcements',
        'active_devices',
        'jarvis_notifications',
        'external_warranty_tracking',
        'customer_notes',
        'quick_notes',
        'fast_notes',
        'services',
        'customer_services'
    ]
    
    print("Starting database reset...")
    
    for table in tables_to_clear:
        try:
            # Check if table exists
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                cursor.execute(f"DELETE FROM {table}")
                print(f"Cleared table: {table}")
            else:
                print(f"Table {table} does not exist, skipping.")
        except Exception as e:
            print(f"Error clearing table {table}: {e}")
            
    # Reset sequences for cleared tables
    try:
        keep_sequences = "('users', 'parts', 'settings', 'personnel')"
        cursor.execute(f"DELETE FROM sqlite_sequence WHERE name NOT IN {keep_sequences}")
        print(f"Reset auto-increment sequences (except {keep_sequences})")
    except Exception as e:
        print(f"Error resetting sequences: {e}")

    conn.commit()
    conn.close()
    print("Database reset completed successfully.")
    print("Kept: Stock (parts), Users, Personnel, Settings (IP Config).")

if __name__ == "__main__":
    reset_database()
