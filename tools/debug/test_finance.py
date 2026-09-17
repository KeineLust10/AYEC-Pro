from datetime import datetime
from src.utils.finance_manager import FinanceManager
from src.database import Database

db = Database()
fm = FinanceManager(db)

print("=== TESTING FINANCE MANAGER ===\n")

# Get date range
start, end = fm._get_date_range('month')
print(f"Date Range (month): {start} to {end}")

# Check what's in database
cursor = db.cursor
cursor.execute("SELECT created_at FROM currency_transactions WHERE transaction_type='DEBIT' LIMIT 1")
row = cursor.fetchone()
if row:
    print(f"Sample created_at from DB: {row[0]}")

# Test revenue calculation
summary = fm.get_financial_summary('month')
print(f"\nRevenue (month): {summary['revenue']:,.2f} TRY")
print(f"Expenses (month): {summary['expenses']:,.2f} TRY")
print(f"Net Profit (month): {summary['net_profit']:,.2f} TRY")

# Try 'all' period
summary_all = fm.get_financial_summary('all')
print(f"\nRevenue (all time): {summary_all['revenue']:,.2f} TRY")
