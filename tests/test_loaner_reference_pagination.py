import os
import csv
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QDateTime, QPoint, QRect, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QPushButton, QFileDialog

from src.ui.pages.loaner_devices_page import LoanerDevicesPage
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.theme_colors import qc
from src.utils.design_system import DesignTokens
from src.utils.theme_manager import ThemeManager


APP = QApplication.instance() or QApplication([])


def test_active_loan_actions_column_expands_to_use_table_width(monkeypatch):
    page = _page(monkeypatch)
    try:
        page.resize(1920, 1080)
        page.show()
        APP.processEvents()
        header = page.table_active.horizontalHeader()
        assert header.sectionResizeMode(7) == header.ResizeMode.Fixed
        assert header.sectionResizeMode(1) == header.ResizeMode.Stretch
        assert header.sectionResizeMode(2) == header.ResizeMode.Stretch
        assert page.table_active.columnWidth(7) <= 200
    finally:
        page.close()


class _Db:
    class _Cursor:
        def execute(self, *_args):
            return self

        def fetchall(self):
            return []

    cursor = _Cursor()

    def get_setting(self, _key, default=None):
        return default

    def get_internal_setting(self, _key, default=None):
        return "0"


def _page(monkeypatch):
    monkeypatch.setattr(LoanerDevicesPage, "_prepare_initial_view", lambda self: None)
    monkeypatch.setattr(LoanerDevicesPage, "request_refresh", lambda self: None)
    return LoanerDevicesPage(_Db())


def _records():
    now = QDateTime.currentDateTime()
    return [dict(id=index, device_id=index, brand_model="Device {}".format(index),
                 customer_name="Customer {}".format(index), customer_phone="555",
                 date_given=now.addDays(-5).toString("yyyy-MM-dd HH:mm:ss"),
                 expected_return=now.addDays(-2 if index == 1 else 3).toString("yyyy-MM-dd HH:mm:ss"),
                 daily_penalty_fee=50)
            for index in range(1, 8)]


def test_refresh_vector_keeps_original_callback_and_disabled_state(monkeypatch):
    calls = []
    monkeypatch.setattr(LoanerDevicesPage, '_prepare_initial_view', lambda self: None)
    monkeypatch.setattr(LoanerDevicesPage, 'request_refresh', lambda self: calls.append('refresh'))
    page = LoanerDevicesPage(_Db())
    try:
        assert page.btn_refresh.accessibleName() == 'RefreshLoanerDevices'
        assert page.btn_refresh.toolTip() == 'Yenile'
        assert page.refresh_glyph.kind == 'refresh'
        page.refresh_glyph.grab()
        assert page.refresh_glyph._renderer.isValid()
        assert page.refresh_glyph._render_key == ('refresh', qc('text_muted').name())
        page.btn_refresh.click()
        assert calls == ['refresh']
        page.btn_refresh.setEnabled(False)
        page.refresh_glyph.grab()
        assert page.refresh_glyph._render_key == ('refresh', qc('border').name())
        page.btn_refresh.click()
        assert calls == ['refresh']
        page.btn_refresh.setEnabled(True)
        page.btn_refresh.click()
        assert calls == ['refresh', 'refresh']
    finally:
        page.close()


def test_active_loan_numeric_typography_preserves_records_and_full_timestamps(monkeypatch):
    page = _page(monkeypatch)
    records = _records()
    records[0]['tracking_no'] = 'SRV-2026-0042'
    before = [dict(record) for record in records]
    try:
        page.load_active_loans(records)
        assert page.table_active.columnCount() == 10
        for row in range(page.table_active.rowCount()):
            for column in (0, 3, 4, 6, 8, 9):
                assert page.table_active.item(row, column).font().family() == DesignTokens.MONO_FONT_NAME
            assert page.table_active.item(row, 3).toolTip() == records[row]['date_given']
            assert page.table_active.item(row, 4).toolTip() == records[row]['expected_return']
        assert page.table_active.item(0, 8).text() == 'SRV-2026-0042'
        assert page.table_active.item(0, 8).toolTip() == 'SRV-2026-0042'
        assert records == before
    finally:
        page.close()


def test_compact_loan_table_pans_to_complete_original_actions(monkeypatch):
    page = _page(monkeypatch)
    old_theme = ThemeManager._current_theme
    try:
        ThemeManager.apply_theme(APP, 'Koyu Mavi', window=page, animate=False)
        ThemeManager.refresh_widget_tree(page)
        page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        page.load_active_loans(_records())
        page.resize(980, 988)
        page.show()
        QTest.qWait(30)
        table = page.table_active
        bar = table.horizontalScrollBar()
        assert bar.maximum() > 0
        assert bar.isVisible()
        assert table.columnWidth(1) >= 180
        assert table.columnWidth(8) >= 140
        bar.setValue(bar.maximum())
        APP.processEvents()
        button = table.cellWidget(0, 7).findChild(QPushButton)
        rectangle = QRect(button.mapTo(table.viewport(), QPoint()), button.size())
        assert table.viewport().rect().contains(rectangle)
        returned = []
        page.return_device = lambda transaction, device: returned.append((transaction, device))
        QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert returned == [('1', 1)]
    finally:
        page.close()
        ThemeManager.apply_theme(APP, old_theme, animate=False)


