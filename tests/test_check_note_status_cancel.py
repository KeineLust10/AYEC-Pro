import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog

from src.database import Database
from src.ui.pages.finance import check_note_page
from src.ui.pages.finance.check_note_page import CheckNotePage


def test_canceling_bank_selection_keeps_check_status_and_finance_unchanged(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "check_status_cancel.db"))
    check_id = db.add_check_note(
        {
            "type": "Check",
            "direction": "Giri\u015f (Al\u0131nan)",
            "portfolio_no": "QA-CANCEL-1",
            "amount": 125.0,
            "due_date": "2026-11-01",
            "issuer": "QA Customer",
            "recipient": "AYEC Pro",
            "bank_name": "QA Bank",
            "branch_name": "Central",
            "check_no": "QA-CANCEL-1",
            "description": "Status cancel regression",
            "status": "Portf\u00f6yde",
        }
    )
    page = CheckNotePage(db, None)
    transactions = []
    monkeypatch.setattr(db, "get_bank_accounts", lambda: [{"id": 1, "bank_name": "QA Bank"}])
    monkeypatch.setattr(db, "add_transaction", lambda **values: transactions.append(values))
    monkeypatch.setattr(QDialog, "exec", lambda self: 0)
    monkeypatch.setattr(check_note_page, "show_success", lambda *_args: None)
    monkeypatch.setattr(check_note_page, "show_error", lambda *_args: None)
    try:
        page.change_status(check_id, "Tahsil Edildi")
        db.cursor.execute("SELECT status FROM checks_notes WHERE id=?", (check_id,))
        assert db.cursor.fetchone()[0] == "Portf\u00f6yde"
        assert transactions == []
    finally:
        page.close()
        db.close()
