import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ui import modern_login_window


class _Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class _Auth:
    def __init__(self):
        self.current_user = None
        self.logged_out = False
        self.token_cleared = False

    def get_saved_token(self):
        return "remember-token"

    def auto_login(self, token):
        assert token == "remember-token"
        self.current_user = {"username": "remembered-user"}
        return True

    def logout(self):
        self.logged_out = True
        self.current_user = None

    def clear_token(self):
        self.token_cleared = True


class _Database:
    def __init__(self, tenant_id="tenant-1"):
        self.settings = {
            "web_sync_tenant_id": tenant_id,
            "server_access_revoked": "0",
        }

    def get_setting(self, key, default=""):
        return self.settings.get(key, default)

    def set_setting(self, key, value):
        self.settings[key] = value


class _LoginHarness:
    def __init__(self):
        self.auth_manager = _Auth()
        self.db = _Database()
        self.started = False
        self._pending_user = None
        self._remembered_server_worker = None

    def start_opening(self):
        self.started = True

    def _remembered_server_access_checked(self, reachable, allowed, message):
        return modern_login_window.ModernLoginWindow._remembered_server_access_checked(
            self,
            reachable,
            allowed,
            message,
        )

    def _clear_remembered_server_worker(self, worker):
        if self._remembered_server_worker is worker:
            self._remembered_server_worker = None


def test_server_bound_remembered_login_is_validated_then_opened(monkeypatch):
    class _Worker:
        def __init__(self, username, tenant_id, parent):
            assert username == "remembered-user"
            assert tenant_id == "tenant-1"
            assert parent is harness
            self.completed = _Signal()
            self.finished = _Signal()

        def start(self):
            self.completed.emit(True, True, "")
            self.finished.emit()

        def deleteLater(self):
            return None

    harness = _LoginHarness()
    monkeypatch.setattr(
        modern_login_window,
        "_RememberedServerAccessWorker",
        _Worker,
    )

    modern_login_window.ModernLoginWindow.check_auto_login(harness)

    assert harness.started is True
    assert harness._pending_user == {"username": "remembered-user"}
    assert harness.db.settings["server_access_revoked"] == "0"


def test_rejected_remembered_server_session_does_not_open(monkeypatch):
    class _Worker:
        def __init__(self, _username, _tenant_id, _parent):
            self.completed = _Signal()
            self.finished = _Signal()

        def start(self):
            self.completed.emit(True, False, "Oturum gecersiz.")
            self.finished.emit()

        def deleteLater(self):
            return None

    harness = _LoginHarness()
    monkeypatch.setattr(
        modern_login_window,
        "_RememberedServerAccessWorker",
        _Worker,
    )
    monkeypatch.setattr(modern_login_window, "show_info", lambda *_args: None)

    modern_login_window.ModernLoginWindow.check_auto_login(harness)

    assert harness.started is False
    assert harness.auth_manager.logged_out is True
    assert harness.auth_manager.token_cleared is True


def test_legacy_revocation_flag_does_not_block_temporary_offline_login(
    monkeypatch,
):
    harness = _LoginHarness()
    harness.auth_manager.current_user = {"username": "remembered-user"}
    harness.db.settings["server_access_revoked"] = "1"
    monkeypatch.setattr(modern_login_window, "show_warning", lambda *_args: None)

    harness._remembered_server_access_checked(False, False, "Bad Gateway")

    assert harness.started is True
    assert harness.auth_manager.logged_out is False


def test_authoritative_revocation_still_blocks_offline_login(monkeypatch):
    harness = _LoginHarness()
    harness.auth_manager.current_user = {"username": "remembered-user"}
    harness.db.settings["server_access_revoked"] = "1"
    harness.db.settings["server_access_revoked_authoritative"] = "1"
    monkeypatch.setattr(modern_login_window, "show_info", lambda *_args: None)

    harness._remembered_server_access_checked(False, False, "Offline")

    assert harness.started is False
    assert harness.auth_manager.logged_out is True
    assert harness.auth_manager.token_cleared is True
