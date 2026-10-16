from types import SimpleNamespace
import os
import csv
import sqlite3
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QTableWidgetItem, QPushButton, QFileDialog, QLabel
from PyQt6.QtCore import QDate
from PyQt6.QtTest import QTest

from src.ui.pages.service_status_page import ServiceStatusPage
from src.utils.design_system import DesignTokens


class _Item:
    def __init__(self, value):
        self.value = value

    def text(self):
        return self.value


class _Table:
    def __init__(self, records):
        self.records = records
        self.hidden = {}

    def rowCount(self):
        return len(self.records)

    def item(self, row, column):
        return _Item(self.records[row][column])

    def setRowHidden(self, row, hidden):
        self.hidden[row] = hidden


def _page(records, critical=False):
    return SimpleNamespace(
        table=_Table(records),
        status_filter_category="all",
        btn_status_filter=SimpleNamespace(isChecked=lambda: critical),
    )


def test_reference_status_categories_filter_rows_without_dropping_records():
    page = _page([
        {3: "TESL\u0130M ED\u0130LD\u0130", 6: "NORMAL"},
        {3: "PAR\u00c7A BEKL\u0130YOR", 6: "AC\u0130L"},
        {3: "TAM\u0130RDE", 6: "NORMAL"},
    ])

    page.status_filter_category = "delivered"
    ServiceStatusPage._apply_status_filters(page)
    assert page.table.hidden == {0: False, 1: True, 2: True}

    page.status_filter_category = "parts"
    ServiceStatusPage._apply_status_filters(page)
    assert page.table.hidden == {0: True, 1: False, 2: True}

    page.status_filter_category = "all"
    ServiceStatusPage._apply_status_filters(page)
    assert page.table.hidden == {0: False, 1: False, 2: False}


def test_critical_filter_combines_with_selected_category():
    page = _page([
        {3: "TESL\u0130M ED\u0130LD\u0130", 6: "NORMAL"},
        {3: "PAR\u00c7A BEKL\u0130YOR", 6: "AC\u0130L"},
    ], critical=True)
    page.status_filter_category = "all"

    ServiceStatusPage._apply_status_filters(page)

    assert page.table.hidden == {0: True, 1: False}


def test_status_refresh_timer_and_initial_load_pause_while_hidden(monkeypatch):
    app = QApplication.instance() or QApplication([])
    load_calls = []
    monkeypatch.setattr(ServiceStatusPage, "load_data", lambda self: load_calls.append(self))
    page = ServiceStatusPage(SimpleNamespace(get_setting=lambda key, default=None: default))

    page.show()
    app.processEvents()
    page.hide()
    app.processEvents()
    QTest.qWait(180)

    assert load_calls == []
    assert not page.refresh_timer.isActive()
    assert not page._initial_load_timer.isActive()

    page.show()
    app.processEvents()
    QTest.qWait(180)
    assert load_calls == [page]
    assert page.refresh_timer.isActive()

    page.hide()
    app.processEvents()
    assert not page.refresh_timer.isActive()

    page._last_load_at = time.monotonic() - 31
    page.show()
    page.hide()
    app.processEvents()
    QTest.qWait(20)
    assert load_calls == [page]

    page.show()
    app.processEvents()
    QTest.qWait(20)
    assert load_calls == [page, page]
    page.close()


