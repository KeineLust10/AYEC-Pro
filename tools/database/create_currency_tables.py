# -*- coding: utf-8 -*-

"""
Create currency_transactions and customer_currency_balances tables
"""
import sqlite3

conn = sqlite3.connect('ayecpro.db')
cursor = conn.cursor()

print("Creating currency tables...")

# 1. Currency Transactions Table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS currency_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL,  -- 'DEBIT' (Borç/Satış) or 'CREDIT' (Alacak/Ödeme)
        amount REAL NOT NULL,
        currency TEXT NOT NULL,  -- 'TRY', 'USD', 'EUR'
        exchange_rate REAL NOT NULL DEFAULT 1.0,
        try_equivalent REAL NOT NULL,  -- TL karşılığı
        description TEXT,
        tracking_no TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id)
    )
""")
print("[OK] currency_transactions table created")

# 2. Customer Currency Balances Table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer_currency_balances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        currency TEXT NOT NULL,  -- 'TRY', 'USD', 'EUR'
        balance REAL NOT NULL DEFAULT 0.0,
        last_updated TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        UNIQUE(customer_id, currency)
    )
""")
print("[OK] customer_currency_balances table created")

# 3. Create indexes for better performance
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_currency_txn_customer 
    ON currency_transactions(customer_id)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_currency_txn_date 
    ON currency_transactions(created_at)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_currency_balance_customer 
    ON customer_currency_balances(customer_id)
""")

print("[OK] Indexes created")

conn.commit()
conn.close()

print("\n[SUCCESS] Currency tables successfully created!")
print("\nYou can now use multi-currency transactions.")