def test_active_pagination_filters_and_return_mapping(monkeypatch):
    page = _page(monkeypatch)
    records = _records()
    records[0]["serial_mac"] = "SERIAL-001"
    records[0]["tracking_no"] = "SRV-001"
    page.load_active_loans(records)
    assert "SERIAL-001" in page.table_active.item(0, 1).text()
    assert page.table_active.item(0, 8).text() == "SRV-001"
    assert page.table_active.item(0, 9).text() == "5 G\u00fcn"
    assert page.table_active.item(0, 3).toolTip() == records[0]["date_given"]
    assert page.table_active.rowCount() == 7
    assert [page.table_active.isRowHidden(row) for row in range(7)] == [False] * 5 + [True] * 2
    page.active_next.click()
    assert page.active_page_label.text() == "2 / 2"
    assert [page.table_active.isRowHidden(row) for row in range(7)] == [True] * 5 + [False] * 2
    returned = []
    page.return_device = lambda transaction, device: returned.append((transaction, device))
    page.table_active.cellWidget(6, 7).findChild(QPushButton).click()
    assert returned == [("7", 7)]
    page.loaner_search.setText("Customer 2")
    assert page.active_page == 0
    assert [row for row in range(7) if not page.table_active.isRowHidden(row)] == [1]
    page.loaner_search.clear()
    page.loaner_status.setCurrentText("Geciken")
    assert [row for row in range(7) if not page.table_active.isRowHidden(row)] == [0]
    page.close()


def test_metrics_use_current_dates_and_available_inventory(monkeypatch):
    page = _page(monkeypatch)
    inventory = [dict(id=index, status="Depoda" if index > 7 else "Musteride",
                      device_type="Laptop", brand_model="Device {}".format(index))
                 for index in range(1, 11)]
    page._update_loaner_metrics(inventory, _records())
    assert [label.text() for label in page.loaner_metric_values] == ["7 Cihaz", "3 Cihaz", "1 Acil", "-"]
    assert "10 Adet" in page.loaner_summary_details[0].text()
    assert sum(page.loaner_category_ring.counts) == 10
    assert "3 Hazir" in page.loaner_summary_details[2].text()
    assigned = []
    page.assign_device = assigned.append
    page.findChild(QPushButton, "LoanerReserve8").click()
    assert assigned == [8]
    inventory[0]["status"] = "Depoda"
    page._update_loaner_metrics(inventory, _records())
    assert page.loaner_metric_values[1].text() == "3 Cihaz"
    records = _records()
    records[0]["expected_return"] = "invalid"
    page.load_active_loans(records)
    page._update_loaner_metrics(inventory, records)
    assert page.loaner_metric_values[2].text() == "0 Acil"
    assert "Gecikti" not in page.table_active.item(0, 5).text()
    page.close()


def test_export_includes_all_filtered_pages_and_preserves_column_order(monkeypatch, tmp_path):
    page = _page(monkeypatch)
    page.load_active_loans(_records())
    output = tmp_path / "loaner.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output), "CSV"))
    page.active_next.click()
    page._show_export_notice()
    with output.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream, delimiter=";"))
    assert len(rows) == 8
    assert len(rows[0]) == 9
    assert rows[0][3] == "\u0130lgili Kay\u0131t"
    assert rows[-1][0] == "7"
    page.loaner_search.setText("Customer 3")
    page._show_export_notice()
    with output.open(encoding="utf-8-sig", newline="") as stream:
        filtered = list(csv.reader(stream, delimiter=";"))
    assert len(filtered) == 2
    assert filtered[1][0] == "3"
    page.close()


def test_reference_navigation_routes_and_overdue_view(monkeypatch):
    page = _page(monkeypatch)
    page.load_active_loans(_records())
    page._loaner_nav_buttons[2][2].click()
    assert page.tabs.currentWidget() is page.tab_active
    assert page.loaner_status.currentText() == "Geciken"
    assert [row for row in range(7) if not page.table_active.isRowHidden(row)] == [0]
    page._loaner_nav_buttons[1][2].click()
    assert page.tabs.currentWidget() is page.tab_inventory
    assert page.loaner_status.currentText() == "Tum Durumlar"
    page._loaner_nav_buttons[0][2].click()
    assert page.tabs.currentWidget() is page.tab_active
    assert sum(not page.table_active.isRowHidden(row) for row in range(7)) == 5
    page._loaner_nav_buttons[3][2].click()
    assert page.tabs.currentWidget() is page.tab_return_history
    page._open_commitments_tab()
    assert page._loaner_nav_buttons[4][2].isChecked()
    page.close()


