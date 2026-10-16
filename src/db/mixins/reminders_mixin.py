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
            self.cursor.execute("PRAGMA table_info(reminders)")
            columns = {row[1] for row in self.cursor.fetchall()}
            personnel_name = ""
            if personnel_id and "personnel" in columns:
                self.cursor.execute("SELECT name FROM personnel WHERE id=?", (personnel_id,))
                person_row = self.cursor.fetchone()
                personnel_name = str(person_row[0] or "") if person_row else ""

            values = {
                "title": title,
                "personnel": personnel_name,
                "date": date,
                "description": desc,
                "status": "Aktif",
                "created_at": now,
                "is_read": 0,
                "personnel_id": personnel_id,
            }
            fields = [
                field for field in (
                    "title", "personnel", "personnel_id", "date", "description",
                    "status", "created_at", "is_read",
                )
                if field in columns
            ]
            if not {"title", "date", "description"}.issubset(fields):
                raise RuntimeError("Hat\u0131rlat\u0131c\u0131 tablosu gerekli alanlar\u0131 i\u00e7ermiyor.")
            field_sql = ", ".join('"{}"'.format(field) for field in fields)
            value_sql = ", ".join("?" for _field in fields)
            self.cursor.execute(
                "INSERT INTO reminders ({}) VALUES ({})".format(field_sql, value_sql),
                tuple(values[field] for field in fields),
            )
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
