import os
import sqlite3
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QTableWidgetItem, QLabel, QPushButton, QToolButton
from PyQt6.QtCore import QDate, QPoint, QRect, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QFontMetrics
from src.ui.pages.job_service_tracking_page import JobServiceTrackingPage
from src.ui.widgets.reference_date_edit import ReferenceDateEdit
from src.utils.design_system import DesignTokens
from src.utils.theme_manager import ThemeManager
from src.ui.widgets.financial_reference_controls import ReferenceMetricValueLabel

APP = QApplication.instance() or QApplication([])


def test_native_service_report_fonts_dates_and_offscreen_canvas(tmp_path):
    from src.database import Database
    from tools.quality.desktop_visual_acceptance import ROOT, seed_visual_fixture

    db = Database(str(tmp_path / 'native_service_report.db'))
    seed_visual_fixture(db)
    before = db.conn.total_changes
    page = JobServiceTrackingPage(db)
    old_theme = ThemeManager._current_theme
    try:
        page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        ThemeManager.apply_theme(APP, 'Koyu Mavi', window=page, animate=False)
        ThemeManager.refresh_widget_tree(page)
        page.resize(1280, 1184)
        page.show()
        page.tabs.setCurrentWidget(page.service_tab)
        APP.processEvents()
        assert page.service_table.columnCount() == 9
        assert page.service_table.rowCount() == 15
        assert page.service_table.rowHeight(0) == 54
        viewport = page.service_table.viewport()
        badge = page.service_table.cellWidget(0, 2).findChild(QLabel)
        assert viewport.rect().contains(QRect(badge.mapTo(viewport, QPoint()), badge.size()))
        assert badge.height() == 24
        calls = []
        page._open_service_archive_detail = lambda tracking: calls.append(('detail', tracking))
        page._open_service_technician_panel = lambda tracking: calls.append(('technician', tracking))
        page._open_service_form = lambda tracking: calls.append(('form', tracking))
        buttons = page.service_table.cellWidget(0, 8).findChildren(QPushButton)
        assert len(buttons) == 3
        tracking = page.service_table.item(0, 0).text()
        for button in buttons:
            assert viewport.rect().contains(QRect(button.mapTo(viewport, QPoint()), button.size()))
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert calls == [('detail', tracking), ('technician', tracking), ('form', tracking)]
        for row in range(page.service_table.rowCount()):
            for column in (0, 4, 5, 6):
                assert page.service_table.item(row, column).font().family() == DesignTokens.MONO_FONT_NAME
            tracking = page.service_table.item(row, 0).text()
            dates = db.conn.execute('SELECT entry_date, exit_date FROM devices WHERE tracking_no=?', (tracking,)).fetchone()
            assert dates is not None
            assert page.service_table.item(row, 5).toolTip() == str(dates[0] or '')
            assert page.service_table.item(row, 6).toolTip() == str(dates[1] or '')
        assert db.conn.total_changes == before
        path = ROOT / 'artifacts' / 'report_service_reference.png'
        path.parent.mkdir(parents=True, exist_ok=True)
        assert page.grab().save(str(path))
    finally:
        page.close()
        ThemeManager.apply_theme(APP, old_theme, animate=False)
        db.close()


