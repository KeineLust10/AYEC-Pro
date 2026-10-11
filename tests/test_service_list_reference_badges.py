import os
import sqlite3
import csv
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt, QPoint, QRect
from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QCheckBox, QStyle, QStyleOptionButton, QWidget
from PyQt6.QtTest import QTest

from src.database import Database
from src.ui.pages.service_list_page import ServiceListPage
from src.utils.theme_colors import tc
from src.utils.status_utils import normalize_device_status
from src.utils.theme_manager import ThemeManager
from tools.quality.desktop_visual_acceptance import ROOT, service_list_geometry_issues, seed_visual_fixture
from src.ui.widgets.financial_reference_controls import FinancialMetricGlyph
from src.utils.currency_helper import CurrencyHelper


def test_service_badges_keep_full_status_accessibility_and_fit_original_columns(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    original_font = app.font()
    font_id = QFontDatabase.addApplicationFont(str(ROOT / ".venv_active" / "Lib" / "site-packages" / "imgaug" / "DejaVuSans.ttf"))
    assert font_id >= 0, "Native offscreen font fixture is required for geometry checks"
    app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    db = Database(str(tmp_path / "service_badges.db"))
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    page.resize(1280, 1024)
    page.show()
    page.table.setRowCount(1)
    try:
        statuses = ["Tamirde", "Teslim Edildi", "\u0130ptal", "Par\u00e7a Bekliyor", "Test S\u00fcrecinde", "Onay Bekliyor", "Bekliyor"]
        changes = db.conn.total_changes
        for status in statuses:
            widget = page._create_status_badge(status)
            page.table.setCellWidget(0, 7, widget)
            page.table.setRowHeight(0, 58)
            app.processEvents()
            label = widget.findChild(QLabel)
            normalized = normalize_device_status(status)
            assert label.accessibleName() == normalized
            assert label.toolTip() == normalized
            assert label.height() == 18
            assert label.text() == normalized.replace("i", "\u0130").replace("\u0131", "I").upper()
            assert label.minimumSizeHint().width() <= label.width(), (normalized, label.font().toString(), label.styleSheet(), label.fontMetrics().horizontalAdvance(label.text()))
            assert "border-radius: 3px" in label.styleSheet()
            assert not widget.grab().isNull()
        for urgency in ("Normal", "Acil", "D\u00fc\u015f\u00fck"):
            widget = page._create_urgency_badge(urgency)
            label = widget.findChild(QLabel)
            assert label.text() == urgency
            assert label.accessibleName() == urgency
            assert label.height() == 18
            if urgency == "Acil":
                assert tc("finance_tertiary") in label.styleSheet()
            else:
                assert "background-color: transparent" in label.styleSheet()
            widget.deleteLater()
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
        app.setFont(original_font)


def test_reference_service_row_keeps_eight_visible_original_actions(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    original_font = app.font()
    original_theme = ThemeManager._current_theme
    font_id = QFontDatabase.addApplicationFont(str(ROOT / ".venv_active" / "Lib" / "site-packages" / "imgaug" / "DejaVuSans.ttf"))
    assert font_id >= 0
    app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    calls = []
    monkeypatch.setattr(ServiceListPage, "open_service_form_shortcut", lambda self, *args: calls.append(("create", None)))
    monkeypatch.setattr(ServiceListPage, "export_records", lambda self, *args: calls.append(("export", None)))
    monkeypatch.setattr(ServiceListPage, "open_context_menu_action", lambda self, action, tracking: calls.append((action, tracking)))
    for method, action in (("open_technician_panel", "edit"), ("print_service", "print"), ("change_status", "status"), ("delete_service", "delete")):
        monkeypatch.setattr(ServiceListPage, method, lambda self, tracking, key=action: calls.append((key, tracking)))
    db = Database(str(tmp_path / "service_actions.db"))
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page._filtered_records = [{"tracking_no": "DEMO-SRV-0001", "customer_name": "Fixture Customer", "device_brand": "AYEC", "device_model": "Test Device 01", "entry_date": "2026-09-30", "status": "Teslim Edildi", "urgency": "Normal", "price": 1000}]
        page._render_current_page()
        page.resize(1088, 988)
        ThemeManager.apply_theme(app, "Koyu Mavi", window=page, animate=False)
        ThemeManager.refresh_widget_tree(page)
        page._render_current_page()
        page.show()
        app.processEvents()
        page.grab().save(str(tmp_path / "service_list_reference.png"))
        changes = db.conn.total_changes
        assert page.table.columnCount() == 10
        assert len(page.findChildren(FinancialMetricGlyph)) == 7
        assert service_list_geometry_issues(page) == []
        assert all(not page.table.isColumnHidden(column) for column in range(10))
        assert sum(page.table.columnWidth(column) for column in range(10)) <= page.table.viewport().width() + 2
        actions = page.table.cellWidget(0, 9).findChildren(QPushButton)
        assert len(actions) == 8
        cell = page.table.visualRect(page.table.model().index(0, 9))
        for button, action in zip(actions, ("info", "edit", "print", "payment", "sms", "whatsapp", "status", "delete")):
            assert button.isVisible()
            assert button.accessibleName() == button.toolTip()
            rect = QRect(button.mapTo(page.table.viewport(), QPoint(0, 0)), button.size())
            assert cell.contains(rect), (action, cell, rect)
            assert page.table.viewport().rect().contains(rect)
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            assert calls[-1] == (action, "DEMO-SRV-0001")
        for column in (1, 6):
            item = page.table.item(0, column)
            from PyQt6.QtGui import QFontMetrics
            assert QFontMetrics(item.font()).horizontalAdvance(item.text()) <= page.table.columnWidth(column) - 16
            assert item.toolTip() == item.text()
        checkbox = page.table.cellWidget(0, 0).findChild(QCheckBox)
        option = QStyleOptionButton()
        checkbox.initStyleOption(option)
        indicator = checkbox.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, checkbox)
        assert checkbox.rect().contains(indicator)
        QTest.mouseClick(checkbox, Qt.MouseButton.LeftButton)
        assert checkbox.isChecked()
        page.btn_add_device.click()
        assert calls[-1] == ("create", None)
        page.btn_export.click()
        assert calls[-1] == ("export", None)
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
        ThemeManager.apply_theme(app, original_theme, animate=False)
        app.setFont(original_font)


def test_reference_bulk_menu_selects_visible_rows_exports_only_selected_and_uses_original_print(monkeypatch, tmp_path):
    import src.ui.pages.service_list_page as service_module

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    messages = []
    prints = []
    monkeypatch.setattr(service_module, "show_warning", lambda parent, text: messages.append(("warning", text)))
    monkeypatch.setattr(service_module, "show_success", lambda parent, text: messages.append(("success", text)))
    monkeypatch.setattr(ServiceListPage, "print_service", lambda self, tracking: prints.append(tracking))
    path = tmp_path / "selected_services.csv"
    monkeypatch.setattr(service_module.QFileDialog, "getSaveFileName", lambda *args: (str(path), "CSV"))
    db = Database(str(tmp_path / "service_bulk.db"))
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        assert page._page_size == 15
        page.combo_page_size.setCurrentIndex(page.combo_page_size.findData(8))
        records = [{"tracking_no": "REF-" + str(index), "customer_name": "Fixture Customer", "device_type": "Laptop", "device_brand": "AYEC", "device_model": "Model " + str(index), "entry_date": "2026-09-30", "status": "Tamirde", "price": 100 + index} for index in range(15)]
        page._all_records = records
        page._filtered_records = records
        page._render_current_page()
        changes = db.conn.total_changes
        actions = page.reference_bulk_menu.actions()
        actions[0].trigger()
        actions[1].trigger()
        assert [level for level, _ in messages] == ["warning", "warning"]
        assert prints == [] and not path.exists()
        checkbox = page.table.cellWidget(1, 0).findChild(QCheckBox)
        checkbox.setChecked(True)
        assert page.btn_bulk_actions.text().endswith("(1)")
        assert [record["tracking_no"] for record in page._checked_service_records()] == ["REF-1"]
        actions[0].trigger()
        with path.open(encoding="utf-8-sig", newline="") as stream:
            exported = list(csv.DictReader(stream))
        assert len(exported) == 1
        assert exported[0]["Takip No"] == "REF-1"
        assert exported[0]["M\u00fc\u015fteri"] == "Fixture Customer"
        assert exported[0]["\u00dccret"] == "101"
        assert len(exported[0]) == 11
        assert messages[-1][0] == "success"
        actions[1].trigger()
        assert prints == ["REF-1"]
        actions[3].trigger()
        assert len(page._checked_service_records()) == 8
        assert page.btn_bulk_actions.text().endswith("(8)")
        actions[0].trigger()
        with path.open(encoding="utf-8-sig", newline="") as stream:
            assert len(list(csv.DictReader(stream))) == 8
        page._go_to_page(2)
        assert page._checked_service_records() == []
        assert page.btn_bulk_actions.text() == "Toplu \u0130\u015flemler"
        actions[3].trigger()
        assert len(page._checked_service_records()) == 7
        actions[4].trigger()
        assert page._checked_service_records() == []
        assert db.conn.total_changes == changes
        assert page._filtered_records == records
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_compact_service_filters_keep_all_categories_and_native_combo_signals(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    original_font = app.font()
    font_id = QFontDatabase.addApplicationFont(str(ROOT / ".venv_active" / "Lib" / "site-packages" / "imgaug" / "DejaVuSans.ttf"))
    assert font_id >= 0
    app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    requests = []
    monkeypatch.setattr(ServiceListPage, "_apply_all_filters", lambda self: requests.append(self.current_filter_category))
    db = Database(str(tmp_path / "service_filters.db"))
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page.resize(1088, 988)
        page.show()
        app.processEvents()
        changes = db.conn.total_changes
        assert len(page._chip_buttons) == 8
        assert page._chip_buttons["all"].isChecked()
        for key, button in page._chip_buttons.items():
            assert button.height() == 24
            assert page.rect().contains(QRect(button.mapTo(page, QPoint(0, 0)), button.size()))
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            assert requests[-1] == key
            assert [name for name, item in page._chip_buttons.items() if item.isChecked()] == [key]
        assert [page.combo_status.itemData(i) for i in range(page.combo_status.count())] == ["all", "Bekliyor", "Tamirde", "Par\u00e7a Bekliyor", "Test S\u00fcrecinde", "Teslim Edildi", "\u0130ptal"]
        for combo in (page.combo_status, page.combo_date, page.combo_priority):
            assert combo.height() == 28
            assert combo.property("referenceChevron")
            events = []
            combo.currentIndexChanged.connect(events.append)
            combo.setCurrentIndex(1)
            assert events == [1]
        page.search_input.setText("actual search")
        assert page._current_search_query == "actual search"
        clear = next(button for button in page.findChildren(QPushButton) if button.text() == "Temizle")
        clear.click()
        assert page.search_input.text() == ""
        assert page.combo_status.currentData() == "all"
        assert page.combo_date.currentData() == "all"
        assert page.combo_priority.currentData() == "all"
        assert page._chip_buttons["all"].isChecked()
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
        app.setFont(original_font)


def test_reference_service_metrics_use_actual_dates_statuses_and_currency(monkeypatch, tmp_path):
    import src.ui.pages.service_list_page as service_module
    from tests.test_financial_reference_periods import FixedDateTime

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(service_module, "datetime", FixedDateTime)
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    db = Database(str(tmp_path / "service_metrics.db"))
    page = ServiceListPage(db)
    try:
        assert all(label.text() == "--" for label in page._reference_kpi_values)
        page._all_records = [
            {"status": "Teslim Edildi", "entry_date": "2026-09-28", "exit_date": "2026-10-01", "price": 100, "delivery_type": "Kargo"},
            {"status": "Teslim Edildi", "entry_date": "2026-09-29", "exit_date": "2026-09-30", "price": 200},
            {"status": "Tamirde", "entry_date": "2026-09-30", "price": 300},
        ]
        changes = db.conn.total_changes
        page._update_reference_kpis()
        assert [label.text() for label in page._reference_kpi_values] == ["1 Cihaz", "0 Cihaz", "0 Cihaz", "1 Paket", CurrencyHelper.format_amount(600, db=db), "2.0 G\u00fcn"]
        assert [label.text() for label in page._reference_footer_values] == ["3", "2.0 G\u00fcn", "1 Cihaz", CurrencyHelper.format_amount(600, db=db)]
        page._all_records.append({"status": "Teslime Hazir", "price": 400})
        page._update_reference_kpis()
        assert page._reference_kpi_values[2].text() == "1 Cihaz"
        assert page._reference_footer_values[2].text() == "1 Cihaz"
        page._all_records = [{"status": "Tamirde", "entry_date": "invalid", "exit_date": "2026-10-01", "price": "nan"}, {"status": "Teslim Edildi", "entry_date": "2026-10-02", "exit_date": "2026-09-30", "price": "invalid"}]
        page._update_reference_kpis()
        assert page._reference_kpi_values[5].text() == "Veri yok"
        assert page._reference_kpi_values[4].text() == CurrencyHelper.format_amount(0, db=db)
        assert page._reference_footer_values[2].text() == "0 Cihaz"
        page._all_records = []
        page._update_reference_kpis()
        assert page._reference_kpi_values[0].text() == "0 Cihaz"
        assert page._reference_kpi_values[5].text() == "Veri yok"
        assert ServiceListPage._reference_date("01.10.2026") == FixedDateTime.now().date()
        assert ServiceListPage._reference_date("01/10/2026") == FixedDateTime.now().date()
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_reference_service_order_keeps_id_order_and_sorts_legacy_dates_without_writes():
    for id_kind in ("absent", "primary", "nullable"):
        conn = sqlite3.connect(":memory:")
        try:
            id_column = {"absent": "", "primary": "id INTEGER PRIMARY KEY, ", "nullable": "id INTEGER, "}[id_kind]
            conn.execute("CREATE TABLE devices (" + id_column + "tracking_no TEXT, entry_date TEXT, status TEXT, is_deleted INTEGER DEFAULT 0, is_archived INTEGER DEFAULT 0)")
            for tracking, date in (("A002", "2026-09-30"), ("A003", "2026-09-29"), ("A001", "2026-09-28")):
                conn.execute("INSERT INTO devices(tracking_no,entry_date,status) VALUES (?,?,'Tamirde')", (tracking, date))
            conn.execute("INSERT INTO devices(tracking_no,entry_date,status,is_archived) VALUES ('ARCHIVED','2026-10-01','Tamirde',1)")
            conn.execute("INSERT INTO devices(tracking_no,entry_date,status,is_deleted) VALUES ('DELETED','2026-10-01','Tamirde',1)")
            conn.commit()
            state = SimpleNamespace(db=SimpleNamespace(conn=conn), _all_records=[])
            changes = conn.total_changes
            ServiceListPage._fetch_records(state)
            expected = ["A001", "A003", "A002"] if id_kind == "primary" else ["A002", "A003", "A001"]
            assert [record["tracking_no"] for record in state._all_records] == expected
            assert conn.total_changes == changes
            assert not conn.in_transaction
        finally:
            conn.close()


def test_reference_service_quick_actions_keep_all_original_callbacks(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    calls = []
    handlers = ("_action_service_history", "_action_print_detail", "_action_print_cargo", "_action_dispatch_note", "_action_e_invoice", "_action_whatsapp")
    for name in handlers:
        monkeypatch.setattr(ServiceListPage, name, lambda self, checked=False, key=name: calls.append(key))
    db = Database(str(tmp_path / "service_quick_actions.db"))
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page.resize(1088, 988)
        page.show()
        app.processEvents()
        changes = db.conn.total_changes
        assert len(page.reference_quick_actions) == 6
        bar = page.findChild(QWidget, "ServiceQuickActions")
        assert bar.height() == 32
        for button in page.reference_quick_actions:
            assert button.height() == 24
            assert button.minimumWidth() >= button.fontMetrics().horizontalAdvance(button.text()) + 34
            assert not button.stacked
            assert button.accessibleName() == button.text()
            assert bar.rect().contains(QRect(button.mapTo(bar, QPoint()), button.size()))
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
        assert calls == list(handlers)
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_service_invoice_chips_use_actual_billing_flags_without_writes(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    db = Database(str(tmp_path / "service_billing_flags.db"))
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        for tracking in ("ISSUED", "PARTIAL", "NEW", "PAYMENT", "OTHER"):
            db.conn.execute("INSERT INTO devices(tracking_no,status,entry_date) VALUES (?, 'Tamirde', '2026-09-30')", (tracking,))
        for tracking, kind, category, issued in (
            ("ISSUED", "Gelir", "Sat\u0131\u015f", 1),
            ("PARTIAL", "Gelir", "Sat\u0131\u015f", 1),
            ("PAYMENT-PAY", "Gelir", "Sat\u0131\u015f", 1),
            ("OTHER", "Gider", "Sat\u0131\u015f", 1),
        ):
            db.conn.execute("INSERT INTO accounting(tracking_no,type,category,is_invoiced) VALUES (?,?,?,?)", (tracking, kind, category, issued))
        for tracking, kind, issued in (("ISSUED", "DEBIT", 1), ("PARTIAL", "DEBIT", 0), ("PAYMENT", "CREDIT", 1)):
            db.conn.execute("INSERT INTO currency_transactions(tracking_no,transaction_type,is_invoiced) VALUES (?,?,?)", (tracking, kind, issued))
        db.conn.commit()
        changes = db.conn.total_changes
        page._fetch_records()
        page._update_chip_counts()
        assert page._chip_buttons["invoiced"].text().endswith("(1)")
        assert page._chip_buttons["uninvoiced"].text().endswith("(4)")
        page._chip_buttons["invoiced"].click()
        assert [r["tracking_no"] for r in page._filtered_records] == ["ISSUED"]
        assert page.table.item(0, 1).text() == "ISSUED"
        page._chip_buttons["uninvoiced"].click()
        assert {r["tracking_no"] for r in page._filtered_records} == {"PARTIAL", "NEW", "PAYMENT", "OTHER"}
        page._chip_buttons["all"].click()
        assert len(page._filtered_records) == 5
        assert db.conn.total_changes == changes
        assert not db.conn.in_transaction
        # A database without finance modules must still expose unbilled services.
        legacy = sqlite3.connect(":memory:")
        try:
            legacy.execute("CREATE TABLE devices(tracking_no TEXT)")
            assert ServiceListPage._read_service_invoice_flags(legacy.cursor()) == {}
        finally:
            legacy.close()
        assert ServiceListPage._service_is_invoiced({"is_invoiced": "1"})
        assert not ServiceListPage._service_is_invoiced({"is_invoiced": "0"})
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_reference_table_height_tracks_actual_rows_and_keeps_pagination(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    db = Database(str(tmp_path / "service_density.db"))
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        assert page._page_size == 15
        page.combo_page_size.setCurrentIndex(page.combo_page_size.findData(8))
        records = [{"tracking_no": "REF-" + str(index), "entry_date": "2026-09-30", "status": "Tamirde", "price": 100} for index in range(15)]
        page._all_records = records
        page._filtered_records = records
        page._render_current_page()
        page.resize(1088, 988)
        page.show()
        app.processEvents()
        changes = db.conn.total_changes
        assert page.table.rowCount() == 8
        assert page.table.horizontalHeader().height() == 32
        assert page.table.alternatingRowColors()
        assert not page.table.showGrid()
        assert all(page.table.rowHeight(row) == 64 for row in range(8))
        assert page.reference_table_wrapper.height() <= 562
        summary = page.findChild(QWidget, "ServiceReferenceSummary")
        assert summary.height() == 84
        left = page.findChild(QWidget, "ServiceMovementSummary")
        right = page.findChild(QWidget, "ServiceSummaryCard3")
        assert left.width() > right.width() * 1.8
        assert right.mapTo(summary, QPoint()).x() >= left.mapTo(summary, QPoint()).x() + left.width()
        assert len(page._reference_footer_values) == 4
        for index, value in enumerate(page._reference_footer_values):
            card = page.findChild(QWidget, "ServiceSummaryCard" + str(index))
            assert card.rect().contains(QRect(value.mapTo(card, QPoint()), value.size()))
        second = next(button for button in page.findChildren(QPushButton) if button.text() == "2")
        second.click()
        app.processEvents()
        assert page._current_page == 2
        assert page.table.rowCount() == 7
        assert page.table.item(0, 1).text() == "REF-8"
        page.combo_page_size.setCurrentIndex(page.combo_page_size.findData(15))
        app.processEvents()
        assert page._current_page == 1
        assert page.table.rowCount() == 15
        assert page.table.item(14, 1).text() == "REF-14"
        assert page.table.verticalScrollBar().maximum() > 0
        page.combo_page_size.setCurrentIndex(page.combo_page_size.findData(8))
        page._filtered_records = records[:1]
        page._render_current_page()
        app.processEvents()
        assert page.reference_table_wrapper.maximumHeight() <= 98
        assert page.table.rowCount() == 1
        assert db.conn.total_changes == changes
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()


def test_reference_service_identity_fields_and_dates_use_actual_record_data(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    original_font = app.font()
    original_theme = ThemeManager._current_theme
    original_stylesheet = app.styleSheet()
    from src.utils.reference_typography import apply_reference_font
    apply_reference_font(app)
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    db = Database(str(tmp_path / "service_identity_fields.db"))
    seed_visual_fixture(db)
    db.conn.execute(
        "UPDATE devices SET customer_name=?, customer_contact=?, serial_no=?, device_model=?, "
        "entry_date=?, exit_date=? WHERE tracking_no=?",
        ("Customer <Actual>", "+90 532 100 00 01", "AC-000123", "Workstation Model",
         "2026-09-21 10:30:00", "2026-09-29 14:15:00", "DEMO-SRV-0015"),
    )
    db.conn.commit()
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    page.resize(1280, 1024)
    ThemeManager.apply_theme(app, "Koyu Mavi", window=page, animate=False)
    page.show()
    try:
        changes = db.conn.total_changes
        page._fetch_records()
        page._apply_all_filters()
        app.processEvents()
        assert page._filtered_records[0]['serial_no'] == 'AC-000123'
        customer = page.table.cellWidget(0, 2).findChildren(QLabel)
        device = page.table.cellWidget(0, 3).findChildren(QLabel)
        assert customer[0].text() == 'Customer <Actual>'
        assert customer[0].textFormat() == Qt.TextFormat.PlainText
        assert '+90 532 100 00 01' in customer[1].text()
        assert 'Workstation Model' in device[1].text()
        assert 'SN: AC-000123' in device[1].text()
        assert all(label.wordWrap() for label in customer + device)
        for column, original, display in ((4, '2026-09-21 10:30:00', '2026-09-21'),
                                          (5, '2026-09-29 14:15:00', '2026-09-29')):
            item = page.table.item(0, column)
            assert item.text() == display
            assert item.toolTip() == original
            assert item.data(Qt.ItemDataRole.UserRole) == original
        for column in (2, 3):
            cell = page.table.cellWidget(0, column)
            assert cell.layout().heightForWidth(cell.width()) <= cell.height()
            for label in cell.findChildren(QLabel):
                assert label.heightForWidth(label.width()) <= label.height()
        assert page.table.item(0, 1).font().family() == 'JetBrains Mono'
        assert db.conn.total_changes == changes
        output = ROOT / 'artifacts' / 'service_reference_identity_fields.png'
        assert page.grab().save(str(output))
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
        ThemeManager._activate_runtime_cache(original_theme)
        app.setStyleSheet(original_stylesheet)
        app.setFont(original_font)


def test_reference_service_real_query_order_matches_native_row_after_theme(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    original_theme = ThemeManager._current_theme
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    db = Database(str(tmp_path / "service_native_order.db"))
    seed_visual_fixture(db)
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        page.resize(1088, 988)
        ThemeManager.apply_theme(app, "Koyu Mavi", window=page, animate=False)
        page.show()
        page._fetch_records()
        page._apply_all_filters()
        app.processEvents()
        first = page._filtered_records[0]["tracking_no"]
        expected = db.conn.execute("SELECT tracking_no FROM devices ORDER BY id DESC LIMIT 1").fetchone()[0]
        assert first == expected
        assert first == "DEMO-SRV-0015"
        assert page.table.item(0, 1).text() == first, (page.table.isSortingEnabled(), page.table.horizontalHeader().sortIndicatorSection(), page.table.horizontalHeader().sortIndicatorOrder())
    finally:
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
        ThemeManager.apply_theme(app, original_theme, animate=False)


def test_native_service_pdf_keeps_selected_rows_and_all_export_fields(monkeypatch, tmp_path):
    from PyQt6.QtPdf import QPdfDocument
    import src.ui.pages.service_list_page as service_module

    app = QApplication.instance() or QApplication([])
    original_font = app.font()
    font_id = QFontDatabase.addApplicationFont(str(ROOT / ".venv_active" / "Lib" / "site-packages" / "imgaug" / "DejaVuSans.ttf"))
    assert font_id >= 0
    app.setFont(QFont(QFontDatabase.applicationFontFamilies(font_id)[0], 9))
    monkeypatch.setattr(ServiceListPage, "refresh_data", lambda self: None)
    messages = []
    monkeypatch.setattr(service_module, "show_success", lambda parent, text: messages.append("success"))
    monkeypatch.setattr(service_module, "show_error", lambda parent, text: messages.append("error"))
    path = tmp_path / "selected_report"
    monkeypatch.setattr(service_module.QFileDialog, "getSaveFileName", lambda *args: (str(path), "PDF Rapor (*.pdf)"))
    db = Database(str(tmp_path / "service_pdf.db"))
    page = ServiceListPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    reader = QPdfDocument(None)
    try:
        page._filtered_records = [{"tracking_no": "PDF-" + str(index), "customer_name": "<Customer & Name>", "company_name": "Company", "device_type": "Laptop", "device_brand": "AYEC", "device_model": "Model", "entry_date": "2026-09-30", "exit_date": "2026-10-01", "status": "Teslim Edildi", "urgency": "Normal", "price": 100 + index} for index in range(2)]
        page._render_current_page()
        page.table.cellWidget(1, 0).findChild(QCheckBox).setChecked(True)
        changes = db.conn.total_changes
        page._export_selected_services()
        pdf = path.with_suffix(".pdf")
        assert pdf.exists()
        assert reader.load(str(pdf)) == QPdfDocument.Error.None_
        text = "\n".join(reader.getAllText(index).text() for index in range(reader.pageCount()))
        assert "PDF-1" in text and "PDF-0" not in text
        assert "<Customer & Name>" in text
        for field in ("Takip No", "M\u00fc\u015fteri", "\u015eirket", "Cihaz T\u00fcr\u00fc", "Marka", "Model", "Giri\u015f Tarihi", "\u00c7\u0131k\u0131\u015f Tarihi", "\u00dccret", "Durum", "Aciliyet"):
            assert field in text
        assert messages == ["success"]
        assert db.conn.total_changes == changes
        reader.close()
        missing = tmp_path / "missing_folder" / "cannot_write.pdf"
        monkeypatch.setattr(service_module.QFileDialog, "getSaveFileName", lambda *args: (str(missing), "PDF Rapor (*.pdf)"))
        page._export_selected_services()
        assert messages[-1] == "error"
        assert not missing.exists()
    finally:
        reader.close()
        page.close()
        page.deleteLater()
        app.processEvents()
        db.close()
        app.setFont(original_font)
