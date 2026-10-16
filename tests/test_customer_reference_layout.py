import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QFrame, QDialog, QWidget, QPushButton, QLabel
from PyQt6.QtNetwork import QNetworkReply
from unittest.mock import patch
import sqlite3

from src.database import Database
from src.ui.dialogs.add_customer_dialog import AddCustomerDialog, CustomerReferenceInput, CustomerReferenceGlyph
from src.services.tomtom_geocoder import TomTomGeocoder
from src.ui.pages._customers_ui_mixin import CustomersUIMixin
from src.ui.pages._customers_func_mixin import CustomersFuncMixin
from src.ui.pages._customers_base_mixin import (
    CustomersBaseMixin,
    _CustomerRowHoverDelegate,
    _CustomerTableWidget,
)
from src.ui.pages._customers_data_mixin import (
    CustomersDataMixin,
    _CustomerSortItem,
    _format_reference_customer_phone,
)


class CustomerFields:
    def get_customer_fields(self):
        return [
            {"name": "device_type", "title": "Device Type", "type": "select", "options": ["Laptop", "Phone"]},
            {"name": "brand", "title": "Brand", "type": "text"},
            {"name": "model", "title": "Model", "type": "text"},
        ]


class CustomerActionProbe(CustomersUIMixin, QWidget):
    def __init__(self):
        super().__init__()
        self.service_customer = None

    def create_service(self, customer):
        self.service_customer = customer

    def open_customer_service_panel(self, customer):
        self.service_customer = customer

    def send_whatsapp(self, _customer):
        pass

    def send_debt_reminder(self, _customer):
        pass

    def open_customer_360(self, _customer):
        pass

    def show_row_menu(self, _row):
        pass


def test_customer_phone_display_matches_reference_grouping():
    assert _format_reference_customer_phone("05550000001") == "0555 000 00 01"
    assert _format_reference_customer_phone("0232 400 00 12") == "0232 400 00 12"
    assert _format_reference_customer_phone("12345") == "12345"


def test_customer_balance_shows_reference_overdue_caption():
    app = QApplication.instance() or QApplication([])

    class CurrencyProbe:
        def get_setting(self, _key, default=None):
            return default or "TRY"

    currency_probe = CurrencyProbe()
    currency_probe.db = currency_probe
    widget = CustomersDataMixin._create_customer_balance_widget(
        currency_probe, {"TRY": -1450.0}, overdue_days=12
    )
    labels = [label.text() for label in widget.findChildren(QLabel)]
    assert "-\u20ba1,450.00" in labels
    assert "BOR\u00c7" in labels
    assert "Vadesi 12 G\u00fcn Ge\u00e7ti" in labels
    widget.close()
    app.processEvents()


def test_customer_row_hover_does_not_change_the_selected_customer():
    app = QApplication.instance() or QApplication([])
    page = CustomerActionProbe()
    page.table = _CustomerTableWidget()
    page.table.setRowCount(2)
    page.table.setColumnCount(1)
    page.customer_row_hover_delegate = _CustomerRowHoverDelegate(page.table)
    page.table.setItemDelegate(page.customer_row_hover_delegate)
    page.table.selectRow(1)
    try:
        page._on_table_cell_entered(0, 0)
        assert page.customer_row_hover_delegate.hovered_row == 0
        assert [index.row() for index in page.table.selectionModel().selectedRows()] == [1]
    finally:
        page.table.close()
        page.close()
        app.processEvents()


def test_customer_id_badges_keep_numeric_sort_and_record_binding():
    app = QApplication.instance() or QApplication([])
    table = _CustomerTableWidget()
    table.setColumnCount(2)
    table.setRowCount(2)
    for row, customer_id in enumerate((58, 2)):
        item = _CustomerSortItem(customer_id)
        item.setData(Qt.ItemDataRole.UserRole, {"id": customer_id})
        table.setItem(row, 1, item)
        table.setCellWidget(row, 1, QLabel("#{:03d}".format(customer_id)))
    table.setSortingEnabled(True)
    table.sortItems(1, Qt.SortOrder.AscendingOrder)
    sorted_ids = [
        table.item(row, 1).data(Qt.ItemDataRole.UserRole)["id"]
        for row in range(table.rowCount())
    ]
    assert sorted_ids == [2, 58]
    table.close()
    app.processEvents()


