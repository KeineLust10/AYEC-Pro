import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QPushButton, QLabel, QFileDialog
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtTest import QTest

from src.ui.pages.external_tracking_page import ExternalTrackingPage
from src.utils.design_system import DesignTokens
from src.utils.theme_manager import ThemeManager


APP = QApplication.instance() or QApplication([])


class _Db:
    def get_external_trackings(self):
        return [
            (1, "GAR-001", "Alpha", "Laptop", "Service A", "A-1", "2026-09-10", "", "", "Onar\u0131mda", ""),
            (2, "GAR-002", "Beta", "Router", "Service B", "B-2", "2026-08-20", "", "", "Geri Geldi", ""),
            (3, "GAR-003", "Alpha", "Camera", "Service A", "A-3", "2026-09-22", "", "", "\u0130ade Bekleniyor", ""),
        ]


def test_reference_tracking_fonts_literal_cargo_and_saved_values():
    import sqlite3

    columns = ('id', 'internal_tracking_no', 'customer_name', 'product_name',
               'external_service_name', 'external_service_no', 'sent_date',
               'outbound_cargo_no', 'inbound_cargo_no', 'status', 'notes',
               'warranty_coverage', 'repair_cost')
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    connection.execute('CREATE TABLE tracking (' + ', '.join(columns) + ')')
    values = list(_Db().get_external_trackings()[0])
    values[1] = 'GAR-2026-0089'
    values[6] = '2026-09-10 14:30:00'
    values[7] = '<Actual Cargo> 4598210348'
    values.extend(('Manufacturer warranty', 4250.0))
    connection.execute('INSERT INTO tracking VALUES (' + ','.join('?' for _ in columns) + ')', values)
    before = connection.total_changes
    db = _Db()
    db.get_external_trackings = lambda: connection.execute('SELECT * FROM tracking').fetchall()
    page = ExternalTrackingPage(db)
    try:
        assert page.table.columnCount() == 9
        assert page.table.columnWidth(0) >= 130
        assert page.table.item(0, 0).text().startswith(values[1])
        assert page.table.item(0, 0).toolTip() == page.table.item(0, 0).text()
        assert page.table.item(0, 3).toolTip() == values[6]
        for column in (0, 3, 8):
            assert page.table.item(0, column).font().family() == DesignTokens.MONO_FONT_NAME
        cargo = page.table.cellWidget(0, 4)
        assert cargo.textFormat() == Qt.TextFormat.PlainText
        assert values[7] in cargo.text()
        assert cargo.toolTip() == cargo.text()
        assert cargo.font().family() == DesignTokens.MONO_FONT_NAME
        assert page.table.item(0, 8).text() == '4250.0'
        assert page.table.item(0, 8).toolTip() == '4250.0'
        for control in (page.status_filter, page.service_filter, page.month_filter):
            assert control.property('referenceChevron')
        assert tuple(page.records[0]) == tuple(values)
        assert connection.total_changes == before
    finally:
        page.close()
        connection.close()


def test_compact_header_and_panned_row_actions_keep_full_controls():
    page = ExternalTrackingPage(_Db())
    old_theme = ThemeManager._current_theme
    try:
        page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        ThemeManager.apply_theme(APP, 'Koyu Mavi', window=page, animate=False)
        ThemeManager.refresh_widget_tree(page)
        page.resize(1008, 988)
        page.show()
        QTest.qWait(30)
        assert page.lbl_sub.wordWrap()
        assert page.lbl_sub.font().family() == DesignTokens.FONT_NAME
        assert page.lbl_sub.font().pixelSize() == 13
        assert page.header_frame.rect().contains(QRect(page.lbl_sub.mapTo(page.header_frame, QPoint()), page.lbl_sub.size()))
        bar = page.table.horizontalScrollBar()
        assert bar.maximum() > 0 and bar.isVisible()
        bar.setValue(bar.maximum())
        APP.processEvents()
        edited, deleted = [], []
        page.edit_record = lambda record: edited.append(record[0])
        page.delete_record = deleted.append
        buttons = page.table.cellWidget(0, 6).findChildren(QPushButton)
        assert len(buttons) == 2
        for button in buttons:
            rectangle = QRect(button.mapTo(page.table.viewport(), QPoint()), button.size())
            assert page.table.viewport().rect().contains(rectangle)
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert edited == [1] and deleted == [1]
    finally:
        page.close()
        ThemeManager.apply_theme(APP, old_theme, animate=False)


def test_external_tracking_search_status_service_and_month_filters():
    page = ExternalTrackingPage(_Db())

    assert page.table.rowCount() == 3
    page.search.setText("alpha")
    assert [page.table.isRowHidden(index) for index in range(3)] == [False, True, False]

    page.search.clear()
    page.status_filter.setCurrentIndex(page.status_filter.findData("Onar\u0131mda"))
    page.service_filter.setCurrentIndex(page.service_filter.findData("Service A"))
    page.month_filter.setCurrentIndex(page.month_filter.findData("2026-09"))
    assert [page.table.isRowHidden(index) for index in range(3)] == [False, True, True]
    assert page.sync_footer.text() == "G\u00f6sterilen 1 / 1 kay\u0131t"
    page.close()


