import sys
sys.path.append('.')
from src.db.database_manager import DatabaseManager

db = DatabaseManager('ayec.db')
cursor = db.cursor

cursor.execute("SELECT * FROM accounting ORDER BY id DESC LIMIT 20")
rows = cursor.fetchall()
print("Accounting Table (Last 20 rows):")
for r in rows:
    print(dict(r) if hasattr(r, 'keys') else r)

cursor.execute("SELECT SUM(amount) FROM accounting WHERE type='Gider'")
print("Total Gider:", cursor.fetchone()[0])
