"""
Unit of Work Pattern Implementation

Manages database transactions across multiple repositories,
ensuring data consistency for complex operations.
"""

import sqlite3
import logging
from typing import Optional, Dict, Type
from contextlib import contextmanager

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UnitOfWork:
    """
    Unit of Work pattern for transaction management.

    Ensures that multiple database operations either all succeed
    or all fail together (atomic transactions).

    Example:
        with UnitOfWork(connection) as uow:
            customer_repo = uow.get_repository(CustomerRepository)
            accounting_repo = uow.get_repository(AccountingRepository)

            customer = customer_repo.create({...})
            accounting_repo.create_transaction({
                'customer_id': customer['id'],
                ...
            })

            # Both operations committed together
            # If either fails, both are rolled back
    """

    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize Unit of Work.

        Args:
            connection: SQLite database connection
        """
        self._conn = connection
        self._repositories: Dict[Type[BaseRepository], BaseRepository] = {}
        self._in_transaction = False

    def __enter__(self):
        """Start transaction when entering context."""
        self.begin()
        return self

    def __exit__(self, exc_type, exc_val, _exc_tb):
        """Commit or rollback on exit."""
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
            logger.error(f"Transaction rolled back due to: {exc_val}")
        return False

    def begin(self):
        """Begin a new transaction."""
        if not self._in_transaction:
            self._conn.execute("BEGIN")
            self._in_transaction = True
            logger.debug("Transaction started")

    def commit(self):
        """Commit the current transaction."""
        if self._in_transaction:
            self._conn.commit()
            self._in_transaction = False
            logger.debug("Transaction committed")

    def rollback(self):
        """Rollback the current transaction."""
        if self._in_transaction:
            self._conn.rollback()
            self._in_transaction = False
            logger.debug("Transaction rolled back")

    def get_repository(self, repository_class: Type[BaseRepository]) -> BaseRepository:
        """
        Get or create a repository instance.

        Args:
            repository_class: Repository class to instantiate

        Returns:
            Repository instance
        """
        if repository_class not in self._repositories:
            self._repositories[repository_class] = repository_class(self._conn)
        return self._repositories[repository_class]

    def execute(self, query: str, parameters: Optional[tuple] = None):
        """
        Execute raw SQL within the transaction.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            SQLite cursor
        """
        cursor = self._conn.cursor()
        if parameters:
            cursor.execute(query, parameters)
        else:
            cursor.execute(query)
        return cursor

    def query_one(self, query: str, parameters: Optional[tuple] = None) -> Optional[Dict]:
        """Execute query and fetch single result."""
        cursor = self.execute(query, parameters)
        row = cursor.fetchone()
        return dict(row) if row else None

    def query_many(self, query: str, parameters: Optional[tuple] = None) -> list:
        """Execute query and fetch all results."""
        cursor = self.execute(query, parameters)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


@contextmanager
def transaction(connection: sqlite3.Connection):
    """
    Simplified context manager for transactions.

    Example:
        with transaction(conn) as uow:
            repo = uow.get_repository(CustomerRepository)
            repo.create({...})
    """
    uow = UnitOfWork(connection)
    try:
        uow.begin()
        yield uow
        uow.commit()
    except Exception as e:
        uow.rollback()
        raise
