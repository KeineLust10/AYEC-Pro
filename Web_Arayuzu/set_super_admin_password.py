"""
Super Admin (ayecpro@gmail.com) sifresini He152430 olarak ayarla.
Sunucuda calistir: python set_super_admin_password.py
"""
import sys
import sqlite3
import hashlib
from pathlib import Path
import datetime

# Sunucuda calisma dizini
BASE = Path(__file__).parent

DB_PATH = BASE / "data" / "ayecpro.db"
if not DB_PATH.exists():
    DB_PATH = BASE / "ayecpro.db"

TENANT_ROOT_CANDIDATES = [
    Path("/Web_Arayuzu/Kullanicilar"),
    BASE / "Kullanicilar",
    BASE.parent / "Kullanicilar",
]

VENDOR_EMAIL = "ayecpro@gmail.com"
NEW_PASSWORD = "He152430"


def hash_pw(password: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        import hmac
        return "sha256:" + hmac.new(b"ayec", password.encode(), hashlib.sha256).hexdigest()


hashed = hash_pw(NEW_PASSWORD)
print(f"Sifre hash alindi: {hashed[:20]}...")

updated_count = 0

# 1. Registry DB'yi bul
if not DB_PATH.exists():
    print(f"HATA: Registry DB bulunamadi: {DB_PATH}")
    sys.exit(1)

print(f"Registry DB: {DB_PATH}")
reg_conn = sqlite3.connect(str(DB_PATH))
reg_conn.row_factory = sqlite3.Row

# Tenant root'u bul
tenant_root = None
for c in TENANT_ROOT_CANDIDATES:
    if c.exists():
        tenant_root = c
        break

if not tenant_root:
    print("UYARI: Kullanicilar/ klasoru bulunamadi.")
else:
    print(f"Tenant root: {tenant_root}")
    tenant_files = list(tenant_root.glob("*.db"))
    print(f"Firma DB sayisi: {len(tenant_files)}")

    for tenant_db in tenant_files:
        try:
            tconn = sqlite3.connect(str(tenant_db))
            tconn.row_factory = sqlite3.Row
            t_tables = {r[0] for r in tconn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "users" not in t_tables:
                tconn.close()
                continue
            user = tconn.execute(
                "SELECT * FROM users WHERE lower(trim(COALESCE(email,'')))=? OR lower(trim(COALESCE(username,'')))=?",
                (VENDOR_EMAIL, "ayecpro")
            ).fetchone()
            if user:
                tconn.execute("UPDATE users SET password=? WHERE id=?", (hashed, user["id"]))
                tconn.commit()
                print(f"  OK: Sifre guncellendi -> {tenant_db.name} (user id={user['id']})")
                updated_count += 1

                # control_admins kaydini garantile
                tenant_row = reg_conn.execute(
                    "SELECT id FROM tenants WHERE db_filename=?", (tenant_db.name,)
                ).fetchone()
                if tenant_row:
                    reg_conn.execute(
                        "INSERT OR IGNORE INTO control_admins(tenant_id, user_id, created_at) VALUES (?,?,?)",
                        (tenant_row["id"], user["id"], datetime.datetime.utcnow().isoformat())
                    )
                    reg_conn.commit()
                    print(f"  OK: control_admins kaydi eklendi (tenant={tenant_row['id']}, user={user['id']})")
            tconn.close()
        except Exception as ex:
            print(f"  {tenant_db.name}: HATA: {ex}")

reg_conn.close()

if updated_count == 0:
    print("\nUYARI: Hicbir kullanici guncellenemedi.")
    print("Cozum: Sunucuya giris yapip once bir firmaya 'ayecpro@gmail.com' kullanicisi ekleyin,")
    print("       sonra bu scripti tekrar calistirin.")
else:
    print(f"\n=== BASARILI === {updated_count} firma DB'de sifre guncellendi.")
    print(f"Giris bilgileri: {VENDOR_EMAIL} / {NEW_PASSWORD}")
    print("Sunucuyu yeniden baslatmaniz gerekmiyor.")
