import json
from datetime import datetime

from src.utils.currency_helper import CurrencyHelper
from src.utils.logger import logger


class OfferAcceptanceError(RuntimeError):
    pass


def _value(row, key, index=None, default=None):
    if row is None:
        return default
    try:
        if hasattr(row, "keys") and key in row.keys():
            value = row[key]
            return default if value is None else value
    except Exception:
        pass
    if index is not None:
        try:
            value = row[index]
            return default if value is None else value
        except Exception:
            pass
    return default


def _decode_item(row):
    raw_payload = _value(row, "payload_json", 10, "") or ""
    try:
        payload = json.loads(raw_payload) if raw_payload else {}
    except Exception:
        payload = {}
    payload = payload if isinstance(payload, dict) else {}
    return {
        "item_id": _value(row, "item_id", 2),
        "type": str(
            _value(row, "item_type", 3, payload.get("type", "")) or ""
        ).strip().lower(),
        "service": str(
            _value(row, "service", 4, payload.get("service", "")) or ""
        ).strip(),
        "description": str(
            _value(row, "description", 5, payload.get("description", "")) or ""
        ).strip(),
        "brand": str(
            _value(row, "brand", 6, payload.get("brand", "")) or ""
        ).strip(),
        "qty": float(_value(row, "qty", 7, payload.get("qty", 1)) or 1),
        "price": float(
            _value(row, "unit_price", 8, payload.get("price", 0)) or 0
        ),
        "line_total": float(_value(row, "line_total", 9, 0) or 0),
    }


