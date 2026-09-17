# -*- coding: utf-8 -*-

"""
Modern Authentication Manager
Handles login, registration, and session management
"""

import secrets
import os
from datetime import datetime
from src.utils.logger import logger
from src.utils.password_security import (
    hash_password,
    hash_session_token,
    validate_new_password,
    verify_password,
)
from src.utils.role_utils import is_admin_role, normalize_role


_BUILTIN_MASTER_PASSWORD_HASH = (
    "$2b$12$5bKPvlp9L6ZrLc84RMM.Su6Mq8y7FLSAaQE27/IRYUF85c3xsLIH2"
)


class AuthManager:
    def __init__(self, db):
        self.db = db
        self.current_user = None
        self.remember_token = None
        
    def hash_password(self, password):
        """Hash a password using the current adaptive algorithm."""
        return hash_password(password)
    
    def generate_token(self):
        """Generate secure remember token"""
        return secrets.token_hex(32)
    
    def register_user(self, username, password, email=None, role='user'):
        """Register new user"""
        try:
            password_error = validate_new_password(password)
            if password_error:
                return False, password_error
            role = normalize_role(role)
            # Check if username exists
            self.db.cursor.execute("SELECT id FROM users WHERE username=?", (username,))
            if self.db.cursor.fetchone():
                return False, "Kullanıcı adı zaten kullanılıyor"
            
            # Check if email exists
            if email:
                email = email.strip()
                if email:
                    self.db.cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                    if self.db.cursor.fetchone():
                        return False, "Bu e-posta adresi zaten başka bir kullanıcı tarafından kullanılıyor"
            
            # Hash password
            password_hash = self.hash_password(password)
            
            # Insert user
            self.db.cursor.execute("""
                INSERT INTO users (username, password, email, role, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
            """, (username, password_hash, email, role))
            
            self.db.conn.commit()
            logger.info(f"New user registered: {username}")
            return True, "Kayıt başarılı"
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return False, f"Kayıt hatası: {str(e)}"
    
    def login(self, username, password, remember=False):
        """Authenticate user"""
        try:
            active_expr = "1"
            name_expr = "username"
            try:
                cols = set(self.db._get_table_columns("users")) if hasattr(self.db, "_get_table_columns") else set()
                if "active" in cols:
                    active_expr = "COALESCE(active, 1)"
                elif "is_active" in cols:
                    active_expr = "COALESCE(is_active, 1)"
                if "full_name" in cols and "name" in cols:
                    name_expr = "COALESCE(NULLIF(full_name, ''), NULLIF(name, ''), username)"
                elif "full_name" in cols:
                    name_expr = "COALESCE(NULLIF(full_name, ''), username)"
                elif "name" in cols:
                    name_expr = "COALESCE(NULLIF(name, ''), username)"
            except Exception:
                pass

            self.db.cursor.execute("""
                SELECT
                    id, username, password, role, auto_login,
                    COALESCE(must_change_password, 0) AS must_change_password,
                    {name_expr} AS display_name
                FROM users 
                WHERE username=? AND {active_expr}=1
            """.format(name_expr=name_expr, active_expr=active_expr), (username,))
            
            user = self.db.cursor.fetchone()
            if user:
                valid, upgraded = verify_password(password, user["password"])
                if not valid:
                    user = None
                elif upgraded:
                    self.db.cursor.execute(
                        """
                        UPDATE users
                        SET password=?, password_updated_at=datetime('now')
                        WHERE id=?
                        """,
                        (upgraded, user["id"]),
                    )
            
            if not user:
                return False, "Kullanıcı adı veya şifre hatalı"
            
            # Update last login
            self.db.cursor.execute("""
                UPDATE users 
                SET last_login = datetime('now')
                WHERE id = ?
            """, (user['id'],))
            
            # Generate remember token and enable auto_login if requested
            if remember:
                token = self.generate_token()
                stored_token = hash_session_token(token)
                self.db.cursor.execute("""
                    UPDATE users 
                    SET remember_token = ?, auto_login = 1
                    WHERE id = ?
                """, (stored_token, user['id']))
                self.remember_token = token
            else:
                # If login succeeded but remember is False, we should probably disable auto_login
                # to ensure next manual login doesn't accidentally trigger auto next time
                self.db.cursor.execute("UPDATE users SET auto_login = 0 WHERE id = ?", (user['id'],))
            
            self.db.conn.commit()
            
            self.current_user = {
                'id': user['id'],
                'username': user['username'],
                'role': normalize_role(user['role']),
                'name': user['display_name'] or user['username'],
                'must_change_password': bool(user['must_change_password']),
            }
            
            logger.info(f"User logged in: {username}")
            return True, "Giriş başarılı"
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, f"Giriş hatası: {str(e)}"
    
    def auto_login(self, token):
        """Login using remember token"""
        try:
            active_expr = "1"
            name_expr = "username"
            try:
                cols = set(self.db._get_table_columns("users")) if hasattr(self.db, "_get_table_columns") else set()
                if "active" in cols:
                    active_expr = "COALESCE(active, 1)"
                elif "is_active" in cols:
                    active_expr = "COALESCE(is_active, 1)"
                if "full_name" in cols and "name" in cols:
                    name_expr = "COALESCE(NULLIF(full_name, ''), NULLIF(name, ''), username)"
                elif "full_name" in cols:
                    name_expr = "COALESCE(NULLIF(full_name, ''), username)"
                elif "name" in cols:
                    name_expr = "COALESCE(NULLIF(name, ''), username)"
            except Exception:
                pass

            token_hash = hash_session_token(token)
            self.db.cursor.execute("""
                SELECT id, username, role, auto_login, remember_token,
                       COALESCE(must_change_password, 0) AS must_change_password,
                       {name_expr} AS display_name
                FROM users
                WHERE remember_token IN (?, ?) AND auto_login=1
                  AND {active_expr}=1
            """.format(name_expr=name_expr, active_expr=active_expr), (token_hash, token))
            
            user = self.db.cursor.fetchone()
            
            if not user:
                return False

            if bool(user["must_change_password"]):
                logger.warning(
                    "Auto-login denied until the user changes the temporary password"
                )
                return False

            if user["remember_token"] == token:
                self.db.cursor.execute(
                    "UPDATE users SET remember_token=? WHERE id=?",
                    (token_hash, user["id"]),
                )
            
            self.current_user = {
                'id': user['id'],
                'username': user['username'],
                'role': normalize_role(user['role']),
                'name': user['display_name'] or user['username'],
                'must_change_password': False,
            }
            
            # Update last login
            self.db.cursor.execute("""
                UPDATE users 
                SET last_login = datetime('now')
                WHERE id = ?
            """, (user['id'],))
            self.db.conn.commit()
            
            logger.info(f"Auto-login successful: {user['username']}")
            return True
            
        except Exception as e:
            logger.error(f"Auto-login error: {e}")
            return False
    
    def logout(self):
        """Logout current user"""
        if self.current_user:
            logger.info(f"User logged out: {self.current_user['username']}")
        self.current_user = None
        self.remember_token = None
    
    def set_auto_login(self, user_id, enabled, password):
        """Enable/disable auto-login (requires password confirmation)"""
        try:
            # Verify password
            self.db.cursor.execute("""
                SELECT password FROM users WHERE id=?
            """, (user_id,))
            
            user = self.db.cursor.fetchone()
            if not user:
                return False, "Kullanıcı bulunamadı"
            
            valid, upgraded = verify_password(password, user["password"])
            if not valid:
                return False, "Şifre hatalı"
            
            if upgraded:
                self.db.cursor.execute(
                    "UPDATE users SET password=?, password_updated_at=datetime('now') "
                    "WHERE id=?",
                    (upgraded, user_id),
                )

            # Update auto_login setting
            self.db.cursor.execute("""
                UPDATE users 
                SET auto_login = ?
                WHERE id = ?
            """, (1 if enabled else 0, user_id))
            
            self.db.conn.commit()
            
            status = "açıldı" if enabled else "kapatıldı"
            logger.info(f"Auto-login {status} for user ID: {user_id}")
            return True, f"Otomatik giriş {status}"
            
        except Exception as e:
            logger.error(f"Auto-login setting error: {e}")
            return False, f"Ayar hatası: {str(e)}"
    
    def get_saved_token(self):
        """Get saved remember token from config file"""
        try:
            from src.utils.path_helper import PathHelper
            import os
            
            token_file = os.path.join(PathHelper.get_app_data_dir(), '.auth_token')
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    return f.read().strip()
        except Exception as e:
            logger.warning(f"Token read error: {e}")
        return None
    
    def save_token(self, token):
        """Save remember token to config file"""
        try:
            from src.utils.path_helper import PathHelper
            import os
            
            token_file = os.path.join(PathHelper.get_app_data_dir(), '.auth_token')
            with open(token_file, 'w') as f:
                f.write(token)
        except Exception as e:
            logger.error(f"Token save error: {e}")
    
    def clear_token(self):
        """Clear saved token"""
        try:
            from src.utils.path_helper import PathHelper
            import os
            
            token_file = os.path.join(PathHelper.get_app_data_dir(), '.auth_token')
            if os.path.exists(token_file):
                os.remove(token_file)
        except Exception as e:
            logger.error(f"Token clear error: {e}")

    @staticmethod
    def verify_master_key(password):
        """Validate an explicitly provisioned emergency master key."""
        try:
            if not password:
                return False
            configured_hash = os.environ.get(
                "AYECPRO_MASTER_PASSWORD_HASH",
                _BUILTIN_MASTER_PASSWORD_HASH,
            ).strip()
            if not configured_hash:
                return False
            valid, _upgraded = verify_password(password, configured_hash)
            return valid
        except Exception as e:
            logger.warning(f"Master key verify error: {e}")
            return False

    def _get_current_user_row(self):
        """Fetch current user row from DB safely."""
        if not self.current_user:
            return None
        try:
            self.db.cursor.execute(
                "SELECT id, username, role, password, interface_edit_access FROM users WHERE id=?",
                (self.current_user.get("id"),),
            )
            return self.db.cursor.fetchone()
        except Exception as e:
            logger.warning(f"Current user query error (extended): {e}")
            try:
                self.db.cursor.execute(
                    "SELECT id, username, role, password FROM users WHERE id=?",
                    (self.current_user.get("id"),),
                )
                return self.db.cursor.fetchone()
            except Exception as fallback_e:
                logger.warning(f"Current user query error (fallback): {fallback_e}")
                return None

    def has_interface_edit_permission(self):
        """Check whether current user can open interface editor drawer."""
        row = self._get_current_user_row()
        if not row:
            # Backward-compatible fallback: if session user is not injected,
            # do not hard-block the drawer entry point.
            return True
        try:
            role = str(row["role"] or "").strip().lower()
        except Exception as e:
            logger.warning(f"Role parse error: {e}")
            role = ""

        if is_admin_role(role):
            return True

        try:
            return bool(row["interface_edit_access"])
        except Exception as e:
            logger.warning(f"Interface edit permission parse error: {e}")
            return False

    def verify_action_password(self, password):
        """Verify current user's password for privileged UI actions."""
        if not password:
            return False
        row = self._get_current_user_row()
        if not row:
            return False
        try:
            stored_hash = row["password"]
        except Exception as e:
            logger.warning(f"Password field parse error: {e}")
            return False
        if not stored_hash:
            return False
        valid, upgraded = verify_password(password, stored_hash)
        if valid and upgraded:
            try:
                self.db.cursor.execute(
                    "UPDATE users SET password=? WHERE id=?",
                    (upgraded, row["id"]),
                )
                self.db.conn.commit()
            except Exception as e:
                logger.warning(f"Action password hash upgrade failed: {e}")
        return bool(valid)
