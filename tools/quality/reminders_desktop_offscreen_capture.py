"""Capture the desktop reminder form and list in Qt offscreen mode."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.pages.reminders_page import RemindersPage
from src.utils.reference_typography import apply_reference_font
from src.utils.theme_manager import ThemeManager


OUTPUT = ROOT / "output" / "playwright"


def main() -> None:
    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    ThemeManager.apply_theme(app, "Koyu Mavi", animate=False)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    temporary = tempfile.TemporaryDirectory(prefix="ayec-reminders-desktop-audit-")
    database = Database(str(Path(temporary.name) / "reminders-audit.db"))
    page = RemindersPage(database)
    page.resize(960, 760)
    page.show()
    app.processEvents()
    form_path = OUTPUT / "reminders-desktop-form.png"
    if not page.grab().save(str(form_path), "PNG"):
        raise RuntimeError("Could not capture the desktop reminder form.")
    database.cursor.execute("INSERT INTO personnel(name,active) VALUES(?,1)", ("QA Tech",))
    database.conn.commit()
    personnel_id = database.cursor.lastrowid
    if not database.add_reminder("QA Reminder", personnel_id, "2026-10-20", "QA reminder details"):
        raise RuntimeError("Could not create the desktop reminder fixture.")
    page.load_reminders()
    page.tabs.setCurrentIndex(1)
    app.processEvents()
    list_path = OUTPUT / "reminders-desktop-list.png"
    if not page.grab().save(str(list_path), "PNG"):
        raise RuntimeError("Could not capture the desktop reminder list.")
    table = page.table
    report = {
        "form": str(form_path),
        "list": str(list_path),
        "table": {
            "width": table.width(),
            "height": table.height(),
            "header_height": table.horizontalHeader().height(),
            "row_height": table.rowHeight(0),
            "column_widths": [table.columnWidth(index) for index in range(table.columnCount())],
        },
    }
    print(report)
    page.close()
    database.conn.close()
    temporary.cleanup()


if __name__ == "__main__":
    main()