class OfferAcceptanceService:
    def __init__(self, db):
        self.db = db

    def _offer(self, offer_id):
        row = self.db.get_offer_record(int(offer_id))
        if not row:
            raise OfferAcceptanceError("Offer record was not found.")
        return row

    def _items(self, offer_id):
        rows = self.db.get_offer_items_detailed(int(offer_id)) or []
        return [_decode_item(row) for row in rows]

    def _validate_stock(self, items):
        required = {}
        for item in items:
            if item["type"] != "part" or not item["item_id"]:
                continue
            part_id = int(item["item_id"])
            quantity = float(item["qty"])
            if quantity <= 0:
                raise OfferAcceptanceError("Offer contains an invalid quantity.")
            required[part_id] = required.get(part_id, 0.0) + quantity

        for part_id, quantity in required.items():
            row = self.db.cursor.execute(
                "SELECT name, stock FROM parts WHERE id=?",
                (part_id,),
            ).fetchone()
            if not row:
                raise OfferAcceptanceError(
                    f"Stock item #{part_id} was not found."
                )
            stock = float(row[1] or 0)
            if stock < quantity:
                raise OfferAcceptanceError(
                    f"Insufficient stock: {row[0]} ({stock}/{quantity})."
                )

    @staticmethod
    def _description(offer_no, items):
        lines = [f"Ref: {offer_no} | Accepted offer"]
        for index, item in enumerate(items, 1):
            lines.append(
                f"{index}. {item['service'] or 'Item'} x{item['qty']:g}"
            )
            if item["description"]:
                lines.append(f"   {item['description']}")
        return "\n".join(lines)

    def _tracking_exists(self, tracking_no):
        row = self.db.cursor.execute(
            "SELECT id FROM currency_transactions WHERE tracking_no=? LIMIT 1",
            (tracking_no,),
        ).fetchone()
        return bool(row)

    def _table_exists(self, table_name):
        row = self.db.cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        return bool(row)

    def _rollback_processing(self, tracking_no):
        if not tracking_no:
            return
        transaction_ids = []
        balance_pairs = set()
        if self._table_exists("currency_transactions"):
            transaction_rows = self.db.cursor.execute(
                    """
                    SELECT id, customer_id, currency
                    FROM currency_transactions
                    WHERE tracking_no=?
                    """,
                    (tracking_no,),
                ).fetchall()
            transaction_ids = [int(row[0]) for row in transaction_rows]
            balance_pairs = {
                (int(row[1]), str(row[2] or "TRY").upper())
                for row in transaction_rows
                if row[1] is not None
            }

        if transaction_ids and self._table_exists("payment_debt_links"):
            placeholders = ", ".join("?" for _ in transaction_ids)
            self.db.cursor.execute(
                "DELETE FROM payment_debt_links "
                f"WHERE payment_txn_id IN ({placeholders}) "
                f"OR debt_txn_id IN ({placeholders})",
                tuple(transaction_ids + transaction_ids),
            )

        if self._table_exists("used_parts"):
            used_rows = self.db.cursor.execute(
                """
                SELECT part_id, COALESCE(quantity, 1)
                FROM used_parts
                WHERE tracking_no=? AND part_id IS NOT NULL
                """,
                (tracking_no,),
            ).fetchall()
            for part_id, quantity in used_rows:
                self.db.cursor.execute(
                    "UPDATE parts SET stock=COALESCE(stock, 0)+? WHERE id=?",
                    (int(quantity or 1), int(part_id)),
                )
            self.db.cursor.execute(
                "DELETE FROM used_parts WHERE tracking_no=?",
                (tracking_no,),
            )

        if self._table_exists("stock_movements"):
            self.db.cursor.execute(
                "DELETE FROM stock_movements WHERE description=?",
                (f"Servis Kullanimi: {tracking_no}",),
            )
        if self._table_exists("accounting"):
            self.db.cursor.execute(
                "DELETE FROM accounting WHERE tracking_no=?",
                (tracking_no,),
            )
        if self._table_exists("currency_transactions"):
            self.db.cursor.execute(
                "DELETE FROM currency_transactions WHERE tracking_no=?",
                (tracking_no,),
            )
            for customer_id, currency in balance_pairs:
                balance_row = self.db.cursor.execute(
                    """
                    SELECT
                        COALESCE(SUM(
                            CASE WHEN transaction_type='CREDIT' THEN amount ELSE 0 END
                        ), 0) -
                        COALESCE(SUM(
                            CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END
                        ), 0)
                    FROM currency_transactions
                    WHERE customer_id=? AND currency=?
                    """,
                    (customer_id, currency),
                ).fetchone()
                balance = round(float(balance_row[0] or 0), 2)
                self.db.cursor.execute(
                    """
                    INSERT OR REPLACE INTO customer_currency_balances
                    (customer_id, currency, balance, last_updated)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        customer_id,
                        currency,
                        balance,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
        self.db.conn.commit()

    @staticmethod
    def _normalized_status(value):
        return (
            str(value or "").strip().lower()
            .replace("\u0131", "i")
            .replace("\u015f", "s")
            .replace("\u0130", "i")
            .replace("\u015e", "s")
            .replace("\u0307", "")
        )

    def reverse_for_revision(self, offer_id, reason, reversed_by=""):
        """Reverse an accepted offer with traceable counter entries."""
        self.db.create_offer_tables()
        offer = self._offer(offer_id)
        status = self._normalized_status(_value(offer, "status", default=""))
        if status not in {"accepted", "processed", "islenmis", "kabul edildi"}:
            raise OfferAcceptanceError("Only a processed offer can be reversed.")

        reason = str(reason or "").strip()
        if len(reason) < 5:
            raise OfferAcceptanceError("A reversal reason is required.")
        original_tracking = str(
            _value(offer, "processed_tracking_no", default="") or ""
        ).strip()
        if not original_tracking:
            raise OfferAcceptanceError("Processed offer tracking was not found.")

        existing = self.db.cursor.execute(
            "SELECT id FROM offer_reversals WHERE offer_id=? AND original_tracking_no=?",
            (int(offer_id), original_tracking),
        ).fetchone()
        if existing:
            raise OfferAcceptanceError("This offer was already reversed.")

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        reversal_tracking = (
            f"{original_tracking}-REV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        offer_no = str(_value(offer, "offer_no", default=offer_id) or offer_id)
        customer_id = _value(offer, "customer_id")
        summary = {
            "currency_entries": 0,
            "accounting_entries": 0,
            "stock_entries": 0,
            "service_logs": 0,
        }

        try:
            self.db.conn.execute("BEGIN IMMEDIATE")

            currency_rows = []
            if self._table_exists("currency_transactions"):
                currency_rows = self.db.cursor.execute(
                    "SELECT * FROM currency_transactions WHERE tracking_no=? ORDER BY id",
                    (original_tracking,),
                ).fetchall()
            transaction_ids = [int(row["id"]) for row in currency_rows]
            if transaction_ids and self._table_exists("payment_debt_links"):
                marks = ",".join("?" for _ in transaction_ids)
                self.db.cursor.execute(
                    "DELETE FROM payment_debt_links "
                    f"WHERE payment_txn_id IN ({marks}) OR debt_txn_id IN ({marks})",
                    tuple(transaction_ids + transaction_ids),
                )

            for row in currency_rows:
                tx_type = str(row["transaction_type"] or "").upper()
                reverse_type = "CREDIT" if tx_type == "DEBIT" else "DEBIT"
                amount = float(row["amount"] or 0)
                currency = str(row["currency"] or "TRY").upper()
                balance_row = self.db.cursor.execute(
                    "SELECT balance FROM customer_currency_balances "
                    "WHERE customer_id=? AND currency=?",
                    (int(row["customer_id"]), currency),
                ).fetchone()
                current_balance = float(balance_row[0] or 0) if balance_row else 0.0
                new_balance = (
                    current_balance - amount
                    if reverse_type == "DEBIT"
                    else current_balance + amount
                )
                self.db.cursor.execute(
                    "INSERT INTO currency_transactions "
                    "(customer_id,transaction_type,amount,currency,exchange_rate,"
                    "try_equivalent,description,tracking_no,created_at,current_balance,is_invoiced) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,0)",
                    (
                        int(row["customer_id"]), reverse_type, amount, currency,
                        float(row["exchange_rate"] or 1),
                        float(row["try_equivalent"] or 0),
                        f"Offer reversal | Ref: {offer_no} | {reason}",
                        reversal_tracking, created_at, round(new_balance, 2),
                    ),
                )
                self.db.cursor.execute(
                    "INSERT OR REPLACE INTO customer_currency_balances "
                    "(customer_id,currency,balance,last_updated) VALUES (?,?,?,?)",
                    (int(row["customer_id"]), currency, round(new_balance, 2), created_at),
                )
                summary["currency_entries"] += 1

            if self._table_exists("accounting"):
                accounting_rows = self.db.cursor.execute(
                    "SELECT * FROM accounting WHERE tracking_no=? ORDER BY id",
                    (original_tracking,),
                ).fetchall()
                columns = [
                    str(item[1])
                    for item in self.db.cursor.execute("PRAGMA table_info(accounting)").fetchall()
                    if str(item[1]) not in {"id", "payment_no"}
                ]
                for row in accounting_rows:
                    values = {name: row[name] for name in columns}
                    old_type = str(values.get("type") or "")
                    values["type"] = "Gider" if old_type.casefold() == "gelir" else "Gelir"
                    values["category"] = "Islem Geri Alma"
                    values["description"] = (
                        f"Offer reversal | Ref: {offer_no} | {reason} | "
                        f"Original: {values.get('description') or ''}"
                    )
                    values["tracking_no"] = reversal_tracking
                    values["ref_no"] = offer_no
                    values["date"] = created_at[:10]
                    values["created_at"] = created_at
                    insert_columns = [name for name in columns if name in values]
                    marks = ",".join("?" for _ in insert_columns)
                    quoted = ",".join(f'"{name}"' for name in insert_columns)
                    self.db.cursor.execute(
                        f"INSERT INTO accounting ({quoted}) VALUES ({marks})",
                        tuple(values[name] for name in insert_columns),
                    )
                    summary["accounting_entries"] += 1

            if self._table_exists("used_parts"):
                used_rows = self.db.cursor.execute(
                    "SELECT part_id,COALESCE(SUM(quantity),0),MAX(part_name) "
                    "FROM used_parts WHERE tracking_no=? AND part_id IS NOT NULL GROUP BY part_id",
                    (original_tracking,),
                ).fetchall()
                for part_id, quantity, part_name in used_rows:
                    stock_row = self.db.cursor.execute(
                        "SELECT COALESCE(stock,0) FROM parts WHERE id=?",
                        (int(part_id),),
                    ).fetchone()
                    current_stock = float(stock_row[0] or 0) if stock_row else 0.0
                    if not self.db.record_stock_movement(
                        int(part_id), float(quantity or 0), current_stock=current_stock,
                        type_val="Giris",
                        desc=(
                            f"Offer reversal: {offer_no} | {part_name or part_id} | "
                            f"Original: {original_tracking}"
                        ),
                        commit=False,
                    ):
                        raise OfferAcceptanceError("Stock reversal could not be recorded.")
                    summary["stock_entries"] += 1

            service_tracking = str(_value(offer, "project_name", default="") or "").strip()
            if service_tracking and self._table_exists("devices"):
                device = self.db.cursor.execute(
                    "SELECT tracking_no FROM devices WHERE tracking_no=? LIMIT 1",
                    (service_tracking,),
                ).fetchone()
                if device and self._table_exists("service_logs"):
                    self.db.cursor.execute(
                        "INSERT INTO service_logs "
                        "(device_tracking_no,log_type,message,created_at,user) VALUES (?,?,?,?,?)",
                        (
                            service_tracking, "Offer Revision",
                            f"Offer {offer_no} reversed for revision. Reason: {reason}",
                            created_at, str(reversed_by or "System"),
                        ),
                    )
                    summary["service_logs"] += 1

            self.db.cursor.execute(
                "INSERT INTO offer_reversals "
                "(offer_id,original_tracking_no,reversal_tracking_no,reason,reversed_by,payload_json,created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    int(offer_id), original_tracking, reversal_tracking, reason,
                    str(reversed_by or ""), json.dumps(summary, ensure_ascii=True), created_at,
                ),
            )
            self.db.cursor.execute(
                "UPDATE offers SET status='revision_pending',processed_tracking_no='',"
                "accepted_at=NULL,accepted_by='',accepted_payment=0,accepted_payment_try=0,"
                "remaining_amount=0,remaining_try=0,payment_method='',processing_error='',"
                "updated_at=? WHERE id=?",
                (created_at, int(offer_id)),
            )
            if self._table_exists("audit_logs"):
                self.db.cursor.execute(
                    "INSERT INTO audit_logs "
                    "(user_id,table_name,action,details,created_at) VALUES (?,?,?,?,?)",
                    (
                        str(reversed_by or "System"), "offers", "REVERSE_FOR_REVISION",
                        f"Offer {offer_no} | Original: {original_tracking} | Reason: {reason}",
                        created_at,
                    ),
                )
            self.db.conn.commit()
        except Exception:
            self.db.conn.rollback()
            raise

        return {
            "offer_id": int(offer_id),
            "offer_no": offer_no,
            "original_tracking_no": original_tracking,
            "reversal_tracking_no": reversal_tracking,
            "customer_id": customer_id,
            **summary,
        }

    def accept(
        self,
        offer_id,
        payment_amount=0.0,
        payment_method="Cari Hesap",
        accepted_by="",
    ):
        offer = self._offer(offer_id)
        status = str(_value(offer, "status", default="") or "").strip().lower()
        status = (
            status.replace("\u0131", "i")
            .replace("\u015f", "s")
            .replace("\u0130", "i")
            .replace("\u015e", "s")
            .replace("\u0307", "")
        )
        previous_tracking = str(
            _value(offer, "processed_tracking_no", default="") or ""
        ).strip()
        if status in {"accepted", "processed", "islenmis", "kabul edildi"}:
            raise OfferAcceptanceError("This offer was already processed.")
        if previous_tracking and self._tracking_exists(previous_tracking):
            raise OfferAcceptanceError(
                "This offer has an existing financial movement and cannot be processed twice."
            )

        customer_id = _value(offer, "customer_id")
        if not customer_id:
            raise OfferAcceptanceError("A registered customer is required.")
        customer_row = self.db.cursor.execute(
            "SELECT id, name FROM customers WHERE id=?",
            (int(customer_id),),
        ).fetchone()
        if not customer_row:
            raise OfferAcceptanceError("Customer record was not found.")

        offer_no = str(_value(offer, "offer_no", default=f"OFF-{offer_id}") or "")
        currency = str(_value(offer, "currency_code", default="TRY") or "TRY").upper()
        exchange_rate = float(_value(offer, "exchange_rate", default=1.0) or 1.0)
        total = round(float(_value(offer, "total", default=0) or 0), 2)
        total_try = round(
            float(_value(offer, "total_try", default=total * exchange_rate) or 0),
            2,
        )
        payment_amount = round(float(payment_amount or 0), 2)
        if total <= 0:
            raise OfferAcceptanceError("Offer total must be greater than zero.")
        if payment_amount < 0 or payment_amount > total:
            raise OfferAcceptanceError(
                "Down payment must be between zero and the offer total."
            )
        if currency != "TRY" and exchange_rate <= 0:
            raise OfferAcceptanceError("Offer exchange rate is invalid.")

        items = self._items(offer_id)
        if not items:
            raise OfferAcceptanceError("Offer has no line items.")
        self._validate_stock(items)

        now_key = datetime.now().strftime("%Y%m%d%H%M%S")
        tracking_no = f"OFFER-{int(offer_id)}-{now_key}"
        payment_try = round(payment_amount * exchange_rate, 2)
        remaining = round(total - payment_amount, 2)
        remaining_try = round(total_try - payment_try, 2)
        description = self._description(offer_no, items)

        self.db.update_offer_processing_state(
            offer_id,
            "processing",
            tracking_no=tracking_no,
            accepted_by=accepted_by,
            payment_amount=payment_amount,
            payment_try=payment_try,
            remaining_amount=remaining,
            remaining_try=remaining_try,
            payment_method=payment_method,
        )

        try:
            debit_ok = self.db.add_currency_transaction(
                customer_id=int(customer_id),
                amount=total,
                currency=currency,
                transaction_type="DEBIT",
                exchange_rate=exchange_rate,
                description=description,
                tracking_no=tracking_no,
            )
            if not debit_ok:
                raise OfferAcceptanceError(
                    "Customer debt movement could not be created."
                )
            debt_transaction_id = self.db.get_last_currency_transaction_id()

            self.db.add_transaction(
                t_type="Gelir",
                category="Satis",
                amount=total,
                description=description,
                customer_name=str(customer_row[1] or ""),
                customer_id=int(customer_id),
                payment_method=payment_method,
                tracking_no=tracking_no,
                ref_no=offer_no,
                selected_services=items,
                currency=currency,
                original_amount=total,
                exchange_rate=exchange_rate,
            )

            material_cost_try = 0.0
            material_lines = []
            for item in items:
                if item["type"] != "part" or not item["item_id"]:
                    continue
                quantity = float(item["qty"])
                part_row = self.db.cursor.execute(
                    """
                    SELECT purchase_price, COALESCE(currency, 'TRY'), name
                    FROM parts
                    WHERE id=?
                    """,
                    (int(item["item_id"]),),
                ).fetchone()
                if not self.db.use_part(
                    int(item["item_id"]),
                    quantity,
                    tracking_no,
                ):
                    raise OfferAcceptanceError(
                        f"Stock could not be deducted: {item['service']}."
                    )
                purchase_price = float(part_row[0] or 0) if part_row else 0.0
                part_currency = str(part_row[1] or "TRY").upper() if part_row else "TRY"
                cost_rate = (
                    1.0
                    if part_currency == "TRY"
                    else CurrencyHelper.require_rate(self.db, part_currency)
                )
                material_cost_try += purchase_price * cost_rate * quantity
                material_lines.append(
                    f"{item['service'] or part_row[2]} x{quantity}"
                )

            if material_cost_try > 0:
                self.db.add_transaction(
                    t_type="Gider",
                    category="Satilan Malin Maliyeti",
                    amount=round(material_cost_try, 2),
                    description=(
                        f"Offer cost | Ref: {offer_no}\n"
                        + "\n".join(material_lines)
                    ),
                    customer_name=str(customer_row[1] or ""),
                    customer_id=int(customer_id),
                    tracking_no=tracking_no,
                    ref_no=offer_no,
                    currency="TRY",
                    original_amount=round(material_cost_try, 2),
                )

            if payment_amount > 0:
                credit_ok = self.db.add_currency_transaction(
                    customer_id=int(customer_id),
                    amount=payment_amount,
                    currency=currency,
                    transaction_type="CREDIT",
                    exchange_rate=exchange_rate,
                    description=f"Down payment | Ref: {offer_no}",
                    tracking_no=tracking_no,
                )
                if not credit_ok:
                    raise OfferAcceptanceError(
                        "Down payment movement could not be created."
                    )
                payment_transaction_id = self.db.get_last_currency_transaction_id()
                self.db.create_payment_debt_links_table()
                self.db.apply_payment_to_debts(
                    customer_id=int(customer_id),
                    payment_amount=payment_amount,
                    currency=currency,
                    payment_transaction_id=payment_transaction_id,
                    selected_debt_ids=[debt_transaction_id]
                    if debt_transaction_id
                    else None,
                )

            self.db.update_offer_processing_state(
                offer_id,
                "accepted",
                tracking_no=tracking_no,
                accepted_by=accepted_by,
                payment_amount=payment_amount,
                payment_try=payment_try,
                remaining_amount=remaining,
                remaining_try=remaining_try,
                payment_method=payment_method,
            )
            return {
                "offer_id": int(offer_id),
                "tracking_no": tracking_no,
                "currency": currency,
                "total": total,
                "payment": payment_amount,
                "remaining": remaining,
                "total_try": total_try,
                "payment_try": payment_try,
                "remaining_try": remaining_try,
            }
        except Exception as exc:
            logger.exception("Offer acceptance failed")
            try:
                self._rollback_processing(tracking_no)
            except Exception:
                logger.exception("Offer acceptance rollback failed")
            self.db.update_offer_processing_state(
                offer_id,
                "processing_error",
                tracking_no=tracking_no,
                error=str(exc),
                accepted_by=accepted_by,
                payment_amount=payment_amount,
                payment_try=payment_try,
                remaining_amount=remaining,
                remaining_try=remaining_try,
                payment_method=payment_method,
            )
            if isinstance(exc, OfferAcceptanceError):
                raise
            raise OfferAcceptanceError(str(exc)) from exc
