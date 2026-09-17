# -*- coding: utf-8 -*-

"""
Logging Mixin
Log ve kayıt yönetimi ile ilgili database metodları
"""

from datetime import datetime
from src.utils.logger import logger


class LoggingMixin:
    """Log ve audit için database metodları"""
    
    def add_log(self, tracking_no, log_type, message, user="Teknisyen"):
        """Log kaydı ekle"""
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO logs (tracking_no, log_type, message, user, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (tracking_no, log_type, message, user, created_at))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Log add error: {e}")
            return False
    
    def get_logs(self, tracking_no):
        """Belirli bir cihaz için logları getir"""
        self.cursor.execute("SELECT * FROM logs WHERE tracking_no=? ORDER BY created_at DESC", (tracking_no,))
        return self.cursor.fetchall()
    
    def get_recent_logs(self, limit=10):
        """Son logları getir"""
        safe_limit = max(1, min(int(limit or 10), 500))
        self.cursor.execute("SELECT * FROM logs ORDER BY created_at DESC LIMIT ?", (safe_limit,))
        return self.cursor.fetchall()
    
    def add_audit_log(self, user, table, action, details):
        """Audit log ekle"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO audit_logs (user_id, table_name, action, details, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user, table, action, details, now))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Audit log error: {e}")
    
    def get_audit_logs(self, limit=50):
        """Audit loglarını getir"""
        self.cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()
    
    def notify_jarvis(self, message, n_type='info', is_critical=False):
        """Jarvis'e bildirim gönder"""
        try:
            self.cursor.execute("""
                INSERT INTO jarvis_notifications (message, type, is_critical)
                VALUES (?, ?, ?)
            """, (message, n_type, 1 if is_critical else 0))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Notify Jarvis error: {e}")
            return False
    
    def get_unread_jarvis_notifications(self, limit=10):
        """Okunmamış Jarvis bildirimlerini getir"""
        try:
            self.cursor.execute("""
                SELECT id, message, type, is_critical, created_at 
                FROM jarvis_notifications 
                WHERE status = 'unread' 
                ORDER BY created_at ASC LIMIT ?
            """, (limit,))
            rows = self.cursor.fetchall()
            
            if rows:
                ids = [row[0] for row in rows]
                placeholders = ','.join(['?'] * len(ids))
                self.cursor.execute(
                    "UPDATE jarvis_notifications SET status='read' WHERE id IN ({placeholders})".format(
                        placeholders=placeholders
                    ),
                    ids,
                )
                self.conn.commit()
            
            return rows
        except Exception as e:
            logger.error(f"Get unread notifications error: {e}")
            return []
