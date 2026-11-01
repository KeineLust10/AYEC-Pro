from pathlib import Path
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from src.database import Database
from tests.test_vendor_management_center import _setup_tenant
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_project_lifecycle_actions_match_desktop_database_operations(monkeypatch, tmp_path):
    database_path = tmp_path / "project-lifecycle.db"
    database = Database(str(database_path))
    project_id = database.add_project({"name": "Lifecycle Project"})
    database.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    assert web_main.desktop_project_lifecycle_action({"project_id": project_id, "action": "archive"})["ok"]
    database = Database(str(database_path), init_mode="connection_only")
    assert database.conn.execute("SELECT is_archived FROM projects WHERE id=?", (project_id,)).fetchone()[0] == 1
    database.close()

    assert web_main.desktop_project_lifecycle_action({"project_id": project_id, "action": "restore"})["ok"]
    assert web_main.desktop_project_lifecycle_action({"project_id": project_id, "action": "complete"})["ok"]
    database = Database(str(database_path), init_mode="connection_only")
    assert tuple(database.conn.execute("SELECT is_archived,status FROM projects WHERE id=?", (project_id,)).fetchone()) == (0, "Tamamland\u0131")
    database.close()

    assert web_main.desktop_project_lifecycle_action({"project_id": project_id, "action": "delete"})["ok"]
    database = Database(str(database_path), init_mode="connection_only")
    assert database.conn.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone() is None
    database.close()


def test_project_lifecycle_action_rejects_unknown_projects_and_actions(monkeypatch, tmp_path):
    database_path = tmp_path / "project-lifecycle-invalid.db"
    Database(str(database_path)).close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    with pytest.raises(LookupError, match="Project was not found"):
        web_main.desktop_project_lifecycle_action({"project_id": 123, "action": "archive"})
    with pytest.raises(ValueError, match="valid project action"):
        web_main.desktop_project_lifecycle_action({"project_id": 123, "action": "rename"})


def test_archived_project_table_query_returns_only_archived_tenant_projects(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    database = Database(str(tenant_path), init_mode="connection_only")
    active_id = database.add_project({"name": "Active Project"})
    archived_id = database.add_project({"name": "Archived Project"})
    database.archive_project(archived_id)
    database.close()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200, login.text

        response = session.get(f"{base_url}/api/desktop/table/projects?limit=30&archived_only=1")
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["count"] == 1
        assert [row["id"] for row in payload["rows"]] == [archived_id]
        assert payload["rows"][0]["name"] == "Archived Project"
        assert active_id != archived_id
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_project_archive_route_uses_filtered_cards_and_lifecycle_actions():
    script = (ROOT / "Web_Arayuzu" / "web" / "project-archive-reference.js").read_text(encoding="utf-8")
    index = (ROOT / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")
    backend = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    route_audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "archived_only=1" in script
    assert 'data-project-archive-action="restore"' in script
    assert 'data-project-archive-action="delete"' in script
    assert 'apiFetch("/api/desktop/projects/lifecycle"' in script
    assert 'query.get("archived_only", ["0"])[0] == "1"' in backend
    assert 'project-archive-reference.js?v=' in index
    assert 'const deleteCancelNoWrite = !calls.some' in route_audit
    assert 'const deleteConfirmReopened = Boolean' in route_audit


def test_project_lifecycle_actions_are_confirmed_in_web_ui():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openProjectLifecycleDialog(")
    end = app.index("function openProjectTransactionDetailDialog(", start)
    flow = app[start:end]

    for action in ("archive", "restore", "complete", "delete"):
        assert f'{action}: [' in flow
    assert 'apiFetch("/api/desktop/projects/lifecycle"' in flow
    assert 'data-p9-project-action="delete"' in app
    assert 'data-p9-project-action="${Number(project.is_archived) ? "restore" : "archive"}"' in app
    assert 'data-p9-project-action="complete"' in app
