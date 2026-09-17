import sqlite3

conn = sqlite3.connect('ayecpro.db')
cursor = conn.cursor()

# Update admin role to uppercase
cursor.execute("UPDATE users SET role = 'ADMIN' WHERE username = 'admin'")
conn.commit()

print("OK - Admin role updated to ADMIN")
conn.close()