def test_report_reference_dates_filters_and_original_change_callbacks(monkeypatch):
    for method in ('load_jobs', 'load_services', 'update_stat_cards', '_refresh_profitability'):
        monkeypatch.setattr(JobServiceTrackingPage, method, lambda self: None)
    connection = sqlite3.connect(':memory:')
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = JobServiceTrackingPage(db)
    old_theme = ThemeManager._current_theme
    try:
        page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        ThemeManager.apply_theme(APP, 'Koyu Mavi', window=page, animate=False)
        ThemeManager.refresh_widget_tree(page)
        page.resize(1280, 1184)
        page.show()
        APP.processEvents()
        for control in (page.report_date_from, page.report_date_to):
            assert isinstance(control, ReferenceDateEdit)
            assert control.height() == 34
            assert control.displayFormat() == 'dd.MM.yyyy'
            assert control.font().family() == DesignTokens.MONO_FONT_NAME
            QTest.mouseClick(control, Qt.MouseButton.LeftButton, pos=QPoint(control.width() - 12, control.height() // 2))
            APP.processEvents()
            assert control.calendarWidget().isVisible()
            control.calendarWidget().window().hide()
        for control in (page.job_status_filter, page.job_currency_filter, page.job_technician_filter):
            assert control.property('referenceChevron')
            assert control.height() == 32
        amount = page.card_total_revenue.findChild(ReferenceMetricValueLabel)
        assert amount is not None
        original = amount.text()
        amount.setText('459,621.16 TRY')
        amount.resize(180, 42)
        font = amount.amount_font(amount.text(), amount.primary_size)
        assert font.family() == DesignTokens.MONO_FONT_NAME
        assert QFontMetrics(font).horizontalAdvance(amount.text()) <= amount.contentsRect().width() - 4
        assert amount.toolTip() == amount.text()
        assert not amount.grab().isNull()
        amount.setText(original)
        calls = []
        page.apply_job_filter = lambda: calls.append('jobs')
        page.apply_service_filter = lambda: calls.append('services')
        page._refresh_profitability = lambda: calls.append('profitability')
        page.report_date_from.setDate(QDate(2026, 9, 2))
        assert page.report_date_enabled.isChecked()
        assert calls == ['jobs', 'services', 'profitability']
        assert page.report_date_from.date() == QDate(2026, 9, 2)
    finally:
        page.close()
        ThemeManager.apply_theme(APP, old_theme, animate=False)
        connection.close()


def test_job_report_counts_matching_credits_without_losing_job_details(monkeypatch, tmp_path):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE customers (id INTEGER, name TEXT, is_deleted INTEGER)")
    connection.execute("INSERT INTO customers VALUES (1, 'Customer', 0)")
    connection.execute("CREATE TABLE currency_transactions (customer_id INTEGER, tracking_no TEXT, description TEXT, transaction_type TEXT, amount REAL, currency TEXT, created_at TEXT)")
    connection.executemany("INSERT INTO currency_transactions VALUES (1, ?, ?, ?, ?, 'TRY', ?)", [
        ("JOB-1", "Original repair", "DEBIT", 100, "2026-09-01"),
        ("JOB-1", "Payment note", "CREDIT", 100, "2026-09-10"),
        ("JOB-2", "Other repair", "DEBIT", 200, "2026-09-02"),
        ("JOB-2", "Partial payment", "CREDIT", 50, "2026-09-11"),
        ("CREDIT-ONLY", "Unmatched credit", "CREDIT", 20, "2026-09-12"),
    ])
    connection.execute("UPDATE currency_transactions SET currency='USD' WHERE tracking_no='JOB-2'")
    monkeypatch.setattr(JobServiceTrackingPage, "load_services", lambda self: None)
    monkeypatch.setattr(JobServiceTrackingPage, "update_stat_cards", lambda self: None)
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = JobServiceTrackingPage(db)
    assert page.job_table.rowCount() == 2
    assert page.job_table.columnCount() == 10
    rows = {page.job_table.item(row, 0).text(): row for row in range(2)}
    paid = rows["JOB-1"]
    assert page.job_table.item(paid, 8).text() == "Al\u0131nd\u0131"
    assert page.job_table.item(rows["JOB-2"], 8).text() == "K\u0131smi \u00d6deme"
    detail_calls = []
    monkeypatch.setattr(page, "_open_job_detail", lambda row: detail_calls.append(row))
    action_buttons = page.job_table.cellWidget(paid, 9).findChildren(QToolButton)
    assert len(action_buttons) == 2
    action_buttons[0].click()
    assert detail_calls == [paid]
    from PyQt6.QtWidgets import QFileDialog
    job_pdf_path = tmp_path / "job.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(job_pdf_path), "PDF"))
    action_buttons[1].click()
    assert job_pdf_path.read_bytes().startswith(b"%PDF-")
    assert job_pdf_path.stat().st_size > 1000
    for row in rows.values():
        for column in (0, 4, 5, 6):
            assert page.job_table.item(row, column).font().family() == DesignTokens.MONO_FONT_NAME
    assert page.job_table.item(paid, 4).data(Qt.ItemDataRole.UserRole) == 100
    assert page.job_table.item(paid, 4).toolTip() == '100.00'
    assert page.job_table.item(paid, 5).toolTip() == '2026-09-01'
    assert page.job_table.item(paid, 2).text() == "Tahsil Edildi"
    assert page.job_table.item(paid, 3).text() == "Original repair"
    assert page.job_table.item(paid, 5).text() == "01.09.2026"
    assert page.job_table.item(rows["JOB-2"], 2).text() == "A\u00e7\u0131k"
    page.job_status_filter.setCurrentIndex(page.job_status_filter.findData("Tahsil Edildi"))
    assert page.job_table.isRowHidden(rows["JOB-2"])
    assert not page.job_table.isRowHidden(paid)
    page.job_currency_filter.setCurrentIndex(page.job_currency_filter.findData("USD"))
    assert all(page.job_table.isRowHidden(row) for row in range(2))
    page.job_status_filter.setCurrentIndex(0)
    assert not page.job_table.isRowHidden(rows["JOB-2"])
    assert page.job_table.isRowHidden(paid)
    page.job_search_input.setText("no matching record")
    page.apply_job_filter()
    assert page.job_result_label.text() == "G\u00f6r\u00fcnt\u00fclenen: 0 / 2 \u0130\u015f Kayd\u0131 \u2022 Sayfa: 1 / 1"
    page.job_search_input.clear()
    page.job_currency_filter.setCurrentIndex(0)
    assert not any(page.job_table.isRowHidden(row) for row in range(2))
    pdf_path = tmp_path / "report.pdf"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(pdf_path), "PDF"))
    page.btn_pdf.click()
    assert pdf_path.read_bytes().startswith(b"%PDF-")
    assert pdf_path.stat().st_size > 1000
    assert page.job_table.cellWidget(paid, 2).findChild(QLabel).text() == "Tahsil Edildi"
    page.job_advanced_button.click()
    assert not page.job_advanced_panel.isHidden()
    page.job_amount_min.setValue(100)
    page.job_amount_max.setValue(150)
    page.job_amount_enabled.setChecked(True)
    assert page._job_matching_rows == [paid]
    assert len(page._report_export_data()[1]) == 1
    page.job_amount_min.setValue(160)
    assert page._job_matching_rows == []
    page.job_advanced_reset.click()
    assert len(page._job_matching_rows) == 2
    assert not page.job_amount_min.isEnabled()
    assert page.job_customer_filter.findData("Customer") > 0
    page.report_date_from.setDate(QDate(2026, 9, 2))
    page.report_date_to.setDate(QDate(2026, 9, 2))
    assert page.report_date_enabled.isChecked()
    assert page._job_matching_rows == [rows["JOB-2"]]
    assert len(page._report_export_data()[1]) == 1
    page.service_table.setRowCount(2)
    for row, name in enumerate(("Visible", "Other")):
        for column, value in enumerate((name, name, "Teslim Edildi", "Device", "100", "02.09.2026", "", "Alice", "")):
            page.service_table.setItem(row, column, QTableWidgetItem(value))
    page.service_search_input.setText("Visible")
    page._service_category = "teslim"
    page.apply_service_filter()
    assert not page.service_table.isRowHidden(0)
    assert page.service_table.isRowHidden(1)
    page.tabs.setCurrentWidget(page.service_tab)
    service_headings, service_values = page._report_export_data()
    assert len(service_headings) == 8
    assert len(service_values) == 1
    page.report_date_to.setDate(QDate(2026, 9, 1))
    assert all(page.service_table.isRowHidden(row) for row in range(2))
    assert page._job_matching_rows == []
    page.report_date_enabled.setChecked(False)
    assert len(page._job_matching_rows) == 2
    page.close()
    connection.close()


