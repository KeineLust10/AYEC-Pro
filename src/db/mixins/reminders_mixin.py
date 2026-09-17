# -*- coding: utf-8 -*-

"""
Reminders Mixin
Hatırlatıcı ve bildirimler ile ilgili database metodları
"""

from datetime import datetime
from src.utils.logger import logger


class RemindersMixin:
    """Hatırlatıcılar için database metodları"""
    
    def add_reminder(self, title, personnel_id, date, desc):
        """Yeni hatırlatıcı ekle"""
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO reminders (title, personnel_id, date, description, created_at, is_read)
                VALUES (?, ?, ?, ?, ?, 0)
            """, (title, personnel_id, date, desc, now))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Reminder add error: {e}")
            return False
    
    def get_reminders(self):
        """Tüm hatırlatıcıları getir"""
        try:
            self.cursor.execute("SELECT * FROM reminders ORDER BY date DESC")
            return self.cursor.fetchall()
        except Exception as e:
            logger.error("Get reminders error: %s", e)
            return []
    
    def get_active_reminders(self):
        """Aktif (okunmamış) hatırlatıcıları getir"""
        today = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT * FROM reminders WHERE is_read=0 AND date <= ?", (today,))
        return self.cursor.fetchall()
    
    def mark_reminder_read(self, rem_id):
        """Hatırlatıcıyı okundu olarak işaretle"""
        self.cursor.execute("UPDATE reminders SET is_read=1 WHERE id=?", (rem_id,))
        self.conn.commit()
