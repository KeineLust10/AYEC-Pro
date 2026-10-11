"""Actual single-sidebar settings routing, without a browser or network."""

import os
import socket

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.database import Database
from tools.quality.desktop_shell_reference_capture import ReferenceCaptureWindow
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_settings_reference_uses_one_shell_sidebar_across_routes(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
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
        assert window.app_sidebar.isVisibleTo(window)
        window.resize(1600, 1024)
        QTest.qWait(300)
        assert settings_sidebar.isVisibleTo(window)
        assert not page.settings_page_selector.isVisible()
        assert len(settings_sidebar.iter_items()) >= 17
        assert not settings_sidebar.footer.isVisibleTo(window)
        assert settings_sidebar.list_widget.verticalScrollBar().value() == 0
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
        window.navigate_back()
        QTest.qWait(300)
        assert not settings_sidebar.isVisibleTo(window)
        assert window.app_sidebar.isVisibleTo(window)
        assert not window.grab().isNull()
    finally:
        app.removeEventFilter(show_probe)
        window.close()
        db.close()