def test_reference_columns_badges_and_actions_preserve_record_mapping():
    page = ExternalTrackingPage(_Db())
    assert page.table.columnCount() == 9
    assert [page.table.horizontalHeader().logicalIndex(index) for index in range(9)] == [0, 1, 2, 3, 4, 7, 8, 5, 6]
    assert page.table.item(0, 7).text() == "-"
    assert page.table.item(0, 8).text() == "-"
    assert "sifir" in page.table.item(0, 8).toolTip()
    assert page.table.cellWidget(0, 5).findChild(QLabel).text() == "Onar\u0131mda"
    edited = []
    deleted = []
    page.edit_record = lambda record: edited.append(record[0])
    page.delete_record = deleted.append
    buttons = page.table.cellWidget(1, 6).findChildren(QPushButton)
    buttons[0].click()
    buttons[1].click()
    assert edited == [2]
    assert deleted == [2]
    page.search.setText("Alpha")
    assert page.table.height() < 400
    assert page.stats_layout.count() == 4
    page.close()


def test_report_exports_filtered_snapshot_with_all_sqlite_columns(monkeypatch):
    import sqlite3
    import pandas as pd
    from src.ui.utils import ui_helpers

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE tracking (id INTEGER, internal_tracking_no TEXT, customer_name TEXT, product_name TEXT, external_service_name TEXT, external_service_no TEXT, sent_date TEXT, outbound_cargo_no TEXT, inbound_cargo_no TEXT, status TEXT, notes TEXT)")
    connection.executemany("INSERT INTO tracking VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", _Db().get_external_trackings())
    db = _Db()
    db.get_external_trackings = lambda: connection.execute("SELECT * FROM tracking").fetchall()
    page = ExternalTrackingPage(db)
    page.search.setText("Alpha")
    page.page_size = 1
    page._apply_filters()
    exported = []
    errors = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: ("test.xlsx", "Excel"))
    monkeypatch.setattr(pd.DataFrame, "to_excel", lambda frame, *args, **kwargs: exported.append(frame.copy()))
    monkeypatch.setattr(ui_helpers, "show_success", lambda *args: None)
    monkeypatch.setattr(ui_helpers, "show_error", lambda *args: errors.append(args))
    page.export_to_csv()
    assert errors == []
    assert exported[0]["ID"].tolist() == [1, 3]
    assert exported[0]["Emanet No"].tolist() == ["GAR-001", "GAR-003"]
    assert exported[0]["Urun"].tolist() == ["Laptop", "Camera"]
    assert len(exported[0].columns) == 11
    page.close()
    connection.close()


def test_manifest_preview_uses_filtered_or_selected_records_and_escapes_html(monkeypatch):
    from PyQt6 import QtPrintSupport
    from types import SimpleNamespace

    page = ExternalTrackingPage(_Db())
    page.search.setText("Alpha")
    page.page_size = 1
    page._apply_filters()
    previews = []

    class _Preview:
        def __init__(self, printer, parent):
            self.paintRequested = SimpleNamespace(connect=lambda callback: previews.append(callback.__self__.toPlainText()))

        def setWindowTitle(self, title):
            pass

        def exec(self):
            return 0

    monkeypatch.setattr(QtPrintSupport, "QPrintPreviewDialog", _Preview)
    class _Printer:
        PrinterMode = SimpleNamespace(HighResolution=1)

        def __init__(self, mode):
            assert mode == self.PrinterMode.HighResolution

    monkeypatch.setattr(QtPrintSupport, 'QPrinter', _Printer)
    page.print_cargo_manifest()
    assert "GAR-001" in previews[0] and "GAR-003" in previews[0]
    assert "GAR-002" not in previews[0]
    page.table.selectRow(2)
    page.print_cargo_manifest()
    assert "GAR-003" in previews[1] and "GAR-001" not in previews[1]
    record = list(_Db().get_external_trackings()[0])
    record[2] = "<script>unsafe</script>"
    markup = page._cargo_manifest_html([record])
    assert "<script>" not in markup
    assert "&lt;script&gt;unsafe&lt;/script&gt;" in markup
    assert not page.cargo_sync_button.isEnabled()
    page.close()


def test_open_and_selected_export_keep_visible_record_identity(monkeypatch):
    import pandas as pd
    from src.ui.pages import external_tracking_page as module

    db = _Db()
    page = ExternalTrackingPage(db)
    db.get_external_trackings = lambda: list(reversed(_Db().get_external_trackings()))
    opened = []
    page.edit_record = lambda record: opened.append(record[0])
    page.open_selected_record(0)
    assert opened == [1]
    exported = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: ("selected.xlsx", "Excel"))
    monkeypatch.setattr(pd.DataFrame, "to_excel", lambda frame, *args, **kwargs: exported.append(frame.copy()))
    monkeypatch.setattr(module, "show_success", lambda *args: None)
    page.export_selected_to_excel([0])
    assert exported[0]["emanet_no"].tolist() == ["GAR-001"]
    page.close()
