
import sqlite3
import os
import sys
from src.utils.path_helper import PathHelper

def reset_transactions():
    print("WARNING: Wiping all transaction history (keeping definitions)...")
    
    db_path = PathHelper.get_db_path("ayecpro.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables_to_clear = [
        "currency_transactions",  # Sales/Service transactions
        "accounting",             # Manual income/expense entries
        "used_parts",            # Stock usage history
        "stock_movements",       # Stock in/out movements
        "audit_logs",            # System logs
        "jarvis_notifications"   # AI notifications
    ]
    
    try:
        for table in tables_to_clear:
            cursor.execute(f"DELETE FROM {table}")
            print(f"Cleared table: {table}")
            
        # Reset sqlite sequences (auto increment IDs)
        for table in tables_to_clear:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
            
        conn.commit()
        print("SUCCESS: Database transactions reset. You can now start from zero.")
        
    except Exception as e:
        print(f"Error resetting DB: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    reset_transactions()
