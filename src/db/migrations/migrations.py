"""
Database Migrations

All migration functions must follow the naming convention:
    migration_XXX_description (e.g., migration_001_initial_schema)

Each function receives a sqlite3.Connection object and performs schema changes.
"""

import sqlite3
from src.utils.logger import logger


def _safe_identifier(name: str) -> str:
    if not name or not name.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQL identifier: {name}")
    return name


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor = conn.cursor()
    cursor.execute(
        "PRAGMA table_info({table})".format(table=_safe_identifier(table))
    )
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    """Check if a table exists."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def migration_001_add_soft_delete_columns(conn: sqlite3.Connection):
    """
    Add is_deleted and deleted_at columns to tables for soft delete support.

    Tables affected:
    - accounting
    - devices (if not exists)
    - services (if not exists)
    - stock_movements
    - personnel
    """
    cursor = conn.cursor()

    tables_to_update = [
        ('accounting', ['is_deleted', 'deleted_at']),
        ('devices', ['is_deleted', 'deleted_at']),
        ('services', ['is_deleted', 'deleted_at']),
        ('stock_movements', ['is_deleted', 'deleted_at']),
        ('personnel', ['is_deleted', 'deleted_at']),
    ]

    for table, columns in tables_to_update:
        if not _table_exists(conn, table):
            logger.warning(f"Table {table} does not exist, skipping")
            continue

        for column in columns:
            if _column_exists(conn, table, column):
                logger.debug(f"Column {column} already exists in {table}, skipping")
                continue

            # Add column with default value
            if column == 'is_deleted':
                cursor.execute(
                    f"ALTER TABLE {_safe_identifier(table)} ADD COLUMN {_safe_identifier(column)} INTEGER DEFAULT 0"
                )
            else:  # deleted_at
                cursor.execute(
                    f"ALTER TABLE {_safe_identifier(table)} ADD COLUMN {_safe_identifier(column)} TEXT"
                )

            logger.info(f"Added column {column} to {table}")

    conn.commit()


def migration_002_add_bank_account_id_to_accounting(conn: sqlite3.Connection):
    """
    Add bank_account_id column to accounting table for bank transaction linking.
    """
    cursor = conn.cursor()

    if not _table_exists(conn, 'accounting'):
        logger.warning("Table accounting does not exist, skipping")
        return

    if _column_exists(conn, 'accounting', 'bank_account_id'):
        logger.debug("Column bank_account_id already exists in accounting, skipping")
        return

    cursor.execute(
        "ALTER TABLE accounting ADD COLUMN bank_account_id INTEGER"
    )
    conn.commit()

    logger.info("Added column bank_account_id to accounting")


def migration_003_add_is_deleted_to_bank_accounts(conn: sqlite3.Connection):
    """
    Add is_deleted and deleted_at columns to bank_accounts table.
    """
    cursor = conn.cursor()

    if not _table_exists(conn, 'bank_accounts'):
        logger.warning("Table bank_accounts does not exist, skipping")
        return

    columns_to_add = [
        ('is_deleted', 'INTEGER DEFAULT 0'),
        ('deleted_at', 'TEXT'),
    ]

    for column, col_type in columns_to_add:
        if _column_exists(conn, 'bank_accounts', column):
            logger.debug(f"Column {column} already exists in bank_accounts, skipping")
            continue

        cursor.execute(
            f"ALTER TABLE bank_accounts ADD COLUMN {_safe_identifier(column)} {col_type}"
        )
        logger.info(f"Added column {column} to bank_accounts")

    conn.commit()


def migration_004_create_indexes_for_soft_delete(conn: sqlite3.Connection):
    """
    Create indexes for soft delete columns to improve query performance.
    """
    cursor = conn.cursor()

    indexes = [
        ('idx_customers_is_deleted', 'customers', 'is_deleted'),
        ('idx_devices_is_deleted', 'devices', 'is_deleted'),
        ('idx_services_is_deleted', 'services', 'is_deleted'),
        ('idx_accounting_is_deleted', 'accounting', 'is_deleted'),
        ('idx_stock_movements_is_deleted', 'stock_movements', 'is_deleted'),
        ('idx_bank_accounts_is_deleted', 'bank_accounts', 'is_deleted'),
        ('idx_personnel_is_deleted', 'personnel', 'is_deleted'),
    ]

    for idx_name, table, column in indexes:
        if not _table_exists(conn, table):
            continue

        # Check if index exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name=?",
            (idx_name,)
        )
        if cursor.fetchone():
            logger.debug(f"Index {idx_name} already exists, skipping")
            continue

        cursor.execute(
            f"CREATE INDEX {_safe_identifier(idx_name)} ON {_safe_identifier(table)}({_safe_identifier(column)})"
        )
        logger.info(f"Created index {idx_name}")

    conn.commit()


def migration_005_add_audit_columns_to_key_tables(conn: sqlite3.Connection):
    """
    Add created_at and updated_at columns to key tables if not exist.
    """
    cursor = conn.cursor()

    tables_and_columns = [
        ('customers', ['created_at', 'updated_at']),
        ('devices', ['updated_at']),
        ('bank_accounts', ['updated_at']),
        ('parts', ['created_at', 'updated_at']),
    ]

    for table, columns in tables_and_columns:
        if not _table_exists(conn, table):
            continue

        for column in columns:
            if _column_exists(conn, table, column):
                continue

            cursor.execute(
                f"ALTER TABLE {_safe_identifier(table)} ADD COLUMN {_safe_identifier(column)} TEXT"
            )
            logger.info(f"Added column {column} to {table}")

    conn.commit()


def migration_006_add_is_deleted_to_customers_and_parts(conn: sqlite3.Connection):
    """
    Add is_deleted and deleted_at columns to customers and parts tables.
    """
    cursor = conn.cursor()

    tables_to_update = [
        ('customers', ['is_deleted', 'deleted_at']),
        ('parts', ['is_deleted', 'deleted_at']),
    ]

    for table, columns in tables_to_update:
        if not _table_exists(conn, table):
            continue

        for column in columns:
            if _column_exists(conn, table, column):
                continue

            if column == 'is_deleted':
                cursor.execute(
                    f"ALTER TABLE {_safe_identifier(table)} ADD COLUMN {_safe_identifier(column)} INTEGER DEFAULT 0"
                )
            else:
                cursor.execute(
                    f"ALTER TABLE {_safe_identifier(table)} ADD COLUMN {_safe_identifier(column)} TEXT"
                )
            logger.info(f"Added column {column} to {table}")

    if _table_exists(conn, 'parts'):
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_parts_is_deleted'")
        if not cursor.fetchone():
            cursor.execute("CREATE INDEX idx_parts_is_deleted ON parts(is_deleted)")
            logger.info("Created index idx_parts_is_deleted")

    conn.commit()


def _create_index_if_columns_exist(
    conn: sqlite3.Connection,
    index_name: str,
    table: str,
    columns_sql: str,
    required_columns: list[str],
):
    if not _table_exists(conn, table):
        return
    if not all(_column_exists(conn, table, column) for column in required_columns):
        return
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=? LIMIT 1",
        (index_name,),
    )
    if cursor.fetchone():
        return
    cursor.execute(
        "CREATE INDEX {index_name} ON {table}({columns})".format(
            index_name=_safe_identifier(index_name),
            table=_safe_identifier(table),
            columns=columns_sql,
        )
    )


def migration_007_add_performance_indexes(conn: sqlite3.Connection):
    """Add indexes used by paged desktop, web, and mobile queries."""
    cursor = conn.cursor()
    for table in ("parts", "accounting", "stock_movements"):
        if _table_exists(conn, table) and _column_exists(conn, table, "is_deleted"):
            cursor.execute(
                "UPDATE {table} SET is_deleted=0 WHERE is_deleted IS NULL".format(
                    table=_safe_identifier(table)
                )
            )
    if _table_exists(conn, "projects") and _column_exists(
        conn, "projects", "is_archived"
    ):
        cursor.execute(
            "UPDATE projects SET is_archived=0 WHERE is_archived IS NULL"
        )

    indexes = [
        (
            "idx_parts_deleted_name_nocase",
            "parts",
            "is_deleted, name COLLATE NOCASE",
            ["is_deleted", "name"],
        ),
        ("idx_parts_code", "parts", "code", ["code"]),
        ("idx_parts_barcode", "parts", "barcode", ["barcode"]),
        (
            "idx_currency_tx_customer_type_balance",
            "currency_transactions",
            "customer_id, transaction_type, current_balance",
            ["customer_id", "transaction_type", "current_balance"],
        ),
        (
            "idx_currency_tx_type_created",
            "currency_transactions",
            "transaction_type, created_at",
            ["transaction_type", "created_at"],
        ),
        (
            "idx_accounting_deleted_date",
            "accounting",
            "is_deleted, date",
            ["is_deleted", "date"],
        ),
        (
            "idx_accounting_customer_date",
            "accounting",
            "customer_id, date",
            ["customer_id", "date"],
        ),
        (
            "idx_stock_movements_deleted_created",
            "stock_movements",
            "is_deleted, created_at",
            ["is_deleted", "created_at"],
        ),
        (
            "idx_stock_movements_part_created",
            "stock_movements",
            "part_id, created_at",
            ["part_id", "created_at"],
        ),
        (
            "idx_projects_archived_created",
            "projects",
            "is_archived, created_at",
            ["is_archived", "created_at"],
        ),
        (
            "idx_project_units_project_sort",
            "project_units",
            "project_id, block_name, floor_no, unit_no",
            ["project_id", "block_name", "floor_no", "unit_no"],
        ),
        (
            "idx_project_units_parent",
            "project_units",
            "parent_unit_id",
            ["parent_unit_id"],
        ),
        (
            "idx_project_transactions_project_date",
            "project_transactions",
            "project_id, date",
            ["project_id", "date"],
        ),
        (
            "idx_project_transactions_project_type_date",
            "project_transactions",
            "project_id, type, date",
            ["project_id", "type", "date"],
        ),
        (
            "idx_project_unit_products_project_unit",
            "project_unit_products",
            "project_id, unit_id, added_at",
            ["project_id", "unit_id", "added_at"],
        ),
        (
            "idx_offers_customer_created",
            "offers",
            "customer_id, created_at",
            ["customer_id", "created_at"],
        ),
    ]
    for index_name, table, columns_sql, required_columns in indexes:
        _create_index_if_columns_exist(
            conn,
            index_name,
            table,
            columns_sql,
            required_columns,
        )
    conn.commit()


def migration_008_rebuild_customer_balances_once(conn: sqlite3.Connection):
    """Rebuild cached balances once instead of on every application start."""
    if not (
        _table_exists(conn, "currency_transactions")
        and _table_exists(conn, "customer_currency_balances")
    ):
        return
    required_tx = {
        "customer_id",
        "currency",
        "transaction_type",
        "amount",
    }
    required_balance = {
        "customer_id",
        "currency",
        "balance",
        "last_updated",
    }
    if not all(
        _column_exists(conn, "currency_transactions", column)
        for column in required_tx
    ):
        return
    if not all(
        _column_exists(conn, "customer_currency_balances", column)
        for column in required_balance
    ):
        return

    cursor = conn.cursor()
    cursor.execute("DELETE FROM customer_currency_balances")
    cursor.execute(
        """
        INSERT INTO customer_currency_balances
            (customer_id, currency, balance, last_updated)
        SELECT
            customer_id,
            UPPER(COALESCE(NULLIF(currency, ''), 'TRY')),
            ROUND(
                SUM(
                    CASE
                        WHEN UPPER(transaction_type) = 'CREDIT' THEN amount
                        ELSE -amount
                    END
                ),
                2
            ),
            datetime('now')
        FROM currency_transactions
        WHERE customer_id IS NOT NULL
        GROUP BY
            customer_id,
            UPPER(COALESCE(NULLIF(currency, ''), 'TRY'))
        """
    )
    conn.commit()


def migration_009_create_payment_allocation_schema(conn: sqlite3.Connection):
    """Create payment allocation schema during startup migration."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_debt_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_txn_id INTEGER NOT NULL,
            debt_txn_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (payment_txn_id) REFERENCES currency_transactions(id),
            FOREIGN KEY (debt_txn_id) REFERENCES currency_transactions(id)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_payment_debt_payment
        ON payment_debt_links(payment_txn_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_payment_debt_debt
        ON payment_debt_links(debt_txn_id)
        """
    )
    conn.commit()


def migration_010_finalize_project_query_indexes(conn: sqlite3.Connection):
    """Finalize project filters and report indexes for existing databases."""
    cursor = conn.cursor()
    if _table_exists(conn, "projects") and _column_exists(
        conn, "projects", "is_archived"
    ):
        cursor.execute(
            "UPDATE projects SET is_archived=0 WHERE is_archived IS NULL"
        )
    _create_index_if_columns_exist(
        conn,
        "idx_project_unit_products_project_unit",
        "project_unit_products",
        "project_id, unit_id, added_at",
        ["project_id", "unit_id", "added_at"],
    )
    conn.commit()


def migration_011_add_finance_lookup_indexes(conn: sqlite3.Connection):
    """Add composite indexes used by finance summaries and customer history."""
    indexes = [
        (
            "idx_currency_tx_type_balance_currency",
            "currency_transactions",
            "transaction_type, current_balance, currency",
            ["transaction_type", "current_balance", "currency"],
        ),
        (
            "idx_currency_tx_type_currency_balance",
            "currency_transactions",
            "transaction_type, currency, current_balance",
            ["transaction_type", "currency", "current_balance"],
        ),
        (
            "idx_currency_tx_customer_currency_type_created",
            "currency_transactions",
            "customer_id, currency, transaction_type, created_at",
            [
                "customer_id",
                "currency",
                "transaction_type",
                "created_at",
            ],
        ),
    ]
    for index_name, table, columns_sql, required_columns in indexes:
        _create_index_if_columns_exist(
            conn,
            index_name,
            table,
            columns_sql,
            required_columns,
        )
    conn.commit()


def migration_012_add_sort_optimized_indexes(conn: sqlite3.Connection):
    """Add indexes that avoid temporary sorting in paged screens."""
    indexes = [
        (
            "idx_currency_tx_customer_currency_created",
            "currency_transactions",
            "customer_id, currency, created_at DESC",
            ["customer_id", "currency", "created_at"],
        ),
        (
            "idx_projects_archived_priority_created",
            "projects",
            "is_archived, "
            "(CASE WHEN status='Devam Ediyor' THEN 0 ELSE 1 END), "
            "created_at DESC",
            ["is_archived", "status", "created_at"],
        ),
        (
            "idx_project_products_project_unit_added_desc",
            "project_unit_products",
            "project_id, unit_id, added_at DESC",
            ["project_id", "unit_id", "added_at"],
        ),
    ]
    for index_name, table, columns_sql, required_columns in indexes:
        _create_index_if_columns_exist(
            conn,
            index_name,
            table,
            columns_sql,
            required_columns,
        )
    conn.commit()


def migration_013_add_project_balance_index(conn: sqlite3.Connection):
    """Add the lookup index used by bulk subcontractor balance queries."""
    _create_index_if_columns_exist(
        conn,
        "idx_project_transactions_ref_balance",
        "project_transactions",
        "ref_table, ref_id, type, status",
        ["ref_table", "ref_id", "type", "status"],
    )
    conn.commit()


def migration_014_add_subcontractor_project_index(conn: sqlite3.Connection):
    """Add the parent index used by paged project subcontractor screens."""
    _create_index_if_columns_exist(
        conn,
        "idx_subcontractors_project_id",
        "subcontractors",
        "project_id, id",
        ["project_id", "id"],
    )
    conn.commit()


def migration_015_add_customer_history_indexes(conn: sqlite3.Connection):
    """Add indexes used by paged customer history tabs."""
    indexes = [
        (
            "idx_devices_customer_deleted_entry",
            "devices",
            "customer_id, is_deleted, entry_date DESC",
            ["customer_id", "is_deleted", "entry_date"],
        ),
        (
            "idx_accounting_customer_type_date_id",
            "accounting",
            "customer_id, type, date DESC, id DESC",
            ["customer_id", "type", "date", "id"],
        ),
        (
            "idx_used_parts_tracking",
            "used_parts",
            "tracking_no",
            ["tracking_no"],
        ),
    ]
    for index_name, table, columns_sql, required_columns in indexes:
        _create_index_if_columns_exist(
            conn,
            index_name,
            table,
            columns_sql,
            required_columns,
        )
    conn.commit()


def migration_016_add_legacy_filter_expression_indexes(
    conn: sqlite3.Connection,
):
    """Add expression indexes matching legacy soft-delete filters."""
    indexes = [
        (
            "idx_devices_customer_active_entry_id",
            "devices",
            "customer_id, is_deleted, entry_date DESC, id DESC",
            ["customer_id", "is_deleted", "entry_date", "id"],
        ),
        (
            "idx_devices_active_archive_entry",
            "devices",
            "COALESCE(is_deleted, 0), COALESCE(is_archived, 0), "
            "entry_date DESC, id DESC",
            ["is_deleted", "is_archived", "entry_date", "id"],
        ),
        (
            "idx_accounting_active_date_id",
            "accounting",
            "COALESCE(is_deleted, 0), date DESC, id DESC",
            ["is_deleted", "date", "id"],
        ),
        (
            "idx_currency_tx_customer_created_id",
            "currency_transactions",
            "customer_id, created_at DESC, id DESC",
            ["customer_id", "created_at", "id"],
        ),
        (
            "idx_currency_tx_created_id",
            "currency_transactions",
            "created_at DESC, id DESC",
            ["created_at", "id"],
        ),
        (
            "idx_parts_active_name_nocase",
            "parts",
            "COALESCE(is_deleted, 0), name COLLATE NOCASE",
            ["is_deleted", "name"],
        ),
        (
            "idx_stock_movements_active_created",
            "stock_movements",
            "COALESCE(is_deleted, 0), created_at DESC, id DESC",
            ["is_deleted", "created_at", "id"],
        ),
        (
            "idx_services_active_name_nocase",
            "services",
            "COALESCE(is_deleted, 0), name COLLATE NOCASE",
            ["is_deleted", "name"],
        ),
        (
            "idx_customers_active_name_nocase",
            "customers",
            "COALESCE(is_deleted, 0), name COLLATE NOCASE",
            ["is_deleted", "name"],
        ),
    ]
    for index_name, table, columns_sql, required_columns in indexes:
        _create_index_if_columns_exist(
            conn,
            index_name,
            table,
            columns_sql,
            required_columns,
        )
    conn.commit()


def migration_017_add_offer_and_activity_indexes(
    conn: sqlite3.Connection,
):
    """Add indexes used by offer details and customer activity views."""
    indexes = [
        (
            "idx_offer_items_offer_id",
            "offer_items",
            "offer_id, id",
            ["offer_id", "id"],
        ),
        (
            "idx_appointments_customer_date_status",
            "appointments",
            "customer_id, date DESC, status",
            ["customer_id", "date", "status"],
        ),
        (
            "idx_used_parts_part_created",
            "used_parts",
            "part_id, created_at DESC",
            ["part_id", "created_at"],
        ),
    ]
    for index_name, table, columns_sql, required_columns in indexes:
        _create_index_if_columns_exist(
            conn,
            index_name,
            table,
            columns_sql,
            required_columns,
        )
    conn.commit()
