import sqlite3

conn = sqlite3.connect(r'C:\Users\Admin\AppData\Local\AYECPro\ayecpro.db')
cursor = conn.cursor()

print("=== CHECKING USD SALES ===\n")

cursor.execute("""
    SELECT id, amount, currency, try_equivalent, exchange_rate, created_at 
    FROM currency_transactions 
    WHERE transaction_type='DEBIT' 
    ORDER BY created_at DESC 
    LIMIT 5
""")

print("Recent Sales:")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Amount: {row[1]} {row[2]}, TRY Equiv: {row[3]}, Rate: {row[4]}, Date: {row[5]}")

cursor.execute("""
    SELECT 
        currency,
        COUNT(*) as count,
        SUM(amount) as total_amount,
        SUM(try_equivalent) as total_try
    FROM currency_transactions 
    WHERE transaction_type='DEBIT'
    GROUP BY currency
""")

print("\n=== REVENUE BY CURRENCY ===")
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]} transactions, {row[2]:,.2f} {row[0]} = {row[3]:,.2f} TRY")

cursor.execute("SELECT SUM(try_equivalent) FROM currency_transactions WHERE transaction_type='DEBIT'")
total = cursor.fetchone()[0] or 0
print(f"\nTotal Revenue (All Currencies): {total:,.2f} TRY")

conn.close()