def test_native_status_pagination_sort_search_and_export_keep_service_identity(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ServiceStatusPage, "load_data", lambda self: None)
    page = ServiceStatusPage(SimpleNamespace(get_setting=lambda key, default=None: default))
    assert page.table.columnWidth(0) == 100
    assert page.table.columnWidth(4) == 72
    page.table.setRowCount(15)
    opened = []
    for row in range(15):
        tracking = "SRV-{:02d}".format(row)
        for column, value in enumerate((tracking, "Customer", "Device", "TESLIM EDILDI" if row % 2 else "TAMIRDE", "2026-09-01", "-", "NORMAL", "")):
            page.table.setItem(row, column, QTableWidgetItem(value))
        button = QPushButton("Open")
        button.clicked.connect(lambda checked=False, ref=tracking: opened.append(ref))
        page.table.setCellWidget(row, 7, button)
    page._apply_status_filters()
    assert page.status_page_label.text() == "1 / 3"
    assert page.table.item(0, 0).text() == "SRV-14"
    assert sum(not page.table.isRowHidden(row) for row in range(15)) == 7
    page.table.cellWidget(0, 7).click()
    assert opened == ["SRV-14"]
    page.status_next.click()
    assert page.status_page_label.text() == "2 / 3"
    path = tmp_path / "status.csv"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *args: (str(path), "CSV"))
    page.export_status_snapshot()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        assert len(list(csv.reader(handle))) == 16
    page.status_sort.setCurrentIndex(1)
    assert page.status_page == 0
    assert page.table.item(0, 0).text() == "SRV-00"
    page.status_search.setText("SRV-14")
    assert len(page._matching_status_rows) == 1
    assert page.table.item(page._matching_status_rows[0], 0).text() == "SRV-14"
    page.status_filter_buttons["delivered"].click()
    assert page._matching_status_rows == []
    page.close()


def test_status_delivery_column_preserves_estimate_and_open_signal(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE devices (id INTEGER, tracking_no TEXT, customer_name TEXT, device_brand TEXT, device_model TEXT, status TEXT, entry_date TEXT, estimated_date TEXT, urgency TEXT, delivered_at TEXT, exit_date TEXT, is_deleted INTEGER, is_archived INTEGER)")
    connection.executemany("INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
        (1, "SRV-A", "Customer A", "Brand", "Model", "TESLIM EDILDI", "2026-09-01", "2026-09-03", "NORMAL", "2026-09-04", "2026-09-05", 0, 0),
        (2, "SRV-B", "Customer B", "Brand", "Model", "PARCA BEKLIYOR", "2026-09-02", "2026-09-06", "ACIL", "", "", 0, 0),
        (3, "SRV-C", "Customer C", "Brand", "Model", "TESLIME HAZIR", "2026-09-03", "2026-09-06", "NORMAL", "", "", 0, 0),
    ])
    monkeypatch.setattr(ServiceStatusPage, "_refresh_status_assistant", lambda self: None)
    monkeypatch.setattr(ServiceStatusPage, "_refresh_status_flow", lambda self: None)
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default)
    page = ServiceStatusPage(db)
    changes = connection.total_changes
    assert page.status_sort.property("referenceChevron")
    assert page.status_sort.height() == 30
    assert page.marquee.font().family() == DesignTokens.FONT_NAME
    timer_rules = dict(rule.strip().split(":", 1) for rule in page.lbl_timer.styleSheet().split(";") if ":" in rule)
    assert timer_rules["background"].strip() != timer_rules["color"].strip()
    checked_rules = page.btn_status_filter.styleSheet().split("QPushButton:checked{", 1)[1].split("}", 1)[0]
    checked_colors = dict(rule.split(":", 1) for rule in checked_rules.split(";") if ":" in rule)
    assert checked_colors["background"] != checked_colors["color"]
    opened = []
    page.load_data()
    monkeypatch.setattr(page, "_open_service_detail", opened.append)
    assert page.table.columnCount() == 9
    assert page.table.isColumnHidden(5)
    page.status_estimated_toggle.setChecked(True)
    assert not page.table.isColumnHidden(5)
    for direction in (1, 0):
        page.status_sort.setCurrentIndex(direction)
        rows = {page.table.item(row, 0).text(): row for row in range(page.table.rowCount())}
        delivered = rows["SRV-A"]
        assert page.table.item(delivered, 5).text() == "2026-09-03"
        assert page.table.item(delivered, 8).text() == "2026-09-04"
        delegate = page.table.itemDelegateForColumn(4)
        assert delegate.displayText(page.table.item(delivered, 4).text(), page.locale()) == "2026-09-\n01"
        assert page.table.item(delivered, 4).text() == "2026-09-01"
        for column in (0, 4, 5, 8):
            item = page.table.item(delivered, column)
            assert item.font().family() == DesignTokens.MONO_FONT_NAME
            assert item.toolTip() == item.text()
        assert page.table.item(delivered, 3).font().family() == DesignTokens.FONT_NAME
        assert delegate.displayText("-", page.locale()) == "-"
        assert page.table.item(rows["SRV-B"], 8).text() == "-"
        for row in rows.values():
            for column in (3, 6):
                badge = page.table.cellWidget(row, column).findChild(QLabel)
                assert badge.text() == page.table.item(row, column).text()
        page.table.cellWidget(delivered, 7).findChild(QPushButton, "status_view").click()
    assert opened == ["SRV-A", "SRV-A"]
    printed, messages = [], []
    page.main_window = SimpleNamespace(pages={"service_list": SimpleNamespace(
        print_service=printed.append,
        open_context_menu_action=lambda kind, ref: messages.append((kind, ref)),
    )})
    page.load_data()
    delivered = next(row for row in range(page.table.rowCount()) if page.table.item(row, 0).text() == "SRV-A")
    actions = page.table.cellWidget(delivered, 7)
    assert len(actions.findChildren(QPushButton)) == 3
    actions.findChild(QPushButton, "status_print").click()
    actions.findChild(QPushButton, "status_sms").click()
    assert printed == ["SRV-A"]
    assert messages == [("sms", "SRV-A")]
    page.set_status_category("delivered")
    assert [page.table.item(row, 0).text() for row in page._matching_status_rows] == ["SRV-A"]
    page.set_status_category("active")
    assert [page.table.item(row, 0).text() for row in page._matching_status_rows] == ["SRV-C"]
    assert connection.total_changes == changes
    page.close()
    connection.close()


