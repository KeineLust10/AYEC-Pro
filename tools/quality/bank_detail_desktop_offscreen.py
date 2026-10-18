import json
import logging
import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication, QTabWidget

from src.database import Database
from src.ui.dialogs.bank_detail_dialog import BankDetailDialog
from src.ui.widgets.modern_dialog import ModernDialog

logging.getLogger("AYECProLogger").setLevel(logging.CRITICAL)
ModernDialog._fit_to_screen = lambda self: None


def main():
    output = Path(sys.argv[1] if len(sys.argv) > 1 else "output/playwright")
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    db = Database(":memory:", init_mode="full")
    db.create_bank_accounts_table()
    if not db.add_bank_account("Audit Bank", "Main", "Audit User", "123456", "TR000000000000000000000000", 15000, "TRY"):
        raise RuntimeError("Could not seed the offscreen bank account.")
    account_id = db.cursor.execute("SELECT id FROM bank_accounts ORDER BY id DESC LIMIT 1").fetchone()[0]
    db.create_finance_tables()
    db.add_bank_card(account_id, "Audit Card", "4321", 10000, 750, 15, 1, True)
    loan_id = db.add_loan("Audit Bank", 10000, 12, 12, "2026-01-01", bank_account_id=account_id, total_payment=12000)
    db.cursor.executemany("INSERT INTO loan_installments (loan_id, installment_no, due_date, total_amount, principal_part, interest_part, status) VALUES (?, ?, ?, ?, ?, ?, ?)", [(loan_id, 1, "2026-02-01", 6000, 5500, 500, "\u00d6dendi"), (loan_id, 2, "2026-03-01", 6000, 5500, 500, "Bekliyor")])
    db.cursor.execute("INSERT INTO accounting (type, category, description, amount, date, bank_account_id, payment_method) VALUES (?, ?, ?, ?, ?, ?, ?)", ("Gider", "Kira", "Office rent", 500, "2026-10-01", account_id, "Havale"))
    db.conn.commit()
    db.create_finance_tables()
    account = db.cursor.execute("SELECT * FROM bank_accounts WHERE id=?", (account_id,)).fetchone()
    dialog = BankDetailDialog(db, account)
    if dialog.account.get("bank_name") != "Audit Bank":
        raise RuntimeError(json.dumps({"account_id": account_id, "account_columns": dialog.account_cols, "account": str(account)}))
    if not dialog.account_cols or dialog.txn_total != 1 or len(dialog.loans) != 1:
        raise RuntimeError(json.dumps({"account_columns": dialog.account_cols, "transactions": dialog.txn_total, "loans": len(dialog.loans)}))
    dialog.resize(1320, 900)
    dialog.show()
    app.processEvents()
    tabs = dialog.findChild(QTabWidget)
    if tabs is None or tabs.count() != 5:
        raise RuntimeError("Desktop bank detail tabs were not initialized.")
    captures = []
    names = ["general", "loans", "transactions", "analytics", "extra"]
    for index, name in enumerate(names):
        tabs.setCurrentIndex(index)
        app.processEvents()
        path = output / f"bank-account-{name}-desktop-offscreen.png"
        if not dialog.grab().save(str(path), "PNG"):
            raise RuntimeError(f"Could not capture {name} tab.")
        captures.append(str(path.resolve()))
    dialog.close()
    db.close()
    app.quit()
    print(json.dumps({"headless": True, "tabs": names, "account_columns": len(dialog.account_cols), "transaction_rows": dialog.txn_total, "linked_loans": len(dialog.loans), "screenshots": captures}, ensure_ascii=True))


if __name__ == "__main__":
    main()
