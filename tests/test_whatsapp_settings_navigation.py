import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QListWidget, QLineEdit, QWidget

from src.ui.pages.settings_widgets.whatsapp_settings import WhatsAppSettingsWidget


APP = QApplication.instance() or QApplication([])


class SettingsDb:
    def __init__(self):
        self.values = {}

    def get_setting(self, key, default=""):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value


def test_integration_shortcuts_navigate_to_real_settings_pages():
    host = QWidget()
    rows = [None, 20, 14, 5, 21, 3]
    sidebar_list = QListWidget(host)
    for _ in rows:
        sidebar_list.addItem("")
    search = QLineEdit(host)
    host.sidebar = SimpleNamespace(
        items_map=rows,
        list_widget=sidebar_list,
        search_inp=search,
    )
    selected_pages = []
    sidebar_list.currentRowChanged.connect(
        lambda row: selected_pages.append(rows[row]) if row >= 0 else None
    )
    search.setText("api")

    widget = WhatsAppSettingsWidget(SettingsDb())
    widget.setParent(host)

    for button in widget.integration_nav_buttons:
        button.click()

    assert selected_pages == [20, 14, 5, 21, 3]
    assert search.text() == ""
    widget.close()
    host.close()
