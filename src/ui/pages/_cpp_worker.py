# -*- coding: utf-8 -*-
from PyQt6.QtCore import QThread, pyqtSignal
from src.utils.currency_helper import CurrencyHelper
import sqlite3

class CustomerWorker(QThread):
    data_loaded = pyqtSignal(list, int)  # customers, total_count
    load_error = pyqtSignal(str)

    def __init__(self, db, limit, offset, search_query, filter_type):
        super().__init__()
        self.db = db
        self.limit = limit
        self.offset = offset
        self.search_query = search_query
        self.filter_type = filter_type

    def run(self):
        conn = None
        try:
            display_currency = CurrencyHelper.get_code(self.db)
            if getattr(self.db, "_db_name", "") == ":memory:":
                conn = self.db.conn
            else:
                from src.utils.path_helper import PathHelper
                db_path = PathHelper.get_db_path(getattr(self.db, "_db_name", "ayecpro.db"))
                conn = sqlite3.connect(db_path, timeout=30.0)
            cur = conn.cursor()
            where_parts = ["(c.is_deleted = 0 OR c.is_deleted IS NULL)"]
            params = []
            if self.filter_type == "PARTNERS":
                where_parts.append("(COALESCE(c.is_partner, 0) = 1)")
            else:
                where_parts.append("(COALESCE(c.is_partner, 0) = 0)")
            if self.search_query:
                where_parts.append(
                    "(c.name LIKE ? OR c.phone LIKE ? OR c.email LIKE ? OR c.company_name LIKE ?)"
                )
                q = f"%{self.search_query}%"
                params.extend([q, q, q, q])
            where_sql = " AND ".join(where_parts)
            debt_where = ""
            if self.filter_type == "OPEN_RECEIVABLES":
                debt_where = """
                    AND EXISTS (
                        SELECT 1
                        FROM currency_transactions ct
                        WHERE ct.customer_id = c.id
                          AND ct.transaction_type = 'DEBIT'
                          AND COALESCE(ct.current_balance, 0) < 0
                    )
                """

            cur.execute(
                "SELECT COUNT(*) FROM customers c WHERE {where_sql} {debt_where}".format(
                    where_sql=where_sql,
                    debt_where=debt_where,
                ),
                tuple(params),
            )
            total = int(cur.fetchone()[0] or 0)

            balance_sub = """
                SELECT customer_id,
                    SUM(CASE WHEN currency='TRY' THEN balance ELSE 0 END) AS balance_try,
                    SUM(CASE WHEN currency='USD' THEN balance ELSE 0 END) AS balance_usd,
                    SUM(CASE WHEN currency='EUR' THEN balance ELSE 0 END) AS balance_eur
                FROM customer_currency_balances
                GROUP BY customer_id
            """
            data_sql = """
                SELECT c.*,
                    COALESCE(b.balance_try, 0) AS balance_try,
                    COALESCE(b.balance_usd, 0) AS balance_usd,
                    COALESCE(b.balance_eur, 0) AS balance_eur
                FROM customers c
                LEFT JOIN ({balance_sub}) b ON b.customer_id = c.id
                WHERE {where_sql}
                {debt_where}
                ORDER BY c.name LIMIT ? OFFSET ?
            """.format(
                balance_sub=balance_sub,
                where_sql=where_sql,
                debt_where=debt_where,
            )
            data_params = list(params) + [int(self.limit), int(self.offset)]
            cur.execute(data_sql, tuple(data_params))
            columns = [col[0] for col in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]

            def _is_partner_row(row):
                try:
                    if int(row.get("is_partner", 0) or 0) == 1:
                        return True
                except Exception:
                    pass
                row_type = str(row.get("type") or "").strip().casefold()
                return row_type in {"bayi", "tedarikçi", "tedarikci"}

            if self.filter_type == "PARTNERS":
                rows = [row for row in rows if _is_partner_row(row)]
            else:
                rows = [row for row in rows if not _is_partner_row(row)]

            if self.filter_type == "DEBTORS":
                filtered_rows = []
                for r in rows:
                    converted_total = 0.0
                    converted_total += CurrencyHelper.convert_amount(
                        self.db,
                        float(r.get("balance_try", 0) or 0),
                        "TRY",
                        display_currency,
                    )
                    converted_total += CurrencyHelper.convert_amount(
                        self.db,
                        float(r.get("balance_usd", 0) or 0),
                        "USD",
                        display_currency,
                    )
                    converted_total += CurrencyHelper.convert_amount(
                        self.db,
                        float(r.get("balance_eur", 0) or 0),
                        "EUR",
                        display_currency,
                    )
                    if converted_total < 0:
                        filtered_rows.append(r)
                rows = filtered_rows
                total = len(rows)

            cur.close()
            if getattr(self.db, "_db_name", "") != ":memory:":
                conn.close()
            conn = None
            self.data_loaded.emit(rows, total)
        except Exception as e:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            self.load_error.emit(str(e))
