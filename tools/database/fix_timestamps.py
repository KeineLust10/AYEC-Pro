import sqlite3
from datetime import datetime

conn = sqlite3.connect(r'C:\Users\Admin\AppData\Local\AYECPro\ayecpro.db')
cursor = conn.cursor()

print("=== FIXING INVALID TIMESTAMPS ===\n")

# Find records with invalid timestamps
cursor.execute("SELECT id, created_at FROM currency_transactions WHERE created_at LIKE '%HH:mm:ss%'")
invalid_records = cursor.fetchall()

print(f"Found {len(invalid_records)} records with invalid timestamps")

# Fix them
for record_id, old_date in invalid_records:
    # Extract date part and add current time
    date_part = old_date.split(' ')[0]  # Get "2026-01-20"
    new_timestamp = f"{date_part} {datetime.now().strftime('%H:%M:%S')}"
    
    cursor.execute("UPDATE currency_transactions SET created_at = ? WHERE id = ?", (new_timestamp, record_id))
    print(f"Fixed ID {record_id}: {old_date} -> {new_timestamp}")

conn.commit()
print(f"\n[SUCCESS] Fixed {len(invalid_records)} records")

conn.close()