def test_advanced_customer_filter_resets_pagination_and_preserves_currency(monkeypatch):
    monkeypatch.setattr(JobServiceTrackingPage, "load_jobs", lambda self: None)
    monkeypatch.setattr(JobServiceTrackingPage, "load_services", lambda self: None)
    monkeypatch.setattr(JobServiceTrackingPage, "update_stat_cards", lambda self: None)
    page = JobServiceTrackingPage(SimpleNamespace(cursor=None, get_setting=lambda key, default=None: default))
    page.job_table.setRowCount(20)
    for row in range(20):
        customer = "Client A" if row < 10 else "Client B"
        for column, value in enumerate(("JOB-{}".format(row), customer, "Open", "Repair", "1,500.00", "01.09.2026", "TRY" if row % 2 else "USD", "Alice")):
            page.job_table.setItem(row, column, QTableWidgetItem(value))
    page._update_job_filter_options()
    page.apply_job_filter()
    page.job_next.click()
    assert page.job_page == 1
    page.job_customer_filter.setCurrentIndex(page.job_customer_filter.findData("Client B"))
    assert page.job_page == 0
    assert len(page._job_matching_rows) == 10
    page.job_currency_filter.setCurrentIndex(page.job_currency_filter.findData("USD"))
    assert len(page._job_matching_rows) == 5
    page.job_amount_min.setValue(1500)
    page.job_amount_max.setValue(1500)
    page.job_amount_enabled.setChecked(True)
    assert len(page._job_matching_rows) == 5
    assert all(values[1] == "Client B" for values in page._report_export_data()[1])
    page.job_advanced_reset.click()
    assert page.job_currency_filter.currentData() == "USD"
    assert len(page._job_matching_rows) == 10
    page.close()