def test_return_history_query_search_and_export(monkeypatch, tmp_path):
    page = _page(monkeypatch)
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE loaner_devices (id INTEGER, brand_model TEXT, serial_mac TEXT, device_type TEXT)")
    cursor.execute("INSERT INTO loaner_devices VALUES (1, 'Laptop', 'SN-100', 'Laptop')")
    cursor.execute("CREATE TABLE loaner_transactions (id INTEGER, device_id INTEGER, customer_name TEXT, date_given TEXT, expected_return TEXT, date_returned TEXT, penalty_applied REAL, condition_in TEXT, status TEXT)")
    cursor.executemany("INSERT INTO loaner_transactions VALUES (?, 1, ?, '2026-09-01', '2026-09-20', ?, ?, 'Good', ?)",
                       [(1, "Customer One", "2026-09-22", 100, "Completed"),
                        (2, "Customer Two", "2026-09-23", 200, "Completed"),
                        (3, "Customer Active", None, 0, "Aktif")])
    page.db.cursor = cursor
    page._select_loaner_view(page.tab_return_history, "Tum Durumlar")
    assert page.table_return_history.rowCount() == 2
    assert page.table_return_history.item(0, 0).text() == "2"
    assert "SN-100" in page.table_return_history.item(0, 1).text()
    page.loaner_search.setText("Customer One")
    assert page.table_return_history.isRowHidden(0)
    assert not page.table_return_history.isRowHidden(1)
    assert page.loaner_history_count.text() == "1 / 2 kayit"
    output = tmp_path / "history.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output), "CSV"))
    page._show_export_notice()
    with output.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream, delimiter=";"))
    assert len(rows) == 2
    assert len(rows[0]) == 9
    assert rows[1][7] == "Good"
    page.loaner_search.clear()
    page.loaner_type_buttons["video"].click()
    assert page.loaner_history_count.text() == "0 / 2 kayit"
    page.loaner_type_buttons["pc"].click()
    assert page.loaner_history_count.text() == "2 / 2 kayit"
    connection.close()
    page.close()


def test_new_loan_uses_only_available_devices_and_preserves_add_device(monkeypatch):
    page = _page(monkeypatch)
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE loaner_devices (id INTEGER, brand_model TEXT, serial_mac TEXT, status TEXT)")
    cursor.executemany("INSERT INTO loaner_devices VALUES (?, ?, 'Serial', ?)",
                       [(1, "A Busy", "Depoda"), (2, "B Ready", "Depoda"), (3, "C Away", "Musteride")])
    cursor.execute("CREATE TABLE loaner_transactions (device_id INTEGER, status TEXT)")
    cursor.execute("INSERT INTO loaner_transactions VALUES (1, 'Aktif')")
    page.db.cursor = cursor
    assigned = []
    page.assign_device = assigned.append
    monkeypatch.setattr(ModernDialog, "exec", lambda self: ModernDialog.DialogCode.Accepted)
    page._start_new_loan()
    assert assigned == [2]
    monkeypatch.setattr(ModernDialog, "exec", lambda self: ModernDialog.DialogCode.Rejected)
    page._start_new_loan()
    assert assigned == [2]
    assert any(button.text() == "+ Yeni Cihaz Ekle" for button in page.tab_inventory.findChildren(QPushButton))
    connection.close()
    page.close()


def test_device_type_filters_use_metadata_not_customer_text(monkeypatch, tmp_path):
    page = _page(monkeypatch)
    records = _records()
    types = ["Laptop", "Switch", "Kamera", "Router", "Sunucu", "NVR", "Telefon"]
    for record, device_type in zip(records, types):
        record["device_type"] = device_type
    records[6]["customer_name"] = "Laptop Switch Camera Customer"
    page.load_active_loans(records)
    page.active_next.click()
    page.loaner_type_buttons["network"].click()
    assert page.active_page == 0
    assert [row for row in range(7) if not page.table_active.isRowHidden(row)] == [1, 3]
    page.loaner_type_buttons["pc"].click()
    assert [row for row in range(7) if not page.table_active.isRowHidden(row)] == [0, 4]
    page.loaner_type_buttons["video"].click()
    assert [row for row in range(7) if not page.table_active.isRowHidden(row)] == [2, 5]
    output = tmp_path / "video.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(output), "CSV"))
    page._show_export_notice()
    with output.open(encoding="utf-8-sig", newline="") as stream:
        exported = list(csv.reader(stream, delimiter=";"))
    assert [row[0] for row in exported[1:]] == ["3", "6"]
    assert LoanerDevicesPage._loaner_type_group("APC UPS") == "other"
    assert LoanerDevicesPage._loaner_type_group("Magaza Telefon") == "other"
    assert LoanerDevicesPage._loaner_type_group("Diz\u00fcst\u00fc / \u0130\u015f \u0130stasyonu") == "pc"
    page.loaner_type_buttons["all"].click()
    assert len(page._active_export_rows) == 7
    page.loaner_search.setText("existing query")
    page._focus_loaner_search()
    assert page.loaner_search.selectedText() == "existing query"
    page.close()
