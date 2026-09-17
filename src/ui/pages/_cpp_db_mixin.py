# -*- coding: utf-8 -*-
from src.utils.logger import logger
from datetime import datetime

class PartnersPageDbMixin:
    def _ensure_partner_runtime_tables(self):
        cur = self.db.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS partner_shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                partner_name TEXT NOT NULL,
                customer_name TEXT,
                product_name TEXT,
                serial_no TEXT,
                issue_summary TEXT,
                shipment_reason TEXT,
                outbound_tracking_no TEXT,
                return_tracking_no TEXT,
                external_ref_no TEXT,
                status TEXT DEFAULT 'Hazirlaniyor',
                partner_cost REAL DEFAULT 0,
                customer_price REAL DEFAULT 0,
                quote_status TEXT DEFAULT 'Beklemede',
                quote_amount REAL DEFAULT 0,
                approval_status TEXT DEFAULT 'Onay Bekliyor',
                contract_type TEXT,
                sla_level TEXT,
                notes TEXT,
                sent_at TEXT,
                returned_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS partner_finance_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                shipment_id INTEGER,
                entry_type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'TRY',
                payment_method TEXT,
                description TEXT,
                invoice_no TEXT,
                invoice_date TEXT,
                entry_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS partner_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                shipment_id INTEGER,
                title TEXT NOT NULL,
                category TEXT,
                file_path TEXT NOT NULL,
                added_at TEXT NOT NULL
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS partner_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                shipment_id INTEGER,
                event_type TEXT NOT NULL,
                detail TEXT,
                event_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        try:
            cols = {row[1] for row in cur.execute("PRAGMA table_info(partner_shipments)").fetchall()}
            required_cols = {
                "partner_id": "INTEGER DEFAULT 0", "partner_name": "TEXT DEFAULT ''",
                "customer_name": "TEXT", "product_name": "TEXT", "serial_no": "TEXT",
                "issue_summary": "TEXT", "shipment_reason": "TEXT", "outbound_tracking_no": "TEXT",
                "return_tracking_no": "TEXT", "external_ref_no": "TEXT",
                "status": "TEXT DEFAULT 'Hazirlaniyor'", "partner_cost": "REAL DEFAULT 0",
                "customer_price": "REAL DEFAULT 0", "currency": "TEXT DEFAULT 'TRY'",
                "quote_status": "TEXT DEFAULT 'Beklemede'", "quote_amount": "REAL DEFAULT 0",
                "approval_status": "TEXT DEFAULT 'Onay Bekliyor'", "contract_type": "TEXT",
                "sla_level": "TEXT", "accessories": "TEXT", "return_qc": "TEXT",
                "cosmetic_status": "TEXT", "missing_parts": "TEXT",
                "cost_responsibility": "TEXT", "notes": "TEXT", "sent_at": "TEXT", "returned_at": "TEXT",
                "created_at": "TEXT", "updated_at": "TEXT"
            }
            for col_name, definition in required_cols.items():
                if col_name not in cols:
                    cur.execute(f"ALTER TABLE partner_shipments ADD COLUMN {col_name} {definition}")

            doc_cols = {row[1] for row in cur.execute("PRAGMA table_info(partner_documents)").fetchall()}
            for col_name, definition in {
                "partner_id": "INTEGER DEFAULT 0", "shipment_id": "INTEGER",
                "title": "TEXT DEFAULT ''", "category": "TEXT", "file_path": "TEXT DEFAULT ''",
                "added_at": "TEXT DEFAULT ''"
            }.items():
                if col_name not in doc_cols:
                    cur.execute(f"ALTER TABLE partner_documents ADD COLUMN {col_name} {definition}")

            fin_cols = {row[1] for row in cur.execute("PRAGMA table_info(partner_finance_entries)").fetchall()}
            for col_name, definition in {
                "partner_id": "INTEGER DEFAULT 0", "shipment_id": "INTEGER",
                "entry_type": "TEXT DEFAULT 'PAYMENT'", "amount": "REAL DEFAULT 0",
                "currency": "TEXT DEFAULT 'TRY'", "payment_method": "TEXT",
                "description": "TEXT", "invoice_no": "TEXT", "invoice_date": "TEXT",
                "entry_date": "TEXT DEFAULT ''", "created_at": "TEXT DEFAULT ''"
            }.items():
                if col_name not in fin_cols:
                    cur.execute(f"ALTER TABLE partner_finance_entries ADD COLUMN {col_name} {definition}")

            time_cols = {row[1] for row in cur.execute("PRAGMA table_info(partner_timeline)").fetchall()}
            for col_name, definition in {
                "partner_id": "INTEGER DEFAULT 0", "shipment_id": "INTEGER",
                "event_type": "TEXT DEFAULT 'GENEL'", "detail": "TEXT",
                "event_date": "TEXT DEFAULT ''", "created_at": "TEXT DEFAULT ''"
            }.items():
                if col_name not in time_cols:
                    cur.execute(f"ALTER TABLE partner_timeline ADD COLUMN {col_name} {definition}")
            
            cur.execute("UPDATE partner_timeline SET event_type = 'GENEL' WHERE COALESCE(event_type, '') = ''")
            cur.execute("UPDATE partner_timeline SET event_date = COALESCE(NULLIF(event_date, ''), datetime('now')) WHERE COALESCE(event_date, '') = ''")
            cur.execute("UPDATE partner_timeline SET created_at = COALESCE(NULLIF(created_at, ''), datetime('now')) WHERE COALESCE(created_at, '') = ''")
        except Exception as exc:
            logger.warning("Partner shipment migration skipped: %s", exc)
        self.db.conn.commit()

    def _partner_trackings(self, partner):
        if not partner: return []
        self._ensure_partner_runtime_tables()
        try:
            self.db.cursor.execute("""
                SELECT id, COALESCE(serial_no, ''), COALESCE(customer_name, ''), COALESCE(product_name, ''),
                       COALESCE(partner_name, ''), COALESCE(external_ref_no, ''), COALESCE(sent_at, ''),
                       COALESCE(outbound_tracking_no, ''), COALESCE(return_tracking_no, ''), COALESCE(status, ''),
                       COALESCE(notes, '')
                FROM partner_shipments
                WHERE partner_id = ?
                ORDER BY COALESCE(sent_at, created_at, updated_at) DESC, id DESC
            """, (int(partner["id"]),))
            return [self._normalize_tracking(row) for row in (self.db.cursor.fetchall() or [])]
        except Exception as e:
            logger.error("Partner tracking load error: %s", e)
            return []

    def _partner_finance_summary(self, partner):
        empty = {"partner_cost": 0.0, "paid_total": 0.0, "customer_total": 0.0, "balance": 0.0}
        if not partner: return empty
        self._ensure_partner_runtime_tables()
        cur = self.db.conn.cursor()
        try:
            cur.execute("SELECT COALESCE(SUM(partner_cost), 0), COALESCE(SUM(customer_price), 0) FROM partner_shipments WHERE partner_id = ?", (int(partner["id"]),))
            cost, cust = cur.fetchone() or (0, 0)
            cur.execute("SELECT COALESCE(SUM(amount), 0) FROM partner_finance_entries WHERE partner_id = ? AND entry_type = 'PAYMENT'", (int(partner["id"]),))
            paid = float((cur.fetchone() or [0])[0] or 0)
            return {"partner_cost": float(cost or 0), "paid_total": paid, "customer_total": float(cust or 0), "balance": float(cost or 0) - paid}
        except Exception: return empty

    def _partner_quote_summary(self, partner):
        if not partner: return {"quote_total": 0.0, "waiting_count": 0, "approved_count": 0}
        self.db.cursor.execute("""
            SELECT COALESCE(SUM(quote_amount), 0),
                   SUM(CASE WHEN COALESCE(approval_status, '') LIKE '%Bekliyor%' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(approval_status, '') LIKE '%Onay%' THEN 1 ELSE 0 END)
            FROM partner_shipments WHERE partner_id = ?
        """, (int(partner["id"]),))
        q, w, a = self.db.cursor.fetchone() or (0, 0, 0)
        return {"quote_total": float(q or 0), "waiting_count": int(w or 0), "approved_count": int(a or 0)}

    def _partner_document_rows(self, partner):
        if not partner: return []
        self.db.cursor.execute("SELECT title, COALESCE(category, ''), COALESCE(shipment_id, ''), added_at FROM partner_documents WHERE partner_id = ? ORDER BY added_at DESC, id DESC", (int(partner["id"]),))
        return self.db.cursor.fetchall() or []

    def _partner_timeline_rows(self, partner):
        if not partner: return []
        self.db.cursor.execute("SELECT event_date, event_type, COALESCE(detail, ''), COALESCE(shipment_id, '') FROM partner_timeline WHERE partner_id = ? ORDER BY event_date DESC, id DESC LIMIT 100", (int(partner["id"]),))
        return self.db.cursor.fetchall() or []

    def _partner_trend_rows(self, partner):
        if not partner: return []
        self.db.cursor.execute("""
            SELECT COALESCE(substr(COALESCE(sent_at, created_at), 1, 7), '-') AS period,
                COUNT(*) AS shipment_count,
                SUM(CASE WHEN COALESCE(status, '') IN ('Geri Geldi', 'Musteriye Teslim Edildi', 'Tamamlandi', 'Teslim Edildi') THEN 1 ELSE 0 END) AS completed_count,
                COALESCE(SUM(partner_cost), 0), COALESCE(SUM(customer_price), 0), COALESCE(SUM(quote_amount), 0)
            FROM partner_shipments WHERE partner_id = ?
            GROUP BY period ORDER BY period DESC
        """, (int(partner["id"]),))
        return self.db.cursor.fetchall() or []
