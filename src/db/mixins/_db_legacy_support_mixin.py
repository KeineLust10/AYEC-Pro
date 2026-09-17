# -*- coding: utf-8 -*-

from datetime import datetime
from src.utils.logger import logger

class DBLegacySupportMixin:
    """Legacy support, audit, and assistant notification methods."""

    def add_audit_log(self, user, table, action, details):
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("INSERT INTO audit_logs (user_id, table_name, action, details, created_at) VALUES (?, ?, ?, ?, ?)", (user, table, action, details, now))
            self.conn.commit()
        except Exception as e:
            logger.error(f"Audit log error: {e}")

    def get_audit_logs(self, limit=50):
        self.cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        return self.cursor.fetchall()

    def get_tickets(self):
        self.cursor.execute("""
            SELECT t.id, c.name, t.subject, t.status, t.priority, t.created_at 
            FROM tickets t LEFT JOIN customers c ON t.customer_id = c.id ORDER BY t.id DESC
        """)
        return self.cursor.fetchall()

    def get_ticket_details(self, ticket_id):
        self.cursor.execute("""
            SELECT t.id, c.name, t.subject, t.description, t.status, t.priority, t.created_at, t.updated_at 
            FROM tickets t LEFT JOIN customers c ON t.customer_id = c.id WHERE t.id=?
        """, (ticket_id,))
        return self.cursor.fetchone()

    def add_ticket(self, customer_id, subject, description, priority):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO tickets (customer_id, subject, description, status, priority, created_at, updated_at) VALUES (?, ?, ?, 'OPEN', ?, ?, ?)", (customer_id, subject, description, priority, now, now))
        self.conn.commit()

    def update_ticket(self, ticket_id, status, priority, description):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("UPDATE tickets SET status=?, priority=?, description=?, updated_at=? WHERE id=?", (status, priority, description, now, ticket_id))
        self.conn.commit()

    def get_kb_articles(self, query=""):
        if query:
            self.cursor.execute("SELECT id, title, content, tags, created_at FROM kb_articles WHERE id IN (SELECT rowid FROM kb_articles_fts WHERE kb_articles_fts MATCH ?) ORDER BY rank", (f"{query}*",))
        else:
            self.cursor.execute("SELECT * FROM kb_articles ORDER BY id DESC")
        return self.cursor.fetchall()

    def add_kb_article(self, title, content, tags):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO kb_articles (title, content, tags, created_at) VALUES (?, ?, ?, ?)", (title, content, tags, now))
        self.conn.commit()

    def delete_kb_article(self, article_id):
        self.cursor.execute("DELETE FROM kb_articles WHERE id=?", (article_id,))
        self.conn.commit()

    def notify_assistant(self, message, n_type="info", is_critical=False):
        try:
            self.cursor.execute("INSERT INTO assistant_notifications (message, type, is_critical) VALUES (?, ?, ?)", (message, n_type, 1 if is_critical else 0))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Notify Assistant error: {e}")
            return False

    def get_unread_assistant_notifications(self, limit=10):
        try:
            self.cursor.execute("SELECT id, message, type, is_critical, created_at FROM assistant_notifications WHERE status = 'unread' ORDER BY created_at ASC LIMIT ?", (limit,))
            rows = self.cursor.fetchall()
            if rows:
                ids = [row[0] for row in rows]
                self.cursor.execute(f"UPDATE assistant_notifications SET status='read' WHERE id IN ({','.join(['?']*len(ids))})", ids)
                self.conn.commit()
            return rows
        except Exception as e:
            logger.error(f"Get unread notifications error: {e}")
            return []
