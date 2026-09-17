"""
Create admin user with correct password hash
"""
import sqlite3
import bcrypt

# Connect to database
conn = sqlite3.connect('ayecpro.db')
cursor = conn.cursor()

# Hash the password
password = 'admin123'
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Delete existing admin user
cursor.execute("DELETE FROM users WHERE username = 'admin'")

# Insert new admin user
cursor.execute("""
    INSERT INTO users (username, password, role, is_active, created_at)
    VALUES (?, ?, ?, ?, datetime('now'))
""", ('admin', hashed, 'Admin', 1))

conn.commit()
conn.close()

print("OK - Admin user created successfully!")
print("Username: admin")
print("Password: admin123")
print(f"Password Hash: {hashed}")
