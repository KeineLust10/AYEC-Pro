import os
import sqlite3
import csv

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QLabel
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QFontMetrics

from src.ui.pages.contracts_page import ContractsPage
from src.ui.widgets.financial_reference_controls import FinancialReferenceActionButton, ReferenceMetricValueLabel
from src.utils.design_system import DesignTokens


APP = QApplication.instance() or QApplication([])


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def execute(self, *_args, **_kwargs):
        return self

    def fetchall(self):
        return list(self._rows)


class _Db:
    def __init__(self):
        self.cursor = _Cursor([
            (index, f"Customer {index}", f"Contract {index}",
             "Gold SLA" if index % 2 else "Bakim", "2026-01-01", "2027-01-01", "Aktif", index * 1000)
            for index in range(1, 7)
        ])


def test_contract_reference_pagination_and_filters():
    page = ContractsPage(_Db())

    assert page.table.rowCount() == 6
    assert page.table.item(0, 8).text().startswith("1,000")
    assert page.table.item(0, 7).text() != "-"
    assert page.table.cellWidget(0, 6).findChild(QLabel).text() == page.table.item(0, 6).text()
    opened = []
    page.open_details = lambda: opened.append(page.table.item(page.table.currentRow(), 0).text())
    page.table.cellWidget(1, 9).click()
    assert opened == ["2"]
    assert [page.table.isRowHidden(index) for index in range(6)] == [
        False, False, False, False, True, True
    ]
    assert page.contract_page_label.text() == "1 / 2"

    page.contract_next.click()
    assert [page.table.isRowHidden(index) for index in range(6)] == [
        True, True, True, True, False, False
    ]

    page.contract_type_filter.setCurrentText("Bakim")
    assert page.contract_page_label.text() == "1 / 1"
    assert page.contract_result_label.text() == "Listelenen: 3 / 3 kayit"
    page.close()


def test_contract_footer_actions_navigate_and_table_avoids_empty_height():
    from types import SimpleNamespace

    db = _Db()
    db.cursor._rows = db.cursor._rows[:1]
    destinations = []
    page = ContractsPage(db, main_window=SimpleNamespace(on_menu_click=destinations.append))

    assert page.table.height() <= 120
    page.contract_footer_actions[0].click()
    assert destinations == [30]
    page.contract_footer_actions[1].setEnabled(True)
    page.contract_footer_actions[1].click()
    assert page.contract_status_filter == "Yenileme"
    page.close()


def test_contract_record_fonts_keep_complete_dates_prices_and_adaptive_volume():
    page = ContractsPage(_Db())
    try:
        assert page.table.columnCount() == 10
        for row in range(page.table.rowCount()):
            for column in (0, 4, 5, 8):
                item = page.table.item(row, column)
                assert item.font().family() == DesignTokens.MONO_FONT_NAME
                assert item.toolTip() == item.text()
                assert QFontMetrics(item.font()).horizontalAdvance(item.text()) + 16 <= page.table.columnWidth(column)
            assert page.table.item(row, 4).text() == '2026-01-01'
            assert page.table.item(row, 5).text() == '2027-01-01'
        volume = page.contract_metric_values[2]
        assert isinstance(volume, ReferenceMetricValueLabel)
        amount = '2,500,000.00 TRY'
        volume.setText(amount)
        volume.resize(140, 28)
        font = volume.amount_font(volume.text(), volume.primary_size)
        assert font.family() == DesignTokens.MONO_FONT_NAME
        assert QFontMetrics(font).horizontalAdvance(amount) <= volume.contentsRect().width() - 4
        assert volume.text() == volume.toolTip() == amount
        assert not volume.grab().isNull()
    finally:
        page.close()


def test_contract_delete_glyph_retains_existing_action(monkeypatch):
    calls = []
    monkeypatch.setattr(ContractsPage, 'delete_contract', lambda self: calls.append('delete'))
    page = ContractsPage(_Db())
    try:
        buttons = page.findChildren(FinancialReferenceActionButton)
        assert len(buttons) == 1
        button = buttons[0]
        assert button.text() == 'S\u00f6zle\u015fme Sil'
        assert button.glyph == 'delete'
        assert button.centered_inline and not button.stacked
        button.click()
        assert calls == ['delete']
        assert page.table.columnCount() == 10
        assert page.table.rowCount() == 6
    finally:
        page.close()


