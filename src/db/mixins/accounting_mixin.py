# -*- coding: utf-8 -*-

"""
Accounting Mixin
Muhasebe ve mali işlemler ile ilgili database metodları
"""

from datetime import datetime
from src.utils.logger import logger


class AccountingMixin:
    """Muhasebe işlemleri için database metodları"""
    

    
    def get_transactions(self, bank_account_id=None):
        """Tüm işlemleri getir"""
        try:
            q = "SELECT * FROM accounting WHERE COALESCE(is_deleted, 0) = 0"
            params = []
            if bank_account_id is not None:
                q += " AND bank_account_id = ?"
                params.append(bank_account_id)
            q += " ORDER BY date DESC"
            self.cursor.execute(q, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error("Get transactions error: %s", e)
            return []
    
    def get_transaction(self, t_id):
        """Belirli bir işlemi getir"""
        self.cursor.execute("SELECT * FROM accounting WHERE id=? AND COALESCE(is_deleted, 0) = 0", (t_id,))
        return self.cursor.fetchone()
    
    def get_transaction_by_id(self, txn_id):
        """İşlemi ID ile getir (alias)"""
        return self.get_transaction(txn_id)
    

    
    def get_balance(self):
        """Genel bakiye hesapla"""
        try:
            self.cursor.execute("SELECT SUM(amount) FROM accounting WHERE type='Gelir' AND COALESCE(is_deleted, 0) = 0")
            income = self.cursor.fetchone()[0] or 0
            
            self.cursor.execute("SELECT SUM(amount) FROM accounting WHERE type='Gider' AND COALESCE(is_deleted, 0) = 0")
            expense = self.cursor.fetchone()[0] or 0
            
            return income - expense
        except Exception as e:
            logger.error("Get balance error: %s", e)
            return 0
    
    def get_cari_list(self, search_query=""):
        """Cari hesap özetini getir"""
        try:
            if search_query:
                q = f"%{search_query}%"
                self.cursor.execute("SELECT * FROM customers WHERE name LIKE ?", (q,))
            else:
                self.cursor.execute("SELECT * FROM customers")
            
            customers = self.cursor.fetchall()
            cari_list = []
            
            for c in customers:
                balance = self.get_customer_balance(c[0])
                cari_list.append({
                    'id': c[0],
                    'name': c[1],
                    'balance': balance
                })
            
            return cari_list
        except Exception as e:
            logger.error(f"Cari list error: {e}")
            return []
    
    def get_uninvoiced_transactions(self, customer_id):
        """Faturalanmamış satış işlemlerini (TL + Döviz) getir - dict listesi döner"""
        try:
            transactions = []

            # 1. TL İşlemleri (accounting tablosu)
            self.cursor.execute("""
                SELECT id, date, description, amount, category
                FROM accounting
                WHERE customer_id = ? AND type = 'Gelir' AND category = 'Satış' AND is_invoiced = 0
                AND COALESCE(is_deleted, 0) = 0
                ORDER BY date DESC
            """, (customer_id,))
            for r in self.cursor.fetchall():
                transactions.append({
                    'id': r[0], 'date': r[1], 'description': r[2],
                    'amount': r[3], 'currency': 'TRY', 'source': 'accounting',
                    'category': r[4] if len(r) > 4 else 'Satış'
                })

            # 2. Dövizli İşlemler (currency_transactions tablosu)
            try:
                self.cursor.execute("""
                    SELECT id, created_at, description, amount, currency, try_equivalent
                    FROM currency_transactions
                    WHERE customer_id = ? AND transaction_type = 'DEBIT' AND is_invoiced = 0
                    ORDER BY created_at DESC
                """, (customer_id,))
                for r in self.cursor.fetchall():
                    transactions.append({
                        'id': r[0], 'date': r[1], 'description': r[2],
                        'amount': r[3], 'currency': r[4], 'try_equivalent': r[5], 'source': 'currency'
                    })
            except Exception:
                pass  # currency_transactions tablosu henüz yoksa devam et

            return transactions
        except Exception as e:
            logger.error("Get uninvoiced transactions error: %s", e)
            return []
    
    def mark_transactions_as_invoiced(self, transaction_ids):
        """İşlemleri faturalandı olarak işaretle"""
        try:
            placeholders = ','.join(['?'] * len(transaction_ids))
            self.cursor.execute(
                f"UPDATE accounting SET is_invoiced=1 WHERE id IN ({placeholders})",
                transaction_ids
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Mark invoiced error: {e}")
            return False
