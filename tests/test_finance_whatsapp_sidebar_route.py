import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QApplication, QWidget

from src.ui.mixins._main_window_nav_mixin import MainWindowNavMixin
from src.ui.widgets._side_menu_accordion import AccordionItem


APP = QApplication.instance() or QApplication([])


class MenuHost(QWidget):
    page_changed = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.db = None
        self.accordion_groups = []
        self._requested_settings_tab = None

    def on_page_changed_internal(self, _page_id):
        pass


class SettingsPage:
    def __init__(self):
        self.selected_tabs = []

    def change_page(self, tab_index):
        self.selected_tabs.append(tab_index)


class FakeWindow(MainWindowNavMixin):
    def __init__(self, side_menu):
        self.app_sidebar = type("Sidebar", (), {"side_menu": side_menu})()
        self.page = SettingsPage()
        self._current_page_index = 106

    def _is_page_allowed_for_active_sector(self, _index):
        return True

    def _sync_back_button(self):
        pass

    def get_page(self, _index):
        return self.page

    def _switch_content_with_fade(self, _page):
        pass


def test_whatsapp_sidebar_route_opens_whatsapp_settings_tab():
    side_menu = MenuHost()
    window = FakeWindow(side_menu)
    side_menu.page_changed.connect(window.on_menu_click)
    item = AccordionItem(
        "WhatsApp API Masas\u0131",
        "\U0001f4ac",
        [("WhatsApp Ayarlar\u0131", 130)],
        side_menu,
        allowed_pages={130},
        main_page_id=130,
    )

    item._on_toggle_clicked()

    assert window._current_page_index == 130
    assert window.page.selected_tabs == [20]
    assert side_menu._requested_settings_tab is None