def test_vip_customer_with_open_service_keeps_reference_service_action_priority():
    app = QApplication.instance() or QApplication([])
    page = CustomerActionProbe()
    customer = {
        "type": "Bireysel",
        "contract_type": "VIP",
        "balance_try": 8100.0,
        "open_service_count": 2,
        "phone": "0555 000 0001",
    }
    try:
        action_widget = page._create_action_widget(0, customer)
        actions = action_widget.findChildren(QPushButton)
        assert actions[0].text() == "Servis A\u00e7"
        actions[0].click()
        assert page.service_customer is customer
        action_widget.deleteLater()
        ready_widget = page._create_action_widget(
            1,
            {
                "type": "Kurumsal Bayi",
                "balance_try": 0,
                "open_service_count": 1,
                "open_delivery_ready_count": 1,
            },
        )
        ready_actions = ready_widget.findChildren(QPushButton)
        assert len(ready_actions) == 1
        assert ready_actions[0].text().startswith("\u0130\u015flem Yap")
        ready_widget.deleteLater()
    finally:
        page.close()
        app.processEvents()


class CustomerServicePanelProbe(CustomersFuncMixin, QWidget):
    def __init__(self, rows):
        super().__init__()
        self.db = type("DatabaseProbe", (), {})()
        self.db.conn = sqlite3.connect(":memory:")
        self.db.conn.row_factory = sqlite3.Row
        self.db.conn.execute(
            "CREATE TABLE devices (tracking_no TEXT, device_type TEXT, brand TEXT, model TEXT, "
            "status TEXT, customer_id INTEGER, customer_name TEXT, is_deleted INTEGER, "
            "is_archived INTEGER, entry_date TEXT, id INTEGER)"
        )
        self.db.conn.executemany(
            "INSERT INTO devices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows
        )
        self.main_window = type("MainWindowProbe", (), {})()
        self.main_window.opened_tracking_no = None
        self.main_window.open_technician_panel = self._capture_panel

    def _capture_panel(self, tracking_no):
        self.main_window.opened_tracking_no = tracking_no


def test_customer_service_action_opens_technician_panel_for_active_device():
    app = QApplication.instance() or QApplication([])
    page = CustomerServicePanelProbe([
        ("SRV-10", "Laptop", "Dell", "XPS", "Onar\u0131m", 7, "Customer", 0, 0, "2026-10-10", 10),
        ("SRV-09", "Phone", "Apple", "15", "Teslim Edildi", 7, "Customer", 0, 0, "2026-10-09", 9),
    ])
    try:
        page.open_customer_service_panel({"id": 7, "name": "Customer"})
        assert page.main_window.opened_tracking_no == "SRV-10"
    finally:
        page.db.conn.close()
        page.close()
        app.processEvents()


