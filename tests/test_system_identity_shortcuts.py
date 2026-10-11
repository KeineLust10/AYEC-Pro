import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QPushButton

from src.database import Database
from src.ui.pages.settings_widgets import system_identity_settings as identity
from src.ui.pages.settings_widgets.system_identity_settings import SystemIdentitySettingsWidget


APP = QApplication.instance() or QApplication([])


def test_system_identity_shortcut_controls_call_desktop_actions(monkeypatch, tmp_path):
    db = Database(str(tmp_path / "identity-shortcuts.db"))
    calls = []
    main = SimpleNamespace(
        current_user={"role": "Admin"},
        is_in_windows_startup=lambda: False,
        toggle_windows_startup=lambda enabled: calls.append(("startup", enabled)),
        create_desktop_shortcut=lambda: calls.append(("desktop", True)),
        create_start_menu_shortcut=lambda: calls.append(("start-menu", True)),
    )
    monkeypatch.setattr(identity, "show_success", lambda *args: None)
    widget = SystemIdentitySettingsWidget(db, main)
    try:
        widget.toggle_startup.setChecked(True)
        buttons = {button.text(): button for button in widget.findChildren(QPushButton)}
        buttons["Masa\u00fcst\u00fc k\u0131sayolu olu\u015ftur"].click()
        buttons["Ba\u015flang\u0131\u00e7 men\u00fcs\u00fc k\u0131sayolu olu\u015ftur"].click()
        assert calls == [("startup", True), ("desktop", True), ("start-menu", True)]
    finally:
        widget.close()
        db.conn.close()
        APP.processEvents()
