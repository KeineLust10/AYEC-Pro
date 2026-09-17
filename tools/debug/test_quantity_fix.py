# -*- coding: utf-8 -*-

"""
Test script to verify quantity fix in multi-select transactions
"""
import sqlite3

# Connect to database
conn = sqlite3.connect('ayecpro.db')
cursor = conn.cursor()

print("=" * 80)
print("CURRENCY TRANSACTIONS - Son 5 Kayıt")
print("=" * 80)

cursor.execute("""
    SELECT id, customer_id, amount, currency, description, created_at 
    FROM currency_transactions 
    WHERE transaction_type='DEBIT'
    ORDER BY created_at DESC 
    LIMIT 5
""")

for row in cursor.fetchall():
    print(f"\nID: {row[0]}")
    print(f"Customer ID: {row[1]}")
    print(f"Amount: {row[2]} {row[3]}")
    print(f"Description:\n{row[4]}")
    print(f"Date: {row[5]}")
    print("-" * 80)

conn.close()