def test_report_pagination_and_technician_filter_preserve_row_identity(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE customers (id INTEGER, name TEXT, is_deleted INTEGER)")
    connection.execute("INSERT INTO customers VALUES (1, 'Customer', 0)")
    connection.execute("CREATE TABLE currency_transactions (customer_id INTEGER, tracking_no TEXT, description TEXT, transaction_type TEXT, amount REAL, currency TEXT, created_at TEXT)")
    connection.execute("CREATE TABLE devices (tracking_no TEXT, technician TEXT, is_deleted INTEGER)")
    for index in range(20):
        tracking = "JOB-{:02d}".format(index)
        connection.execute("INSERT INTO currency_transactions VALUES (1, ?, 'Repair', 'DEBIT', 100, 'TRY', '2026-09-01')", (tracking,))
        connection.execute("INSERT INTO devices VALUES (?, ?, 0)", (tracking, "Alice" if index < 10 else "Bob"))
    monkeypatch.setattr(JobServiceTrackingPage, "load_services", lambda self: None)
    monkeypatch.setattr(JobServiceTrackingPage, "update_stat_cards", lambda self: None)
    page = JobServiceTrackingPage(SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default))
    assert page.job_page_label.text() == "1 / 2"
    assert sum(not page.job_table.isRowHidden(row) for row in range(20)) == 15
    page.job_next.click()
    assert page.job_page_label.text() == "2 / 2"
    assert sum(not page.job_table.isRowHidden(row) for row in range(20)) == 5
    page.job_select_all.click()
    assert page.job_selection_label.text() == "Se\u00e7ilen: 5 sat\u0131r"
    assert all(not page.job_table.isRowHidden(index.row()) for index in page.job_table.selectionModel().selectedRows())
    page.job_table.clearSelection()
    headings, values = page._report_export_data()
    assert len(values) == 20
    assert [value[0] for value in values] == [page.job_table.item(row, 0).text() for row in page._job_matching_rows]
    assert values[0][2] in ("Alice", "Bob")
    import pandas as pd
    from PyQt6.QtWidgets import QFileDialog
    exported = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: ("report.xlsx", "Excel"))
    monkeypatch.setattr(pd.DataFrame, "to_excel", lambda frame, path, index: exported.append((frame.copy(), path, index)))
    page.btn_excel.click()
    assert len(exported[0][0]) == 20
    assert list(exported[0][0].columns) == headings
    assert exported[0][1:] == ("report.xlsx", False)
    page.job_technician_filter.setCurrentIndex(page.job_technician_filter.findData("Alice"))
    assert page.job_page == 0
    assert len(page._job_matching_rows) == 10
    assert all(page.job_table.item(row, 7).text() == "Alice" for row in page._job_matching_rows)
    assert page.job_page_label.text() == "1 / 1"
    assert len(page._report_export_data()[1]) == 10
    selected = page._job_matching_rows[0]
    page.job_table.selectRow(selected)
    assert page.job_selection_label.text() == "Se\u00e7ilen: 1 sat\u0131r"
    assert [page.job_table.horizontalHeader().logicalIndex(index) for index in range(8)] == [0, 1, 7, 3, 2, 4, 6, 5]
    page.close()
    connection.close()


def test_report_print_markup_escapes_cells():
    markup = JobServiceTrackingPage._report_print_html(["<Title>"], [["Customer & <script>"]])
    assert "&lt;Title&gt;" in markup
    assert "Customer &amp; &lt;script&gt;" in markup
    assert "<script>" not in markup