def test_customer_density_keeps_validators_footer_type_flags_and_sector_fields(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "customer_reference.db"))
    before = [tuple(row) for row in db.conn.execute("SELECT * FROM customers")]
    dialog = AddCustomerDialog(db, sector_manager=CustomerFields())
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dialog.set_dialog_size(864, 820)
    dialog.show()
    app.processEvents()
    try:
        assert len(dialog.findChildren(QFrame, "customerReferenceCard")) == 6
        assert len(dialog.findChildren(CustomerReferenceGlyph)) == 7
        assert dialog.logo_label.isHidden()
        assert dialog.reference_header_badge.text() == "Cari Kart Tan\u0131m\u0131"
        assert dialog.btn_close.width() == 28
        type_bar = dialog.findChild(QFrame, "customerTypeBar")
        assert dialog.card_layout.indexOf(type_bar) == 1
        assert type_bar.height() == 48
        assert dialog.txt_note.height() == 72
        assert dialog.footer_layout.indexOf(dialog.btn_save) >= 0
        assert dialog.footer_layout.indexOf(dialog.btn_cancel) >= 0
        assert dialog.rb_individual.isChecked()
        assert dialog.inp_tc.isEnabled()
        assert not dialog.inp_tax_no.isEnabled()
        dialog.rb_corporate.setChecked(True)
        assert not dialog.inp_tc.isEnabled()
        assert dialog.inp_tax_no.isEnabled()
        assert dialog.inp_tax_office.isEnabled()
        assert dialog.inp_company.isEnabled()
        dialog.rb_individual.setChecked(True)
        assert dialog.inp_tc.isEnabled()
        assert isinstance(dialog.inp_phone, CustomerReferenceInput)
        dialog.inp_phone.setText("invalid phone")
        assert dialog.inp_phone.is_valid is False
        dialog.inp_phone.setText("05550001122")
        assert dialog.inp_phone.is_valid is True
        assert dialog.inp_phone.styleSheet().count(CustomerReferenceInput.DENSITY_MARKER) == 1
        assert 24 <= dialog.inp_phone.height() <= 34
        dialog.inp_email.setText("not-an-email")
        assert not dialog.inp_email.is_valid
        dialog.inp_email.setText("fixture@example.test")
        assert dialog.inp_email.is_valid
        dialog.chk_sms.setChecked(False)
        assert "kapal\u0131" in dialog.chk_sms.toolTip()
        dialog.chk_problem.setChecked(True)
        assert dialog.chk_problem.toolTip() == "Sorunlu kay\u0131t"
        assert set(dialog.plugin_customer_widgets) == {"device_type", "brand", "model"}
        dialog.plugin_customer_widgets["device_type"].setCurrentText("Phone")
        dialog.plugin_customer_widgets["brand"].setText("Fixture Brand")
        model = dialog.plugin_customer_widgets["model"]
        model.setText("Fixture Model")
        assert dialog._collect_plugin_customer_values() == {
            "device_type": "Phone", "brand": "Fixture Brand", "model": "Fixture Model",
        }
        grid = model.parentWidget().layout().itemAt(1).layout()
        assert grid.getItemPosition(grid.count() - 1) == (1, 0, 1, 2)
        dialog.btn_cancel.click()
        assert dialog.result() == QDialog.DialogCode.Rejected
        assert [tuple(row) for row in db.conn.execute("SELECT * FROM customers")] == before
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        db.conn.close()


def test_customer_reference_toolbar_stays_pinned_and_close_keeps_reject_mapping(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "customer_pinned_toolbar.db"))
    dialog = AddCustomerDialog(db, sector_manager=CustomerFields())
    dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    dialog.set_dialog_size(600, 520)
    dialog.show()
    for _ in range(5):
        app.processEvents()
    rejected = []
    dialog.rejected.connect(lambda: rejected.append(True))
    try:
        toolbar = dialog.findChild(QFrame, "customerTypeBar")
        position = toolbar.mapTo(dialog, toolbar.rect().topLeft())
        bar = dialog.scroll_area.verticalScrollBar()
        assert bar.maximum() > 0
        bar.setValue(bar.maximum())
        app.processEvents()
        assert toolbar.mapTo(dialog, toolbar.rect().topLeft()) == position
        assert toolbar.isVisible()
        assert dialog.content_container is dialog.scroll_area.widget()
        assert dialog.content_layout is dialog.content_container.layout()
        assert dialog.btn_save.isVisible()
        dialog.btn_close.click()
        assert rejected == [True]
        assert dialog.result() == QDialog.DialogCode.Rejected
        assert db.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        db.conn.close()


