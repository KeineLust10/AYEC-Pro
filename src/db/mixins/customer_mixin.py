# -*- coding: utf-8 -*-

"""
Customer Mixin
Müşteri yönetimi ile ilgili database metodları
"""

from datetime import datetime
import re
from src.utils.logger import logger
from src.utils.performance_monitor import perf_span


class CustomerMixin:
    """Müşteriler için database metodları"""

    def _safe_identifier(self, value):
        value = str(value or "").strip()
        if not value or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ValueError(f"Unsafe SQL identifier: {value!r}")
        return value
    
    def _resolve_customer_identity(self, customer_identifier):
        customer_id = None
        customer_name = None
        try:
            if isinstance(customer_identifier, int) or str(customer_identifier).isdigit():
                customer_id = int(customer_identifier)
                self.cursor.execute("SELECT name FROM customers WHERE id=?", (customer_id,))
                row = self.cursor.fetchone()
                customer_name = row[0] if row else None
            else:
                customer_name = str(customer_identifier).strip()
                self.cursor.execute(
                    "SELECT id, name FROM customers WHERE TRIM(UPPER(name))=TRIM(UPPER(?)) LIMIT 1",
                    (customer_name,),
                )
                row = self.cursor.fetchone()
                if row:
                    customer_id = row[0]
                    customer_name = row[1]
        except Exception as e:
            logger.error(f"Customer identity resolve error: {e}")
        return customer_id, customer_name

    def add_customer(self, data):
        """Add a customer."""
        try:
            self._last_customer_error = ""
            self.cursor.execute("PRAGMA table_info(customers)")
            valid_columns = {row[1] for row in (self.cursor.fetchall() or [])}
            safe_items = []
            for key, value in (data or {}).items():
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(key or "")):
                    continue
                if key not in valid_columns:
                    continue
                safe_items.append((key, value))

            if not safe_items:
                raise ValueError("No valid customer columns supplied")

            keys = ", ".join(self._safe_identifier(key) for key, _ in safe_items)
            values_ph = ", ".join(["?"] * len(safe_items))
            values = tuple(value for _, value in safe_items)
            sql = "INSERT INTO customers ({keys}) VALUES ({values_ph})".format(
                keys=keys,
                values_ph=values_ph,
            )
            self.cursor.execute(sql, values)
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            self._last_customer_error = str(e)
            logger.exception("Customer add error")
            return None
    
    def get_customers(self):
        """Tüm müşterileri getir (Silinmemiş olanlar)"""
        try:
            self.cursor.execute("SELECT * FROM customers WHERE is_deleted=0 OR is_deleted IS NULL ORDER BY name")
            return self.cursor.fetchall()
        except Exception as e:
            logger.warning(f"Customer list fallback triggered: {e}")
            # Fallback if is_deleted column doesn't exist yet
            self.cursor.execute("SELECT * FROM customers ORDER BY name")
            return self.cursor.fetchall()
    
    def get_all_customers(self):
        """Tüm müşterileri getir (alias)"""
        return self.get_customers()
    
    def get_customers_paginated_with_balances(self, limit=50, offset=0, search_query=None, filter_type=None):
        """
        Sayfalı müşteri listesi (tek sorguda bakiye özetleriyle).
        Corrected to use: customer_currency_balances, devices, used_parts
        """
        try:
            logger.debug(
                "get_customers_paginated_with_balances start: limit=%s offset=%s search=%s filter=%s",
                limit, offset, search_query, filter_type
            )
            cur = self.conn.cursor()
            
            where_parts = ["(c.is_deleted = 0 OR c.is_deleted IS NULL)"]
            params = []

            if search_query:
                where_parts.append("(c.name LIKE ? OR c.phone LIKE ? OR c.email LIKE ? OR c.company_name LIKE ?)")
                q = f"%{search_query}%"
                params.extend([q, q, q, q])

            where_sql = " AND ".join(where_parts)

            # Tek kaynak: müşteri cari bakiyeleri customer_currency_balances tablosundan okunur.
            # Eski cihaz/parça toplamlarını burada tekrar eklemek bakiyeyi iki kez saydırıyordu.
            balance_subquery = """
                SELECT 
                    customer_id,
                    SUM(CASE WHEN currency='TRY' THEN balance ELSE 0 END) AS balance_try,
                    SUM(CASE WHEN currency='USD' THEN balance ELSE 0 END) AS balance_usd,
                    SUM(CASE WHEN currency='EUR' THEN balance ELSE 0 END) AS balance_eur
                FROM customer_currency_balances
                GROUP BY customer_id
            """

            debt_where = ""
            if filter_type == "DEBTORS":
                debt_where = """
                    AND (
                        COALESCE(b.balance_try, 0) < 0
                        OR COALESCE(b.balance_usd, 0) < 0
                        OR COALESCE(b.balance_eur, 0) < 0
                    )
                """
            elif filter_type == "OPEN_RECEIVABLES":
                debt_where = """
                    AND EXISTS (
                        SELECT 1
                        FROM currency_transactions ct
                        WHERE ct.customer_id = c.id
                          AND ct.transaction_type = 'DEBIT'
                          AND COALESCE(ct.current_balance, 0) < 0
                    )
                """

            count_sql = """
                SELECT COUNT(*)
                FROM customers c
                LEFT JOIN ({balance_subquery}) b ON b.customer_id = c.id
                WHERE {where_sql}
                {debt_where}
            """.format(balance_subquery=balance_subquery, where_sql=where_sql, debt_where=debt_where)
            with perf_span(
                "sql.customers.count",
                extra=f"filter={filter_type or 'ALL'}",
                threshold_ms=75,
            ):
                cur.execute(count_sql, tuple(params))
                total = int(cur.fetchone()[0] or 0)
            logger.debug("get_customers_paginated_with_balances count=%s", total)

            data_sql = """
                SELECT
                    c.*,
                    COALESCE(b.balance_try, 0) AS balance_try,
                    COALESCE(b.balance_usd, 0) AS balance_usd,
                    COALESCE(b.balance_eur, 0) AS balance_eur
                FROM customers c
                LEFT JOIN ({balance_subquery}) b ON b.customer_id = c.id
                WHERE {where_sql}
                {debt_where}
                ORDER BY c.name
                LIMIT ? OFFSET ?
            """.format(balance_subquery=balance_subquery, where_sql=where_sql, debt_where=debt_where)
            data_params = list(params) + [int(limit), int(offset)]
            
            with perf_span(
                "sql.customers.page",
                extra=f"limit={limit} offset={offset}",
                threshold_ms=75,
            ):
                cur.execute(data_sql, tuple(data_params))
                columns = [column[0] for column in cur.description]
                rows = [dict(zip(columns, row)) for row in cur.fetchall()]
            logger.debug("get_customers_paginated_with_balances rows=%s", len(rows))

            cur.close()
            return rows, total
        except Exception as e:
            logger.warning(f"Paginated customer query error: {e}")
            try:
                # Emergency Fallback: return customers without balances
                cur2 = self.conn.cursor()
                cur2.execute(
                    "SELECT * FROM customers WHERE is_deleted=0 OR is_deleted IS NULL ORDER BY name LIMIT ? OFFSET ?",
                    (limit, offset)
                )
                cols = [c[0] for c in cur2.description]
                rows = [dict(zip(cols, row)) for row in cur2.fetchall()]
                cur2.execute("SELECT COUNT(*) FROM customers WHERE is_deleted=0 OR is_deleted IS NULL")
                total = cur2.fetchone()[0]
                cur2.close()
                return rows, total
            except Exception as inner_e:
                logger.error(f"Fallback list failed: {inner_e}")
                return [], 0


    def search_customers(self, query):
        """Müşteri ara"""
        q = f"%{query}%"
        self.cursor.execute(
            "SELECT * FROM customers WHERE (name LIKE ? OR phone LIKE ?) AND COALESCE(is_deleted, 0) = 0",
            (q, q),
        )
        return self.cursor.fetchall()
    
    def delete_customer(self, customer_id):
        """Müşteri sil (Soft Delete - İşlem geçmişi korunur)"""
        try:
            if hasattr(self, "soft_delete_record"):
                return self.soft_delete_record("customers", "id", customer_id)
            deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "UPDATE customers SET is_deleted=1, deleted_at=? WHERE id=?",
                (deleted_at, customer_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Customer delete error: {e}")
            return False
    
    def get_customer_history(self, customer_identifier):
        """Müşteri servis geçmişini customer_id öncelikli getir."""
        customer_id, customer_name = self._resolve_customer_identity(customer_identifier)
        if not customer_id and not customer_name:
            return []

        self.cursor.execute(
            """
            SELECT *
            FROM devices
            WHERE (
                    (? IS NOT NULL AND customer_id=?)
                    OR TRIM(UPPER(customer_name))=TRIM(UPPER(?))
                  )
              AND COALESCE(is_deleted, 0) = 0
            ORDER BY COALESCE(entry_date, created_at) DESC
            """,
            (customer_id, customer_id, customer_name or ""),
        )
        return self.cursor.fetchall()
    
    def get_customer_history_summary(self, customer_identifier):
        """Müşteri Özet istatistiklerini customer_id öncelikli getir."""
        try:
            customer_id, customer_name = self._resolve_customer_identity(customer_identifier)
            if not customer_id and not customer_name:
                return None

            self.cursor.execute("""
                SELECT COUNT(*), SUM(COALESCE(labor_cost, 0)), MAX(COALESCE(entry_date, created_at))
                FROM devices
                WHERE (
                        (? IS NOT NULL AND customer_id = ?)
                        OR TRIM(UPPER(customer_name)) = TRIM(UPPER(?))
                      )
                  AND COALESCE(is_deleted, 0) = 0
            """, (customer_id, customer_id, customer_name or ""))
            job_count, total_spend, last_visit = self.cursor.fetchone()
            
            if not job_count:
                return None
            
            self.cursor.execute("""
                SELECT device_brand, device_model, COUNT(*) as visit_count 
                FROM devices 
                WHERE ((? IS NOT NULL AND customer_id = ?)
                   OR TRIM(UPPER(customer_name)) = TRIM(UPPER(?)))
                  AND COALESCE(is_deleted, 0) = 0
                GROUP BY device_brand, device_model
                ORDER BY visit_count DESC
            """, (customer_id, customer_id, customer_name or ""))
            device_history = self.cursor.fetchall()
            
            self.cursor.execute("""
                SELECT device_brand, device_model, status, COALESCE(entry_date, created_at)
                FROM devices 
                WHERE ((? IS NOT NULL AND customer_id = ?)
                   OR TRIM(UPPER(customer_name)) = TRIM(UPPER(?)))
                  AND COALESCE(is_deleted, 0) = 0
                ORDER BY COALESCE(entry_date, created_at) DESC LIMIT 3
            """, (customer_id, customer_id, customer_name or ""))
            recent_jobs = self.cursor.fetchall()
            
            return {
                "name": customer_name or str(customer_identifier),
                "job_count": job_count,
                "total_spend": total_spend or 0,
                "last_visit": last_visit,
                "device_history": device_history,
                "recent_jobs": recent_jobs
            }
        except Exception as e:
            logger.error(f"Customer history summary error: {e}")
            return None
    
    def get_customer_balance(self, customer_id):
        """
        Müşteri bakiyesini hesapla (Döviz + Legacy + Accounting)
        Returns: float (TL cinsinden toplam net borç)
        """
        try:
            # Database class inherits from CurrencyMixin
            if hasattr(self, 'get_customer_total_balance_in_try'):
                return self.get_customer_total_balance_in_try(customer_id)
            
            return 0.0
        except Exception as e:
            logger.error(f"Customer unified balance error: {e}")
            return 0.0
    
    def get_customers_with_debt(self):
        """Borcu olan müşterileri getir"""
        try:
            customers = self.get_customers()
            debtors = []
            for c in customers:
                balance = self.get_customer_balance(c[0])
                if balance < 0:
                    debtors.append(c)
            return debtors
        except Exception as e:
            logger.error(f"Get customers with debt error: {e}")
            return []
    
    def get_customer_balances(self):
        """Tüm müşteri bakiyelerini getir"""
        try:
            customers = self.get_customers()
            balances = []
            for c in customers:
                balance = self.get_customer_balance(c[0])
                balances.append((c[0], c[1], balance))
            return balances
        except Exception as e:
            logger.error(f"Get customer balances error: {e}")
            return []
    
    def add_customer_note(self, customer_id, note_type, content):
        """Müşteriye özel not ekle"""
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("PRAGMA table_info(customer_notes)")
            columns = [row[1] for row in self.cursor.fetchall() or []]
            type_column = "note_type" if "note_type" in columns else "type"
            self.cursor.execute(
                f"""
                INSERT INTO customer_notes (customer_id, {type_column}, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (customer_id, note_type, content, created_at),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Customer note add error: {e}")
            return False
