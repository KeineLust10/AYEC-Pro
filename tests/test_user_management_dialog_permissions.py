import json
import os
import sqlite3

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QTableWidgetItem

from src.ui.pages.settings_widgets.user_management_dialogs import UserDialog
from src.ui.pages.settings_widgets.user_management import UserManagementWidget
from src.ui.pages.settings_sidebar import PremiumSettingsSidebar
from src.ui.pages.settings_widgets.management_center_settings import ManagementCenterSettingsWidget
from src.utils.desktop_web_sync import configured_sync_url


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


def test_user_management_detail_panel_uses_selected_database_user():
    _app()
    db = DialogDatabase()
    db.cursor.execute("ALTER TABLE users ADD COLUMN active INTEGER DEFAULT 1")
    db.cursor.execute("ALTER TABLE users ADD COLUMN interface_edit_access INTEGER DEFAULT 0")
    db.cursor.execute("INSERT INTO personnel (id, name) VALUES (7, 'Test Person')")
    user_id = db.add_user("Personel", json.dumps({"pages": [21, 50]}))
    db.cursor.execute("UPDATE users SET personnel_id=7 WHERE id=?", (user_id,))
    db.conn.commit()
    db._get_table_columns = lambda table: [
        row[1] for row in db.cursor.execute(f"PRAGMA table_info({table})").fetchall()
    ]

    widget = UserManagementWidget(db)
    widget.table.setRowCount(1)
    widget.table.setItem(0, 0, QTableWidgetItem(str(user_id)))
    widget._update_detail_panel(0)

    assert widget.detail_title.text() == "Test Person"
    assert "test-user" in widget.detail_status.text()
    assert widget.detail_values["personnel"].text() == "Test Person"
    assert widget.detail_values["role"].text() == "Personel"
    assert widget._permission_baseline == {21, 50}
    assert {page_id for page_id, check in widget.detail_permission_checks.items()
            if check.isChecked()} == {21, 50}
    for page_ids, label in widget.detail_permission_rows.values():
        granted = len({21, 50}.intersection(page_ids))
        assert label.text() == f"{granted} / {len(page_ids)} izin"
    db.cursor.execute("UPDATE users SET personnel_id=NULL WHERE id=?", (user_id,))
    db.conn.commit()
    widget._update_detail_panel(0)
    assert widget.detail_title.text() == "test-user"
    assert "test-user" in widget.detail_status.text()
    widget.close()


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
    assert opened == [configured_sync_url().rstrip("/") + "/?page=control-center"]
    widget.close()