def test_customer_location_coordinates_persist_and_reverse_address_fills_fields(tmp_path):
    app = QApplication.instance() or QApplication([])
    db = Database(str(tmp_path / "customer_location.db"))
    dialog = AddCustomerDialog(db)
    try:
        app.processEvents()
        dialog.inp_name.setText("Location Test")
        assert dialog._set_location_coordinates(40.1044, 27.6564)
        dialog._apply_reverse_geocode(
            {
                "address": {
                    "countrySubdivision": "Balikesir",
                    "municipality": "Gonen",
                    "municipalitySubdivision": "Akcaali",
                    "street": "Ornek Sokak",
                    "streetNumber": "12",
                    "postalCode": "10900",
                    "freeformAddress": "Ornek Sokak 12, Gonen, Balikesir",
                }
            }
        )

        with patch("src.ui.dialogs.add_customer_dialog.show_success"), patch(
            "src.ui.dialogs.add_customer_dialog.show_error"
        ):
            dialog.save()

        row = db.conn.execute(
            "SELECT latitude, longitude, street, zip_code FROM customers WHERE id=?",
            (dialog.saved_customer_id,),
        ).fetchone()
        assert row is not None
        assert row[0] == 40.1044
        assert row[1] == 27.6564
        assert row[2] == "Ornek Sokak 12"
        assert row[3] == "10900"
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()
        db.close()


def test_tomtom_geocoder_accepts_qt_no_error_enum_and_parses_reverse_address():
    app = QApplication.instance() or QApplication([])
    client = TomTomGeocoder("fixture-key")

    class Reply:
        def property(self, name):
            return "reverse:test"

        def error(self):
            return QNetworkReply.NetworkError.NoError

        def errorString(self):
            return "Unknown error"

        def readAll(self):
            return (
                b'{"addresses":[{"address":{"freeformAddress":"Gonen, Balikesir"}}]}'
            )

        def deleteLater(self):
            pass

    received = []
    client.resolved.connect(lambda *args: received.append(args))
    client._finish(Reply())

    assert len(received) == 1
    assert received[0][0] == "reverse:test"
    assert received[0][1]["address"]["freeformAddress"] == "Gonen, Balikesir"
    assert received[0][2] == ""


def test_customer_theme_styles_follow_active_light_and_dark_palette():
    from PyQt6.QtWidgets import QLineEdit, QTableWidget, QVBoxLayout
    from src.utils.theme_manager import ThemeManager

    app = QApplication.instance() or QApplication([])

    class ThemeProbe(CustomersBaseMixin, QWidget):
        def __init__(self):
            super().__init__()
            self.layout = QVBoxLayout(self)
            self.table = QTableWidget(self)
            self.inp_search = QLineEdit(self)
            self._setup_reference_metrics()
            self._setup_banners()
            self.layout.addWidget(self.customer_quick_filter_bar)

    previous_theme = ThemeManager._current_theme
    page = ThemeProbe()
    try:
        page.show()
        for theme_name in ("AYEC", "Koyu Mavi"):
            ThemeManager.apply_theme(app, theme_name, animate=False)
            page.apply_theme_styles()
            app.processEvents()
            page.customer_quick_filter_bar.show()
            app.processEvents()
            window_color = ThemeManager.get_palette_color(theme_name, "window")
            text_color = ThemeManager.get_palette_color(theme_name, "text")
            muted_color = ThemeManager.get_palette_color(theme_name, "text_muted")
            warning_color = ThemeManager.get_palette_color(theme_name, "warning")
            accent_color = ThemeManager.get_palette_color(theme_name, "accent")
            assert window_color.lower() in page.styleSheet().lower()
            assert text_color.lower() in page.styleSheet().lower()
            assert window_color.lower() in page.table.styleSheet().lower()
            assert text_color.lower() in page.table.styleSheet().lower()
            assert text_color.lower() in page._customer_metric_values[0].styleSheet().lower()
            assert muted_color.lower() in page._customer_metric_title_labels[0].styleSheet().lower()
            warning_button = page.customer_filter_buttons["DEBTORS"]
            assert warning_color.lower() in warning_button.styleSheet().lower()
            assert accent_color.lower() in page._customer_metric_bars[3].styleSheet().lower()
            assert "@window" not in page.styleSheet()
            assert "@text" not in page.table.styleSheet()
            page.customer_quick_filter_bar.hide()
    finally:
        ThemeManager.apply_theme(app, previous_theme, animate=False)
        page.deleteLater()
        app.processEvents()
