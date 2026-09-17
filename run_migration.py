#!/usr/bin/env python3
"""
Database Migration Runner

Usage:
    python run_migration.py           # Run all pending migrations
    python run_migration.py --status  # Show migration status
    python run_migration.py --help    # Show help
"""

import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database import Database
from src.db.migrations import MigrationManager
from src.utils.logger import logger


def run_migrations():
    """Run all pending migrations."""
    print("Running database migrations...")

    try:
        # Initialize database
        db = Database(init_mode="schema_only")

        # Create migration manager (use conn property)
        manager = MigrationManager(db.conn)

        # Run migrations
        manager.migrate()

        print("Migrations completed successfully!")

        # Show status
        status = manager.status()
        print(f"\nMigration Status:")
        print(f"   Applied: {status['applied_count']}")
        print(f"   Available: {status['available_count']}")
        print(f"   Pending: {status['pending_count']}")

        db.close()
        return 0

    except Exception as e:
        print(f"Migration failed: {e}")
        logger.error(f"Migration failed: {e}", exc_info=True)
        return 1


def show_status():
    """Show migration status."""
    print("Checking migration status...")

    try:
        db = Database(init_mode="schema_only")
        manager = MigrationManager(db.conn)

        status = manager.status()

        print(f"\nMigration Status:")
        print(f"   Applied: {status['applied_count']}")
        print(f"   Available: {status['available_count']}")
        print(f"   Pending: {status['pending_count']}")

        if status['last_applied']:
            print(f"   Last Applied: {status['last_applied']}")

        if status['pending']:
            print(f"\nPending Migrations:")
            for version in status['pending']:
                print(f"   - {version}")
        else:
            print(f"\nAll migrations are up to date!")

        db.close()
        return 0

    except Exception as e:
        print(f"Failed to get status: {e}")
        logger.error(f"Status check failed: {e}", exc_info=True)
        return 1


def main():
    parser = argparse.ArgumentParser(
        description='AYEC Pro Database Migration Tool'
    )
    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='Show migration status without running migrations'
    )

    args = parser.parse_args()

    if args.status:
        return show_status()
    else:
        return run_migrations()


if __name__ == '__main__':
    sys.exit(main())
