# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.ui.widgets.side_menu import AccordionItem, SideMenu
from src.utils.theme_manager import ThemeManager


class MockCursor:
    def execute(self, *args, **kwargs):
        return self

    def fetchone(self):
        return None


class MockDB:
    def get_setting(self, _key, default=None):
        return default

    def get_internal_setting(self, _key, default=None):
        return default

    def get_language(self):
        return "tr"

    def get_all_labels(self):
        return {}

    @property
    def cursor(self):
        return MockCursor()


class PermissionCursor:
    def __init__(self, users):
        self.users = users
        self.row = None

    def execute(self, _query, params):
        self.row = self.users.get(params[0])
        return self

    def fetchone(self):
        return self.row


class PermissionDB(MockDB):
    def __init__(self, last_user, users):
        self.last_user = last_user
        self._cursor = PermissionCursor(users)

    def get_setting(self, key, default=None):
        return self.last_user if key == "last_login_user" else default

    @property
    def cursor(self):
        return self._cursor


class SideMenuPermissionHarness:
    _get_allowed_pages = SideMenu._get_allowed_pages


class BadgeButton:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text

    def setText(self, value):
        self._text = value


class BadgeCursor:
    def __init__(self):
        self._query = ""

    def execute(self, query, _params=()):
        self._query = query
        return self

    def fetchall(self):
        if "FROM devices" in self._query:
            return [
                ("Bekliyor", 1),
                ("Tamirde", 2),
                ("Test Ediliyor", 1),
                ("Teslim Edildi", 2),
            ]
        return []

    def fetchone(self):
        if "FROM appointments" in self._query:
            return (0,)
        return None


class BadgeDB:
    def __init__(self):
        self.cursor = BadgeCursor()


class SideMenuBadgeHarness:
    set_badge = SideMenu.set_badge
    refresh_badges = SideMenu.refresh_badges

    def __init__(self):
        self.db = BadgeDB()
        self._btn_map = {
            41: BadgeButton("Durum Paneli"),
            30: BadgeButton("Randevular"),
        }
        self._badge_names = {
            41: "Durum Paneli",
            30: "Randevular",
        }


def _qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    return app


def test_side_menu_expands_first_accordion():
    app = _qapp()
    changed_pages = []

    menu = SideMenu(callback=changed_pages.append, db=MockDB())
    menu.show()
    app.processEvents()

    accordion = next(iter(menu.findChildren(AccordionItem)), None)
    assert accordion is not None
    assert accordion.sub_container.maximumHeight() == 0

    accordion.expand()
    QTest.qWait(380)
    app.processEvents()

    assert accordion.is_expanded is True
    assert accordion.sub_container.maximumHeight() > 0
    assert accordion.arrow_label.text() == "v"

    menu.close()
    menu.deleteLater()
    app.processEvents()


def test_side_menu_theme_refresh_replays_nested_card_styles():
    app = _qapp()
    previous_theme = ThemeManager._current_theme
    menu = SideMenu(callback=lambda _page_id: None, db=MockDB())
    menu.show()
    app.processEvents()

    try:
        initial_style = menu.brand_card.styleSheet()
        target_theme = "AYEC" if previous_theme != "AYEC" else "Koyu Mavi"
        ThemeManager._activate_runtime_cache(target_theme)
        menu.refresh_theme()
        app.processEvents()

        assert menu.brand_card.styleSheet() != initial_style
        assert "@" not in menu.brand_card.styleSheet()
        assert (
            menu.brand_card._theme_applied_generation
            == ThemeManager._theme_generation
        )
    finally:
        ThemeManager._activate_runtime_cache(previous_theme)
        menu.close()
        menu.deleteLater()
        app.processEvents()


def test_nested_menu_groups_keep_their_parent_open():
    app = _qapp()
    menu = SideMenu(callback=lambda _page_id: None, db=MockDB())
    menu.show()
    app.processEvents()
    groups = {
        group._title: group
        for group in menu.findChildren(AccordionItem)
    }

    service_group = groups["Servis Y\u00f6netimi"]
    stock_group = groups["Stok / Sipari\u015f"]
    offer_group = groups["Teklif Y\u00f6netimi"]

    assert 150 not in [page_id for _, page_id in stock_group.sub_buttons]
    assert 150 in [page_id for _, page_id in offer_group.sub_buttons]
    assert 146 in [page_id for _, page_id in service_group.sub_buttons]

    menu.close()
    menu.deleteLater()
    app.processEvents()


def test_side_menu_uses_current_user_instead_of_stale_last_login():
    menu = SideMenuPermissionHarness()
    menu.db = PermissionDB(
        "stale-user",
        {
            "active-user": {"role": "User", "permissions": '{"pages":[40,50,101]}'},
            "stale-user": {"role": "User", "permissions": '{"pages":[10]}'},
        },
    )
    menu.current_user = {"username": "active-user", "role": "User"}

    assert menu._get_allowed_pages() == {40, 50, 101}


def test_side_menu_current_admin_bypasses_stale_restrictions():
    menu = SideMenuPermissionHarness()
    menu.db = PermissionDB(
        "stale-user",
        {"stale-user": {"role": "User", "permissions": '{"pages":[10]}'}},
    )
    menu.current_user = {"username": "owner", "role": "Company Admin"}

    assert menu._get_allowed_pages() is None


def test_side_menu_badge_excludes_delivered_services():
    menu = SideMenuBadgeHarness()

    menu.refresh_badges()

    assert menu._btn_map[41].text() == "Durum Paneli  (4)"
