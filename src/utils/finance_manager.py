# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import re
from src.utils.logger import logger
from src.utils.income_tax_tariff_service import IncomeTaxTariffService


class FinanceManager:
    def _repair_accounting_currency_values(self):
        """Keep accounting amount and TRY equivalent canonical for foreign rows."""
        try:
            columns = set(self.db._get_table_columns("accounting"))
            required = {"amount", "original_amount", "try_equivalent", "currency", "exchange_rate"}
            if not required.issubset(columns):
                return
            self.db.cursor.execute(
                """
                UPDATE accounting
                   SET amount = ROUND(original_amount * exchange_rate, 4),
                       try_equivalent = ROUND(original_amount * exchange_rate, 4)
                 WHERE UPPER(COALESCE(currency, 'TRY')) IN ('USD', 'EUR')
                   AND COALESCE(original_amount, 0) > 0
                   AND COALESCE(exchange_rate, 0) > 1
                   AND ABS(COALESCE(try_equivalent, 0) - (original_amount * exchange_rate)) > 0.01
                """
            )
            if self.db.cursor.rowcount:
                self.db.conn.commit()
        except Exception as exc:
            logger.warning("Accounting currency repair skipped: %s", exc)

    """
    Centralized Finance Manager to aggregate data from:
    1. 'transactions' table (Legacy Customer Transactions)
    2. 'currency_transactions' table (New Multi-Currency Transactions)
    3. 'accounting' table (Operational Expenses/Manual Income)
    """

    def __init__(self, db):
        self.db = db

    def get(self, key, default=None):
        """Allow FinanceManager to be accessed partially like a dictionary for compatibility."""
        return getattr(self, key, default)

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            text = str(value).strip().replace(" ", "")
            if not text:
                return default
            if "," in text and "." in text:
                text = text.replace(",", "")
            elif "," in text:
                text = text.replace(",", ".")
            return float(text)
        except Exception:
            return default

    @staticmethod
    def _parse_sort_datetime(value):
        text = str(value or "").strip()
        if not text:
            return datetime.min
        text = text.replace("T", " ")
        if "." in text:
            text = text.split(".", 1)[0]
        formats = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d",
            "%d.%m.%Y %H:%M:%S",
            "%d.%m.%Y %H:%M",
            "%d.%m.%Y",
        )
        for fmt in formats:
            try:
                return datetime.strptime(text, fmt)
            except Exception:
                pass
        return datetime.min

    @classmethod
    def _sort_payload(cls, value):
        parsed = cls._parse_sort_datetime(value)
        if parsed == datetime.min:
            return "", 0.0
        return parsed.strftime("%Y-%m-%d %H:%M:%S"), parsed.timestamp()

    def _extract_original_amount(self, description, currency):
        if not description or currency == "TRY":
            return None
        text = str(description)
        currency = (currency or "TRY").upper()
        token_map = {
            "USD": [r"USD", r"\$"],
            "EUR": [r"EUR", r"\u20ac", "€"],
            "TRY": [r"TRY", r"TL", r"\u20ba", "₺"],
        }
        for token in token_map.get(currency, [re.escape(currency)]):
            match = re.search(rf"([0-9][0-9\.,]*)\s*{token}", text, flags=re.IGNORECASE)
            if match:
                return self._safe_float(match.group(1), None)
        return None

    def _infer_stock_purchase_meta(self, description, currency, amount_try, rate):
        text = str(description or "")
        match = re.search(
            r"(?:Stok\s+Al.m.|Stok\s+Ekleme(?:\s*\(K.s.*?\))?)\s*:?\s*(\d+(?:[\.,]\d+)?)\s*x\s*(.+?)(?:\||$)",
            text,
            re.IGNORECASE,
        )
        if not match:
            return currency, None, rate
        qty = self._safe_float(match.group(1), None)
        part_name = match.group(2).strip(" -")
        if not qty or not part_name:
            return currency, None, rate
        try:
            row = self.db.cursor.execute(
                "SELECT UPPER(COALESCE(currency,'TRY')), COALESCE(purchase_price,0) FROM parts WHERE name=? ORDER BY id DESC LIMIT 1",
                (part_name,),
            ).fetchone()
        except Exception:
            row = None
        if not row:
            return currency, None, rate
        part_currency = str(row[0] or "TRY").upper()
        unit_price = self._safe_float(row[1], 0.0)
        if unit_price <= 0:
            return part_currency, None, rate
        original_amount = round(unit_price * qty, 2)
        if part_currency == "TRY":
            inferred_rate = 1.0
        else:
            inferred_rate = rate or 1.0
            if (
                amount_try
                and original_amount
                and float(amount_try) != float(original_amount)
            ):
                inferred_rate = round(float(amount_try or 0) / original_amount, 4)
            if not inferred_rate or inferred_rate == 1.0:
                try:
                    from src.utils.exchange_rate_manager import ExchangeRateManager

                    inferred_rate = float(
                        ExchangeRateManager.get_current_rate(
                            self.db, part_currency, "selling"
                        )
                        or inferred_rate
                        or 1.0
                    )
                except Exception:
                    inferred_rate = inferred_rate or 1.0
        return part_currency, original_amount, inferred_rate

    def _get_date_range(self, period="month"):
        """Return inclusive datetime range strings for finance summaries."""
        now = datetime.now()
        period = str(period or "month").lower().strip()

        if period == "fiscal":
            start = None
            try:
                fiscal_start = str(
                    self.db.get_internal_setting("fiscal_year_start", "") or ""
                ).strip()
                if fiscal_start:
                    start = datetime.strptime(fiscal_start, "%Y-%m-%d")
                    if start > now:
                        start = None
            except Exception:
                start = None

            if start is None:
                start = now.replace(
                    month=1, day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:
                start = start.replace(hour=0, minute=0, second=0, microsecond=0)

            try:
                end = start.replace(year=start.year + 1) - timedelta(seconds=1)
            except ValueError:
                end = (start + timedelta(days=366)).replace(
                    hour=23, minute=59, second=59, microsecond=0
                )

            return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        elif period == "week":
            start = (now - timedelta(days=now.weekday())).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = (start + timedelta(days=6)).replace(
                hour=23, minute=59, second=59, microsecond=0
            )
        elif period == "year":
            start = now.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
            end = now.replace(
                month=12, day=31, hour=23, minute=59, second=59, microsecond=0
            )
        else:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start.month == 12:
                next_month = start.replace(year=start.year + 1, month=1, day=1)
            else:
                next_month = start.replace(month=start.month + 1, day=1)
            end = (next_month - timedelta(seconds=1)).replace(microsecond=0)

        return start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _normalized_category(value):
        return str(value or "").strip().lower()

    def _is_mirrored_customer_income(self, entry):
        if not entry:
            return False
        if str(entry.get("type") or "").strip().lower() != "gelir":
            return False
        category = self._normalized_category(entry.get("category"))
        mirrored_categories = {"tahsilat", "satış", "satis", "servis geliri"}
        return bool(entry.get("customer_id")) and category in mirrored_categories

    def _is_opening_entry(self, category=None, description=None, entry_type=None):
        category_text = self._normalized_category(category)
        description_text = str(description or "").strip().lower()
        type_text = str(entry_type or "").strip().lower()
        if type_text == "acilis":
            return True
        if "devir" in category_text or "acilis" in category_text:
            return True
        return "[fiscal_opening]" in description_text

    def _calculate_revenue(self, start_date, end_date):
        total = 0.0
        try:
            row = self.db.cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(try_equivalent, amount)), 0)
                FROM currency_transactions
                WHERE transaction_type = 'DEBIT'
                  AND created_at BETWEEN ? AND ?
                """,
                (start_date, end_date),
            ).fetchone()
            total += self._safe_float(row[0] if row else 0.0)
        except Exception as exc:
            logger.error(f"Revenue calc error (currency): {exc}")

        try:
            row = self.db.cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(try_equivalent, amount)), 0)
                FROM accounting
                WHERE type = 'Gelir'
                  AND date >= SUBSTR(?, 1, 10)
                  AND date <= SUBSTR(?, 1, 10)
                  AND LOWER(TRIM(COALESCE(type, ''))) != 'acilis'
                  AND NOT (
                        customer_id IS NOT NULL
                    AND LOWER(TRIM(COALESCE(category, ''))) IN ('tahsilat', 'satış', 'satis', 'servis geliri')
                  )
                """,
                (start_date, end_date),
            ).fetchone()
            total += self._safe_float(row[0] if row else 0.0)
        except Exception as exc:
            logger.error(f"Revenue calc error (accounting): {exc}")

        return total

    def _calculate_expenses(self, start_date, end_date):
        try:
            row = self.db.cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(try_equivalent, amount)), 0)
                FROM accounting
                WHERE type = 'Gider'
                  AND date >= SUBSTR(?, 1, 10)
                  AND date <= SUBSTR(?, 1, 10)
                  AND LOWER(TRIM(COALESCE(type, ''))) != 'acilis'
                """,
                (start_date, end_date),
            ).fetchone()
            return self._safe_float(row[0] if row else 0.0)
        except Exception as exc:
            logger.error(f"Expense calc error: {exc}")
            return 0.0

    def _calculate_hot_cash(self, start_date, end_date):
        income = 0.0
        expense = 0.0
        try:
            row = self.db.cursor.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN type = 'Gelir' THEN COALESCE(try_equivalent, amount) ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN type = 'Gider' THEN COALESCE(try_equivalent, amount) ELSE 0 END), 0)
                FROM accounting
                WHERE date >= SUBSTR(?, 1, 10)
                  AND date <= SUBSTR(?, 1, 10)
                  AND LOWER(TRIM(COALESCE(type, ''))) != 'acilis'
                  AND NOT (
                        type = 'Gelir'
                    AND customer_id IS NOT NULL
                    AND LOWER(TRIM(COALESCE(category, ''))) IN ('tahsilat', 'satış', 'satis', 'servis geliri')
                  )
                """,
                (start_date, end_date),
            ).fetchone()
            if row:
                income = self._safe_float(row[0])
                expense = self._safe_float(row[1])
        except Exception as exc:
            logger.error(f"Hot cash calc error (accounting): {exc}")

        try:
            row = self.db.cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(try_equivalent, amount)), 0)
                FROM accounting
                WHERE LOWER(TRIM(COALESCE(type, ''))) = 'acilis'
                  AND LOWER(TRIM(COALESCE(category, ''))) = 'banka devir bakiyesi'
                  AND date >= SUBSTR(?, 1, 10)
                  AND date <= SUBSTR(?, 1, 10)
                """,
                (start_date, end_date),
            ).fetchone()
            income += self._safe_float(row[0] if row else 0.0)
        except Exception as exc:
            logger.error(f"Hot cash calc error (opening): {exc}")

        try:
            row = self.db.cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(try_equivalent, amount)), 0)
                FROM currency_transactions
                WHERE transaction_type = 'CREDIT'
                  AND created_at BETWEEN ? AND ?
                """,
                (start_date, end_date),
            ).fetchone()
            income += self._safe_float(row[0] if row else 0.0)
        except Exception as exc:
            logger.error(f"Hot cash calc error (currency): {exc}")

        return income - expense

    def _calculate_pending_collections(self):
        totals = {"TRY": 0.0, "USD": 0.0, "EUR": 0.0}
        total_try = 0.0
        try:
            row = self.db.cursor.execute(
                """
                SELECT
                    SUM(
                        CASE WHEN UPPER(COALESCE(currency, 'TRY')) = 'TRY'
                            THEN ABS(current_balance) ELSE 0 END
                    ) AS try_balance,
                    SUM(
                        CASE WHEN UPPER(COALESCE(currency, 'TRY')) = 'USD'
                            THEN ABS(current_balance) ELSE 0 END
                    ) AS usd_balance,
                    SUM(
                        CASE WHEN UPPER(COALESCE(currency, 'TRY')) = 'EUR'
                            THEN ABS(current_balance) ELSE 0 END
                    ) AS eur_balance,
                    SUM(
                        CASE
                            WHEN UPPER(COALESCE(currency, 'TRY')) = 'TRY'
                                THEN ABS(current_balance)
                            ELSE ABS(current_balance)
                                * COALESCE(NULLIF(exchange_rate, 0), 1)
                        END
                    ) AS try_total
                FROM currency_transactions
                WHERE transaction_type = 'DEBIT'
                  AND current_balance < 0
                """
            ).fetchone()
            if row:
                totals["TRY"] = self._safe_float(row[0])
                totals["USD"] = self._safe_float(row[1])
                totals["EUR"] = self._safe_float(row[2])
                total_try = self._safe_float(row[3])
        except Exception as exc:
            logger.error(f"Pending collections calc error: {exc}")

        return total_try, {
            "tl_receivables": totals.get("TRY", 0.0),
            "usd_receivables": totals.get("USD", 0.0),
            "eur_receivables": totals.get("EUR", 0.0),
        }

    def get_financial_summary(self, period="month"):
        """
        Calculates Total Revenue, Total Expenses, and Net Profit for a given period.
        Refined for Turkish Market: Gross/Net Ciro, Hot Cash, Pocket Net.
        """
        self._repair_accounting_currency_values()
        start_date, end_date = self._get_date_range(period)

        gross_revenue = self._calculate_revenue(start_date, end_date)
        # Per-entry VAT rates are not reliable in the current ledger schema.
        # Keep revenue unchanged instead of inventing a blanket 20 percent VAT.
        net_revenue = gross_revenue
        expenses = self._calculate_expenses(start_date, end_date)
        hot_cash = self._calculate_hot_cash(start_date, end_date)
        service_revenue = self._calculate_service_revenue(start_date, end_date)
        # BUG FİX: calculate_income_tax artık KDV dâhil değerleri (gross) alıp kendi içinde nete çeviriyor.
        # Dashboard net reflects the actual ledger. Tax/VAT estimates stay in
        # the tax analysis because rows can use different rates or no VAT.
        pocket_net = gross_revenue - expenses
        pending, pending_details = self._calculate_pending_collections()
        uninvoiced_data = self._calculate_uninvoiced_stats(start_date, end_date)

        return {
            "gross_revenue": gross_revenue,
            "net_revenue": net_revenue,
            "expenses": expenses,
            "pocket_net": pocket_net,
            "hot_cash": hot_cash,
            "pending": pending,
            "pending_details": pending_details,
            "uninvoiced_count": uninvoiced_data["count"],
            "uninvoiced_sum": uninvoiced_data["sum"],
            "revenue": gross_revenue,
            "service_revenue": service_revenue,
        }

    def _calculate_uninvoiced_stats(self, start, end):
        """Henüz faturası kesilmemiş (is_invoiced=0) satışların istatistiği"""
        sql = """
            SELECT COUNT(*), SUM(try_equivalent) FROM currency_transactions 
            WHERE transaction_type = 'DEBIT' AND is_invoiced = 0
            AND created_at BETWEEN ? AND ?
        """
        res = self.db.cursor.execute(sql, (start, end)).fetchone()
        return {"count": res[0] or 0, "sum": res[1] or 0.0}

    def _calculate_service_revenue(self, start, end):
        """Sadece 'Servis Geliri' kategorisine ait gelirleri döndürür"""
        total = 0.0
        try:
            row = self.db.cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(try_equivalent, amount)), 0)
                FROM currency_transactions
                WHERE transaction_type = 'DEBIT'
                  AND created_at BETWEEN ? AND ?
                """,
                (start, end),
            ).fetchone()
            total += self._safe_float(row[0] if row else 0.0)
        except Exception as exc:
            logger.error(f"Service revenue calc error (currency): {exc}")

        try:
            row = self.db.cursor.execute(
                """
                SELECT COALESCE(SUM(COALESCE(try_equivalent, amount)), 0)
                FROM accounting
                WHERE type = 'Gelir'
                  AND category = 'Servis Geliri'
                  AND date >= SUBSTR(?, 1, 10)
                  AND date <= SUBSTR(?, 1, 10)
                  AND LOWER(TRIM(COALESCE(type, ''))) != 'acilis'
                  AND customer_id IS NULL
                """,
                (start, end),
            ).fetchone()
            total += self._safe_float(row[0] if row else 0.0)
        except Exception as exc:
            logger.error(f"Service revenue calc error (accounting): {exc}")
        return total

    def get_unified_ledger(self, limit=1000, offset=0):
        """
        Returns a merged list of latest transactions from all sources.
        Sorted by date DESC.
        """
        self._repair_accounting_currency_values()
        limit = max(1, int(limit or 1000))
        offset = max(0, int(offset or 0))
        source_limit = limit + offset
        ledger = []
        try:
            accounting_cols = (
                set(self.db._get_table_columns("accounting"))
                if hasattr(self.db, "_get_table_columns")
                else set()
            )
        except Exception:
            accounting_cols = set()

        start_date, end_date = self._get_date_range("fiscal")
        cur = self.db.conn.cursor()

        optional_accounting_fields = [
            "customer_id",
            "customer_name",
            "tracking_no",
            "ref_no",
            "selected_services",
            "payment_method",
            "bank_account_id",
            "currency",
            "exchange_rate",
            "try_equivalent",
            "original_amount",
            "product_service_id",
            "product_service_type",
            "created_at",
        ]
        accounting_select_parts = [
            "id",
            "date",
            "description",
            "amount",
            "type",
            "category",
        ]
        accounting_select_parts.extend(
            [field for field in optional_accounting_fields if field in accounting_cols]
        )
        cursor = cur.execute(
            f"SELECT {', '.join(accounting_select_parts)} FROM accounting WHERE date >= SUBSTR(?, 1, 10) AND date <= SUBSTR(?, 1, 10) ORDER BY date DESC LIMIT ?",
            (start_date, end_date, source_limit),
        )

        for row in cursor.fetchall():
            entry = dict(zip(accounting_select_parts, row))
            if self._is_mirrored_customer_income(entry):
                continue
            rid = entry.get("id")
            date = entry.get("date")
            created_at = entry.get("created_at")
            desc = entry.get("description") or ""
            amt = entry.get("amount") or 0
            ttype = entry.get("type")
            cat = entry.get("category") or ""
            is_opening = self._is_opening_entry(cat, desc, ttype)

            item_color = (
                "cyan" if is_opening else ("red" if ttype == "Gider" else "green")
            )
            status = "Devredildi" if is_opening else "Tamamlandı"
            type_label = "Açılış" if is_opening else ttype
            if not is_opening and "tahsilat" in self._normalized_category(cat):
                type_label = "Tahsilat"
            currency = (entry.get("currency") or "TRY").upper()
            amount_try = entry.get("try_equivalent")
            if amount_try is None:
                amount_try = amt
            rate = self._safe_float(entry.get("exchange_rate"), 1.0) or 1.0
            amount_foreign = 0.0

            if currency != "TRY":
                parsed_amount = self._extract_original_amount(desc, currency)
                if entry.get("original_amount") not in (None, "", 0, 0.0):
                    amount_foreign = self._safe_float(entry.get("original_amount"), 0.0)
                elif parsed_amount is not None:
                    amount_foreign = parsed_amount
                elif rate and rate != 1.0:
                    amount_foreign = round(float(amount_try or 0) / rate, 2)
                elif "Stok Al" in str(cat):
                    inferred_currency, inferred_amount, inferred_rate = (
                        self._infer_stock_purchase_meta(
                            desc, currency, amount_try, rate
                        )
                    )
                    currency = inferred_currency or currency
                    amount_foreign = inferred_amount or float(amt or 0)
                    rate = inferred_rate or rate or 1.0
                else:
                    amount_foreign = float(amt or 0)
                if (
                    amount_foreign
                    and (not rate or rate == 1.0)
                    and amount_try
                    and amount_try != amount_foreign
                ):
                    rate = round(float(amount_try or 0) / amount_foreign, 4)
            elif "Stok Al" in str(cat):
                inferred_currency, inferred_amount, inferred_rate = (
                    self._infer_stock_purchase_meta(desc, currency, amount_try, rate)
                )
                if inferred_currency != "TRY" and inferred_amount:
                    currency = inferred_currency
                    amount_foreign = inferred_amount
                    rate = inferred_rate or rate or 1.0

            final_desc = (
                desc
                if str(desc).strip().lower().startswith(str(cat).strip().lower())
                else f"{cat} - {desc}"
            )
            final_desc = final_desc.replace("Stok Alımı - Stok Alımı:", "Stok Alımı:")

            ledger.append(
                {
                    "id": rid,
                    "source": "accounting",
                    "date": date,
                    "description": final_desc,
                    "amount": amount_foreign,
                    "amount_try": amount_try,
                    "currency": currency,
                    "rate": rate,
                    "status": status,
                    "type_label": type_label,
                    "color_code": item_color,
                    "customer_id": entry.get("customer_id"),
                    "customer_name": entry.get("customer_name"),
                    "tracking_no": entry.get("tracking_no"),
                    "ref_no": entry.get("ref_no") or entry.get("tracking_no"),
                    "selected_services": entry.get("selected_services"),
                    "payment_method": entry.get("payment_method"),
                    "bank_account_id": entry.get("bank_account_id"),
                    "product_service_id": entry.get("product_service_id"),
                    "product_service_type": entry.get("product_service_type"),
                    "sort_key": self._sort_payload(created_at or date)[0],
                    "sort_ts": self._sort_payload(created_at or date)[1],
                }
            )


        # --- Merge currency_transactions (payments, collections) ---
        try:
            ct_cursor = cur.execute(
                """
                SELECT ct.id, ct.created_at, ct.description, ct.amount,
                       ct.currency, ct.transaction_type, ct.exchange_rate,
                       ct.try_equivalent, ct.current_balance, ct.customer_id,
                       ct.tracking_no, c.name AS customer_name
                FROM currency_transactions ct
                LEFT JOIN customers c ON c.id=ct.customer_id
                WHERE ct.created_at >= ? AND ct.created_at <= ?
                ORDER BY ct.created_at DESC LIMIT ?
                """,
                (start_date, end_date, source_limit),
            )
            for row in ct_cursor.fetchall():
                (
                    rid, date, desc, amt, curr, gtype, rate, try_val,
                    current_balance, customer_id, tracking_no, customer_name,
                ) = row
                curr = (curr or "TRY").upper()
                rate = self._safe_float(rate, 1.0) or 1.0
                try_val = self._safe_float(try_val, 0.0) or self._safe_float(amt, 0.0)
                amt_foreign = self._safe_float(amt, 0.0)
                if gtype == "DEBIT":
                    type_label = "Sat\u0131\u015f/Devir"
                    status = "Tamamland\u0131" if self._safe_float(current_balance, 0.0) >= 0 else "Tahsilat Bekliyor"
                    color = "green"
                elif gtype == "CREDIT":
                    type_label = "Tahsilat"
                    status = "Tamamland\u0131"
                    color = "blue"
                else:
                    type_label = gtype or "\u0130\u015flem"
                    status = "Tamamland\u0131"
                    color = "green"
                ledger.append({
                    "id": rid, "source": "currency", "date": date,
                    "description": desc or type_label,
                    "amount": amt_foreign, "amount_try": try_val,
                    "currency": curr, "rate": rate,
                    "status": status, "type_label": type_label, "color_code": color,
                    "customer_id": customer_id, "customer_name": customer_name,
                    "tracking_no": tracking_no, "ref_no": tracking_no, "selected_services": None,
                    "payment_method": None, "bank_account_id": None,
                    "product_service_id": None, "product_service_type": None,
                    "sort_key": self._sort_payload(date)[0],
                    "sort_ts": self._sort_payload(date)[1],
                })
        except Exception as exc:
            logger.error(f"Unified ledger currency_transactions error: {exc}")
        ledger.sort(key=lambda x: (x.get("sort_ts") or 0, x.get("id") or 0), reverse=True)
        return ledger[offset : offset + limit]

    def get_customer_ledger(self, customer_id, limit=100):
        """
        Returns a merged list of transactions for a specific customer.
        Sorted by date DESC.
        Format expanded for TR commercial view.
        """
        ledger = []

        cursor = self.db.cursor.execute(
            """
            SELECT id, created_at, description, amount, currency, transaction_type, exchange_rate, try_equivalent, current_balance
            FROM currency_transactions
            WHERE customer_id = ?
            ORDER BY created_at DESC LIMIT ?
            """,
            (customer_id, limit),
        )

        for row in cursor.fetchall():
            rid, date, desc, amt, curr, gtype, rate, try_val, current_balance = row
            label_type = "Satış" if gtype == "DEBIT" else "Tahsilat"
            if gtype == "DEBIT":
                status = (
                    "Tahsilat Bekliyor"
                    if self._safe_float(current_balance, 0.0) < 0
                    else "Tamamlandı"
                )
            else:
                status = "Tamamlandı"
            item_color = "blue"
            if gtype == "CREDIT":
                item_color = "green"

            ledger.append(
                {
                    "id": rid,
                    "source": "currency",
                    "date": date,
                    "category": "Satış" if gtype == "DEBIT" else "Tahsilat",
                    "description": desc,
                    "amount": amt,
                    "currency": curr,
                    "rate": rate,
                    "amount_try": try_val if try_val else amt,
                    "status": status,
                    "type_label": label_type,
                    "color_code": item_color,
                    "sort_key": self._sort_payload(date)[0],
                    "sort_ts": self._sort_payload(date)[1],
                }
            )

        cursor = self.db.cursor.execute(
            """
            SELECT id, date, description, amount, type, category
            FROM accounting
            WHERE customer_id = ?
            ORDER BY date DESC LIMIT ?
            """,
            (customer_id, limit),
        )

        for row in cursor.fetchall():
            rid, date, desc, amt, ttype, cat = row
            if self._is_mirrored_customer_income(
                {"type": ttype, "category": cat, "customer_id": customer_id}
            ):
                continue
            is_opening = self._is_opening_entry(cat, desc, ttype)
            item_color = (
                "cyan" if is_opening else ("red" if ttype == "Gider" else "green")
            )
            status = "Devredildi" if is_opening else "Tamamlandı"
            type_label = "Açılış" if is_opening else ttype

            ledger.append(
                {
                    "id": rid,
                    "source": "accounting",
                    "date": date,
                    "category": cat,
                    "description": desc,
                    "amount": 0,
                    "currency": "TRY",
                    "rate": 1.0,
                    "amount_try": amt,
                    "status": status,
                    "type_label": type_label,
                    "color_code": item_color,
                    "sort_key": self._sort_payload(date)[0],
                    "sort_ts": self._sort_payload(date)[1],
                }
            )

        ledger.sort(key=lambda x: (x.get("sort_ts") or 0, x.get("id") or 0), reverse=True)
        return ledger[:limit]

    def calculate_cogs(self, start_date=None, end_date=None):
        """
        Calculates Cost of Goods Sold (COGS) / Satılan Malın Maliyeti.
        Uses used_parts table which tracks parts used in services.
        """
        try:
            # Check if used_parts exists first
            self.db.cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='used_parts'"
            )
            if not self.db.cursor.fetchone():
                return 0.0

            # used_parts table has: id, tracking_no, part_name, price, created_at
            # We sum up the prices (which represent the cost of parts used)
            sql = """
                SELECT COALESCE(SUM(price), 0) as total_cogs
                FROM used_parts
            """
            params = []

            if start_date and end_date:
                sql += " WHERE created_at BETWEEN ? AND ?"
                params.extend([start_date, end_date])

            cursor = self.db.cursor.execute(sql, params)
            result = cursor.fetchone()
            total_cogs = result[0] if result else 0.0

            return total_cogs
        except Exception as e:
            logger.error(f"COGS calc error: {e}")
            return 0.0

    def calculate_income_tax(
        self, income, expense, period="year", tax_year=None, income_type="non_wage"
    ):
        """
        Calculates progressive income tax using the cached official GIB tariff.
        """
        # Calculate Year-to-Date COGS
        start, end = self._get_date_range(period)
        cogs = self.calculate_cogs(start, end)

        # VAT Separation (Tüm girişlerin KDV DAHİL (Gross) olduğunu varsayıyoruz)
        # Accounting rows do not store a reliable per-entry VAT rate. Applying
        # a blanket rate understates zero-rated and non-VAT expenses.
        income_excl_vat = float(income or 0)
        expense_excl_vat = float(expense or 0)
        vat_collected = 0.0
        vat_paid = 0.0

        # Ödenecek KDV (Tahmini): Tahsil Edilen KDV - Ödenen KDV
        # Eğer sonuç negatifse "0" görünmeli.
        vat_payable = 0.0

        # Net Kâr (Vergi Matrahı): Toplam Gelir (KDV Hariç) - Toplam Gider (KDV Hariç) - SMM
        profit = income_excl_vat - (expense_excl_vat + cogs)

        result_template = {
            "profit_base": profit,
            "income_excl_vat": income_excl_vat,
            "expense_excl_vat": expense_excl_vat,
            "vat_collected": vat_collected,
            "vat_paid": vat_paid,
            "vat_payable": vat_payable,
            "cogs": cogs,
            "brackets": [],
            "tax": 0.0,
            "net_after_tax": profit - vat_payable,  # Initial net before income tax
        }

        if profit <= 0:
            result_template["net_after_tax"] = profit - vat_payable
            return result_template

        tariff_result = IncomeTaxTariffService().calculate(
            profit,
            year=tax_year or datetime.now().year,
            income_type=income_type,
        )
        tax_total = tariff_result["tax"]
        breakdown = tariff_result["brackets"]

        # Vergi ve KDV Sonrası Net: Net Kâr - Hesaplanan Gelir Vergisi - Ödenecek KDV
        net_result = profit - tax_total - vat_payable

        result_template.update(
            {
                "tax": tax_total,
                "net_after_tax": net_result,
                "brackets": breakdown,
                "tax_year": tariff_result["year"],
                "income_type": tariff_result["income_type"],
                "tariff_source": tariff_result["source"],
                "tariff_updated_at": tariff_result["updated_at"],
            }
        )

        return result_template
