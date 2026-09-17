"""
ayecpro@gmail.com Super Admin sifresini He152430 olarak ayarla.
Sunucudaki veritabani uzerinde calisir.
"""
import sys
import sqlite3
import hashlib
import os
from pathlib import Path

# Sunucu veritabani yolunu bul
DB_CANDIDATES = [
    Path("Web_Arayuzu/data/ayecpro.db"),
    Path("Web_Arayuzu/ayecpro.db"),
    Path("ayecpro.db"),
    Path("data/ayecpro.db"),
]

db_path = None
for c in DB_CANDIDATES:
    if c.exists():
        db_path = c
        break

if not db_path:
    print("HATA: ayecpro.db bulunamadi!")
    sys.exit(1)

print(f"Veritabani: {db_path.resolve()}")

EMAIL = "ayecpro@gmail.com"
NEW_PASSWORD = "He152430"

def hash_password(password: str) -> str:
    """bcrypt yoksa sha256 fallback. Sunucu ile ayni algoritmayi kullanmali."""
    try:
        import bcrypt
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")
    except ImportError:
        # sha256 fallback
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

# Tenant tabanlarinda da ara
# Once registry'deki control_admins tablosuna bak
tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
print(f"Tablolar: {', '.join(sorted(tables))}")

updated = False

# --- users tablosunda ara ---
if "users" in tables:
    user = conn.execute("SELECT * FROM users WHERE email=? OR username=?", (EMAIL, EMAIL)).fetchone()
    if user:
        hashed = hash_password(NEW_PASSWORD)
        conn.execute("UPDATE users SET password=? WHERE id=?", (hashed, user["id"]))
        conn.commit()
        print(f"OK: '{EMAIL}' kullanicisinin sifresi guncellendi (users tablosu, id={user['id']})")
        print(f"    is_platform_admin = {user['is_platform_admin'] if 'is_platform_admin' in user.keys() else 'alan yok'}")
        updated = True
    else:
        print(f"BILGI: '{EMAIL}' users tablosunda bulunamadi.")

# --- control_admins tablosunda ara ---
if "control_admins" in tables:
    admin = conn.execute("SELECT * FROM control_admins WHERE email=?", (EMAIL,)).fetchone()
    if admin:
        hashed = hash_password(NEW_PASSWORD)
        conn.execute("UPDATE control_admins SET password=? WHERE id=?", (hashed, admin["id"]))
        conn.commit()
        print(f"OK: '{EMAIL}' control_admins tablosunda guncellendi (id={admin['id']})")
        updated = True
    else:
        print(f"BILGI: '{EMAIL}' control_admins tablosunda bulunamadi.")

if not updated:
    print("\nHicbir kayit guncellenemedi.")
    print("Tum users kayitlari:")
    if "users" in tables:
        for u in conn.execute("SELECT id, username, email, role FROM users"):
            print(f"  id={u['id']} username={u['username']} email={u['email']} role={u['role']}")
else:
    print(f"\nBasarili! '{EMAIL}' icin sifre 'He152430' olarak ayarlandi.")
    print("Sunucu paketi yeniden gonderilmeli.")

conn.close()
