# -*- coding: utf-8 -*-

"""
Security Mixin
Güvenlik ve yetkilendirme ile ilgili database metodları
"""

from datetime import datetime
from src.utils.logger import logger
from src.utils.password_security import hash_password, verify_password
from src.utils.role_utils import is_admin_role


class SecurityMixin:
    def create_users_table(self):
        """Kullanıcılar tablosunu oluştur ve varsayılan admin ekle"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                email TEXT,
                role TEXT,
                created_at TEXT,
                commission_rate REAL DEFAULT 0,
                last_login TEXT,
                remember_token TEXT,
                auto_login INTEGER DEFAULT 0,
                must_change_password INTEGER DEFAULT 0,
                password_updated_at TEXT
            )
        """)
        self.conn.commit()
        
        # Varsayılan admin kontrolü
        columns = {
            row[1]
            for row in self.cursor.execute("PRAGMA table_info(users)").fetchall()
        }
        if "must_change_password" not in columns:
            self.cursor.execute(
                "ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0"
            )
        if "password_updated_at" not in columns:
            self.cursor.execute(
                "ALTER TABLE users ADD COLUMN password_updated_at TEXT"
            )
        self.conn.commit()

    def add_user(
        self,
        username,
        password,
        email="",
        role="Personel",
        must_change_password=False,
    ):
        """Yeni kullanıcı ekle (Veya mevcut olanı güncelle)"""
        try:
            hashed_pw = hash_password(password)
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                """
                INSERT INTO users (
                    username, password, email, role, created_at,
                    must_change_password, password_updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    password=excluded.password,
                    email=excluded.email,
                    role=excluded.role,
                    must_change_password=excluded.must_change_password,
                    password_updated_at=excluded.password_updated_at
                """,
                (
                    username,
                    hashed_pw,
                    email,
                    role,
                    created_at,
                    1 if must_change_password else 0,
                    created_at,
                ),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"User add error: {e}")
            return False
    
    def authenticate_user(self, username, password):
        """Kullanıcı doğrula"""
        self.cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        user = self.cursor.fetchone()
        if not user:
            return None
        valid, upgraded = verify_password(password, user["password"])
        if not valid:
            return None
        if upgraded:
            self.cursor.execute(
                """
                UPDATE users
                SET password=?, password_updated_at=datetime('now')
                WHERE id=?
                """,
                (upgraded, user["id"]),
            )
            self.conn.commit()
            self.cursor.execute("SELECT * FROM users WHERE id=?", (user["id"],))
            user = self.cursor.fetchone()
        return user
    
    def check_permission(self, role, action):
        """Rol bazlı yetki kontrolü"""
        # Admin her şeyi yapabilir
        if is_admin_role(role):
            return True
        
        # Diğer roller için kısıtlı yetkiler
        permissions = {
            "Teknisyen": {
                "view_dashboard",
                "view_stock",
                "add_service",
                "update_status",
            },
            "Muhasebe": {
                "view_dashboard",
                "view_accounting",
                "add_transaction",
                "export_excel",
            },
            "Sat\u0131\u015f": {
                "view_dashboard",
                "view_stock",
                "create_offer",
                "create_sale",
            },
            "Personel": {
                "view_dashboard",
            },
            "Stajyer": {
                "view_dashboard",
                "view_stock",
            },
        }
        from src.utils.role_utils import normalize_role

        return str(action or "") in permissions.get(normalize_role(role), set())
    
    def get_registration(self):
        """Kayıt bilgilerini getir"""
        self.cursor.execute("SELECT * FROM registration LIMIT 1")
        return self.cursor.fetchone()
    
    def save_registration(self, data):
        """Kayıt bilgilerini kaydet"""
        try:
            # Clear previous registration to support Re-Registration
            self.cursor.execute("DELETE FROM registration")
            self.cursor.execute("DELETE FROM license_info")
            
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check if registration_date column exists (schema compatibility)
            self.cursor.execute("PRAGMA table_info(registration)")
            columns = [row[1] for row in self.cursor.fetchall()]
            
            if "registration_date" in columns:
                # New schema with registration_date
                self.cursor.execute("""
                    INSERT INTO registration (full_name, email, company_name, phone, purpose, trial_start_date, registration_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (data['full_name'], data['email'], data['company_name'], data['phone'], data['purpose'], now, now))
            else:
                # Old schema without registration_date
                self.cursor.execute("""
                    INSERT INTO registration (full_name, email, company_name, phone, purpose, trial_start_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (data['full_name'], data['email'], data['company_name'], data['phone'], data['purpose'], now))
            
            # License bilgisi varsa kaydet
            if "license" in data:
                lic = data["license"]
                self.cursor.execute("""
                    INSERT INTO license_info (encrypted_key, license_type, start_date, expiry_date, last_check_date, hwid)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (lic['encrypted_key'], lic['license_type'], lic['start_date'], lic['expiry_date'], lic['last_check_date'], lic['hwid']))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Registration save error: {e}")
            return False
