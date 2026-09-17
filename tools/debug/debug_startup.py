
import sys
import os
from PyQt6.QtWidgets import QApplication, QStackedWidget, QLabel

# Mock Database
class MockDB:
    def get_setting(self, key, default=""):
        return default
    def set_setting(self, key, value):
        pass

# Add src to path
sys.path.append(os.getcwd())

def test_startup():
    print("--- STARTING DEBUG TEST ---")
    app = QApplication(sys.argv)
    db = MockDB()
    
    print("1. Attempting to import BackupPage...")
    try:
        from src.ui.pages.backup_page import BackupPage
        print("   SUCCESS: BackupPage imported.")
    except Exception as e:
        print(f"   FATAL ERROR: Could not import BackupPage: {e}")
        return

    print("2. Attempting to instantiate BackupPage...")
    try:
        page_backup = BackupPage(db)
        print("   SUCCESS: BackupPage instantiated.")
    except Exception as e:
        print(f"   FATAL ERROR: Could not instantiate BackupPage: {e}")
        import traceback
        traceback.print_exc()
        return

    print("3. Verifying MainWindow Stack Indices...")
    stack = QStackedWidget()
    
    # Mimic MainWindow logic exactly
    try:
        # We use Labels as placeholders for other pages to save imports
        p0 = QLabel("Dashboard"); stack.addWidget(p0)
        p1 = QLabel("Summary"); stack.addWidget(p1)
        p2 = QLabel("Accounting"); stack.addWidget(p2)
        p3 = QLabel("Personnel"); stack.addWidget(p3)
        p4 = QLabel("Reports"); stack.addWidget(p4)
        p5 = QLabel("Appointments"); stack.addWidget(p5)
        p6 = QLabel("Settings"); stack.addWidget(p6)
        p7 = QLabel("Services"); stack.addWidget(p7)
        p8 = QLabel("Stock"); stack.addWidget(p8)
        p9 = QLabel("KB"); stack.addWidget(p9)
        p10 = QLabel("Support"); stack.addWidget(p10)
        p11 = QLabel("ServiceBoard"); stack.addWidget(p11)
        p12 = QLabel("Customers"); stack.addWidget(p12)
        p13 = QLabel("StatusScreen"); stack.addWidget(p13)
        p14 = QLabel("AI"); stack.addWidget(p14)
        
        # ADD BACKUP PAGE
        index_backup = stack.addWidget(page_backup)
        print(f"   BackupPage added at index: {index_backup}")
        
    except Exception as e:
        print(f"Stack Error: {e}")

    print("--- TEST FINISHED ---")

if __name__ == "__main__":
    test_startup()
