from pathlib import Path

import pytest

from src.database import Database
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
