# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.append(str(Path(__file__).resolve().parents[1]))

from PyQt6.QtTest import QTest
from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication

from src.ui.widgets.side_menu import AccordionItem, SideMenu
from src.utils.theme_manager import ThemeManager


def test_service_settings_return_to_service_menu_and_labor_price_stays_in_stock():
    class SectionsHarness:
        _legacy_product_group_reference_navigation = False

        def _build_technical_sections_base(self):
            return [
                ("SERVIS OPERASYON", [
                    ("Servis Y\u00f6netimi", "wrench", [
                        ("Overview", 40),
                        ("Di\u011fer Servis \u0130\u015flemleri", [
                            ("Appointments", 30), ("Logistics", 65), ("Service reports", 201),
                        ]),
                    ]),
                    ("Servis Y\u00f6netim Ayar\u0131", "gear", [
                        ("Labor settings", 140), ("Brands", 145),
                        ("Product groups", 146), ("Report templates", 147),
                    ]),
                ]),
                ("TICARI", [("Stok / Siparis", "box", [("Stock", 50), ("Spare parts", 60)])]),
                ("SISTEM", [("Sistem Yardimcilari", "gear", [("Settings", 130)])]),
            ]

    sections = SideMenu._build_technical_sections(SectionsHarness())
    groups = {group[0]: group[2] for _section, entries in sections for group in entries}
    stock_group = next(group for group in groups.values() if any(item[1] == 50 for item in group))
    service_settings = groups["Servis Y\u00f6netim Ayar\u0131"]
    service_group = next(group for group in groups.values() if any(item[1] == 40 for item in group))
    service_ids = [item[1] for item in service_group]
    assert 140 in [item[1] for item in stock_group]
    assert {145, 146, 147}.issubset({item[1] for item in service_settings})
    assert 140 not in {item[1] for item in service_settings}
    assert not {145, 146, 147}.intersection({item[1] for item in stock_group})
    assert not any(group[0] == "Ticari Listeler" for _section, entries in sections for group in entries)
    assert 40 in service_ids
    assert {30, 65, 201}.issubset(set(service_ids))
    assert any(item == ("Kargo & Lojistik", 65) for item in service_group)


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


def test_navigation_glyphs_follow_selection_without_changing_routes():
    app = _qapp()
    changed_pages = []
    menu = SideMenu(callback=changed_pages.append, db=MockDB())
    try:
        menu.on_page_changed_internal(145)
        selected = menu._btn_map[145]
        assert selected._icon_lbl.active
        assert not menu._btn_map[146]._icon_lbl.active
        group = next(group for group in menu.accordion_groups
                     if any(pid == 145 for _button, pid in group.sub_buttons))
        assert group._icon_lbl.active
        selected.click()
        assert changed_pages[-1] == 145
        menu._btn_map[146].setEnabled(False)
        menu.on_page_changed_internal(146)
        assert not selected._icon_lbl.active
        assert menu._btn_map[146]._icon_lbl.disabled
    finally:
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


def test_reference_footer_keeps_logout_signal_and_theme_styles():
    app = _qapp()
    previous_theme = ThemeManager._current_theme
    menu = SideMenu(callback=lambda _page_id: None, db=MockDB())
    signals = []
    menu.logout_requested.connect(lambda: signals.append(True))
    try:
        for theme in ("AYEC", "Koyu Mavi"):
            ThemeManager._activate_runtime_cache(theme)
            menu.refresh_theme()
            assert menu.logout_btn.styleSheet() == ThemeManager.transform_qss(menu._logout_button_qss())
            assert "@" not in menu.logout_btn.styleSheet()
            assert menu.logout_btn.text() == "Oturumu Kapat"
            assert menu.version_label.text().endswith("Premium")
            menu.logout_btn.click()
        assert len(signals) == 2
    finally:
        ThemeManager._activate_runtime_cache(previous_theme)
        menu.close()
        menu.deleteLater()
        app.processEvents()


