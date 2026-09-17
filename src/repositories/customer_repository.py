# -*- coding: utf-8 -*-

"""
Customer Repository

Handles all database operations for customer management.
"""

from typing import Optional, List, Dict, Any
from .base_repository import BaseRepository


class CustomerRepository(BaseRepository):
    """Repository for customer CRUD operations."""

    def _get_table_name(self) -> str:
        return 'customers'

    def create_customer(self, customer_data: Dict[str, Any]) -> int:
        """
        Create a new customer record.

        Args:
            customer_data: Dictionary containing customer fields

        Returns:
            ID of the created customer
        """
        # Set default values if not provided
        defaults = {
            'balance': 0.0,
            'currency_balance_try': 0.0,
            'currency_balance_usd': 0.0,
            'currency_balance_eur': 0.0,
            'risk_score': 'Düşük',
        }

        for key, value in defaults.items():
            if key not in customer_data:
                customer_data[key] = value

        return self.insert(customer_data)

    def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Find customer by phone number.

        Args:
            phone: Phone number to search

        Returns:
            Customer record or None
        """
        query = """
            SELECT * FROM customers
            WHERE (phone = ? OR phone2 = ?)
            AND (is_deleted = 0 OR is_deleted IS NULL)
            LIMIT 1
        """
        return self.fetch_one(query, (phone, phone))

    def get_customer_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Find customer by email.

        Args:
            email: Email address to search

        Returns:
            Customer record or None
        """
        query = """
            SELECT * FROM customers
            WHERE email = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            LIMIT 1
        """
        return self.fetch_one(query, (email,))

    def search_customers(
        self,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search customers by name, phone, or company.

        Args:
            search_term: Search string
            limit: Maximum results to return

        Returns:
            List of matching customers
        """
        query = """
            SELECT * FROM customers
            WHERE (
                name LIKE ? OR
                phone LIKE ? OR
                company_name LIKE ? OR
                email LIKE ?
            )
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY name ASC
            LIMIT ?
        """
        pattern = f"%{search_term}%"
        return self.fetch_many(query, (pattern, pattern, pattern, pattern, limit))

    def get_customers_with_balance(
        self,
        min_balance: float = 0.01
    ) -> List[Dict[str, Any]]:
        """
        Get customers with outstanding balance.

        Args:
            min_balance: Minimum balance threshold

        Returns:
            List of customers with balance
        """
        query = """
            SELECT * FROM customers
            WHERE ABS(balance) >= ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY ABS(balance) DESC
        """
        return self.fetch_many(query, (min_balance,))

    def update_balance(self, customer_id: int, amount: float) -> bool:
        """
        Update customer balance by adding amount.

        Args:
            customer_id: Customer ID
            amount: Amount to add (negative for credit)

        Returns:
            True if updated successfully
        """
        query = """
            UPDATE customers
            SET balance = balance + ?
            WHERE id = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """
        cursor = self.execute(query, (amount, customer_id))
        self._conn.commit()
        return cursor.rowcount > 0

    def get_customer_statistics(self) -> Dict[str, Any]:
        """
        Get aggregate statistics for customers.

        Returns:
            Dictionary with customer statistics
        """
        stats = {}

        # Total customers
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM customers
            WHERE is_deleted = 0 OR is_deleted IS NULL
        """)
        stats['total_customers'] = result['count'] if result else 0

        # Total balance
        result = self.fetch_one("""
            SELECT SUM(balance) as total FROM customers
            WHERE is_deleted = 0 OR is_deleted IS NULL
        """)
        stats['total_balance'] = result['total'] if result and result['total'] else 0.0

        # Customers with debt
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM customers
            WHERE balance < 0
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """)
        stats['customers_with_debt'] = result['count'] if result else 0

        # New customers this month
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM customers
            WHERE created_at >= date('now', 'start of month')
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """)
        stats['new_this_month'] = result['count'] if result else 0

        return stats

    def get_top_customers(
        self,
        limit: int = 10,
        by_revenue: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get top customers by revenue or transaction count.

        Args:
            limit: Number of customers to return
            by_revenue: If True, sort by revenue; else by transaction count

        Returns:
            List of top customers
        """
        if by_revenue:
            order_by = "total_revenue DESC"
        else:
            order_by = "transaction_count DESC"

        query = """
            SELECT
                c.*,
                COALESCE(SUM(CASE WHEN a.type = 'income' THEN a.amount ELSE 0 END), 0) as total_revenue,
                COUNT(a.id) as transaction_count
            FROM customers c
            LEFT JOIN accounting a ON c.id = a.customer_id
                AND (a.is_deleted = 0 OR a.is_deleted IS NULL)
            WHERE (c.is_deleted = 0 OR c.is_deleted IS NULL)
            GROUP BY c.id
            ORDER BY {order_by}
            LIMIT ?
        """.format(order_by=order_by)
        return self.fetch_many(query, (limit,))
