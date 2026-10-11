import importlib.util
import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from src.utils import windows_shortcuts


ROOT = Path(__file__).resolve().parents[1]


def test_local_admin_system_actions_route(monkeypatch, tmp_path):
    monkeypatch.setenv("AYEC_DB_PATH", str(tmp_path / "registry.db"))
    monkeypatch.setenv("AYEC_TENANT_DIR", str(tmp_path / "tenants"))
    (tmp_path / "tenants").mkdir()
    name = "ayec_web_identity_actions_test"
    spec = importlib.util.spec_from_file_location(name, ROOT / "Web_Arayuzu/Main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.DB_PATH = tmp_path / "system-actions.db"
    with module.closing(module.db_connect()) as connection:
        module.ensure_web_schema(connection)
        connection.execute(
            "INSERT INTO users (id,username,password,role) VALUES (1,'admin','unused','Admin')"
        )
        connection.commit()

    calls = []
    monkeypatch.setattr(windows_shortcuts, "is_in_windows_startup", lambda: True)
    monkeypatch.setattr(windows_shortcuts, "set_windows_startup", lambda enabled: calls.append(("startup", enabled)))
    monkeypatch.setattr(windows_shortcuts, "open_database_folder", lambda path: calls.append(("open", str(path))))
    monkeypatch.setattr(windows_shortcuts, "create_shortcut", lambda location: calls.append(("shortcut", location)) or tmp_path / "AYEC Pro.lnk")

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
    root = "http://127.0.0.1:" + str(server.server_address[1])
    try:
        with urllib.request.urlopen(root + "/api/desktop/system-info") as response:
            info = json.load(response)
        assert info["startup_enabled"] is True
        assert info["shell_actions_available"] is (module.os.name == "nt")

        for payload in (
            {"action": "startup", "enabled": False},
            {"action": "open-database-folder"},
            {"action": "desktop-shortcut"},
            {"action": "start-menu-shortcut"},
        ):
            request = urllib.request.Request(
                root + "/api/desktop/system-actions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "Origin": root},
                method="POST",
            )
            with urllib.request.urlopen(request) as response:
                assert json.load(response)["ok"] is True
        assert calls[0] == ("startup", False)
        assert calls[1][0] == "open"
        assert calls[2:] == [("shortcut", "desktop"), ("shortcut", "start-menu")]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
