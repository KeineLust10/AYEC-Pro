"""
AYEC Pro Sunucu Tam Onarim Scripti v2
Calistirin: python onarim.py

Yapilacaklar:
1. Registry DB'de tenants tablosunu olustur (yoksa)
2. Kullanıcılar/ altindaki tum DB'leri tenants tablosuna kaydet
3. Her firmanin kullanıcıları listele
4. Mevcut ayecpro@gmail.com hesabini raporla
5. Mevcut platform yonetici kaydini dogrula
"""
import sys
import sqlite3
import datetime
import re
from pathlib import Path

# -------------------------
VENDOR_EMAIL    = "ayecpro@gmail.com"
VENDOR_USERNAME = "ayecpro"

REGISTRY_DB  = Path("data/ayecpro.db")
TENANT_ROOT  = Path("Kullanıcılar")
# -------------------------


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:32] or "firma"


def new_tenant_id(name: str, existing: set) -> str:
    base = slugify(name)
    tid = base
    i = 2
    while tid in existing:
        tid = f"{base}-{i}"
        i += 1
    return tid


# -------------------------
print("=" * 60)
print("AYEC Pro Sunucu Tam Onarim v2")
print("=" * 60)

if not REGISTRY_DB.exists():
    print(f"HATA: Registry DB bulunamadi: {REGISTRY_DB.resolve()}")
    sys.exit(1)

if not TENANT_ROOT.exists():
    print(f"HATA: Kullanıcılar/ klasoru bulunamadi: {TENANT_ROOT.resolve()}")
    sys.exit(1)

tenant_dbs = sorted(TENANT_ROOT.glob("*.db"))
print(f"Registry DB : {REGISTRY_DB.resolve()}")
print(f"Tenant root : {TENANT_ROOT.resolve()}")
print(f"Firma DB    : {len(tenant_dbs)} adet")

# -------------------------
# Registry DB'ye baglan ve schema olustur
# -------------------------
reg = sqlite3.connect(str(REGISTRY_DB))
reg.row_factory = sqlite3.Row

reg.execute("""
    CREATE TABLE IF NOT EXISTS tenants (
        id TEXT PRIMARY KEY,
        company_name TEXT NOT NULL,
        db_filename TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL,
        active INTEGER DEFAULT 1,
        sector TEXT DEFAULT 'otomotiv',
        license_type TEXT,
        license_start TEXT,
        license_end TEXT,
        contact_name TEXT,
        phone TEXT,
        email TEXT
    )
""")
reg.execute("""
    CREATE TABLE IF NOT EXISTS control_admins (
        tenant_id TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY (tenant_id, user_id)
    )
""")
reg.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        tenant_id TEXT,
        created_at TEXT,
        last_seen TEXT,
        user_agent TEXT,
        ip TEXT,
        expires_at TEXT
    )
""")
reg.commit()
print("\n[OK] Registry schema hazir.")

# -------------------------
# Mevcut tenant kayitlari
# -------------------------
existing_ids = {r["id"] for r in reg.execute("SELECT id FROM tenants")}
existing_files = {r["db_filename"].lower() for r in reg.execute("SELECT db_filename FROM tenants")}

# -------------------------
# Her firma DB'yi tara
# -------------------------
print("\n--- Firma DB Taramasi ---")

vendor_found = None   # (db_file, user_id, tenant_id)

for db_file in tenant_dbs:
    print(f"\n[{db_file.name}]")

    # Registry'ye kaydet (yoksa)
    if db_file.name.lower() not in existing_files:
        company_name = db_file.stem
        # DB icerisinden sirket adini al
        try:
            tc = sqlite3.connect(str(db_file))
            tc.row_factory = sqlite3.Row
            info = tc.execute("SELECT company_name FROM company_info LIMIT 1").fetchone()
            if info and info["company_name"]:
                company_name = info["company_name"]
            tc.close()
        except Exception:
            pass
        tid = new_tenant_id(company_name, existing_ids)
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
        reg.execute(
            "INSERT OR IGNORE INTO tenants(id, company_name, db_filename, created_at, active) VALUES (?,?,?,?,1)",
            (tid, company_name, db_file.name, now)
        )
        reg.commit()
        existing_ids.add(tid)
        existing_files.add(db_file.name.lower())
        print(f"  Tenants'a eklendi: id={tid}, name={company_name}")

    tenant_row = reg.execute("SELECT id FROM tenants WHERE lower(db_filename)=?", (db_file.name.lower(),)).fetchone()
    tid = tenant_row["id"] if tenant_row else None

    # Kullancılar listele
    try:
        conn = sqlite3.connect(str(db_file))
        conn.row_factory = sqlite3.Row
        t_tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "users" not in t_tables:
            print("  users tablosu yok, atlandi.")
            conn.close()
            continue

        user_list = list(conn.execute("SELECT id, username, email, password, role, active FROM users"))
        print(f"  Kullanici sayisi: {len(user_list)}")
        for u in user_list:
            em = str(u["email"] or "-")
            un = str(u["username"] or "-")
            pw = str(u["password"] or "")
            if pw.startswith("pbkdf2_sha256$"):
                fmt = "pbkdf2 (dogru)"
            elif len(pw) == 64:
                fmt = "sha256 (eski)"
            elif pw:
                fmt = f"belirsiz ({len(pw)} chr)"
            else:
                fmt = "BOS"
            aktif = "aktif" if u["active"] else "pasif"
            print(f"    id={u['id']} | {un} | {em} | {u['role']} | {aktif} | {fmt}")

            if em.lower() == VENDOR_EMAIL or un.lower() in (VENDOR_USERNAME, VENDOR_EMAIL):
                if vendor_found is None:
                    vendor_found = (db_file, u["id"], tid)
                print(f"    --> VENDOR HESABI BULUNDU")

        conn.close()

    except Exception as ex:
        print(f"  HATA: {ex}")

# -------------------------
# Mevcut platform yoneticisi denetimi
# -------------------------
now_str = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()

if vendor_found:
    db_file, uid, tid = vendor_found
    print(f"\n[BILGI] '{VENDOR_EMAIL}' mevcut. Kullanici ve sifre korunuyor.")
    print(f"  id={uid}, tenant={tid}")
else:
    uid = tid = None
    print(f"\n[BILGI] '{VENDOR_EMAIL}' bulunamadi. Kullanici olusturulmadi.")

# -------------------------
# control_admins kaydini garantile
# -------------------------
if tid and uid:
    reg.execute(
        "INSERT OR IGNORE INTO control_admins(tenant_id, user_id, created_at) VALUES (?,?,?)",
        (tid, uid, now_str)
    )
    reg.commit()
    check = reg.execute(
        "SELECT 1 FROM control_admins WHERE tenant_id=? AND user_id=?", (tid, uid)
    ).fetchone()
    if check:
        print(f"\n[OK] control_admins kaydi: tenant={tid}, user_id={uid}")
    else:
        print("\n[HATA] control_admins kaydi eklenemedi!")
else:
    print("\n[UYARI] tid veya uid bos, control_admins atlandi.")

reg.close()

# -------------------------
print("\n" + "=" * 60)
print("ISLEM TAMAMLANDI")
print("=" * 60)
print("Mevcut kullanicilarin sifreleri degistirilmedi.")
print(f"  Tenant  : {tid}")
print(f"  User ID : {uid}")
print("")
print("Web panelden giris yaparken firma secin: ilk firma listesini kullanin.")
print("AYECAdmin.exe ile giris yapabilirsiniz (firma secimi gerekmez).")
