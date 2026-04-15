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
                        logger.warning(
                            f"No rate found for {currency}, defaulting to 1.0"
                        )
                        exchange_rate = 1.0

            # 2. TL Karşılığını hesapla (Tam hassasiyet)
            try_equivalent = round(amount * exchange_rate, 4)

            # 3. Tarih belirle
            if not created_at:
                created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            allocated = 0.0
            linked_debts = []

            # Eğer seçili borç yoksa, açık borçları getir (en eski başlayarak)
            if not selected_debt_ids:
                debts = self.cursor.execute(
                    """
                    SELECT id, amount, current_balance 
                    FROM currency_transactions 
                    WHERE customer_id = ? AND currency = ? AND transaction_type = 'DEBIT'
                    AND (current_balance < 0 OR current_balance IS NULL)
                    ORDER BY created_at ASC
                """,
                    (customer_id, currency),
                ).fetchall()
            else:
                # Seçili borçları getir
                placeholders = ",".join(["?" for _ in selected_debt_ids])
                debts = self.cursor.execute(
                    """
                    SELECT id, amount, current_balance 
                    FROM currency_transactions 
                    WHERE id IN ({placeholders})
                      AND customer_id = ?
                      AND currency = ?
                      AND transaction_type = 'DEBIT'
                    ORDER BY created_at ASC
                """.format(placeholders=placeholders),
                    tuple(selected_debt_ids) + (customer_id, currency),
                ).fetchall()

            remaining_payment = payment_amount

            for debt_id, debt_amount, current_balance in debts:
                if remaining_payment <= 0:
                    break

                # Borç kalanını hesapla (pozitif değer = ödenmesi gereken)
                if current_balance is None:
                    debt_remaining = debt_amount
                elif current_balance < 0:
                    # Negatif bakiye = kapanmamış borç
                    debt_remaining = abs(current_balance)
                else:
                    continue  # Bu borç zaten kapanmış

                # Bu borca ne kadar ödeme yapılabilir
                payment_for_this = min(remaining_payment, debt_remaining)

                if payment_for_this > 0:
                    if current_balance is None:
                        new_debt_balance = round(
                            (-float(debt_amount or 0)) + payment_for_this, 2
                        )
                    else:
                        new_debt_balance = round(
                            float(current_balance or 0) + payment_for_this, 2
                        )
                    # Ödeme-borç bağlantısını kaydet
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
                        (new_debt_balance, debt_id),
                    )

                    linked_debts.append(
                        {
                            "debt_id": debt_id,
                            "amount": payment_for_this,
                            "debt_remaining_before": debt_remaining,
                            "debt_remaining_after": max(0.0, abs(new_debt_balance))
                            if new_debt_balance < 0
                            else 0.0,
                        }
                    )

                    allocated += payment_for_this
                    remaining_payment -= payment_for_this

            try:
                self.recalculate_all_customer_balances()
            except Exception as recalc_err:
                logger.warning(
                    f"Balance recalc after payment allocation skipped: {recalc_err}"
                )

            self.conn.commit()

            return {
                "allocated": allocated,
                "remaining": remaining_payment,
                "linked_debts": linked_debts,
            }

        except Exception as e:
            logger.error(f"Error applying payment to debts: {e}")
            self.conn.rollback()
            return {"allocated": 0, "remaining": payment_amount, "linked_debts": []}

    def get_unpaid_debts(self, customer_id, currency=None):
        """
        Müşterinin ödenmemiş borç kalemlerini getir.

        Returns:
            list: [(id, amount, currency, description, tracking_no, created_at, current_balance), ...]
        """
        try:
            query = """
                SELECT id, amount, currency, description, tracking_no, created_at, current_balance
                FROM currency_transactions 
                WHERE customer_id = ? AND transaction_type = 'DEBIT'
                AND (current_balance < 0 OR current_balance IS NULL)
            """
            params = [customer_id]

            if currency:
                query += " AND currency = ?"
                params.append(currency)

            query += " ORDER BY created_at DESC"

            return self.cursor.execute(query, params).fetchall()
        except Exception as e:
            logger.error(f"Error getting unpaid debts: {e}")
            return []

    def create_payment_debt_links_table(self):
        """Ödeme-borç bağlantı tablosunu oluştur (yoksa)"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS payment_debt_links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    payment_txn_id INTEGER NOT NULL,
                    debt_txn_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (payment_txn_id) REFERENCES currency_transactions(id),
                    FOREIGN KEY (debt_txn_id) REFERENCES currency_transactions(id)
                )
            """)
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_payment_debt_payment 
                ON payment_debt_links(payment_txn_id)
            """)
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_payment_debt_debt 
                ON payment_debt_links(debt_txn_id)
            """)
            self.conn.commit()
            logger.info("Payment debt links table created/verified")
        except Exception as e:
            logger.error(f"Error creating payment debt links table: {e}")
