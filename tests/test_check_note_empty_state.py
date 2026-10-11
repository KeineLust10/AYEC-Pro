import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QFrame

from src.database import Database
from src.ui.pages.finance.check_note_page import CheckNotePage


def test_check_note_table_shows_a_resizable_empty_state(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "checks.db"))
    db.get_checks_notes = lambda status_filter=None: []
    page = CheckNotePage(db, None)
    try:
        page.resize(1400, 850)
        page.show()
        app.processEvents()
        assert page.table.rowCount() == 0
        assert not page.empty_state.isHidden()
        assert page.empty_state.geometry() == page.table.viewport().rect()
        cards = [
            page.findChild(QFrame, "metric_detail_frame_" + key).parentWidget()
            for key in ("portfolio", "due", "received", "discounted")
        ]
        assert max(card.height() for card in cards) < 195
        assert sum(page.table.columnWidth(i) for i in range(page.table.columnCount())) >= page.table.viewport().width() - 2

        page.resize(1600, 850)
        app.processEvents()
        assert sum(page.table.columnWidth(i) for i in range(page.table.columnCount())) >= page.table.viewport().width() - 2

        page.table.setRowCount(1)
        page._update_empty_state()
        assert page.empty_state.isHidden()
    finally:
        page.close()
        db.conn.close()
