import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QDialog

from src.ui.dialogs.app_lock_dialog import AppLockDialog
from src.utils.password_security import hash_password
from src.utils.secure_setting_store import SecureSettingStore


class _Db:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get_setting(self, key, default=""):
        return self.values.get(key, default)

    def set_setting(self, key, value):
        self.values[key] = value
        return True


def _app():
    return QApplication.instance() or QApplication([])


def test_secure_setting_store_migrates_legacy_value_and_round_trips():
    db = _Db({"smtp_password": "legacy-secret"})

    assert SecureSettingStore.get(db, "smtp_password") == "legacy-secret"
    assert db.values["smtp_password"].startswith(SecureSettingStore.PREFIX)
    assert SecureSettingStore.get(db, "smtp_password") == "legacy-secret"


def test_secure_setting_store_does_not_encrypt_empty_values():
    db = _Db()

    SecureSettingStore.set(db, "telegram_bot_token", "")

    assert db.values["telegram_bot_token"] == ""


def test_app_lock_dialog_accepts_hash_and_reports_legacy_upgrade():
    _app()
    dialog = AppLockDialog(hash_password("SafePass1234"))
    dialog.inp_password.setText("SafePass1234")
    dialog.check_password()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.upgraded_hash is None
    dialog.close()


def test_app_lock_dialog_upgrades_legacy_password_after_success():
    _app()
    dialog = AppLockDialog("legacy-secret")
    dialog.inp_password.setText("legacy-secret")
    dialog.check_password()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.upgraded_hash.startswith("$2")
    dialog.close()
