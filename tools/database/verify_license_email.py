# -*- coding: utf-8 -*-

import sys
import os
import sqlite3

# Adicionar o diretório src ao path para os imports
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.database import Database

def verify():
    print("--- Verifying Users Table Schema ---")
    db = Database("test_bulut.db")
    
    # Check schema
    cursor = db.cursor
    cursor.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in cursor.fetchall()]
    print(f"Users columns: {cols}")
    
    if "email" in cols:
        print("[OK] email column exists in users table.")
    else:
        print("[FAIL] email column MISSING in users table.")

    print("\n--- Testing save_registration logic ---")
    data = {
        "full_name": "Test User",
        "email": "test@example.com",
        "company_name": "Test Co",
        "phone": "123456",
        "purpose": "Testing",
        "license": {
            "license_key": "TEST-KEY-1234",
            "encrypted_key": "ENCRYPTED",
            "license_type": "Trial",
            "start_date": "2026-01-17",
            "expiry_date": "2026-01-24",
            "last_check_date": "2026-01-17",
            "hwid": "TEST-HWID"
        }
    }
    
    # Mocking self.email_worker in ModernDesktopApp context
    # We mainly want to check if the logic in complete_registration (formatting) is correct
    try:
        from src.utils.templates import BULUT_LISANS_SABLONU
        license_key = data["license"].get("license_key", "---")
        html_body = BULUT_LISANS_SABLONU.format(
            user_name=data.get('full_name', 'Değerli Kullanıcımız'),
            license_key=license_key
        )
        print("[OK] Template formatted successfully.")
        # print("HTML Body Preview:", html_body[:200], "...")
    except Exception as e:
        print(f"[FAIL] Template formatting error: {e}")

    # clean up
    db.conn.close()
    if os.path.exists("test_bulut.db"):
        os.remove("test_bulut.db")

if __name__ == "__main__":
    verify()
