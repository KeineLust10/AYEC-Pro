import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QBoxLayout, QComboBox, QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout, QPushButton
from PyQt6.QtCore import QTimer

from src.ui.pages._customers_base_mixin import CustomersBaseMixin


def test_customer_quick_filters_remain_available_without_extra_toolbar_row():
    from PyQt6.QtWidgets import QWidget, QVBoxLayout

    class FilterPage(CustomersBaseMixin, QWidget):
        def __init__(self):
            super().__init__()
            self.layout = QVBoxLayout(self)
            self.selected_filter = None
            self._setup_header()
            self._setup_banners()

        def export_excel(self):
            pass

        def print_list(self):
            pass

        def export_pdf(self):
            pass

        def notify(self, _message):
            pass

        def add_customer(self):
            pass

        def _open_selected_customer_sms(self):
            pass

        def _open_selected_customer_history(self):
            pass

        def filter_by_type(self, value):
            self.selected_filter = value

    app = QApplication.instance() or QApplication([])
    page = FilterPage()
    try:
        page.resize(1600, 100)
        page.show()
        app.processEvents()
        buttons = page.customer_filter_group.buttons()
        assert len(buttons) == 5
        assert page.customer_quick_filter_bar.isHidden()
        assert page.btn_add_customer.text() == "+ YEN\u0130 M\u00dc\u015eTER\u0130 EKLE"
        assert page.btn_add_customer.width() == 194
        buttons[-1].click()
        assert page.selected_filter == "OPEN_SERVICES"
    finally:
        page.close()


def test_customer_toolbar_filters_accept_turkish_debt_label_and_location():
    app = QApplication.instance() or QApplication([])
    table = QTableWidget(2, 2)
    customers = [
        {"type": "Bireysel", "city": "Ankara", "balance_try": -120.0},
        {"type": "Bireysel", "city": "Istanbul", "balance_try": 120.0},
    ]
    for row, customer in enumerate(customers):
        item = QTableWidgetItem("customer")
        item.setData(Qt.ItemDataRole.UserRole, customer)
        table.setItem(row, 1, item)

    type_filter = QComboBox()
    type_filter.addItems(["T\u00fcm Tipler (Bireysel / Kurumsal)", "Bireysel", "Kurumsal"])
    location_filter = QComboBox()
    location_filter.addItem("T\u00fcm Lokasyonlar (\u0130l / \u0130l\u00e7e)", "")
    location_filter.addItem("Ankara", "Ankara")
    balance_filter = QComboBox()
    balance_filter.addItems(["T\u00fcm Bakiyeler", "Bor\u00e7", "Alacak", "Dengede"])

    page = SimpleNamespace(
        table=table,
        customer_type_filter=type_filter,
        customer_location_filter=location_filter,
        customer_balance_filter=balance_filter,
    )
    location_filter.setCurrentIndex(1)
    balance_filter.setCurrentIndex(1)
    CustomersBaseMixin._apply_customer_toolbar_filters(page)
    app.processEvents()

    assert not table.isRowHidden(0)
    assert table.isRowHidden(1)

    balance_filter.setCurrentIndex(2)
    location_filter.setCurrentIndex(0)
    CustomersBaseMixin._apply_customer_toolbar_filters(page)
    app.processEvents()
    assert table.isRowHidden(0)
    assert not table.isRowHidden(1)


def test_customer_filters_live_in_secondary_toolbar_and_add_action_stays_in_header(tmp_path):
    from src.utils.reference_typography import apply_reference_font
    from src.utils.theme_manager import ThemeManager

    class ToolbarPage(CustomersBaseMixin, QWidget):
        def __init__(self):
            super().__init__()
            self.layout = QVBoxLayout(self)
            self.table = QTableWidget(self)
            self.search_timer = QTimer(self)
            self.btn_add_customer = QPushButton("Add customer")
            self._setup_toolbar()

        def copy_list(self):
            pass

        print_list = copy_list
        export_excel = copy_list
        export_pdf = copy_list
        open_documents_center = copy_list
        import_customers = copy_list
        toggle_multiselect = copy_list

    app = QApplication.instance() or QApplication([])
    apply_reference_font(app)
    ThemeManager.apply_theme(app, "AYEC", animate=False)
    page = ToolbarPage()
    try:
        page.resize(1500, 260)
        page.show()
        app.processEvents()
        page._apply_customer_toolbar_responsive_widths()
        app.processEvents()
        toolbar_layout = page.customer_toolbar_card.layout()
        search_row = toolbar_layout.itemAt(0).layout()
        row = toolbar_layout.itemAt(1).layout()
        assert page.customer_toolbar_card.height() == 42
        assert toolbar_layout.direction() == QBoxLayout.Direction.LeftToRight
        assert search_row.indexOf(page.inp_search) >= 0
        assert page.inp_search.x() < page.customer_type_filter.x()
        assert page.inp_search.height() == 32
        assert row.indexOf(page.btn_customer_filter) >= 0
        assert row.indexOf(page.btn_add_customer) < 0
        assert all(row.indexOf(control) >= 0 for control in (
            page.customer_type_filter,
            page.customer_location_filter,
            page.customer_balance_filter,
        ))
        assert page.customer_filter_menu.actions()[0].defaultWidget() is not None
        assert page.grab().save(str(tmp_path / "customer_filters_toolbar.png"))
        page.customer_toolbar_card.resize(1024, 42)
        page._apply_customer_toolbar_responsive_widths()
        assert page.customer_toolbar_card.height() == 78
        assert toolbar_layout.direction() == QBoxLayout.Direction.TopToBottom
    finally:
        page.close()


