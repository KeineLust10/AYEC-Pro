"""
Database Migration System for AYEC Pro

SQLite-specific migration manager that tracks and applies schema changes.
"""

from .migration_manager import MigrationManager
from .migrations import *

__all__ = ['MigrationManager']
