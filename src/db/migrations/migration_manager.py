"""
Database Migration Manager

Manages schema migrations for SQLite database.
"""

import sqlite3
import os
import re
from datetime import datetime
from typing import List, Callable, Optional
from src.utils.logger import logger


class MigrationManager:
    """
    Manages database schema migrations.

    Usage:
        from src.db.migrations import MigrationManager

        manager = MigrationManager(db.connection)
        manager.migrate()  # Run all pending migrations
    """

    def __init__(self, connection: sqlite3.Connection):
        """
        Initialize migration manager.

        Args:
            connection: SQLite database connection
        """
        self._conn = connection
        self._ensure_migration_table()

    def _ensure_migration_table(self):
        """Create migration tracking table if not exists."""
        cursor = self._conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                checksum TEXT
            )
        """)
        self._conn.commit()

    def get_applied_migrations(self) -> List[str]:
        """Get list of already applied migration versions."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT version FROM _migrations ORDER BY id"
        )
        return [row[0] for row in cursor.fetchall()]

    def is_migration_applied(self, version: str) -> bool:
        """Check if a specific migration is already applied."""
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT 1 FROM _migrations WHERE version = ? LIMIT 1",
            (version,)
        )
        return cursor.fetchone() is not None

    def apply_migration(
        self,
        version: str,
        name: str,
        up_func: Callable[[sqlite3.Connection], None]
    ) -> bool:
        """
        Apply a single migration.

        Args:
            version: Migration version (e.g., '001')
            name: Migration name
            up_func: Function that performs the migration

        Returns:
            True if migration was applied, False if already applied
        """
        if self.is_migration_applied(version):
            logger.debug(f"Migration {version} already applied, skipping")
            return False

        try:
            logger.info(f"Applying migration {version}: {name}")

            # Run migration
            up_func(self._conn)

            # Record migration
            cursor = self._conn.cursor()
            cursor.execute(
                """INSERT INTO _migrations (version, name, applied_at)
                   VALUES (?, ?, datetime('now'))""",
                (version, name)
            )
            self._conn.commit()

            logger.info(f"Migration {version} applied successfully")
            return True

        except Exception as e:
            self._conn.rollback()
            logger.error(f"Migration {version} failed: {e}")
            raise

    def migrate(self):
        """Run all pending migrations in order."""
        migrations = self._get_available_migrations()
        applied = self.get_applied_migrations()

        pending = [m for m in migrations if m['version'] not in applied]

        if not pending:
            logger.info("No pending migrations")
            return

        logger.info(f"Found {len(pending)} pending migrations")

        for migration in pending:
            self.apply_migration(
                migration['version'],
                migration['name'],
                migration['up']
            )

        logger.info("All migrations completed")

    def _get_available_migrations(self) -> List[dict]:
        """Get list of all available migrations."""
        from . import migrations as migrations_module

        migrations = []

        # Find all migration functions in the migrations module
        for attr_name in dir(migrations_module):
            match = re.match(r'migration_(\d+)_(.+)', attr_name)
            if match:
                version = match.group(1)
                name = match.group(2).replace('_', ' ').title()
                func = getattr(migrations_module, attr_name)

                migrations.append({
                    'version': version,
                    'name': name,
                    'up': func
                })

        # Sort by version number
        migrations.sort(key=lambda m: int(m['version']))
        return migrations

    def rollback(self, version: Optional[str] = None):
        """
        Rollback migrations.

        Args:
            version: Version to rollback to (None = rollback last migration)
        """
        # TODO: Implement rollback functionality
        logger.warning("Rollback not yet implemented")

    def status(self) -> dict:
        """Get migration status."""
        applied = self.get_applied_migrations()
        available = self._get_available_migrations()

        return {
            'applied_count': len(applied),
            'available_count': len(available),
            'pending_count': len(available) - len(applied),
            'last_applied': applied[-1] if applied else None,
            'pending': [m['version'] for m in available if m['version'] not in applied]
        }