def test_status_metrics_use_real_dates_capacity_and_ignore_deleted_records(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE devices (entry_date TEXT, delivered_at TEXT, exit_date TEXT, status TEXT, urgency TEXT, is_deleted INTEGER, is_archived INTEGER)")
    today = QDate.currentDate()
    date = lambda days: today.addDays(days).toString("yyyy-MM-dd")
    connection.executemany("INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?, ?)", [
        (date(0), date(0), "", "TESLIM EDILDI", "NORMAL", 0, 0),
        (date(-4), "", date(-2), "TESLIM EDILDI", "NORMAL", 0, 0),
        (date(-3), "", "", "TAMIRDE", "NORMAL", 0, 0),
        (date(-1), "", "", "TESLIME HAZIR", "NORMAL", 0, 0),
        (date(0), "", "", "PARCA BEKLIYOR", "ACIL", 0, 0),
        (date(-1), "", "", "IPTAL", "ACIL", 0, 0),
        (date(0), "", "", "PARCA BEKLIYOR", "ACIL", 1, 0),
        (date(0), "", "", "PARCA BEKLIYOR", "ACIL", 0, 1),
    ])
    monkeypatch.setattr(ServiceStatusPage, "load_data", lambda self: None)
    db = SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: "1" if key == "workshop_capacity" else default)
    page = ServiceStatusPage(db)
    changes = connection.total_changes
    page._update_status_metrics()
    assert [label.text() for label in page.status_kpi_values] == ["2 Cihaz", "%300", "1 Cihaz Bekliyor", "1.0 G\u00fcn"]
    assert connection.total_changes == changes
    db.get_setting = lambda key, default=None: default
    page._update_status_metrics()
    assert page.status_kpi_values[1].text() == "-"
    assert "3 cihaz" in page.status_kpi_values[1].toolTip()
    connection.execute("UPDATE devices SET delivered_at='',exit_date='' WHERE status='TESLIM EDILDI'")
    page._update_status_metrics()
    assert page.status_kpi_values[3].text() == "-"
    page.close()
    connection.close()


