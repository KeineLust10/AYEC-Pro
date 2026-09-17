import json
import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from src.ui.pages.settings_widgets.user_management_dialogs import UserDialog
from src.ui.pages.settings_sidebar import PremiumSettingsSidebar
from src.ui.pages.settings_widgets.management_center_settings import ManagementCenterSettingsWidget


APP = QApplication.instance() or QApplication([])


class DialogDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.cursor = self.conn.cursor()
        self.cursor.execute("CREATE TABLE personnel (id INTEGER PRIMARY KEY, name TEXT)")
        self.cursor.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                email TEXT,
                role TEXT,
                personnel_id INTEGER,
                permissions TEXT,
                auto_login INTEGER,
                secret_question TEXT
            )
            """
        )

    def add_user(self, role, permissions):
        self.cursor.execute(
            """
            INSERT INTO users (
                username, email, role, personnel_id, permissions,
                auto_login, secret_question
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("test-user", "test@example.com", role, None, permissions, 0, ""),
        )
        self.conn.commit()
        return self.cursor.lastrowid


def _app():
    return APP


def test_admin_always_sees_all_permissions_enabled_and_locked():
    _app()
    db = DialogDatabase()
    user_id = db.add_user("Admin", json.dumps({"pages": []}))

    dialog = UserDialog(db, user_id=user_id)

    assert dialog.perm_toggles
    assert all(toggle.isChecked() for toggle in dialog.perm_toggles.values())
    assert all(not toggle.isEnabled() for toggle in dialog.perm_toggles.values())
    dialog.close()


def test_non_admin_keeps_saved_custom_permissions():
    _app()
    db = DialogDatabase()
    user_id = db.add_user("Personel", json.dumps({"pages": [21, 70]}))

    dialog = UserDialog(db, user_id=user_id)
    checked = {page_id for page_id, toggle in dialog.perm_toggles.items() if toggle.isChecked()}

    assert checked == {21, 70}
    assert all(toggle.isEnabled() for toggle in dialog.perm_toggles.values())
    dialog.close()


def test_role_change_to_admin_applies_all_permissions():
    _app()
    db = DialogDatabase()
    user_id = db.add_user("Personel", json.dumps({"pages": [21]}))
    dialog = UserDialog(db, user_id=user_id)

    dialog.cmb_role.setCurrentText("Admin")

    assert all(toggle.isChecked() for toggle in dialog.perm_toggles.values())
    assert all(not toggle.isEnabled() for toggle in dialog.perm_toggles.values())
    dialog.close()


def test_footer_actions_fit_inside_dialog():
    app = _app()
    db = DialogDatabase()
    user_id = db.add_user("Admin", json.dumps({"mode": "all"}))
    dialog = UserDialog(db, user_id=user_id)
    dialog.show()
    app.processEvents()

    for button in (dialog.btn_save, dialog.btn_cancel):
        top_left = button.mapTo(dialog.container, button.rect().topLeft())
        bottom_right = button.mapTo(dialog.container, button.rect().bottomRight())
        assert button.isVisible()
        assert top_left.x() >= 0
        assert top_left.y() >= 0
        assert bottom_right.x() < dialog.container.width()
        assert bottom_right.y() < dialog.container.height()
    dialog.close()


def test_management_center_menu_is_visible_only_for_admin_roles():
    _app()
    admin_sidebar = PremiumSettingsSidebar(lambda _page_id: None, current_user={"role": "Admin"})
    staff_sidebar = PremiumSettingsSidebar(lambda _page_id: None, current_user={"role": "Personel"})

    assert 24 in admin_sidebar.items_map
    assert 24 not in staff_sidebar.items_map
    admin_sidebar.close()
    staff_sidebar.close()


def test_management_center_button_opens_control_center(monkeypatch):
    _app()
    opened = []
    monkeypatch.setattr(
        "src.ui.pages.settings_widgets.management_center_settings.QDesktopServices.openUrl",
        lambda url: opened.append(url.toString()) or True,
    )

    widget = ManagementCenterSettingsWidget(None, type("Window", (), {"current_user": {"role": "Admin"}})())
    widget.btn_open.click()

    assert widget.btn_open.isEnabled()
    assert opened == ["http://85.117.239.60/?page=control-center"]
    widget.close()
