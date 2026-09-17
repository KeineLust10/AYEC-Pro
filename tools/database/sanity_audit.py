import sys
import os
import traceback

# Project Path
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'src'))

def safe_test(name, func):
    print(f"Testing {name}...", end=" ", flush=True)
    try:
        func()
        print("OK")
    except Exception as e:
        print(f"FAIL -> {e}")
        # traceback.print_exc()

def audit_database():
    from src.database import Database
    db = Database("audit_test.db")
    db.get_field_technicians()
    db.close()
    if os.path.exists("audit_test.db"):
        os.remove("audit_test.db")

def audit_uifiles():
    # Only import checks to avoid needing a QApp loop for complex instantiation
    from src.ui.pages.dashboard_page import DashboardPage
    from src.ui.pages.field_service_page import FieldServicePage
    from src.ui.pages.personnel_page import PersonnelPage
    from src.ui.pages.accounting_page import AccountingPage
    from src.ui.pages.stock_page import StockPage
    _ = (DashboardPage, FieldServicePage, PersonnelPage, AccountingPage, StockPage)

def audit_utils():
    from src.utils.design_system import DesignTokens
    from src.utils.theme_manager import ThemeManager
    from src.utils.security_manager import SecurityManager

if __name__ == "__main__":
    print("--- AYEC Pro Sanity Audit ---")
    safe_test("Core Database & Mixins", audit_database)
    safe_test("UI Module Imports", audit_uifiles)
    safe_test("Utility Module Imports", audit_utils)
    print("--- Audit Complete ---")
