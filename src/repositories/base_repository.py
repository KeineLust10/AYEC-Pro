"""
Base Repository Class

Provides common database operations and connection management for all repositories.
"""

import sqlite3
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class RepositoryError(Exception):
    """Base exception for repository errors."""
    pass


class RecordNotFoundError(RepositoryError):
    """Raised when a record is not found."""
    pass


class DuplicateRecordError(RepositoryError):
    """Raised when attempting to create a duplicate record."""
    pass


class BaseRepository(ABC):
    """
    Abstract base class for all repositories.

    Provides common database operations and enforces consistent interface
    across all domain repositories.
    """

    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize repository with database connection.

        Args:
            connection: SQLite database connection
        """
        self._conn = connection
        self._table_name = self._get_table_name()

    def _safe_identifier(self, value: str) -> str:
        text = str(value or "").strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", text):
            raise RepositoryError(f"Invalid identifier: {value}")
        return text

    @property
    def connection(self) -> sqlite3.Connection:
        """Get the database connection."""
        return self._conn

    @abstractmethod
    def _get_table_name(self) -> str:
        """Return the table name for this repository."""
        pass

    @contextmanager
    def _get_cursor(self):
        """Context manager for database cursor."""
        cursor = self._conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute(
        self,
        query: str,
        parameters: Optional[Tuple] = None
    ) -> sqlite3.Cursor:
        """
        Execute a SQL query.

        Args:
            query: SQL query string
            parameters: Query parameters (to prevent SQL injection)

        Returns:
            SQLite cursor object

        Raises:
            RepositoryError: If query execution fails
        """
        try:
            cursor = self._conn.cursor()
            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {query}")
            logger.error(f"Error: {e}")
            raise RepositoryError(f"Database error: {e}") from e

    def execute_many(
        self,
        query: str,
        parameters_list: List[Tuple]
    ) -> sqlite3.Cursor:
        """
        Execute a SQL query multiple times with different parameters.

        Args:
            query: SQL query string
            parameters_list: List of parameter tuples

        Returns:
            SQLite cursor object
        """
        try:
            cursor = self._conn.cursor()
            cursor.executemany(query, parameters_list)
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Batch query execution failed: {e}")
            raise RepositoryError(f"Database error: {e}") from e

    def fetch_one(
        self,
        query: str,
        parameters: Optional[Tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute query and fetch single result as dictionary.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            Single record as dictionary, or None if not found
        """
        cursor = self.execute(query, parameters)
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def fetch_many(
        self,
        query: str,
        parameters: Optional[Tuple] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query and fetch all results as list of dictionaries.

        Args:
            query: SQL query string
            parameters: Query parameters

        Returns:
            List of records as dictionaries
        """
        cursor = self.execute(query, parameters)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def insert(self, data: Dict[str, Any]) -> int:
        """
        Insert a single record.

        Args:
            data: Dictionary of column names and values

        Returns:
            ID of the inserted record
        """
        table_name = self._safe_identifier(self._table_name)
        columns = ', '.join(self._safe_identifier(key) for key in data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = "INSERT INTO {table_name} ({columns}) VALUES ({placeholders})".format(
            table_name=table_name,
            columns=columns,
            placeholders=placeholders,
        )

        try:
            cursor = self.execute(query, tuple(data.values()))
            self._conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            logger.error(f"Insert failed - integrity error: {e}")
            raise DuplicateRecordError(f"Record already exists: {e}") from e

    def update(
        self,
        record_id: int,
        data: Dict[str, Any],
        id_column: str = 'id'
    ) -> bool:
        """
        Update a record by ID.

        Args:
            record_id: ID of record to update
            data: Dictionary of columns to update
            id_column: Name of the ID column

        Returns:
            True if record was updated, False if not found
        """
        if not data:
            return False

        table_name = self._safe_identifier(self._table_name)
        safe_id_column = self._safe_identifier(id_column)
        set_clause = ', '.join([f"{self._safe_identifier(k)} = ?" for k in data.keys()])
        query = "UPDATE {table_name} SET {set_clause} WHERE {id_column} = ?".format(
            table_name=table_name,
            set_clause=set_clause,
            id_column=safe_id_column,
        )

        cursor = self.execute(query, tuple(data.values()) + (record_id,))
        self._conn.commit()

        return cursor.rowcount > 0

    def delete(self, record_id: int, id_column: str = 'id') -> bool:
        """
        Soft delete a record by ID (sets is_deleted=1).

        Args:
            record_id: ID of record to delete
            id_column: Name of the ID column

        Returns:
            True if record was deleted, False if not found
        """
        table_name = self._safe_identifier(self._table_name)
        safe_id_column = self._safe_identifier(id_column)
        query = """
            UPDATE {table_name}
            SET is_deleted = 1, deleted_at = datetime('now')
            WHERE {safe_id_column} = ? AND (is_deleted = 0 OR is_deleted IS NULL)
        """.format(table_name=table_name, safe_id_column=safe_id_column)
        cursor = self.execute(query, (record_id,))
        self._conn.commit()

        return cursor.rowcount > 0

    def hard_delete(self, record_id: int, id_column: str = 'id') -> bool:
        """
        Permanently delete a record by ID.

        Warning: Use with caution! Prefer soft delete in most cases.

        Args:
            record_id: ID of record to delete
            id_column: Name of the ID column

        Returns:
            True if record was deleted, False if not found
        """
        table_name = self._safe_identifier(self._table_name)
        safe_id_column = self._safe_identifier(id_column)
        query = "DELETE FROM {table_name} WHERE {id_column} = ?".format(
            table_name=table_name,
            id_column=safe_id_column,
        )
        cursor = self.execute(query, (record_id,))
        self._conn.commit()

        return cursor.rowcount > 0

    def get_by_id(
        self,
        record_id: int,
        id_column: str = 'id',
        include_deleted: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single record by ID.

        Args:
            record_id: ID of record to fetch
            id_column: Name of the ID column
            include_deleted: Whether to include soft-deleted records

        Returns:
            Record as dictionary, or None if not found
        """
        table_name = self._safe_identifier(self._table_name)
        safe_id_column = self._safe_identifier(id_column)
        query = "SELECT * FROM {table_name} WHERE {id_column} = ?".format(
            table_name=table_name,
            id_column=safe_id_column,
        )

        if not include_deleted:
            query += " AND (is_deleted = 0 OR is_deleted IS NULL)"

        return self.fetch_one(query, (record_id,))

    def get_all(
        self,
        include_deleted: bool = False,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all records.

        Args:
            include_deleted: Whether to include soft-deleted records
            limit: Maximum number of records to return
            offset: Number of records to skip

        Returns:
            List of records as dictionaries
        """
        table_name = self._safe_identifier(self._table_name)
        query = "SELECT * FROM {table_name}".format(table_name=table_name)

        if not include_deleted:
            query += " WHERE is_deleted = 0 OR is_deleted IS NULL"

        query += " ORDER BY id DESC"

        parameters = None
        if limit is not None:
            try:
                safe_limit = int(limit)
                safe_offset = int(offset)
            except (TypeError, ValueError) as exc:
                raise RepositoryError("Limit and offset must be integers") from exc
            if safe_limit < 0 or safe_offset < 0:
                raise RepositoryError("Limit and offset cannot be negative")
            query += " LIMIT ? OFFSET ?"
            parameters = (safe_limit, safe_offset)

        return self.fetch_many(query, parameters)

    def count(self, include_deleted: bool = False) -> int:
        """
        Get total count of records.

        Args:
            include_deleted: Whether to include soft-deleted records

        Returns:
            Total record count
        """
        table_name = self._safe_identifier(self._table_name)
        query = "SELECT COUNT(*) as count FROM {table_name}".format(table_name=table_name)

        if not include_deleted:
            query += " WHERE is_deleted = 0 OR is_deleted IS NULL"

        result = self.fetch_one(query)
        return result['count'] if result else 0

    def exists(self, record_id: int, id_column: str = 'id') -> bool:
        """
        Check if a record exists.

        Args:
            record_id: ID to check
            id_column: Name of the ID column

        Returns:
            True if record exists, False otherwise
        """
        table_name = self._safe_identifier(self._table_name)
        safe_id_column = self._safe_identifier(id_column)
        query = """
            SELECT 1 FROM {table_name}
            WHERE {id_column} = ? AND (is_deleted = 0 OR is_deleted IS NULL)
            LIMIT 1
        """.format(table_name=table_name, id_column=safe_id_column)
        result = self.fetch_one(query, (record_id,))
        return result is not None
