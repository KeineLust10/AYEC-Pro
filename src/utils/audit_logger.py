# -*- coding: utf-8 -*-

"""
Kullanıcı Aktivite Loglama Sistemi
AYEC Pro Teknik Servis Yonetim Sistemi

Bu modül, kullanıcı aktivitelerini audit_logs tablosuna kaydeder.
"""

import logging
from datetime import datetime
from functools import wraps

logger = logging.getLogger('AuditLogger')

class AuditLogger:
    """
    Kullanıcı aktivitelerini loglayan sınıf
    """
    
    def __init__(self, db):
        self.db = db
        self.current_user = None
    
    def set_current_user(self, user_id):
        """
        Aktif kullanıcıyı ayarlar
        
        Args:
            user_id: Kullanıcı ID'si
        """
        self.current_user = user_id
        logger.info(f"Aktif kullanıcı ayarlandı: {user_id}")
    
    def log_action(self, table_name, action, details='', user_id=None):
        """
        Bir aktiviteyi loglar
        
        Args:
            table_name: İşlem yapılan tablo
            action: İşlem tipi (INSERT, UPDATE, DELETE, VIEW, EXPORT, etc.)
            details: İşlem detayları
            user_id: Kullanıcı ID (None ise current_user kullanılır)
        """
        try:
            if user_id is None:
                user_id = self.current_user or 'SYSTEM'
            
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            self.db.cursor.execute("""
                INSERT INTO audit_logs (user_id, table_name, action, details, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, table_name, action, details, created_at))
            
            self.db.conn.commit()
            
            logger.debug(f"[{user_id}] {action} on {table_name}: {details}")
            
        except Exception as e:
            logger.error(f"Audit log hatası: {str(e)}")
    
    def log_login(self, user_id, success=True):
        """
        Giriş işlemini loglar
        """
        action = "LOGIN_SUCCESS" if success else "LOGIN_FAILED"
        self.log_action('users', action, f"User {user_id} login attempt", user_id)
    
    def log_logout(self, user_id):
        """
        Çıkış işlemini loglar
        """
        self.log_action('users', 'LOGOUT', f"User {user_id} logged out", user_id)
    
    def log_create(self, table_name, record_id, details=''):
        """
        Kayıt oluşturma işlemini loglar
        """
        self.log_action(table_name, 'INSERT', f"Created record ID: {record_id}. {details}")
    
    def log_update(self, table_name, record_id, changes=''):
        """
        Kayıt güncelleme işlemini loglar
        """
        self.log_action(table_name, 'UPDATE', f"Updated record ID: {record_id}. Changes: {changes}")
    
    def log_delete(self, table_name, record_id, details=''):
        """
        Kayıt silme işlemini loglar
        """
        self.log_action(table_name, 'DELETE', f"Deleted record ID: {record_id}. {details}")
    
    def log_view(self, table_name, details=''):
        """
        Görüntüleme işlemini loglar
        """
        self.log_action(table_name, 'VIEW', details)
    
    def log_export(self, table_name, format_type, record_count):
        """
        Dışa aktarma işlemini loglar
        """
        self.log_action(table_name, 'EXPORT', f"Exported {record_count} records as {format_type}")
    
    def log_import(self, table_name, record_count, source=''):
        """
        İçe aktarma işlemini loglar
        """
        self.log_action(table_name, 'IMPORT', f"Imported {record_count} records from {source}")
    
    def log_search(self, table_name, query, result_count):
        """
        Arama işlemini loglar
        """
        self.log_action(table_name, 'SEARCH', f"Query: '{query}', Results: {result_count}")
    
    def log_print(self, document_type, document_id=''):
        """
        Yazdırma işlemini loglar
        """
        self.log_action('documents', 'PRINT', f"Printed {document_type} ID: {document_id}")
    
    def log_email(self, recipient, subject, success=True):
        """
        E-posta gönderimi loglar
        """
        action = "EMAIL_SENT" if success else "EMAIL_FAILED"
        self.log_action('emails', action, f"To: {recipient}, Subject: {subject}")
    
    def log_sms(self, recipient, message, success=True):
        """
        SMS gönderimi loglar
        """
        action = "SMS_SENT" if success else "SMS_FAILED"
        self.log_action('sms', action, f"To: {recipient}, Message: {message[:50]}...")
    
    def log_backup(self, backup_file, size_mb):
        """
        Yedekleme işlemini loglar
        """
        self.log_action('system', 'BACKUP', f"Created backup: {backup_file} ({size_mb:.2f} MB)")
    
    def log_restore(self, backup_file):
        """
        Geri yükleme işlemini loglar
        """
        self.log_action('system', 'RESTORE', f"Restored from: {backup_file}")
    
    def log_settings_change(self, setting_name, old_value, new_value):
        """
        Ayar değişikliğini loglar
        """
        self.log_action('settings', 'UPDATE', f"{setting_name}: '{old_value}' -> '{new_value}'")
    
    def get_user_activity(self, user_id, limit=100):
        """
        Bir kullanıcının aktivite geçmişini getirir
        
        Args:
            user_id: Kullanıcı ID
            limit: Maksimum kayıt sayısı
        
        Returns:
            list: Aktivite kayıtları
        """
        try:
            self.db.cursor.execute("""
                SELECT * FROM audit_logs 
                WHERE user_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (user_id, limit))
            
            return self.db.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Get user activity error: {str(e)}")
            return []
    
    def get_table_activity(self, table_name, limit=100):
        """
        Bir tablonun aktivite geçmişini getirir
        
        Args:
            table_name: Tablo adı
            limit: Maksimum kayıt sayısı
        
        Returns:
            list: Aktivite kayıtları
        """
        try:
            self.db.cursor.execute("""
                SELECT * FROM audit_logs 
                WHERE table_name = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (table_name, limit))
            
            return self.db.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Get table activity error: {str(e)}")
            return []
    
    def get_recent_activity(self, limit=50):
        """
        Son aktiviteleri getirir
        
        Args:
            limit: Maksimum kayıt sayısı
        
        Returns:
            list: Aktivite kayıtları
        """
        try:
            self.db.cursor.execute("""
                SELECT * FROM audit_logs 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            
            return self.db.cursor.fetchall()
            
        except Exception as e:
            logger.error(f"Get recent activity error: {str(e)}")
            return []
    
    def get_activity_stats(self, days=30):
        """
        Aktivite istatistiklerini getirir
        
        Args:
            days: Son kaç gün
        
        Returns:
            dict: İstatistikler
        """
        try:
            from datetime import timedelta
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            # Toplam aktivite
            self.db.cursor.execute("""
                SELECT COUNT(*) FROM audit_logs 
                WHERE created_at >= ?
            """, (start_date,))
            total = self.db.cursor.fetchone()[0]
            
            # Aksiyon bazında
            self.db.cursor.execute("""
                SELECT action, COUNT(*) as count 
                FROM audit_logs 
                WHERE created_at >= ?
                GROUP BY action 
                ORDER BY count DESC
            """, (start_date,))
            by_action = dict(self.db.cursor.fetchall())
            
            # Kullanıcı bazında
            self.db.cursor.execute("""
                SELECT user_id, COUNT(*) as count 
                FROM audit_logs 
                WHERE created_at >= ?
                GROUP BY user_id 
                ORDER BY count DESC
            """, (start_date,))
            by_user = dict(self.db.cursor.fetchall())
            
            return {
                'total': total,
                'by_action': by_action,
                'by_user': by_user,
                'period_days': days
            }
            
        except Exception as e:
            logger.error(f"Get activity stats error: {str(e)}")
            return {'total': 0, 'by_action': {}, 'by_user': {}, 'period_days': days}

def audit_log(table_name, action):
    """
    Decorator: Fonksiyon çağrılarını otomatik loglar
    
    Usage:
        @audit_log('customers', 'INSERT')
        def add_customer(self, name, phone):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            
            # Eğer self'in db ve audit_logger attribute'u varsa logla
            if hasattr(self, 'db') and hasattr(self, 'audit_logger'):
                details = f"Function: {func.__name__}, Args: {args[:3]}"  # İlk 3 argüman
                self.audit_logger.log_action(table_name, action, details)
            
            return result
        return wrapper
    return decorator

# Global audit logger instance
_audit_logger = None

def get_audit_logger(db):
    """
    Global audit logger instance'ını döndürür
    """
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(db)
    return _audit_logger

if __name__ == '__main__':
    logger.info("Audit Logger - Test Modu")
    logger.info("Bu modül database bağlantısı gerektirir.")