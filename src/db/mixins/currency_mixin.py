# -*- coding: utf-8 -*-

"""
Currency Mixin - Çoklu para birimi veritabanı işlemleri
"""

from datetime import datetime
from src.utils.logger import logger


class CurrencyMixin:
    """Çoklu para birimi işlemleri için mixin"""

    def get_last_currency_transaction_id(self):
        try:
            return int(getattr(self, "_last_currency_transaction_id", 0) or 0) or None
        except Exception:
            return None

    def add_currency_transaction(
        self,
        customer_id,
        amount,
        currency,
        transaction_type,
        exchange_rate=None,
        description="",
        tracking_no="",
        created_at=None,
        is_invoiced=0,
        commit=True,
    ):
        """
        Dövizli işlem ekle
        Args:
            exchange_rate: None ise TCMB'den otomatik çekilir
        """
        try:
            from src.utils.exchange_rate_manager import ExchangeRateManager

            self._last_currency_transaction_id = None

            # 1. Kur Belirle (TCMB Entegrasyonu)
            if not exchange_rate or exchange_rate == 0:
                if currency == "TRY":
                    exchange_rate = 1.0
                else:
                    # TCMB'den çek veya DB'deki son geçerli kuru al
                    ExchangeRateManager.update_rates_if_needed(self)
                    exchange_rate = ExchangeRateManager.get_current_rate(
                        self, currency, "selling"
                    )
                    if not exchange_rate:
                        raise ValueError(
                            f"Exchange rate unavailable for {currency}"
                        )

            # 2. TL Karşılığını hesapla (Tam hassasiyet)
            try_equivalent = round(amount * exchange_rate, 4)

            # 3. Tarih belirle
            if not created_at:
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Prevent over-collection: a credit cannot exceed the open
            # balance in the selected currency.
            if transaction_type == "CREDIT":
                # The new credit has not been inserted yet, so there is no
                # transaction id to exclude from the legacy allocation scan.
                payment_transaction_id = 0
                if tracking_no:
                    mismatched = self.cursor.execute(
                        """SELECT 1 FROM currency_transactions
                           WHERE customer_id=? AND tracking_no=?
                             AND transaction_type='DEBIT' AND UPPER(currency)<>UPPER(?)
                           LIMIT 1""",
                        (customer_id, tracking_no, currency),
                    ).fetchone()
                    if mismatched:
                        logger.warning(
                            "Payment rejected with mismatched currency: customer=%s tracking=%s currency=%s",
                            customer_id, tracking_no, currency,
                        )
                        return False
                open_row = self.cursor.execute(
                    """
                    SELECT COALESCE(SUM(
                        CASE
                          WHEN links.paid IS NOT NULL THEN MAX(d.amount-links.paid, 0)
                          WHEN legacy.paid IS NOT NULL THEN MAX(d.amount-legacy.paid, 0)
                          ELSE MAX(COALESCE(-d.current_balance, 0), 0)
                        END
                    ), 0)
                    FROM currency_transactions d
                    LEFT JOIN (
                        SELECT debt_txn_id, SUM(amount) AS paid
                        FROM payment_debt_links GROUP BY debt_txn_id
                    ) links ON links.debt_txn_id=d.id
                    LEFT JOIN (
                        SELECT d2.id, SUM(c.amount) AS paid
                        FROM currency_transactions d2
                        JOIN currency_transactions c
                          ON c.customer_id=d2.customer_id AND c.currency=d2.currency
                         AND c.transaction_type='CREDIT'
                         AND (c.tracking_no=d2.tracking_no OR c.tracking_no=d2.tracking_no || '-PAY')
                         AND c.id<>?
                         AND NOT EXISTS (
                             SELECT 1 FROM payment_debt_links pcl
                             WHERE pcl.payment_txn_id=c.id
                         )
                        WHERE d2.transaction_type='DEBIT'
                        GROUP BY d2.id
                    ) legacy ON legacy.id=d.id
                    WHERE d.customer_id=? AND d.currency=? AND d.transaction_type='DEBIT'
                    """,
                    (payment_transaction_id, customer_id, currency),
                ).fetchone()
                open_balance = float(open_row[0] or 0.0) if open_row else 0.0
                if float(amount) > open_balance + 0.009:
                    logger.warning(
                        "Payment rejected above open balance: customer=%s currency=%s amount=%s open=%s",
                        customer_id, currency, amount, open_balance,
                    )
                    return False

            # 4. Güncel Bakiyeyi Hesapla (Current Balance Engine)
            # Konvansiyon: Negatif bakiye = müşteri bize borçlu (Alacak)
            #              Pozitif bakiye = müşterinin fazla ödemesi (Borç - biz müşteriye borçluyuz)
            # DEBIT (satış/servis) → bakiye negatife gider (müşteri borçlanır)
            # CREDIT (tahsilat/ödeme) → bakiye sıfıra yaklaşır (borç kapanır)
            prev_balance = self.get_customer_currency_balance(customer_id, currency)
            if transaction_type == "DEBIT":
                new_balance = prev_balance - amount  # Müşteri borçlanır
            else:
                new_balance = prev_balance + amount  # Müşteri ödeme yapar, borç azalır

            # 5. Transaction kaydet
            self.cursor.execute(
                """
                INSERT INTO currency_transactions 
                (customer_id, transaction_type, amount, currency, exchange_rate, 
                 try_equivalent, description, tracking_no, created_at, current_balance, is_invoiced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    customer_id,
                    transaction_type,
                    amount,
                    currency,
                    exchange_rate,
                    try_equivalent,
                    description,
                    tracking_no,
                    created_at,
                    round(new_balance, 2),
                    is_invoiced,
                ),
            )
            transaction_id = self.cursor.lastrowid
            self._last_currency_transaction_id = transaction_id

            # 6. Müşteri özet tablosunu (balances) güncelle
            self.cursor.execute(
                """
                INSERT OR REPLACE INTO customer_currency_balances (customer_id, currency, balance, last_updated)
                VALUES (?, ?, ?, ?)
            """,
                (
                    customer_id,
                    currency,
                    round(new_balance, 2),
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )

            if commit:
                self.conn.commit()
            logger.info(
                f"Smart Transaction: {amount} {currency} (Rate: {exchange_rate}) for customer {customer_id}. New Balance: {new_balance}"
            )
            return True

        except Exception as e:
            self._last_currency_transaction_id = None
            logger.error(f"Error adding currency transaction: {e}")
            self.conn.rollback()
            return False

    def _update_customer_currency_balance(
        self, customer_id, currency, amount, transaction_type
    ):
        """Müşteri döviz bakiyesini güncelle"""
        try:
            # Mevcut bakiyeyi al
            result = self.cursor.execute(
                """
                SELECT balance FROM customer_currency_balances
                WHERE customer_id = ? AND currency = ?
            """,
                (customer_id, currency),
            ).fetchone()

            if result:
                current_balance = result[0]
            else:
                current_balance = 0
                # İlk kayıt oluştur
                self.cursor.execute(
                    """
                    INSERT INTO customer_currency_balances (customer_id, currency, balance, last_updated)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        customer_id,
                        currency,
                        0,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )

            # Yeni bakiyeyi hesapla
            # DEBIT (satış) → negatife gider, CREDIT (ödeme) → sıfıra yaklaşır
            if transaction_type == "DEBIT":
                new_balance = current_balance - amount
            else:  # CREDIT
                new_balance = current_balance + amount

            # Bakiyeyi güncelle
            self.cursor.execute(
                """
                UPDATE customer_currency_balances
                SET balance = ?, last_updated = ?
                WHERE customer_id = ? AND currency = ?
            """,
                (
                    new_balance,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    customer_id,
                    currency,
                ),
            )

        except Exception as e:
            logger.error(f"Error updating customer currency balance: {e}")
            raise

    def recalculate_all_customer_balances(self):
        """Tüm müşteri bakiyelerini transaction geçmişinden yeniden hesapla.
        Balance fix sonrası mevcut verileri düzeltmek için kullanılır.
        Konvansiyon: DEBIT → -amount (müşteri borçlanır), CREDIT → +amount (müşteri öder)
        """
        try:
            # Tüm müşteri+döviz çiftlerini bul
            pairs = self.cursor.execute("""
                SELECT DISTINCT customer_id, currency FROM currency_transactions
            """).fetchall()

            fixed_count = 0
            for pair in pairs:
                cid, curr = pair[0], pair[1]
                # Doğru bakiyeyi hesapla
                row = self.cursor.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN transaction_type='CREDIT' THEN amount ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN transaction_type='DEBIT' THEN amount ELSE 0 END), 0)
                    FROM currency_transactions
                    WHERE customer_id = ? AND currency = ?
                """,
                    (cid, curr),
                ).fetchone()

                correct_balance = round(row[0], 2) if row else 0.0

                self.cursor.execute(
                    """
                    INSERT OR REPLACE INTO customer_currency_balances
                    (customer_id, currency, balance, last_updated)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        cid,
                        curr,
                        correct_balance,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                fixed_count += 1

            self.conn.commit()
            logger.info(
                f"Recalculated balances for {fixed_count} customer-currency pairs"
            )
            return fixed_count
        except Exception as e:
            logger.error(f"Error recalculating balances: {e}")
            return 0

    def recalculate_customer_currency_balance(
        self,
        customer_id,
        currency,
        commit=True,
    ):
        """Rebuild one customer/currency balance from immutable transactions."""
        row = self.cursor.execute(
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
        correct_balance = round(float(row[0] or 0.0), 2) if row else 0.0
        self.cursor.execute(
            """
            INSERT OR REPLACE INTO customer_currency_balances
            (customer_id, currency, balance, last_updated)
            VALUES (?, ?, ?, ?)
            """,
            (
                customer_id,
                currency,
                correct_balance,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        if commit:
            self.conn.commit()
        return correct_balance

    def get_customer_currency_balance(self, customer_id, currency):
        """Müşterinin belirli döviz bakiyesini getir"""
        try:
            result = self.cursor.execute(
                """
                SELECT balance FROM customer_currency_balances
                WHERE customer_id = ? AND currency = ?
            """,
                (customer_id, currency),
            ).fetchone()

            return result[0] if result else 0.0
        except Exception as e:
            logger.error(f"Error getting customer currency balance: {e}")
            return 0.0

    def get_customer_all_balances(self, customer_id):
        """
        Müşterinin tüm döviz bakiyelerini getir
        Returns: dict {'TRY': 50000, 'USD': 1200, 'EUR': 500}
        """
        try:
            results = self.cursor.execute(
                """
                SELECT currency, balance FROM customer_currency_balances
                WHERE customer_id = ?
            """,
                (customer_id,),
            ).fetchall()

            balances = {}
            for row in results:
                if row[1] != 0:  # Sadece 0 olmayan bakiyeleri göster
                    balances[row[0]] = row[1]

            return balances
        except Exception as e:
            logger.error(f"Error getting customer all balances: {e}")
            return {}

    def get_customer_total_balance_in_try(self, customer_id):
        """
        Müşterinin tüm döviz bakiyelerini ve legacy (devices) borçlarını TL'ye çevirip topla
        Returns: float (TL cinsinden toplam borç)
        """
        try:
            from src.utils.exchange_rate_manager import ExchangeRateManager

            # 1. New Multi-Currency Balances
            balances = self.get_customer_all_balances(customer_id)
            total_try = 0.0

            for currency, amount in balances.items():
                if currency == "TRY":
                    total_try += amount
                else:
                    # Güncel kuru al
                    rate = ExchangeRateManager.get_current_rate(
                        self, currency, "selling"
                    )
                    if rate:
                        total_try += amount * rate
                    else:
                        logger.warning(f"No exchange rate found for {currency}")

            # 2. Legacy 'devices' table debts (price - payments in accounting)
            # COALESCE(paid_amount, 0) was causing crash as column doesn't exist
            # We must sum labor_cost + used_parts and subtract accounting payments
            self.cursor.execute(
                """
                SELECT tracking_no, labor_cost, cargo_fee
                FROM devices 
                WHERE customer_id = ?
            """,
                (customer_id,),
            )
            devices = self.cursor.fetchall()

            legacy_debt = 0.0
            for tno, labor, cargo_fee in devices:
                legacy_debt += labor or 0.0
                legacy_debt += cargo_fee or 0.0
                # Add used parts for this device
                self.cursor.execute(
                    "SELECT SUM(price) FROM used_parts WHERE tracking_no = ?", (tno,)
                )
                part_sum = self.cursor.fetchone()[0] or 0.0
                legacy_debt += part_sum

            return total_try + legacy_debt

        except Exception as e:
            logger.error(f"Error calculating total balance in TRY: {e}")
            return 0.0

    def get_currency_transactions(self, customer_id=None, currency=None, limit=100):
        """
        Dövizli işlemleri getir
        Args:
            customer_id: Müşteri ID (None ise tüm müşteriler)
            currency: Para birimi (None ise tüm para birimleri)
            limit: Maksimum kayıt sayısı
        Returns: list of dicts
        """
        try:
            query = "SELECT * FROM currency_transactions WHERE 1=1"
            params = []

            if customer_id:
                query += " AND customer_id = ?"
                params.append(customer_id)

            if currency:
                query += " AND currency = ?"
                params.append(currency)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            results = self.cursor.execute(query, params).fetchall()

            transactions = []
            for row in results:
                transactions.append(
                    {
                        "id": row[0],
                        "customer_id": row[1],
                        "transaction_type": row[2],
                        "amount": row[3],
                        "currency": row[4],
                        "exchange_rate": row[5],
                        "try_equivalent": row[6],
                        "description": row[7],
                        "tracking_no": row[8],
                        "created_at": row[9],
                    }
                )

            return transactions
        except Exception as e:
            logger.error(f"Error getting currency transactions: {e}")
            return []

    def apply_payment_to_debts(
        self,
        customer_id,
        payment_amount,
        currency,
        payment_transaction_id=None,
        selected_debt_ids=None,
        commit=True,
    ):
        """
        Tahsilatı seçili borç kalemlerine dağıt ve kalanı cari hesaba işle.

        Args:
            customer_id: Müşteri ID
            payment_amount: Ödeme tutarı
            currency: Para birimi
            payment_transaction_id: Ödeme işleminin ID'si (CREDIT kaydı)
            selected_debt_ids: Seçili borç kayıtlarının ID listesi (None ise otomatik dağıtım)

        Returns:
            dict: {'allocated': dağıtılan tutar, 'remaining': kalan tutar, 'linked_debts': bağlanan borçlar}
        """
        try:
            payment_amount = round(float(payment_amount or 0.0), 2)
            if payment_amount <= 0:
                raise ValueError("Payment amount must be positive")
            if not payment_transaction_id:
                raise ValueError("Payment transaction id is required")
            if not self.create_payment_debt_links_table(commit=commit):
                raise RuntimeError("Payment allocation schema is unavailable")

            payment_row = self.cursor.execute(
                """
                SELECT amount
                FROM currency_transactions
                WHERE id=? AND customer_id=? AND currency=?
                  AND transaction_type='CREDIT'
                """,
                (payment_transaction_id, customer_id, currency),
            ).fetchone()
            if not payment_row:
                raise ValueError("Payment transaction does not match the customer")

            payment_total = round(float(payment_row[0] or 0.0), 2)
            already_linked_row = self.cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM payment_debt_links
                WHERE payment_txn_id=?
                """,
                (payment_transaction_id,),
            ).fetchone()
            already_linked = round(
                float(already_linked_row[0] or 0.0)
                if already_linked_row
                else 0.0,
                2,
            )
            remaining_payment = round(
                max(0.0, min(payment_amount, payment_total) - already_linked),
                2,
            )
            allocated = 0.0
            linked_debts = []

            if not selected_debt_ids:
                debts = self.cursor.execute(
                    """
                    SELECT
                        ct.id,
                        ct.amount,
                        COALESCE(SUM(pdl.amount), 0) + COALESCE(legacy.total, 0)
                        AS paid_amount
                    FROM currency_transactions ct
                    LEFT JOIN payment_debt_links pdl
                      ON pdl.debt_txn_id=ct.id
                    LEFT JOIN (
                        SELECT d2.id, SUM(c.amount) AS total
                        FROM currency_transactions d2
                        JOIN currency_transactions c
                          ON c.customer_id=d2.customer_id AND c.currency=d2.currency
                         AND c.transaction_type='CREDIT'
                         AND (c.tracking_no=d2.tracking_no OR c.tracking_no=d2.tracking_no || '-PAY')
                        WHERE d2.transaction_type='DEBIT'
                        GROUP BY d2.id
                    ) legacy ON legacy.id=ct.id
                    WHERE ct.customer_id=? AND ct.currency=?
                      AND ct.transaction_type='DEBIT'
                    GROUP BY ct.id, ct.amount, ct.created_at
                    HAVING COALESCE(ct.amount, 0) -
                           (COALESCE(SUM(pdl.amount), 0) + COALESCE(legacy.total, 0)) > 0.009
                    ORDER BY ct.created_at ASC, ct.id ASC
                    """,
                    (customer_id, currency),
                ).fetchall()
            else:
                debt_ids = [
                    int(debt_id)
                    for debt_id in selected_debt_ids
                    if debt_id is not None
                ]
                if not debt_ids:
                    debts = []
                else:
                    placeholders = ",".join(["?"] * len(debt_ids))
                    debts = self.cursor.execute(
                        """
                        SELECT
                            ct.id,
                            ct.amount,
                            COALESCE(SUM(pdl.amount), 0) + COALESCE(legacy.total, 0)
                            AS paid_amount
                        FROM currency_transactions ct
                        LEFT JOIN payment_debt_links pdl
                          ON pdl.debt_txn_id=ct.id
                        LEFT JOIN (
                            SELECT d2.id, SUM(c.amount) AS total
                            FROM currency_transactions d2
                            JOIN currency_transactions c
                              ON c.customer_id=d2.customer_id AND c.currency=d2.currency
                             AND c.transaction_type='CREDIT'
                             AND (c.tracking_no=d2.tracking_no OR c.tracking_no=d2.tracking_no || '-PAY')
                             AND c.id<>?
                             AND NOT EXISTS (
                                 SELECT 1 FROM payment_debt_links pcl
                                 WHERE pcl.payment_txn_id=c.id
                             )
                            WHERE d2.transaction_type='DEBIT'
                            GROUP BY d2.id
                        ) legacy ON legacy.id=ct.id
                        WHERE ct.id IN ({placeholders})
                          AND ct.customer_id=?
                          AND ct.currency=?
                          AND ct.transaction_type='DEBIT'
                        GROUP BY ct.id, ct.amount, ct.created_at
                        HAVING COALESCE(ct.amount, 0) -
                               (COALESCE(SUM(pdl.amount), 0) + COALESCE(legacy.total, 0)) > 0.009
                        ORDER BY ct.created_at ASC, ct.id ASC
                        """.format(placeholders=placeholders),
                        (payment_transaction_id,) + tuple(debt_ids) + (customer_id, currency),
                    ).fetchall()

            for debt_id, debt_amount, linked_amount in debts:
                if remaining_payment <= 0:
                    break

                debt_remaining = round(
                    max(
                        0.0,
                        float(debt_amount or 0.0)
                        - float(linked_amount or 0.0),
                    ),
                    2,
                )
                payment_for_this = round(
                    min(remaining_payment, debt_remaining),
                    2,
                )

                if payment_for_this > 0:
                    new_debt_remaining = round(
                        max(0.0, debt_remaining - payment_for_this),
                        2,
                    )
                    self.cursor.execute(
                        """
                        INSERT INTO payment_debt_links 
                        (payment_txn_id, debt_txn_id, amount, created_at)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            payment_transaction_id,
                            debt_id,
                            payment_for_this,
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ),
                    )
                    self.cursor.execute(
                        """
                        UPDATE currency_transactions
                        SET current_balance = ?
                        WHERE id = ?
                    """,
                        (-new_debt_remaining, debt_id),
                    )

                    linked_debts.append(
                        {
                            "debt_id": debt_id,
                            "amount": payment_for_this,
                            "debt_remaining_before": debt_remaining,
                            "debt_remaining_after": new_debt_remaining,
                        }
                    )

                    allocated += payment_for_this
                    remaining_payment = round(
                        max(0.0, remaining_payment - payment_for_this),
                        2,
                    )

            self.recalculate_customer_currency_balance(
                customer_id,
                currency,
                commit=False,
            )
            if commit:
                self.conn.commit()

            return {
                "ok": True,
                "allocated": allocated,
                "remaining": remaining_payment,
                "linked_debts": linked_debts,
            }

        except Exception as e:
            logger.error(f"Error applying payment to debts: {e}")
            if commit:
                self.conn.rollback()
            return {
                "ok": False,
                "error": str(e),
                "allocated": 0,
                "remaining": payment_amount,
                "linked_debts": [],
            }

    def get_unpaid_debts(self, customer_id, currency=None):
        """Return each debt's unpaid amount, never its running account balance."""
        try:
            query = """
                SELECT ct.id, ct.amount, ct.currency, ct.description,
                       ct.tracking_no, ct.created_at,
                       -ROUND(
                           CASE WHEN paid.total IS NOT NULL
                                THEN MAX(ct.amount - paid.total, 0)
                                WHEN legacy.total IS NOT NULL
                                THEN MAX(ct.amount - legacy.total, 0)
                                ELSE MIN(MAX(ct.amount, 0), MAX(COALESCE(-ct.current_balance, 0), 0))
                           END, 2)
                FROM currency_transactions ct
                LEFT JOIN (
                    SELECT debt_txn_id, SUM(amount) AS total
                    FROM payment_debt_links GROUP BY debt_txn_id
                ) paid ON paid.debt_txn_id = ct.id
                LEFT JOIN (
                    SELECT d.id, SUM(c.amount) AS total
                    FROM currency_transactions d
                    JOIN currency_transactions c
                      ON c.customer_id=d.customer_id AND c.currency=d.currency
                     AND c.transaction_type='CREDIT'
                     AND (c.tracking_no=d.tracking_no OR c.tracking_no=d.tracking_no || '-PAY')
                    WHERE d.transaction_type='DEBIT'
                    GROUP BY d.id
                ) legacy ON legacy.id=ct.id
                WHERE ct.customer_id = ? AND ct.transaction_type = 'DEBIT'
                  AND ROUND(CASE WHEN paid.total IS NOT NULL THEN MAX(ct.amount - paid.total, 0)
                                 WHEN legacy.total IS NOT NULL THEN MAX(ct.amount - legacy.total, 0)
                                 ELSE MIN(MAX(ct.amount, 0), MAX(COALESCE(-ct.current_balance, 0), 0)) END, 2) > 0.009
            """
            params = [customer_id]

            if currency:
                query += " AND ct.currency = ?"
                params.append(currency)

            query += " ORDER BY ct.created_at DESC, ct.id DESC"

            return self.cursor.execute(query, params).fetchall()
        except Exception as e:
            logger.error(f"Error getting unpaid debts: {e}")
            return []

    def create_payment_debt_links_table(self, commit=True):
        """Ödeme-borç bağlantı tablosunu oluştur (yoksa)"""
        try:
            row = self.cursor.execute(
                """
                SELECT 1
                FROM sqlite_master
                WHERE type='table' AND name='payment_debt_links'
                LIMIT 1
                """
            ).fetchone()
            if row:
                return True
            logger.error(
                "Payment allocation schema is missing; startup migration required"
            )
            return False
        except Exception as e:
            logger.error(f"Error verifying payment debt links table: {e}")
            return False

    def auto_allocate_unlinked_customer_payments(self, customer_id=None, currency=None):
        """
        Linklenmemis tahsilatlari ayni musterinin acik borclarina FIFO mantigiyla dagit.
        """
        try:
            if not self.create_payment_debt_links_table():
                raise RuntimeError("Payment allocation schema is unavailable")

            customer_sql = "SELECT DISTINCT customer_id FROM currency_transactions"
            customer_params = []
            if customer_id is not None:
                customer_sql += " WHERE customer_id=?"
                customer_params.append(customer_id)

            customer_rows = self.cursor.execute(
                customer_sql, tuple(customer_params)
            ).fetchall() or []
            customers = [row[0] for row in customer_rows if row and row[0] is not None]

            allocations = 0
            affected_pairs = set()

            for cid in customers:
                currency_sql = """
                    SELECT DISTINCT currency
                    FROM currency_transactions
                    WHERE customer_id=?
                """
                currency_params = [cid]
                if currency:
                    currency_sql += " AND currency=?"
                    currency_params.append(currency)

                currency_rows = self.cursor.execute(
                    currency_sql, tuple(currency_params)
                ).fetchall() or []
                currencies = [row[0] for row in currency_rows if row and row[0]]

                for curr in currencies:
                    credit_rows = self.cursor.execute(
                        """
                        SELECT
                            ct.id,
                            ct.amount,
                            ct.created_at,
                            COALESCE(SUM(pdl.amount), 0) AS linked_amount
                        FROM currency_transactions ct
                        LEFT JOIN payment_debt_links pdl ON pdl.payment_txn_id = ct.id
                        WHERE ct.customer_id=?
                          AND ct.currency=?
                          AND ct.transaction_type='CREDIT'
                        GROUP BY ct.id, ct.amount, ct.created_at
                        HAVING COALESCE(ct.amount, 0) - COALESCE(SUM(pdl.amount), 0) > 0.009
                        ORDER BY ct.created_at ASC, ct.id ASC
                        """,
                        (cid, curr),
                    ).fetchall() or []

                    debt_rows = self.cursor.execute(
                        """
                        SELECT
                            ct.id,
                            ct.amount,
                            ct.created_at,
                            COALESCE(SUM(pdl.amount), 0) AS linked_amount
                        FROM currency_transactions ct
                        LEFT JOIN payment_debt_links pdl ON pdl.debt_txn_id = ct.id
                        WHERE ct.customer_id=?
                          AND ct.currency=?
                          AND ct.transaction_type='DEBIT'
                        GROUP BY ct.id, ct.amount, ct.created_at
                        HAVING COALESCE(ct.amount, 0) - COALESCE(SUM(pdl.amount), 0) > 0.009
                        ORDER BY ct.created_at ASC, ct.id ASC
                        """,
                        (cid, curr),
                    ).fetchall() or []

                    if not credit_rows or not debt_rows:
                        continue

                    debt_state = [
                        {
                            "id": row[0],
                            "remaining": round(
                                max(0.0, float(row[1] or 0.0) - float(row[3] or 0.0)), 2
                            ),
                        }
                        for row in debt_rows
                    ]

                    for credit in credit_rows:
                        payment_id = credit[0]
                        credit_remaining = round(
                            max(0.0, float(credit[1] or 0.0) - float(credit[3] or 0.0)),
                            2,
                        )
                        if credit_remaining <= 0.009:
                            continue

                        for debt in debt_state:
                            if credit_remaining <= 0.009:
                                break
                            if debt["remaining"] <= 0.009:
                                continue

                            allocate_amount = round(
                                min(credit_remaining, debt["remaining"]), 2
                            )
                            if allocate_amount <= 0.009:
                                continue

                            self.cursor.execute(
                                """
                                INSERT INTO payment_debt_links
                                (payment_txn_id, debt_txn_id, amount, created_at)
                                VALUES (?, ?, ?, ?)
                                """,
                                (
                                    payment_id,
                                    debt["id"],
                                    allocate_amount,
                                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                ),
                            )
                            debt["remaining"] = round(
                                max(0.0, debt["remaining"] - allocate_amount), 2
                            )
                            credit_remaining = round(
                                max(0.0, credit_remaining - allocate_amount), 2
                            )
                            allocations += 1
                            affected_pairs.add((cid, curr))

                    for debt in debt_state:
                        self.cursor.execute(
                            """
                            UPDATE currency_transactions
                            SET current_balance=?
                            WHERE id=?
                            """,
                            (round(-debt["remaining"], 2), debt["id"]),
                        )

            if allocations:
                for cid, curr in affected_pairs:
                    self.rebuild_customer_currency_balance(
                        cid,
                        curr,
                        commit=False,
                    )
                self.conn.commit()
            return allocations
        except Exception as e:
            logger.error(f"Error auto allocating customer payments: {e}")
            self.conn.rollback()
            return 0
