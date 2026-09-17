# -*- coding: utf-8 -*-


from src.utils.logger import logger
import json
from datetime import datetime

class NotificationMixin:
    """Merkezi Bildirim Sistemi için veritabanı metodları"""

    def create_notification_table(self):
        """Bildirim tablosunu oluşturur"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT, -- 'Finance', 'Stock', 'Technical', 'System'
                    title TEXT,
                    content TEXT,
                    link_id TEXT, -- formatted link e.g. "stock:123", "loan:45", "customer:99"
                    status TEXT DEFAULT 'unread', -- 'unread', 'read', 'archived'
                    priority TEXT DEFAULT 'normal', -- 'normal', 'high', 'critical'
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP
                )
            """)
            self.conn.commit()
            logger.info("Notification table created/verified.")
        except Exception as e:
            logger.error(f"Error creating notification table: {e}")

    def add_notification(self, category, title, content, link_id=None, priority='normal', unique_key=None):
        """
        Yeni bildirim ekler.
        unique_key: Eğer verilirse, aynı link_id ve category'ye sahip okunmamış bir bildirim varsa tekrar eklemez.
        """
        try:
            if str(self.get_setting("notifications_enabled", "1")) != "1":
                return None
            if unique_key:
                # Duplicate check for active notifications
                self.cursor.execute(
                    """
                    SELECT id
                    FROM notifications
                    WHERE link_id=? AND category=? AND status='unread'
                    """,
                    (unique_key, category),
                )
                if self.cursor.fetchone():
                    return None # Already exists

            self.cursor.execute("""
                INSERT INTO notifications (category, title, content, link_id, priority)
                VALUES (?, ?, ?, ?, ?)
            """, (category, title, content, link_id, priority))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding notification: {e}")
            return None

    def get_notifications(self, status='unread', limit=50):
        """Bildirimleri önceliğe ve zamana göre getirir"""
        try:
            # Order: Critical first, then High, then Normal. Then date DESC.
            # Using CASE for custom order
            query = """
                SELECT *
                FROM notifications
                WHERE status=?
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        ELSE 4
                    END,
                    created_at DESC
                LIMIT ?
            """
            self.cursor.execute(query, (status, limit))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting notifications: {e}")
            return []

    def get_notification_history(self, search_query='', limit=100):
        """Geçmiş bildirimleri getirir (Arama destekli)"""
        try:
            query = "SELECT * FROM notifications WHERE 1=1"
            params = []
            
            if search_query:
                query += " AND (title LIKE ? OR content LIKE ?)"
                wildcard = f"%{search_query}%"
                params.extend([wildcard, wildcard])
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting notification history: {e}")
            return []

    def mark_notification_read(self, n_id):
        """Bildirimi okundu olarak işaretler"""
        try:
            self.cursor.execute("""
                UPDATE notifications 
                SET status='read', read_at=CURRENT_TIMESTAMP 
                WHERE id=?
            """, (n_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking notification read: {e}")
            return False

    def mark_all_read(self):
        """Tümünü okundu işaretle"""
        try:
            self.cursor.execute("""
                UPDATE notifications 
                SET status='read', read_at=CURRENT_TIMESTAMP 
                WHERE status='unread'
            """)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking all read: {e}")
            return False

    def archive_notification(self, n_id):
        """Arşive kaldır (opsiyonel, şimdilik read yeterli ama yapı dursun)"""
        try:
            self.cursor.execute("UPDATE notifications SET status='archived' WHERE id=?", (n_id,))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error archiving notification: {e}")

    def get_unread_count(self):
        """Okunmamış sayısını döndürür"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM notifications WHERE status='unread'")
            res = self.cursor.fetchone()
            return res[0] if res else 0
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
