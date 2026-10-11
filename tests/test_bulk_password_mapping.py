import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit

from src.database import Database
from src.ui.dialogs.bulk_password_dialog import BulkPasswordDialog
from src.ui.widgets.modern_confirm_dialog import ModernConfirmDialog
from src.ui.pages.settings_widgets.user_management import UserManagementWidget
from src.utils.user_account_actions import change_account_passwords
from src.utils.password_security import verify_password
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_bulk_password_validation_authority_and_atomic_rollback(monkeypatch, tmp_path):
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "bulk_atomic.db"))
    seed_visual_fixture(db)
    baseline = [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
    try:
        for actor, entries, error in (
            (3, [(2, "StrongPassword11"), (6, "short")], ValueError),
            (3, [(2, "StrongPassword11"), (6, "StrongPassword11")], ValueError),
            (4, [(2, "StrongPassword11")], PermissionError),
            (3, [(1, "StrongPassword11")], PermissionError),
            (3, [(999999, "StrongPassword11")], PermissionError),
        ):
            with pytest.raises(error):
                change_account_passwords(db, actor, entries)
            assert baseline == [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
        db.conn.execute("CREATE TRIGGER fail_second_password BEFORE UPDATE OF password ON users WHEN OLD.id=6 BEGIN SELECT RAISE(ABORT, 'blocked-test'); END")
        db.conn.commit()
        with pytest.raises(Exception, match="blocked-test"):
            change_account_passwords(db, 3, [(2, "StrongPassword11"), (6, "DifferentPassword22")])
        assert baseline == [tuple(row) for row in db.conn.execute("SELECT * FROM users ORDER BY id")]
    finally:
        db.close()


def test_bulk_button_uses_existing_password_codec_and_requires_confirmation(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv("AYEC_VISUAL_ACCEPTANCE", "1")
    db = Database(str(tmp_path / "bulk_widget.db"))
    seed_visual_fixture(db)
    before = {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
    owner = QWidget()
    owner.db = db
    owner.current_user = {"id": 3, "role": "Master"}
    owner.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    page = UserManagementWidget(db)
    page.setParent(owner)
    page.show()
    owner.show()
    app.processEvents()
    opened = []

    def run_dialog(dialog):
        opened.append(dialog)
        assert dialog.db is db
        assert dialog.actor_id == 3
        assert not dialog.account_controls[1][0].isEnabled()
        assert not dialog.account_controls[3][0].isEnabled()
        checkbox, password = dialog.account_controls[2]
        assert password.echoMode() == QLineEdit.EchoMode.Password
        checkbox.setChecked(True)
        password.setText("ChangedPassword19")
        monkeypatch.setattr(ModernConfirmDialog, "exec", lambda _dialog: 0)
        dialog.apply_button.click()
        assert before == {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
        monkeypatch.setattr(ModernConfirmDialog, "exec", lambda _dialog: 1)
        dialog.apply_button.click()
        after = {row["id"]: dict(row) for row in db.conn.execute("SELECT * FROM users")}
        assert verify_password("ChangedPassword19", after[2]["password"])[0]
        assert after[2]["password"] != before[2]["password"]
        assert after[2]["remember_token"] is None
        assert after[2]["auto_login"] == 0
        assert after[2]["must_change_password"] == 0
        assert after[2]["password_updated_at"]
        for user_id, original in before.items():
            for key, value in original.items():
                if user_id != 2 or key not in {"password", "password_updated_at", "remember_token", "auto_login", "must_change_password"}:
                    assert after[user_id][key] == value
        assert password.text() == ""
        return 1

    monkeypatch.setattr(BulkPasswordDialog, "exec", run_dialog)
    try:
        assert page.bulk_password_button.isEnabled()
        page.bulk_password_button.click()
        assert len(opened) == 1
        owner.current_user = {"id": 4, "role": "Muhasebe"}
        page._open_bulk_password_dialog()
        assert len(opened) == 1
    finally:
        page.close()
        page.deleteLater()
        owner.close()
        owner.deleteLater()
        app.processEvents()
        db.close()