def test_status_assistant_uses_real_sources_and_preserves_navigation(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE appointments (date TEXT,time TEXT,customer_name TEXT,description TEXT,status TEXT,is_deleted INTEGER)")
    today = QDate.currentDate().toString("yyyy-MM-dd")
    connection.executemany("INSERT INTO appointments VALUES (?, ?, ?, ?, ?, ?)", [
        (today, "10:00", "Actual customer", "Actual visit", "Bekliyor", 0),
        (today, "11:00", "Completed", "Done", "Tamamland\u0131", 0),
        (today, "12:00", "Deleted", "Hidden", "Bekliyor", 1),
        (today, "13:00", "Cancelled", "Hidden", "\u0130PTAL", 0),
    ])
    connection.execute("CREATE TABLE parts (name TEXT,stock REAL,min_stock REAL,is_deleted INTEGER)")
    connection.executemany("INSERT INTO parts VALUES (?, ?, ?, ?)", [("Actual cable", 1, 2, 0), ("Healthy", 10, 5, 0), ("Deleted", 0, 5, 1)])
    connection.execute("CREATE TABLE personnel (name TEXT,role TEXT,status TEXT,is_deleted INTEGER,is_active INTEGER)")
    connection.executemany("INSERT INTO personnel VALUES (?, ?, ?, ?, ?)", [
        ("Actual technician", "TEKN\u0130SYEN", "Gorevde", 0, 1),
        ("Manager", "Yonetici", "Busy", 0, 1),
        ("Inactive", "Teknisyen", "Busy", 0, 0),
        ("Deleted", "Saha", "Busy", 1, 1),
    ])
    monkeypatch.setattr(ServiceStatusPage, "load_data", lambda self: None)
    routes = []
    page = ServiceStatusPage(SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default),
                             SimpleNamespace(on_menu_click=routes.append))
    changes = connection.total_changes
    page._refresh_status_assistant()
    assert "1 bekleyen randevu" in page.status_appointment_notice.text()
    assert "Actual customer" in page.status_appointment_notice.text()
    assert "Actual cable" in page.status_stock_notice.text()
    assert "Deleted" not in page.status_stock_notice.text()
    assert page.status_personnel_layout.count() == 1
    first_person = page.status_personnel_layout.itemAt(0).widget()
    assert any("Actual technician" in label.text() for label in first_person.findChildren(QLabel))
    assert any("Gorevde" in label.text() for label in first_person.findChildren(QLabel))
    for button in (page.status_appointment_button, page.status_stock_button, page.status_personnel_button):
        button.click()
    assert routes == [30, 50, 10]
    assert connection.total_changes == changes
    connection.execute("UPDATE appointments SET status='Tamamland\u0131'")
    connection.execute("UPDATE parts SET stock=10")
    page._refresh_status_assistant()
    assert "0 bekleyen randevu" in page.status_appointment_notice.text()
    assert "bulunmuyor" in page.status_stock_notice.text()
    assert page.status_personnel_layout.count() == 1
    page.close()
    connection.close()


def test_hourly_flow_counts_admissions_without_guessing_missing_times(monkeypatch):
    app = QApplication.instance() or QApplication([])
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE devices (entry_date TEXT,is_deleted INTEGER,is_archived INTEGER)")
    today = QDate.currentDate().toString("yyyy-MM-dd")
    connection.executemany("INSERT INTO devices VALUES (?, ?, ?)", [
        (today + " 09:15:00", 0, 0), (today + "T09:45:00", 0, 0),
        (today + " 14:10:00", 0, 0), (today, 0, 0),
        (today + " invalid", 0, 0), (today + " 09:30:00", 1, 0),
        (today + " 09:30:00", 0, 1),
        (QDate.currentDate().addDays(-1).toString("yyyy-MM-dd") + " 09:30:00", 0, 0),
    ])
    monkeypatch.setattr(ServiceStatusPage, "load_data", lambda self: None)
    page = ServiceStatusPage(SimpleNamespace(cursor=connection.cursor(), get_setting=lambda key, default=None: default))
    changes = connection.total_changes
    page._refresh_status_flow()
    assert page.status_flow_chart.counts[9] == 2
    assert page.status_flow_chart.counts[14] == 1
    assert sum(page.status_flow_chart.counts) == 3
    assert "09:00 (2 cihaz)" in page.status_flow_note.text()
    assert "2 kay\u0131tta saat yok" in page.status_flow_note.text()
    assert connection.total_changes == changes
    page.status_flow_chart.resize(700, 86)
    assert not page.status_flow_chart.grab().isNull()
    connection.execute("DELETE FROM devices")
    page._refresh_status_flow()
    assert not any(page.status_flow_chart.counts)
    assert "Saat bilgili" in page.status_flow_note.text()
    page.close()
    connection.close()
