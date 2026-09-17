import sqlite3

conn = sqlite3.connect(r'C:\Users\Admin\AppData\Local\AYECPro\ayecpro.db')
cursor = conn.cursor()

print("=== REVENUE ANALYSIS ===\n")

# Check currency transactions
cursor.execute("""
    SELECT 
        currency, 
        COUNT(*) as count,
        SUM(amount) as total_amount,
        SUM(try_equivalent) as total_try
    FROM currency_transactions 
    WHERE transaction_type = 'DEBIT'
    GROUP BY currency
""")

print("Revenue by Currency:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} transactions, {row[2]:,.2f} {row[0]} = {row[3]:,.2f} TRY")

# Total
cursor.execute("SELECT SUM(try_equivalent) FROM currency_transactions WHERE transaction_type = 'DEBIT'")
total = cursor.fetchone()[0] or 0
print(f"\nTotal Revenue (All Currencies in TRY): {total:,.2f} TRY")

# Check year filter
cursor.execute("""
    SELECT SUM(try_equivalent) 
    FROM currency_transactions 
    WHERE transaction_type = 'DEBIT' 
    AND created_at >= '2026-01-01'
""")
year_total = cursor.fetchone()[0] or 0
print(f"Total Revenue (2026 YTD): {year_total:,.2f} TRY")

# Check TRY transactions
cursor.execute("SELECT COUNT(*), SUM(try_equivalent) FROM currency_transactions WHERE transaction_type = 'DEBIT' AND currency = 'TRY'")
try_data = cursor.fetchone()
print(f"\nTRY Transactions: {try_data[0]} count, {try_data[1] or 0:,.2f} TRY")

conn.close()

