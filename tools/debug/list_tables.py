import sqlite3

conn = sqlite3.connect('ayecpro.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [r[0] for r in cursor.fetchall()]

print("All tables:")
for t in sorted(all_tables):
    print(f"  - {t}")

print("\nCurrency-related tables:")
currency_tables = [t for t in all_tables if 'curr' in t.lower()]
print(currency_tables if currency_tables else "  None found")

conn.close()
