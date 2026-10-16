"""Actual single-sidebar settings routing, without a browser or network."""

import os
import socket
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.database import Database
from tools.quality.desktop_shell_reference_capture import ReferenceCaptureWindow
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_settings_reference_uses_one_shell_sidebar_across_routes(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    previous_app_font = app.font()
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    monkeypatch.setattr(socket.socket, "connect", lambda *_args: (_ for _ in ()).throw(AssertionError("Network disabled")))
    db = Database(str(tmp_path / "settings_shell.db"))
    seed_visual_fixture(db)
    window = ReferenceCaptureWindow(db, {"username": "fixture", "role": "Admin"})
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.resize(1280, 1024)
    window.show()
    QTest.qWait(100)
    transient_windows = []

    class TopLevelShowProbe(QObject):
        def eventFilter(self, watched, event):
            if (
                event.type() == QEvent.Type.Show
                and watched is not window
                and hasattr(watched, "isWindow")
                and watched.isWindow()
            ):
                transient_windows.append(type(watched).__name__)
            return False

    show_probe = TopLevelShowProbe()
    app.installEventFilter(show_probe)
    window.app_header.btn_settings.click()
    QTest.qWait(400)
    page = window.pages[130]
    settings_sidebar = page.sidebar
    menu = window.app_sidebar.side_menu
    try:
        assert menu._icon_only
        assert window.app_sidebar.width() == 64
        assert menu.scroll_area.isVisibleTo(window)
        assert menu.accordion_groups
        assert all(group._icon_lbl.isVisibleTo(window) for group in menu.accordion_groups)
        assert not transient_windows
        assert page.parentWidget() is window.content_area
        assert page.pages[4].parentWidget() is page.content_area
        assert not [
            widget for widget in app.topLevelWidgets()
            if widget is not window and widget.isVisible()
        ]
        assert window.app_sidebar.isVisibleTo(window)
        assert menu.isVisibleTo(window)
        assert not settings_sidebar.isVisibleTo(window)
        assert page.settings_page_selector.isVisible()
        assert page.settings_page_selector.count() == len(settings_sidebar.iter_items())
        assert page.settings_page_selector.currentData() == 4
        target_index = page.settings_page_selector.findData(6)
        page.settings_page_selector.setCurrentIndex(target_index)
        page.settings_page_selector.activated.emit(target_index)
        assert page.content_area.currentIndex() == 6
        assert menu._icon_only
        assert window.app_sidebar.width() == 64
        assert window.app_sidebar.isVisibleTo(window)
        window.resize(1600, 1024)
        QTest.qWait(300)
        assert settings_sidebar.isVisibleTo(window)
        assert not page.settings_page_selector.isVisible()
        assert len(settings_sidebar.iter_items()) >= 17
        assert not settings_sidebar.footer.isVisibleTo(window)
        assert settings_sidebar.list_widget.verticalScrollBar().value() == 0
        settings_sidebar.list_widget.setCurrentRow(settings_sidebar.items_map.index(20))
        QTest.qWait(250)
        whatsapp_page = page.pages[20]
        assert page.content_area.currentIndex() == 20
        assert settings_sidebar.isVisibleTo(window)
        next(item for item in whatsapp_page.integration_nav_buttons if item.property("settingsPageId") == 21).click()
        QTest.qWait(250)
        assert page.content_area.currentIndex() == 21
        assert settings_sidebar.isVisibleTo(window)
        assert settings_sidebar.list_widget.currentItem().data(Qt.ItemDataRole.UserRole) == 21
        settings_sidebar.list_widget.setCurrentRow(settings_sidebar.items_map.index(16))
        QTest.qWait(250)
        telegram_page = page.pages[16]
        assert settings_sidebar.isVisibleTo(window)
        telegram_page.settings_tab_buttons[2].click()
        QTest.qWait(250)
        assert page.content_area.currentIndex() == 2
        assert settings_sidebar.isVisibleTo(window)
        assert settings_sidebar.list_widget.currentItem().data(Qt.ItemDataRole.UserRole) == 2
        integration_row = settings_sidebar.items_map.index(21)
        integration_item = settings_sidebar.list_widget.item(integration_row)
        settings_sidebar.list_widget.scrollToItem(integration_item)
        QTest.qWait(100)
        QTest.mouseClick(
            settings_sidebar.list_widget.viewport(),
            Qt.MouseButton.LeftButton,
            pos=settings_sidebar.list_widget.visualItemRect(integration_item).center(),
        )
        QTest.qWait(300)
        assert page.content_area.currentIndex() == 21
        assert settings_sidebar.isVisibleTo(window)
        assert not page.settings_navigation_row.isVisibleTo(window)
        assert not page.settings_page_selector.isVisibleTo(window)
        assert window.app_sidebar.isVisibleTo(window)
        assert menu.scroll_area.isVisibleTo(window)
        assert all(group._icon_lbl.isVisibleTo(window) for group in menu.accordion_groups)
        window.resize(1280, 753)
        QTest.qWait(300)
        selector_index = page.settings_page_selector.findData(21)
        page.settings_page_selector.setCurrentIndex(selector_index)
        page.settings_page_selector.activated.emit(selector_index)
        QTest.qWait(300)
        hub = page.content_area.currentWidget()
        assert hub.open_tab_by_key("smtp")
        QTest.qWait(300)
        capture = Path(__file__).resolve().parents[1] / "output" / "part9-captures" / "email-smtp-shell-desktop.png"
        capture.parent.mkdir(parents=True, exist_ok=True)
        assert window.grab().save(str(capture), "PNG")
        assert hub.open_tab_by_key("sms")
        window.resize(1280, 659)
        QTest.qWait(300)
        sms_capture = capture.with_name("sms-provider-shell-desktop.png")
        assert window.grab().save(str(sms_capture), "PNG")
        assert hub.open_tab_by_key("telegram")
        window.resize(1280, 816)
        QTest.qWait(300)
        telegram_capture = capture.with_name("telegram-bot-shell-desktop-1280x816.png")
        assert window.grab().save(str(telegram_capture), "PNG")
        window.resize(1600, 1024)
        QTest.qWait(300)
        settings_sidebar.list_widget.setCurrentRow(settings_sidebar.items_map.index(4))
        QTest.qWait(300)
        window.resize(1280, 1024)
        QTest.qWait(300)
        assert not settings_sidebar.isVisibleTo(window)
        assert page.settings_page_selector.isVisible()
        menu.refresh_menu()
        QTest.qWait(300)
        assert page.sidebar is settings_sidebar
        assert not settings_sidebar.isVisibleTo(window)
        assert window.app_sidebar.isVisibleTo(window)
        menu.set_collapsed(True)
        app.processEvents()
        assert window.app_sidebar.isVisibleTo(window)
        menu.set_collapsed(False)
        QTest.qWait(300)
        menu.set_menu_label_mode("icons", persist=False)
        QTest.qWait(300)
        assert window.app_sidebar.isVisibleTo(window)
        menu.set_menu_label_mode("labels", persist=False)
        QTest.qWait(300)
        window.apply_nav_mode("ust_bar")
        app.processEvents()
        assert window.app_sidebar.isVisibleTo(window)
        window.apply_nav_mode("sol_menu")
        QTest.qWait(300)
        window.on_menu_click(145)
        QTest.qWait(300)
        assert not settings_sidebar.isVisibleTo(window)
        assert not menu._is_collapsed
        assert window.app_sidebar.width() > 64
        window.navigate_back()
        QTest.qWait(300)
        assert not settings_sidebar.isVisibleTo(window)
        assert window.app_sidebar.isVisibleTo(window)
        assert window._current_page_index == 130
        assert menu._icon_only
        assert window.app_sidebar.width() == 64
        assert hasattr(window, "_settings_sidebar_auto_previous_icon_only")
        window.app_sidebar.toggle_menu()
        QTest.qWait(350)
        assert not menu._icon_only
        assert window.app_sidebar.width() > 64
        window.navigate_back()
        QTest.qWait(300)
        assert window._current_page_index == 40
        assert not menu._is_collapsed
        assert not window.grab().isNull()
    finally:
        app.removeEventFilter(show_probe)
        window.close()
        db.close()
        app.setFont(previous_app_font)
