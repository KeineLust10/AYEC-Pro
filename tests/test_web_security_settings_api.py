import importlib.util
import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_web_module(monkeypatch, tmp_path):
    monkeypatch.setenv("AYEC_DB_PATH", str(tmp_path / "registry.db"))
    monkeypatch.setenv("AYEC_TENANT_DIR", str(tmp_path / "tenants"))
    (tmp_path / "tenants").mkdir()
    name = "ayec_web_security_settings_test"
    spec = importlib.util.spec_from_file_location(name, ROOT / "Web_Arayuzu/Main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.DB_PATH = tmp_path / "security.db"
    return module


def test_security_settings_api_hashes_passwords_and_keeps_tenant_user_scope(monkeypatch, tmp_path):
    module = _load_web_module(monkeypatch, tmp_path)
    with module.closing(module.db_connect()) as connection:
        module.ensure_web_schema(connection)
        connection.execute(
            "INSERT INTO users (id,username,password,role,auto_login) VALUES (1,'admin','unused','Admin',0)"
        )
        connection.commit()

    class Handler(module.AYECRequestHandler):
        def current_user(self):
            return {"id": 1, "username": "admin", "role": "Admin"}

        def same_origin(self):
            return True

        def log_message(self, _format, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    root = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        invalid = urllib.request.Request(
            root + "/api/desktop/security-settings",
            data=json.dumps({"app_lock_active": True, "app_password": "x"}).encode(),
            headers={"Content-Type": "application/json", "Origin": root},
            method="POST",
        )
        try:
            urllib.request.urlopen(invalid)
            assert False, "short password should be rejected"
        except urllib.error.HTTPError as error:
            assert error.code == 400

        update = urllib.request.Request(
            root + "/api/desktop/security-settings",
            data=json.dumps({
                "app_lock_active": True,
                "app_password": "Valid-Password-4321",
                "tech_lock_active": True,
                "tech_password": "Valid-Tech-Password-4321",
                "auto_login": True,
                "security_question": "City of birth",
                "security_answer": "Example City",
            }).encode(),
            headers={"Content-Type": "application/json", "Origin": root},
            method="POST",
        )
        with urllib.request.urlopen(update) as response:
            assert json.load(response)["ok"] is True

        with module.closing(module.db_connect()) as connection:
            stored = module.setting_value(connection, "app_password")
            assert stored != "Valid-Password-4321"
            assert stored.startswith(("$2a$", "$2b$", "$2y$"))
            user = connection.execute("SELECT auto_login FROM users WHERE id=1").fetchone()
            assert user[0] == 1

        with urllib.request.urlopen(root + "/api/desktop/security-settings") as response:
            state = json.load(response)
        assert state["app_lock_active"] is True
        assert state["app_password_configured"] is True
        assert state["tech_lock_active"] is True
        assert state["tech_password_configured"] is True
        assert state["auto_login"] is True
        assert state["security_question"] == "City of birth"
        assert "app_password" not in state

        wrong_lock_password = urllib.request.Request(
            root + "/api/desktop/security-settings/verify-app-lock",
            data=json.dumps({"password": "Wrong-Password-4321"}).encode(),
            headers={"Content-Type": "application/json", "Origin": root},
            method="POST",
        )
        try:
            urllib.request.urlopen(wrong_lock_password)
            assert False, "wrong app-lock password should be rejected"
        except urllib.error.HTTPError as error:
            assert error.code == 401

        valid_lock_password = urllib.request.Request(
            root + "/api/desktop/security-settings/verify-app-lock",
            data=json.dumps({"password": "Valid-Password-4321"}).encode(),
            headers={"Content-Type": "application/json", "Origin": root},
            method="POST",
        )
        with urllib.request.urlopen(valid_lock_password) as response:
            assert json.load(response) == {"ok": True, "required": True}

        wrong_tech_password = urllib.request.Request(
            root + "/api/desktop/security-settings/verify-tech-lock",
            data=json.dumps({"password": "Wrong-Tech-Password-4321"}).encode(),
            headers={"Content-Type": "application/json", "Origin": root},
            method="POST",
        )
        try:
            urllib.request.urlopen(wrong_tech_password)
            assert False, "wrong technician-lock password should be rejected"
        except urllib.error.HTTPError as error:
            assert error.code == 401

        valid_tech_password = urllib.request.Request(
            root + "/api/desktop/security-settings/verify-tech-lock",
            data=json.dumps({"password": "Valid-Tech-Password-4321"}).encode(),
            headers={"Content-Type": "application/json", "Origin": root},
            method="POST",
        )
        with urllib.request.urlopen(valid_tech_password) as response:
            assert json.load(response) == {"ok": True, "required": True}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_disconnected_client_during_response_headers_is_handled(monkeypatch, tmp_path):
    module = _load_web_module(monkeypatch, tmp_path)
    handler = object.__new__(module.AYECRequestHandler)
    handler._notify_sync_listeners_after_write = lambda _status: (_ for _ in ()).throw(
        AssertionError("disconnected writes must not publish sync events")
    )
    monkeypatch.setattr(
        handler,
        "_headers",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ConnectionResetError()),
        raising=False,
    )

    assert handler.send_json({"ok": True}) is None
