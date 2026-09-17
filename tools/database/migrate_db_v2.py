# -*- coding: utf-8 -*-

import sqlite3
import os
import datetime
import sys

# Proje dizinini sys.path'e ekle
sys.path.append(os.getcwd())
from src.utils.path_helper import PathHelper

db_path = PathHelper.get_db_path()
print(f"Migrating database at: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def add_column_if_not_exists(cursor, table, column, definition):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    if not cursor.fetchone():
        print(f"Table '{table}' does not exist, skipping '{column}'.")
        return
    cursor.execute(f"PRAGMA table_info({table});")
    columns = [col[1] for col in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition};")
        print(f"Column '{column}' added to {table}.")
    else:
        print(f"Column '{column}' already exists in {table}.")

# --- Yeni Tablolar (Mali Yıllar ve Dönemler) ---
cursor.execute('''
CREATE TABLE IF NOT EXISTS fiscal_years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year_name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    is_active INTEGER DEFAULT 1,
    closing_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS account_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fiscal_year_id INTEGER,
    period_name TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    is_active INTEGER DEFAULT 1,
    closing_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fiscal_year_id) REFERENCES fiscal_years(id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS financial_statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fiscal_year_id INTEGER,
    account_period_id INTEGER,
    statement_type TEXT,
    total_income REAL DEFAULT 0,
    total_expense REAL DEFAULT 0,
    net_profit REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(fiscal_year_id) REFERENCES fiscal_years(id),
    FOREIGN KEY(account_period_id) REFERENCES account_periods(id)
)
''')
print("Mali yıl, dönem ve finansal tablo tabloları oluşturuldu.")

# --- Tablolara fiscal_year_id ekleme ---
add_column_if_not_exists(cursor, 'accounting', 'fiscal_year_id', 'INTEGER')
add_column_if_not_exists(cursor, 'currency_transactions', 'fiscal_year_id', 'INTEGER')

# settings tablosuna current_fiscal_year ayarı ekleyelim
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='settings'")
if cursor.fetchone():
    cursor.execute("SELECT value FROM settings WHERE key='current_fiscal_year'")
    if not cursor.fetchone():
        current_year = str(datetime.datetime.now().year)
        cursor.execute("INSERT INTO settings (key, value) VALUES ('current_fiscal_year', ?)", (current_year,))
        print(f"current_fiscal_year ({current_year}) settings tablosuna eklendi.")

conn.commit()
conn.close()
print("Migration completed successfully.")