def test_profitability_reuses_ledger_rules_without_writing_or_guessing_rates(monkeypatch):
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE currency_transactions (amount REAL, try_equivalent REAL, currency TEXT, transaction_type TEXT, created_at TEXT)")
    connection.execute("CREATE TABLE accounting (amount REAL, try_equivalent REAL, currency TEXT, type TEXT, date TEXT, customer_id INTEGER, category TEXT)")
    connection.executemany("INSERT INTO currency_transactions VALUES (?, ?, ?, ?, ?)", [
        (100, 4400, "USD", "DEBIT", "2026-09-30T23:59:59.999999+03:00"),
        (100, 4400, "USD", "CREDIT", "2026-09-30 12:00:00"),
        (999, 999, "TRY", "DEBIT", "2026-10-01"),
    ])
    connection.executemany("INSERT INTO accounting VALUES (?, NULL, 'TRY', ?, ?, ?, ?)", [
        (50, "Gelir", "2026-09-01", None, "Other"),
        (100, "Gelir", "2026-09-02", 1, "Tahsilat"),
        (80, "Gider", "2026-09-30", None, "Other"),
    ])
    monkeypatch.setattr(JobServiceTrackingPage, "load_jobs", lambda self: None)
    monkeypatch.setattr(JobServiceTrackingPage, "load_services", lambda self: None)
    monkeypatch.setattr(JobServiceTrackingPage, "update_stat_cards", lambda self: None)
    page = JobServiceTrackingPage(SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default))
    page.report_date_from.setDate(QDate(2026, 9, 1))
    page.report_date_to.setDate(QDate(2026, 9, 30))
    changes = connection.total_changes
    page.tabs.setCurrentWidget(page.profitability_tab)
    headings, values = page._report_export_data()
    assert len(headings) == 5
    assert values == [["2026-09-01 - 2026-09-30", "4,450.00", "80.00", "4,370.00", "98.2%"]]
    assert not page.profitability_period.isEnabled()
    assert connection.total_changes == changes
    connection.execute("INSERT INTO currency_transactions VALUES (20, NULL, 'EUR', 'DEBIT', '2026-09-20')")
    changes = connection.total_changes
    page._refresh_profitability()
    assert page._report_export_data()[1][0][1:] == ["-", "-", "-", "-"]
    assert "TRY" in page.profitability_status.text()
    assert connection.total_changes == changes
    page.report_date_from.setDate(QDate(2026, 10, 1))
    assert page._report_export_data()[1][0][1:] == ["-", "-", "-", "-"]
    page.close()
    connection.close()


def test_technician_matrix_uses_real_dates_and_drills_into_matching_services(monkeypatch):
    monkeypatch.setattr(JobServiceTrackingPage, "load_jobs", lambda self: None)
    monkeypatch.setattr(JobServiceTrackingPage, "load_services", lambda self: None)
    monkeypatch.setattr(JobServiceTrackingPage, "update_stat_cards", lambda self: None)
    page = JobServiceTrackingPage(SimpleNamespace(cursor=None, get_setting=lambda key, default=None: default))
    records = [
        ("SRV-1", "Teslim Edildi", "01.09.2026", "03.09.2026", "Alice"),
        ("SRV-2", "Tamamlandi", "01.09.2026", "05.09.2026", "Alice"),
        ("SRV-3", "Iptal", "02.09.2026", "", "Bob"),
        ("SRV-4", "Bekliyor", "01.09.2026", "", ""),
    ]
    page.service_table.setRowCount(len(records))
    for row, (tracking, status, start, end, technician) in enumerate(records):
        for column, value in enumerate((tracking, "Customer", status, "Device", "100", start, end, technician, "")):
            page.service_table.setItem(row, column, QTableWidgetItem(value))
    page.apply_service_filter()
    page.tabs.setCurrentWidget(page.technician_tab)
    headings, values = page._report_export_data()
    assert len(headings) == 6
    assert len(values) == 3
    alice = next(value for value in values if value[0] == "Alice")
    assert alice == ["Alice", "2", "0", "2", "0", "3.0"]
    bob = next(value for value in values if value[0] == "Bob")
    assert bob == ["Bob", "1", "0", "0", "1", "-"]
    alice_row = next(row for row in range(3) if page.technician_table.item(row, 0).text() == "Alice")
    page.technician_table.cellDoubleClicked.emit(alice_row, 0)
    assert page.tabs.currentWidget() is page.service_tab
    assert [not page.service_table.isRowHidden(row) for row in range(4)] == [True, True, False, False]
    page.service_search_clear_button.click()
    assert not any(page.service_table.isRowHidden(row) for row in range(4))
    page.report_date_from.setDate(QDate(2026, 9, 1))
    page.report_date_to.setDate(QDate(2026, 9, 1))
    page.tabs.setCurrentWidget(page.technician_tab)
    assert page.technician_table.rowCount() == 2
    page.close()
