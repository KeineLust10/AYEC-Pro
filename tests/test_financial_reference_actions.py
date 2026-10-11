import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtCore import QRect
from PyQt6.QtGui import QImage, QPainter, QPen, QColor, QBrush
from PyQt6.QtWidgets import QApplication, QLabel, QStyleOptionViewItem

from src.database import Database
from src.ui.pages.accounting_page import AccountingPage
from src.ui.pages.finance.check_note_page import CheckNotePage
from src.ui.widgets.financial_reference_controls import FinancialReferenceActionButton, FinancialMetricGlyph
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_check_note_reference_filters_search_seeded_rows(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "check_note_reference_filters.db"))
    seed_visual_fixture(db)
    page = CheckNotePage(db, None)
    try:
        assert page.table.rowCount() == 4
        for row in range(page.table.rowCount()):
            status_cell = page.table.cellWidget(row, 9)
            status_chip = status_cell.findChild(QLabel) if status_cell else None
            assert status_chip is not None
            status_qss = status_chip.styleSheet()
            assert status_qss.count("{") == 1
            assert status_qss.count("}") == 1
        first_serial = page.table.item(0, 6)
        assert first_serial.text() == "CK-\n8849201"
        assert first_serial.data(Qt.ItemDataRole.UserRole + 2) == "CK-8849201"
        assert not page.btn_export.icon().isNull()
        page.reference_filter_buttons["checks"].click()
        assert page.table.rowCount() == 2
        page.reference_filter_buttons["notes"].click()
        assert page.table.rowCount() == 2
        page.reference_filter_buttons["endorsed"].click()
        assert page.table.rowCount() == 1
        page.reference_filter_buttons["all"].click()
        page.search_input.setText("Ahmet")
        assert page.table.rowCount() == 1
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_native_financial_actions_keep_all_original_callbacks(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(AccountingPage, "refresh_data", lambda self: None)
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    callbacks = ["export_to_excel", "export_to_pdf", "print_ledger", "open_collection_dialog",
                 "open_income_dialog", "open_expense_dialog", "open_transfer_dialog", "open_tax_dialog"]
    calls = []
    for callback in callbacks:
        monkeypatch.setattr(AccountingPage, callback, lambda self, *args, key=callback: calls.append(key))
    db = Database(str(tmp_path / "financial_reference_actions.db"))
    page = AccountingPage(db, None)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    page.resize(1088, 988)
    page.show()
    app.processEvents()
    changes = db.conn.total_changes
    try:
        assert len(page.findChildren(FinancialMetricGlyph)) == 7
        assert len(page.quick_action_buttons) == len(callbacks)
        for index, button in enumerate(page.quick_action_buttons):
            assert isinstance(button, FinancialReferenceActionButton)
            assert not button.grab().isNull()
            button.click()
            assert calls == callbacks[:index + 1]
        for index, button in enumerate(page.reference_header_actions):
            button.click()
            assert calls[-1] == callbacks[index]
        for button, callback in zip(page.reference_command_actions, ("open_income_dialog", "open_expense_dialog", "open_collection_dialog")):
            assert isinstance(button, FinancialReferenceActionButton)
            assert not button.stacked
            assert button.height() == 24
            assert not button.grab().isNull()
            button.click()
            assert calls[-1] == callback
        page._financial_summary = {"hot_cash": 33.50, "pending": 17.75}
        for _ in range(3):
            page.update_footer()
            app.processEvents()
            assert page.ledger_pager_frame.parentWidget() is page.reference_ledger_footer
            assert page.ledger_next_button.isVisible()
            assert page.reference_ledger_footer.height() == 32
        page.ledger_has_more = True
        page._update_ledger_pagination()
        page.ledger_next_button.click()
        assert page.ledger_current_page == 1
        page._update_ledger_pagination()
        page.ledger_prev_button.click()
        assert page.ledger_current_page == 0
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_reference_ledger_delegate_preserves_painter_state_between_cells(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(AccountingPage, "refresh_data", lambda self: None)
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "financial_delegate_state.db"))
    seed_visual_fixture(db)
    page = AccountingPage(db, None)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    page.on_data_loaded(page.finance_manager.get_unified_ledger(100), page.finance_manager.get_financial_summary("fiscal"), False)
    delegate = page.table.itemDelegate()
    try:
        cases = [(1, column, 180) for column in (0, 1, 2, 5, 6, 7)]
        cases.extend([(0, 0, 600), (0, 0, 800)])
        for row, column, width in cases:
            image = QImage(width, 55, QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.transparent)
            painter = QPainter(image)
            painter.setPen(QPen(QColor("#123456"), 2))
            painter.setBrush(QBrush(QColor("#654321")))
            painter.setClipRect(QRect(2, 2, width - 10, 50))
            original = (painter.pen(), painter.brush(), painter.font(), painter.clipRegion(), painter.transform())
            option = QStyleOptionViewItem()
            option.initFrom(page.table)
            option.widget = page.table
            option.rect = QRect(0, 0, width, 55)
            try:
                delegate.paint(painter, option, page.table.model().index(row, column))
                assert (painter.pen(), painter.brush(), painter.font(), painter.clipRegion(), painter.transform()) == original
            finally:
                painter.end()
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_reference_description_keeps_metadata_and_original_detail_actions(monkeypatch, tmp_path):
    import src.ui.pages._accounting_table_mixin as table_module

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(AccountingPage, "refresh_data", lambda self: None)
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    opened = []

    class Details:
        def __init__(self, db, entry, parent):
            opened.append(entry)

        def exec(self):
            return 0

    monkeypatch.setattr(table_module, "TransactionDetailsDialog", Details)
    db = Database(str(tmp_path / "financial_description.db"))
    seed_visual_fixture(db)
    page = AccountingPage(db, None)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        entries = page.finance_manager.get_unified_ledger(100)
        descriptions = [entry["description"] for entry in entries]
        page.on_data_loaded(entries, page.finance_manager.get_financial_summary("fiscal"), False)
        changes = db.conn.total_changes
        item = page.table.item(1, 2)
        entry = item.data(Qt.ItemDataRole.UserRole)
        assert entry["description"] in item.text()
        assert entry["customer_name"] in item.text()
        assert item.toolTip() == item.text()
        page.on_table_double_click(1, 2)
        assert opened == [entry]
        row_count = page.table.rowCount()
        page.on_table_double_click(0, 0)
        assert page.table.rowCount() < row_count
        page.on_table_double_click(0, 0)
        assert page.table.rowCount() == row_count
        assert [entry["description"] for entry in entries] == descriptions
        repeated = {"description": "Ref: EXISTING | Customer", "ref_no": "EXISTING", "customer_name": "Customer"}
        assert page._ledger_description_text(repeated) == repeated["description"]
        assert page._ledger_description_text({"description": "First\nSecond"}) == "First\nSecond"
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
