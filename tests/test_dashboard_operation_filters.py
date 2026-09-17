import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
)

from src.utils.appearance_mode import AppearanceModeManager
from src.ui.pages._dashboard_constants import get_filter_button_defs
from src.ui.pages._dashboard_data_mixin import DashboardDataMixin
from src.ui.pages._dashboard_widgets import create_filter_button, dashboard_icon
from src.ui.pages.dashboard_page import DashboardPage


APP = QApplication.instance() or QApplication([])
APP.setQuitOnLastWindowClosed(False)


class _Db:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        self.cursor.execute(
            """
            CREATE TABLE devices (
                id INTEGER PRIMARY KEY,
                tracking_no TEXT,
                customer_name TEXT,
                device_type TEXT,
                device_brand TEXT,
                device_model TEXT,
                service_source TEXT,
                delivery_type TEXT,
                entry_date TEXT,
                status TEXT,
                urgency TEXT,
                price REAL,
                labor_cost REAL,
                payment_status TEXT,
                is_archived INTEGER DEFAULT 0,
                is_deleted INTEGER DEFAULT 0
            )
            """
        )
        self.cursor.execute(
            """
            CREATE TABLE accounting (
                id INTEGER PRIMARY KEY,
                tracking_no TEXT,
                is_invoiced INTEGER DEFAULT 0
            )
            """
        )
        rows = [
            (
                "SRV-CARGO",
                "Cargo Customer",
                "Laptop",
                "Brand",
                "Model",
                "",
                "Kargo",
                "2026-07-30",
                "Kargo Bekliyor",
            ),
            (
                "SRV-INVOICE",
                "Invoice Customer",
                "Monitor",
                "Brand",
                "Model",
                "",
                "",
                "2026-07-30",
                "Tamirde",
            ),
            (
                "SRV-OUT",
                "External Customer",
                "Phone",
                "Brand",
                "Model",
                "dis servis",
                "",
                "2026-07-30",
                "Dis Servise Verildi",
            ),
            (
                "SRV-RETURN",
                "Return Customer",
                "Tablet",
                "Brand",
                "Model",
                "dondu",
                "",
                "2026-07-30",
                "Dis Servisten Dondu",
            ),
        ]
        self.cursor.executemany(
            """
            INSERT INTO devices (
                tracking_no, customer_name, device_type, device_brand,
                device_model, service_source, delivery_type, entry_date,
                status, urgency, price, labor_cost, payment_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Orta', 100, 50, 'Bekliyor')
            """,
            rows,
        )
        self.cursor.execute(
            """
            INSERT INTO accounting (tracking_no, is_invoiced)
            VALUES ('SRV-INVOICE', 1)
            """
        )
        self.conn.commit()

    def get_setting(self, _key, default=None):
        return default


class _DashboardHarness(DashboardDataMixin):
    def __init__(self):
        self.db = _Db()
        self.table = QTableWidget(0, 12)
        self.current_filter_category = "all"

    def _is_automotive(self):
        return False

    def _set_tracking_cell(self, row, text):
        self.table.setItem(row, 0, QTableWidgetItem(text))

    def _set_action_cell(self, _row, _tracking_no):
        return

    def _set_text_cell(self, row, col, text, center=False, bold=False):
        self.table.setItem(row, col, QTableWidgetItem(str(text)))

    def _set_badge_cell(self, row, col, text, *_args, **_kwargs):
        self.table.setItem(row, col, QTableWidgetItem(str(text)))

    def _update_recent_empty_state(self):
        return


def _filtered_tracking_numbers(category):
    dashboard = _DashboardHarness()
    try:
        dashboard.current_filter_category = category
        dashboard.populate_table()
        return [
            dashboard.table.item(row, 0).text()
            for row in range(dashboard.table.rowCount())
        ]
    finally:
        dashboard.db.conn.close()


def test_dashboard_exposes_reference_operation_filters():
    keys = {item[0] for item in get_filter_button_defs("teknik_servis")}

    assert {
        "cargo_waiting",
        "invoiced",
        "uninvoiced",
        "external_out",
        "external_return",
    }.issubset(keys)


def test_dashboard_svg_icons_are_rendered_instead_of_empty_placeholders():
    icon = dashboard_icon("all", "#1E88E5", 18)
    assert not icon.isNull()
    assert not icon.pixmap(18, 18).isNull()

    db = _Db()
    button = create_filter_button(
        None,
        "today",
        "Appointments",
        "R",
        "#D41462",
        "filter",
        db=db,
    )
    try:
        assert button.text() == "Appointments"
        assert not button.icon().isNull()
    finally:
        button.close()
        db.conn.close()

    svg = (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2"><circle cx="12" cy="12" r="9"/></svg>'
    )
    harness = _DashboardHarness()
    row_button = DashboardDataMixin._make_track_action_button(
        harness,
        svg,
        "#1E88E5",
        "Details",
        lambda: None,
    )
    try:
        assert not row_button.icon().isNull()
    finally:
        row_button.close()
        harness.db.conn.close()


def test_dashboard_operation_filters_select_expected_records():
    assert _filtered_tracking_numbers("cargo_waiting") == ["SRV-CARGO"]
    assert _filtered_tracking_numbers("invoiced") == ["SRV-INVOICE"]
    assert _filtered_tracking_numbers("external_out") == ["SRV-OUT"]
    assert _filtered_tracking_numbers("external_return") == ["SRV-RETURN"]
    assert set(_filtered_tracking_numbers("uninvoiced")) == {
        "SRV-CARGO",
        "SRV-OUT",
        "SRV-RETURN",
    }


def test_dashboard_initial_refresh_populates_all_devices():
    dashboard = _DashboardHarness()
    try:
        DashboardPage._refresh_initial_device_list(dashboard)
        assert dashboard.table.rowCount() == 4
    finally:
        dashboard.db.conn.close()


def test_dashboard_delayed_refresh_preserves_active_filter():
    dashboard = _DashboardHarness()
    dashboard.current_filter_category = "cargo_waiting"
    try:
        DashboardPage._refresh_initial_device_list(dashboard)
        assert dashboard.table.rowCount() == 1
        assert dashboard.table.item(0, 0).text() == "SRV-CARGO"
    finally:
        dashboard.db.conn.close()


def test_classic_appearance_uses_light_tooltips():
    original_palette = QToolTip.palette()
    original_stylesheet = APP.styleSheet()
    try:
        AppearanceModeManager.apply(APP, mode=AppearanceModeManager.CLASSIC)
        palette = QToolTip.palette()
        assert palette.color(QPalette.ColorRole.ToolTipBase).name() == "#ffffff"
        assert palette.color(QPalette.ColorRole.ToolTipText).name() == "#111827"
    finally:
        QToolTip.setPalette(original_palette)
        APP.setStyleSheet(original_stylesheet)