def test_reference_brand_header_preserves_identity_and_pin_action():
    app = _qapp()
    menu = SideMenu(callback=lambda _page_id: None, db=MockDB())
    pins = []
    menu.pin_changed.connect(pins.append)
    try:
        menu.update_branding(company_name="Customer Company", site_title="Main Branch")
        assert menu.branding_title.text() == "Customer Company"
        assert menu.branding_subtitle.text() == "Main Branch"
        assert menu.brand_card.objectName() == "SideMenuBrandCard"
        assert "QFrame#SideMenuBrandCard" in menu.brand_card.styleSheet()
        assert "border: none" in menu.branding_title.styleSheet()
        assert "border: none" in menu.branding_subtitle.styleSheet()
        menu.set_pinned(True, persist=False)
        assert menu.header.height() == 126
        assert menu.pin_glyph.active
        assert menu.pin_glyph.kind == "thumbtack"
        menu.pin_button.click()
        assert not menu._is_pinned
        assert not menu.pin_glyph.active
        menu.pin_button.click()
        assert menu._is_pinned
        assert menu.pin_glyph.active
        assert pins[-2:] == [False, True]
        menu.refresh_theme()
        assert menu.branding_title.text() == "Customer Company"
        assert "border: none" in menu.branding_title.styleSheet()
    finally:
        menu.close()
        menu.deleteLater()
        app.processEvents()


def test_finance_section_uses_the_shared_accordion_navigation():
    app = _qapp()
    menu = SideMenu(callback=lambda _page_id: None, db=MockDB())
    routed_pages = []
    menu.page_changed.connect(routed_pages.append)
    try:
        group = next(
            item for item in menu.accordion_groups
            if any(page_id == 106 for _button, page_id in item.sub_buttons)
        )
        assert group._title == "F\u0130NANS & MUHASEBE"
        assert not group.is_expanded
        group.toggle_btn.click()
        assert group.is_expanded
        assert any(page_id == 100 for _button, page_id in group.sub_buttons)
        group.toggle_btn.click()
        assert not group.is_expanded
        next(button for button, page_id in group.sub_buttons if page_id == 106).click()
        assert routed_pages[-1] == 106
    finally:
        menu.close()
        menu.deleteLater()
        app.processEvents()


def test_expanded_sidebar_width_tracks_reference_shell_proportions():
    app = _qapp()
    from PyQt6.QtWidgets import QWidget
    window = QWidget()
    menu = SideMenu(callback=lambda _page_id: None, db=MockDB(), parent=window)
    try:
        window.show()
        app.processEvents()
        for viewport_width, expected in ((991, 240), (1366, 273), (1600, 320), (1920, 320)):
            window.resize(viewport_width, 900)
            app.processEvents()
            assert menu.expanded_width_for_window() == expected
    finally:
        window.close()
        menu.deleteLater()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
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
    service_settings_group = groups["Servis Y\u00f6netim Ayar\u0131"]
    stock_group = groups["Stok / Sipari\u015f"]
    offer_group = groups["Teklif Olu\u015ftur"]

    assert 150 not in [page_id for _, page_id in stock_group.sub_buttons]
    assert offer_group.main_page_id == 150
    assert [page_id for _, page_id in offer_group.sub_buttons] == [313, 314]
    settings_pages = [page_id for _, page_id in service_settings_group.sub_buttons]
    assert 146 in settings_pages
    assert 145 in settings_pages
    assert 147 in settings_pages
    assert 140 in [page_id for _, page_id in stock_group.sub_buttons]
    assert menu._btn_map[145].accessibleName() == "Marka Adlar\u0131 Y\u00f6netimi"

    menu.close()
    menu.deleteLater()
    app.processEvents()


def test_reference_sidebar_stays_the_same_across_module_routes():
    app = _qapp()
    menu = SideMenu(callback=lambda _page_id: None, db=MockDB())
    menu.show()
    app.processEvents()
    expected_titles = tuple(group._title for group in menu.accordion_groups)
    company_branding = (menu.branding_title.text(), menu.branding_subtitle.text())

    for page_id in (115, 100, 42, 147, 145):
        menu.on_page_changed_internal(page_id)
        assert tuple(group._title for group in menu.accordion_groups) == expected_titles
        assert (menu.branding_title.text(), menu.branding_subtitle.text()) == company_branding

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
