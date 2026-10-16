# -*- coding: utf-8 -*-
import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.components.app_header import AppHeader
from src.utils.theme_manager import ThemeManager
from tools.quality.desktop_shell_reference_capture import ReferenceCaptureWindow


def test_reference_header_preserves_every_original_control_callback(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    calls = []
    names = (
        'navigate_back', 'open_interface_layout_editor', 'on_menu_click',
        'toggle_dashboard_shortcuts', 'toggle_theme_from_header', 'on_header_theme_changed',
        'window_minimize', 'window_maximize_restore', 'window_close', 'start_web_sync', 'toggle_assistant',
    )
    for name in names:
        monkeypatch.setattr(ReferenceCaptureWindow, name,
            lambda self, *args, action=name, **kwargs: calls.append((action, args, kwargs)))
    monkeypatch.setattr(AppHeader, 'open_notification_panel', lambda self: calls.append(('notifications', (), {})))
    silent_state = {'value': False}
    monkeypatch.setattr(ReferenceCaptureWindow, 'is_assistant_silent_mode', lambda self: silent_state['value'])

    def set_silent(self, value):
        silent_state['value'] = value
        calls.append(('set_assistant_silent_mode', (value,), {}))
        return True

    monkeypatch.setattr(ReferenceCaptureWindow, 'set_assistant_silent_mode', set_silent)
    db = Database(str(tmp_path / 'header.db'))
    db.set_setting('color_theme_full', 'Koyu Mavi')
    old_theme = ThemeManager._current_theme
    window = ReferenceCaptureWindow(db, {'username': 'fixture', 'role': 'Admin'})
    window.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    try:
        window.resize(1600, 1280)
        window.show()
        app.processEvents()
        header = window.app_header
        assert header.height() == 70
        original_page_id = window._current_page_index
        for page_id in (21, 42, 101, 115, 145, 146, 147):
            window._current_page_index = page_id
            header._apply_service_header_presentation()
            header._apply_compact_width_presentation()
            assert header.height() == 70
            assert not header.lbl_brand_pro.isVisible()
            assert header.btn_back.isVisible()
            assert header.btn_web_sync.isVisible(), page_id
            assert header.notification_bell.isVisible()
            assert header.cmb_theme.isVisible()
            assert header.service_profile.isVisible()
        window._current_page_index = original_page_id
        header._apply_service_header_presentation()
        calls.clear()
        header.set_back_enabled(True)
        for button, action in (
            (header.btn_back, 'navigate_back'),
            (header.btn_interface_edit, 'open_interface_layout_editor'),
            (header.btn_settings, 'on_menu_click'),
            (header.btn_shortcuts, 'toggle_dashboard_shortcuts'),
            (header.btn_theme_toggle, 'toggle_theme_from_header'),
            (header.btn_web_sync, 'start_web_sync'),
            (header.btn_minimize, 'window_minimize'),
            (header.btn_maximize, 'window_maximize_restore'),
            (header.btn_close, 'window_close'),
            (header.notification_bell, 'notifications'),
            (header.breadcrumb.assistant_btn, 'toggle_assistant'),
        ):
            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            assert calls[-1][0] == action
            assert button.isVisible()
        assert ('on_menu_click', (130,), {}) in calls
        assert ('start_web_sync', (), {'silent': False}) in calls
        assert header.breadcrumb._user_label_full == 'fixture'
        assert header.breadcrumb.user_lbl.text()
        assert header.breadcrumb.user_lbl.textFormat() == Qt.TextFormat.PlainText
        assert header.breadcrumb.user_lbl.toolTip() == 'fixture'
        for value in (True, False):
            QTest.mouseClick(header.breadcrumb.mute_btn, Qt.MouseButton.LeftButton)
            assert calls[-1] == ('set_assistant_silent_mode', (value,), {})
            assert silent_state['value'] == value
            assert not header.breadcrumb.mute_btn.icon().isNull()
        assert 'border-radius: 4px' in header.breadcrumb.assistant_btn.styleSheet()
        assert 'border-radius: 4px' in header.breadcrumb.mute_btn.styleSheet()
        assert header.cmb_theme.count() == len(ThemeManager.get_available_themes(db))
        index = (header.cmb_theme.currentIndex() + 1) % header.cmb_theme.count()
        header.cmb_theme.setCurrentIndex(index)
        assert calls[-1] == ('on_header_theme_changed', (header.cmb_theme.currentText(),), {})
        assert header.cmb_theme.property('referenceChevron')
        assert header.cmb_theme.height() == 34
        for control in (
            header.btn_back, header.btn_interface_edit, header.btn_settings,
            header.btn_shortcuts, header.btn_theme_toggle, header.btn_web_sync,
            header.btn_minimize, header.btn_maximize, header.btn_close, header.cmb_theme,
        ):
            radius = '7px' if control is header.btn_back else '4px'
            assert f'border-radius: {radius}' in control.styleSheet()
            assert '@finance_' not in control.styleSheet()
            assert header.rect().contains(control.mapTo(header, control.rect().topLeft()))
            assert header.rect().contains(control.mapTo(header, control.rect().bottomRight()))
        header.set_web_sync_state(running=True)
        assert not header.btn_web_sync.isEnabled()
        header.set_web_sync_state(success=False, detail='Fixture failure')
        assert header.btn_web_sync.isEnabled()
        assert header.btn_web_sync.toolTip() == 'Fixture failure'
        header.notification_bell.set_count(19)
        assert header.notification_bell.badge.isVisible()
        assert header.notification_bell.badge.text() == '9+'
        assert header.notification_bell.rect().contains(header.notification_bell.badge.geometry())
        header.notification_bell.set_count(0)
        assert not header.notification_bell.badge.isVisible()
        window.resize(1280, 1024)
        app.processEvents()
        assert not header.service_profile.text()
        assert any(action.text() == 'Sistem Ayarlar\u0131' for action in header.service_profile_menu.actions())
        for control in (header.btn_minimize, header.btn_maximize, header.btn_close):
            assert control.isVisible()
            assert not control.icon().isNull()
            assert header.rect().contains(control.mapTo(header, control.rect().bottomRight()))
        breadcrumb = header.breadcrumb
        assert breadcrumb.assistant_btn.width() == 32
        assert breadcrumb.assistant_btn.toolTip() == 'AYEC PRO CORE'
        for control in (breadcrumb.assistant_btn, breadcrumb.mute_btn, breadcrumb.user_lbl):
            assert breadcrumb.rect().contains(control.geometry())
        QTest.mouseClick(breadcrumb.assistant_btn, Qt.MouseButton.LeftButton)
        assert calls[-1][0] == 'toggle_assistant'
        window.resize(1600, 1280)
        app.processEvents()
        assert breadcrumb.assistant_btn.width() in (32, 144)
        assert breadcrumb.rect().contains(breadcrumb.assistant_btn.geometry())
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        ThemeManager.apply_theme(app, old_theme, animate=False)
        db.close()
