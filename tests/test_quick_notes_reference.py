"""Fast-note schema and settings-page behavior for the reference layout."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel

from src.database import Database
from src.ui.pages.quick_notes_settings_widget import QuickNotesSettingsWidget
from src.ui.widgets.animated_toggle import AnimatedToggle


def test_fast_note_display_fields_keep_legacy_data_and_toggle_behavior(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "fast_notes_reference.db"))
    page = None
    try:
        db.add_fast_note(
            "Ariza Notu", "EKRAN KIRIK", 1, 7, "Cep Telefonu", "Ariza Hizli Secimi"
        )
        note = db.get_fast_notes()[0]
        note_id = note[0]
        assert note[:5] == (note_id, "Ariza Notu", "EKRAN KIRIK", 1, 7)
        assert note[5:7] == ("Cep Telefonu", "Ariza Hizli Secimi")

        db.update_fast_note(
            note_id, "EKRAN DEGISTI", 1, "Ariza Notu", 8,
            "Cep Telefonu", "Islem Detayi",
        )
        updated = db.get_fast_notes()[0]
        assert updated[2] == "EKRAN DEGISTI"
        assert updated[4:7] == (8, "Cep Telefonu", "Islem Detayi")

        page = QuickNotesSettingsWidget(db)
        assert page.table.columnCount() == 6
        assert page.table.rowCount() == 1
        category_cell = page.table.cellWidget(0, 1)
        assert any(
            isinstance(label, QLabel) and label.text() == "Cep Telefonu"
            for label in category_cell.findChildren(QLabel)
        )
        assert page.table.cellWidget(0, 2).text() == "EKRAN DEGISTI"

        status_cell = page.table.cellWidget(0, 4)
        toggle = status_cell.findChild(AnimatedToggle)
        assert toggle is not None and toggle.isChecked()
        toggle.setChecked(False)
        app.processEvents()
        assert db.get_fast_notes()[0][3] == 0
    finally:
        if page is not None:
            page.close()
            page.deleteLater()
        db.close()
        app.processEvents()