def test_customer_header_actions_resolve_checked_customer_records():
    from src.ui.pages._customers_func_mixin import CustomersFuncMixin

    app = QApplication.instance() or QApplication([])
    table = QTableWidget(2, 2)
    first = QTableWidgetItem("")
    first.setFlags(first.flags() | Qt.ItemFlag.ItemIsUserCheckable)
    first.setCheckState(Qt.CheckState.Unchecked)
    second = QTableWidgetItem("")
    second.setFlags(second.flags() | Qt.ItemFlag.ItemIsUserCheckable)
    second.setCheckState(Qt.CheckState.Checked)
    first_customer = {"id": 1, "name": "First", "phone": "111"}
    second_customer = {"id": 2, "name": "Second", "phone": "222"}
    table.setItem(0, 0, first)
    table.setItem(1, 0, second)
    first_record = QTableWidgetItem("#001")
    first_record.setData(Qt.ItemDataRole.UserRole, first_customer)
    second_record = QTableWidgetItem("#002")
    second_record.setData(Qt.ItemDataRole.UserRole, second_customer)
    table.setItem(0, 1, first_record)
    table.setItem(1, 1, second_record)
    table.setCurrentCell(0, 1)
    page = SimpleNamespace(table=table)

    assert CustomersFuncMixin._selected_customer_records(page) == [second_customer]

    second.setCheckState(Qt.CheckState.Unchecked)
    assert CustomersFuncMixin._selected_customer_records(page) == [first_customer]
    table.close()


def test_customer_row_quick_actions_follow_reference_states_and_keep_menu_access():
    from src.ui.pages._customers_ui_mixin import CustomersUIMixin

    app = QApplication.instance() or QApplication([])

    class ActionPage(CustomersUIMixin):
        def __init__(self):
            self.calls = []

        def open_customer_360(self, customer):
            self.calls.append(("profile", customer["id"]))

        def send_debt_reminder(self, customer):
            self.calls.append(("remind", customer["id"]))

        def create_service(self, customer):
            self.calls.append(("service", customer["id"]))

        def send_whatsapp(self, customer):
            self.calls.append(("message", customer["id"]))

        def show_row_menu(self, row):
            self.calls.append(("menu", row))

    page = ActionPage()
    customer = {"id": 3, "name": "Customer", "phone": "555"}
    vip_widget = page._create_action_widget(2, dict(customer, type="Kurumsal", contract_type="VIP"))
    vip_buttons = vip_widget.findChildren(QPushButton)
    assert [button.text() for button in vip_buttons] == ["Cari Kart", ""]
    assert not vip_buttons[1].icon().isNull()
    vip_buttons[0].click()
    vip_buttons[1].click()

    debt_widget = page._create_action_widget(4, dict(customer, balance_try=-10))
    debt_buttons = debt_widget.findChildren(QPushButton)
    assert [button.text() for button in debt_buttons] == ["Hat\u0131rlat", ""]
    assert not debt_buttons[1].icon().isNull()
    debt_buttons[0].click()

    service_widget = page._create_action_widget(0, dict(customer, open_service_count=1))
    service_buttons = service_widget.findChildren(QPushButton)
    assert [button.text() for button in service_buttons] == ["Servis A\u00e7", "", ""]
    assert not service_buttons[2].icon().isNull()
    service_buttons[0].click()
    service_buttons[1].click()

    assert page.calls == [
        ("profile", 3), ("menu", 2), ("remind", 3), ("service", 3), ("message", 3),
    ]
    for widget in (vip_widget, debt_widget, service_widget):
        widget.close()


def test_customer_page_number_controls_follow_reference_and_reload_selected_page():
    from PyQt6.QtWidgets import QLabel

    class PaginationPage(CustomersBaseMixin, QWidget):
        def __init__(self):
            super().__init__()
            self.total_count = 28
            self.limit = 10
            self.current_page = 0
            self.reload_count = 0
            self.lbl_page = QLabel()
            self.btn_prev = QPushButton()
            self.btn_next = QPushButton()
            self.page_number_buttons = [QPushButton(str(index + 1)) for index in range(3)]
            for index, button in enumerate(self.page_number_buttons):
                button.setCheckable(True)
                button.clicked.connect(
                    lambda _checked=False, page=index: self._go_to_customer_page(page)
                )

        def request_reload(self):
            self.reload_count += 1

    app = QApplication.instance() or QApplication([])
    page = PaginationPage()
    page._update_pagination_ui()
    assert [button.text() for button in page.page_number_buttons] == ["1", "2", "3"]
    assert [button.isChecked() for button in page.page_number_buttons] == [True, False, False]
    page.page_number_buttons[1].click()
    assert page.current_page == 1
    assert page.reload_count == 1
    page._update_pagination_ui()
    assert [button.isChecked() for button in page.page_number_buttons] == [False, True, False]
    page.close()
