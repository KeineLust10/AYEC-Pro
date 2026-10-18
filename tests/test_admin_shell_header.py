import sys
from pathlib import Path

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QMainWindow, QLabel, QProgressBar, QPushButton, QStackedWidget, QWidget

ROOT = Path(__file__).resolve().parents[1]
ADMIN_ROOT = ROOT / "Admin_Konsol"
if str(ADMIN_ROOT) not in sys.path:
    sys.path.insert(0, str(ADMIN_ROOT))

from main_window import MainWindow
import api_client
from product_catalog import product_names, product_code


def test_admin_header_metrics_bind_live_server_status(persistent_qapplication, monkeypatch):
    monkeypatch.setattr(api_client, "server_status", lambda: {"cpu_percent": 23, "ram_percent": 51, "disk_percent": 30})
    class HeaderHarness(MainWindow):
        def __init__(self):
            QMainWindow.__init__(self)

    window = HeaderHarness()
    window._header_status_thread = None
    window._header_metric_widgets = {
        key: (QProgressBar(window), QLabel("--", window))
        for key in ("cpu_percent", "ram_percent", "disk_percent")
    }

    MainWindow._refresh_header_status(window)
    assert window._header_status_thread.wait(3000)
    persistent_qapplication.processEvents()

    assert [(bar.value(), value.text()) for bar, value in window._header_metric_widgets.values()] == [
        (23, "23%"), (51, "51%"), (30, "30%")
    ]
    MainWindow._update_header_metrics(window, {})
    assert [value.text() for _bar, value in window._header_metric_widgets.values()] == ["--", "--", "--"]
    window.close()


def test_admin_header_height_matches_each_reference_shell(persistent_qapplication):
    class HeaderHarness(QMainWindow):
        def __init__(self):
            QMainWindow.__init__(self)
            self._top_bar = QFrame(self)
            self._global_search = QLineEdit(self)

    window = HeaderHarness()
    MainWindow._apply_reference_header_layout(window, "dashboard")
    assert window._top_bar.minimumHeight() == 56
    assert window._top_bar.maximumHeight() == 56
    assert window._top_bar.property("referenceStyle") == "standard"
    assert window._global_search.width() == 320
    MainWindow._apply_reference_header_layout(window, "license_requests")
    assert window._top_bar.minimumHeight() == 48
    assert window._top_bar.maximumHeight() == 48
    assert window._top_bar.property("referenceStyle") == "license"
    assert window._global_search.width() == 256
    MainWindow._apply_reference_header_layout(window, "backups")
    assert window._top_bar.minimumHeight() == 56
    assert window._top_bar.maximumHeight() == 56
    assert window._top_bar.property("referenceStyle") == "console"
    assert window._global_search.width() == 288
    window.close()


def test_admin_header_search_uses_reference_search_icon():
    assert not MainWindow._search_icon().isNull()


def test_firmas_menu_lists_programs_and_routes_actions(persistent_qapplication, monkeypatch):
    navigations = []
    product_contexts = []
    monkeypatch.setattr(MainWindow, "_navigate", lambda self, page_id: navigations.append(page_id))
    monkeypatch.setattr(MainWindow, "_refresh_header_status", lambda self: None)
    monkeypatch.setattr(api_client, "set_product_context", product_contexts.append)

    window = MainWindow()
    assert window._firm_button.text() == "Programlarim \u25be"
    assert not window._firm_button.isHidden()
    assert window._firm_button.menu() is window._firm_menu
    assert window._firm_menu.actions()[0].text() == "Firma Y\u00f6netimi"
    assert window._firm_menu.actions()[2].text() == "Programlar\u0131m"
    assert tuple(window._program_actions) == product_names()
    assert tuple(window._program_actions[name].text() for name in product_names()) == (
        "AYEC Pro Teknik Servis Takip", "Barkod Okuyucu", "Elek", "Ciro Takip"
    )

    selected_product = product_names()[1]
    window._program_actions[selected_product].trigger()
    persistent_qapplication.processEvents()
    assert window._active_product == selected_product
    assert product_contexts[-1]
    assert navigations[-1] == "companies"

    window._firm_menu.actions()[0].trigger()
    persistent_qapplication.processEvents()
    assert navigations[-1] == "companies"
    window.close()


def test_header_actions_route_to_their_pages_and_refresh(persistent_qapplication, monkeypatch):
    navigations = []
    refreshes = []
    monkeypatch.setattr(MainWindow, "_navigate", lambda self, page_id: navigations.append(page_id))
    monkeypatch.setattr(MainWindow, "_refresh_header_status", lambda self: refreshes.append("header"))
    monkeypatch.setattr(MainWindow, "_refresh_current_page", lambda self: refreshes.append("page"))
    monkeypatch.setattr(api_client, "set_product_context", lambda _code: None)

    window = MainWindow()
    navigations.clear()
    refreshes.clear()
    window._quick_header_button.click()
    window._header_notifications.click()
    window._refresh_header_button.click()

    assert navigations == ["license_requests", "notifications"]
    assert refreshes == ["page", "header"]
    window.close()


def test_program_selection_reapplies_filter_to_current_and_cached_company_page(
    persistent_qapplication, monkeypatch
):
    product_contexts = []
    monkeypatch.setattr(api_client, "set_product_context", product_contexts.append)

    class FilterPage(QWidget):
        def __init__(self):
            super().__init__()
            self.products = []

        def set_product_filter(self, product_name):
            self.products.append(product_name)

    class HeaderHarness(MainWindow):
        def __init__(self):
            QMainWindow.__init__(self)

    window = HeaderHarness()
    window._active_product = "AYEC Pro Teknik Servis"
    window._current_page = "companies"
    window._pages = {"companies": FilterPage()}
    window._program_actions = {}
    window._header_title = QLabel()
    MainWindow._product_changed(window, "AYEC Pro Barkod Okuyucu")
    assert window._pages["companies"].products[-1] == "AYEC Pro Barkod Okuyucu"
    assert product_contexts[-1] == product_code("AYEC Pro Barkod Okuyucu")

    target = FilterPage()
    window._pages = {"companies": target}
    window._current_page = "dashboard"
    window._stack = QStackedWidget(window)
    window._stack.addWidget(target)
    window._nav_btns = {}
    window._header_title = QLabel()
    window._active_product = "AYEC Pro Elek"
    window._get_page = lambda _page_id: target
    monkeypatch.setattr(MainWindow, "_apply_reference_header_layout", lambda _self, _page_id: None)
    MainWindow._navigate(window, "companies")
    assert target.products == ["AYEC Pro Elek"]
    window.close()


def test_every_sidebar_menu_action_and_logout_button_has_a_working_route(
    persistent_qapplication, monkeypatch
):
    navigations = []
    logout_calls = []
    monkeypatch.setattr(MainWindow, "_navigate", lambda self, page_id: navigations.append(page_id))
    monkeypatch.setattr(MainWindow, "_logout", lambda self: logout_calls.append(True))
    monkeypatch.setattr(MainWindow, "_refresh_header_status", lambda self: None)
    monkeypatch.setattr(api_client, "set_product_context", lambda _code: None)

    window = MainWindow()
    navigations.clear()
    for page_id, button in window._nav_btns.items():
        button.click()
        assert navigations[-1] == page_id

    logout_button = window.findChild(QPushButton, "logoutBtn")
    assert logout_button is not None
    logout_button.click()
    assert logout_calls == [True]
    window.close()