def test_sla_filter_unicode_search_and_shortcut_preserve_contract_rows():
    page = ContractsPage(_Db())
    page.contract_next.click()
    page.contract_sla_filter.setCurrentIndex(page.contract_sla_filter.findData("Gold SLA"))
    assert page.current_page == 0
    assert page._matching_contract_rows == [0, 2, 4]
    page.contract_type_filter.setCurrentText("Bakim")
    assert page._matching_contract_rows == []
    page.contract_type_filter.setCurrentText("Tum turler")
    page.table.item(0, 2).setText("\u0130\u015f Bak\u0131m\u0131")
    page.contract_search.setText("is bakimi")
    assert page._matching_contract_rows == [0]
    page.contract_search.clear()
    page.load_contracts()
    assert page.contract_sla_filter.currentData() == "Gold SLA"
    assert page._matching_contract_rows == [0, 2, 4]
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    page.show()
    APP.processEvents()
    APP.setActiveWindow(page)
    page.contract_search_shortcut.activated.emit()
    assert APP.focusWidget() is page.contract_search
    page.close()


def test_contract_expiry_and_renewal_filters_use_dates_and_exclusive_selection():
    page = ContractsPage(_Db())
    page.table.item(0, 5).setText(QDate.currentDate().addDays(-1).toString("yyyy-MM-dd"))
    page.table.item(1, 6).setText("Taslak")
    page.table.item(2, 5).setText(QDate.currentDate().addDays(14).toString("yyyy-MM-dd"))
    page._update_contract_metrics(21000)
    assert page.contract_metric_values[0].text() == "4"
    assert page.contract_metric_values[1].text() == "1"
    page.contract_status_buttons["Suresi"].click()
    assert [row for row in range(6) if not page.table.isRowHidden(row)] == [0]
    page.contract_status_buttons["Yenileme"].click()
    assert [row for row in range(6) if not page.table.isRowHidden(row)] == [2]
    assert sum(button.isChecked() for button in page.contract_status_buttons.values()) == 1
    page.close()


def test_contract_footer_reads_active_maintenance_and_routes_calendar():
    db = _Db()
    db.conn = sqlite3.connect(":memory:")
    db.conn.execute(
        "CREATE TABLE appointments (date TEXT, time TEXT, customer_name TEXT, description TEXT, "
        "status TEXT, personnel_name TEXT, is_deleted INTEGER)"
    )
    today = QDate.currentDate().toString("yyyy-MM-dd")
    db.conn.executemany("INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?, ?)", [
        (today, "10:00", "Live Company", "Bakim kontrolu", "Bekliyor", "Tech One", 0),
        (today, "11:00", "Deleted Company", "Bakim", "Bekliyor", "Tech Two", 1),
        (today, "12:00", "Cancelled Company", "Bakim", "\u0130ptal", "Tech Three", 0),
        (today, "13:00", "Repair Company", "Onarim", "Bekliyor", "Tech Four", 0),
    ])
    class Navigation:
        def __init__(self):
            self.visited = []

        def on_menu_click(self, page_id):
            self.visited.append(page_id)

    navigation = Navigation()
    page = ContractsPage(db, navigation)
    summary = page.contract_footer_details[0].text()
    assert "Live Company" in summary and "Tech One" in summary
    assert "Deleted Company" not in summary and "Cancelled Company" not in summary
    assert "Repair Company" not in summary
    page.contract_footer_actions[0].click()
    assert navigation.visited == [30]
    page.table.item(0, 5).setText(QDate.currentDate().addDays(14).toString("yyyy-MM-dd"))
    page._update_contract_metrics(21000)
    page.contract_footer_actions[1].click()
    assert [row for row in range(6) if not page.table.isRowHidden(row)] == [0]
    page.close()
    db.conn.close()


def test_contract_export_includes_all_matching_pages(tmp_path, monkeypatch):
    import src.ui.pages.contracts_page as contracts_module
    path = tmp_path / "contracts.csv"
    monkeypatch.setattr(contracts_module.QFileDialog, "getSaveFileName", lambda *_args: (str(path), "CSV (*.csv)"))
    monkeypatch.setattr(contracts_module, "show_success", lambda *_args: None)
    page = ContractsPage(_Db())
    page.contract_export_button.click()
    with path.open(encoding="utf-8-sig", newline="") as report:
        rows = list(csv.reader(report, delimiter=";"))
    assert len(rows) == 7
    assert rows[-1][0] == "6"
    page.contract_type_filter.setCurrentText("Bakim")
    page.contract_export_button.click()
    with path.open(encoding="utf-8-sig", newline="") as report:
        filtered = list(csv.reader(report, delimiter=";"))
    assert [row[0] for row in filtered[1:]] == ["2", "4", "6"]
    assert "1,000" not in str(filtered)
    page.close()
