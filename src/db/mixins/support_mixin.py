# -*- coding: utf-8 -*-

"""
Support Mixin
Destek biletleri ve bilgi bankası ile ilgili database metodları
"""

from datetime import datetime
from src.utils.logger import logger


class SupportMixin:
    """Destek sistemi için database metodları"""
    
    # =====================
    # Ticket Methods
    # =====================
    
    def get_tickets(self):
        """Tüm destek biletlerini getir"""
        self.cursor.execute("""
            SELECT t.id, c.name, t.subject, t.status, t.priority, t.created_at 
            FROM tickets t 
            LEFT JOIN customers c
                ON t.customer_id = c.id
               AND COALESCE(c.is_deleted, 0) = 0
            ORDER BY t.id DESC
        """)
        return self.cursor.fetchall()
    
    def get_ticket_details(self, ticket_id):
        """Belirli bir biletin detaylarını getir"""
        self.cursor.execute("""
            SELECT t.id, c.name, t.subject, t.description, t.status, t.priority, t.created_at, t.updated_at 
            FROM tickets t 
            LEFT JOIN customers c
                ON t.customer_id = c.id
               AND COALESCE(c.is_deleted, 0) = 0
            WHERE t.id=?
        """, (ticket_id,))
        return self.cursor.fetchone()
    
    def add_ticket(self, customer_id, subject, description, priority):
        """Yeni destek bileti ekle"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            INSERT INTO tickets (customer_id, subject, description, status, priority, created_at, updated_at) 
            VALUES (?, ?, ?, 'OPEN', ?, ?, ?)
        """, (customer_id, subject, description, priority, now, now))
        self.conn.commit()
    
    def update_ticket(self, ticket_id, status, priority, description):
        """Destek biletini güncelle"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("""
            UPDATE tickets 
            SET status=?, priority=?, description=?, updated_at=?
            WHERE id=?
        """, (status, priority, description, now, ticket_id))
        self.conn.commit()
    
    # =====================
    # Knowledge Base Methods
    # =====================
    
    def get_kb_articles(self, query=""):
        """Bilgi bankası makalelerini getir (isteğe bağlı arama ile)"""
        if query:
            # Gelişmiş arama (FTS5)
            q = f"{query}*"
            self.cursor.execute("""
                SELECT id, title, content, tags, created_at 
                FROM kb_articles 
                WHERE id IN (SELECT rowid FROM kb_articles_fts WHERE kb_articles_fts MATCH ?)
                ORDER BY rank
            """, (q,))
        else:
            self.cursor.execute("SELECT * FROM kb_articles ORDER BY id DESC")
        return self.cursor.fetchall()
    
    def add_kb_article(self, title, content, tags=""):
        """Yeni bilgi bankası makalesi ekle"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO kb_articles (title, content, tags, created_at) VALUES (?, ?, ?, ?)", 
            (title, content, tags, now)
        )
        self.conn.commit()
    
    def delete_kb_article(self, article_id):
        """Bilgi bankası makalesini sil"""
        self.cursor.execute("DELETE FROM kb_articles WHERE id=?", (article_id,))
        self.conn.commit()
