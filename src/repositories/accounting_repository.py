# -*- coding: utf-8 -*-

"""
Accounting Repository

Muhasebe ve finansal işlemler için veritabanı işlemleri.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from .base_repository import BaseRepository


class AccountingRepository(BaseRepository):
    """Muhasebe işlemleri için repository."""

    def _get_table_name(self) -> str:
        return 'accounting'

    def create_transaction(
        self,
        transaction_type: str,
        category: str,
        amount: float,
        description: str,
        customer_id: Optional[int] = None,
        customer_name: Optional[str] = None,
        bank_account_id: Optional[int] = None
    ) -> int:
        """
        Yeni finansal işlem oluştur.

        Args:
            transaction_type: 'income' (gelir) veya 'expense' (gider)
            category: İşlem kategorisi
            amount: Tutar
            description: Açıklama
            customer_id: Müşteri ID (opsiyonel)
            customer_name: Müşteri adı (opsiyonel)
            bank_account_id: Banka hesap ID (opsiyonel)

        Returns:
            Oluşturulan işlem ID'si
        """
        data = {
            'type': transaction_type,
            'category': category,
            'amount': amount,
            'description': description,
            'date': datetime.now().isoformat(),
            'customer_id': customer_id,
            'customer_name': customer_name,
            'bank_account_id': bank_account_id,
            'is_invoiced': 0,
            'is_deleted': 0,
        }
        return self.insert(data)

    def get_transactions_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """
        Müşteriye ait işlemleri getir.

        Args:
            customer_id: Müşteri ID

        Returns:
            İşlem listesi
        """
        query = """
            SELECT * FROM accounting
            WHERE customer_id = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY date DESC
        """
        return self.fetch_many(query, (customer_id,))

    def get_transactions_by_date_range(
        self,
        start_date: str,
        end_date: str,
        transaction_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Tarih aralığına göre işlemleri getir.

        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD)
            end_date: Bitiş tarihi (YYYY-MM-DD)
            transaction_type: 'income' veya 'expense' (opsiyonel)

        Returns:
            İşlem listesi
        """
        if transaction_type:
            query = """
                SELECT * FROM accounting
                WHERE date BETWEEN ? AND ?
                AND type = ?
                AND (is_deleted = 0 OR is_deleted IS NULL)
                ORDER BY date DESC
            """
            return self.fetch_many(query, (start_date, end_date, transaction_type))
        else:
            query = """
                SELECT * FROM accounting
                WHERE date BETWEEN ? AND ?
                AND (is_deleted = 0 OR is_deleted IS NULL)
                ORDER BY date DESC
            """
            return self.fetch_many(query, (start_date, end_date))

    def get_income_by_period(self, start_date: str, end_date: str) -> float:
        """
        Belirli dönemdeki toplam geliri hesapla.

        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi

        Returns:
            Toplam gelir
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM accounting
            WHERE date BETWEEN ? AND ?
            AND type = 'income'
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """
        result = self.fetch_one(query, (start_date, end_date))
        return result['total'] if result else 0.0

    def get_expense_by_period(self, start_date: str, end_date: str) -> float:
        """
        Belirli dönemdeki toplam gideri hesapla.

        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi

        Returns:
            Toplam gider
        """
        query = """
            SELECT COALESCE(SUM(amount), 0) as total
            FROM accounting
            WHERE date BETWEEN ? AND ?
            AND type = 'expense'
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """
        result = self.fetch_one(query, (start_date, end_date))
        return result['total'] if result else 0.0

    def get_balance_by_period(self, start_date: str, end_date: str) -> float:
        """
        Belirli dönemdeki net bakiyeyi hesapla.

        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi

        Returns:
            Net bakiye (gelir - gider)
        """
        income = self.get_income_by_period(start_date, end_date)
        expense = self.get_expense_by_period(start_date, end_date)
        return income - expense

    def get_category_summary(
        self,
        start_date: str,
        end_date: str,
        transaction_type: str
    ) -> List[Dict[str, Any]]:
        """
        Kategorilere göre özet rapor.

        Args:
            start_date: Başlangıç tarihi
            end_date: Bitiş tarihi
            transaction_type: 'income' veya 'expense'

        Returns:
            Kategori özet listesi
        """
        query = """
            SELECT
                category,
                COUNT(*) as count,
                COALESCE(SUM(amount), 0) as total
            FROM accounting
            WHERE date BETWEEN ? AND ?
            AND type = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            GROUP BY category
            ORDER BY total DESC
        """
        return self.fetch_many(query, (start_date, end_date, transaction_type))

    def get_monthly_summary(self, year: int) -> List[Dict[str, Any]]:
        """
        Aylık finansal özet.

        Args:
            year: Yıl

        Returns:
            Aylık özet listesi
        """
        query = """
            SELECT
                strftime('%m', date) as month,
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expense
            FROM accounting
            WHERE strftime('%Y', date) = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            GROUP BY month
            ORDER BY month
        """
        return self.fetch_many(query, (str(year),))

    def get_uninvoiced_transactions(self) -> List[Dict[str, Any]]:
        """
        Faturalanmamış işlemleri getir.

        Returns:
            Faturalanmamış işlem listesi
        """
        query = """
            SELECT * FROM accounting
            WHERE is_invoiced = 0
            AND type = 'income'
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY date DESC
        """
        return self.fetch_many(query)

    def mark_as_invoiced(self, transaction_id: int) -> bool:
        """
        İşlemi faturalanmış olarak işaretle.

        Args:
            transaction_id: İşlem ID

        Returns:
            Başarılı ise True
        """
        return self.update(transaction_id, {'is_invoiced': 1})

    def get_financial_summary(self) -> Dict[str, Any]:
        """
        Genel finansal özet.

        Returns:
            Finansal özet sözlüğü
        """
        summary = {}

        # Bugün
        today = datetime.now().strftime('%Y-%m-%d')
        summary['today_income'] = self.get_income_by_period(today, today)
        summary['today_expense'] = self.get_expense_by_period(today, today)

        # Bu ay
        result = self.fetch_one("""
            SELECT date('now', 'start of month') as start_date,
                   date('now', 'start of month', '+1 month', '-1 day') as end_date
        """)
        if result:
            summary['month_income'] = self.get_income_by_period(
                result['start_date'], result['end_date']
            )
            summary['month_expense'] = self.get_expense_by_period(
                result['start_date'], result['end_date']
            )

        # Bu yıl
        year = datetime.now().year
        result = self.fetch_one("""
            SELECT date('now', 'start of year') as start_date,
                   date('now', 'start of year', '+1 year', '-1 day') as end_date
        """)
        if result:
            summary['year_income'] = self.get_income_by_period(
                result['start_date'], result['end_date']
            )
            summary['year_expense'] = self.get_expense_by_period(
                result['start_date'], result['end_date']
            )

        # Toplam bakiye
        result = self.fetch_one("""
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) -
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as balance
            FROM accounting
            WHERE is_deleted = 0 OR is_deleted IS NULL
        """)
        summary['total_balance'] = result['balance'] if result else 0.0

        # Faturalanmamış tutar
        result = self.fetch_one("""
            SELECT COALESCE(SUM(amount), 0) as total
            FROM accounting
            WHERE is_invoiced = 0
            AND type = 'income'
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """)
        summary['uninvoiced_amount'] = result['total'] if result else 0.0

        return summary
