from pathlib import Path

import pytest

from src.database import Database
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]


def test_bulk_project_units_create_desktop_named_units(monkeypatch, tmp_path):
    database_path = tmp_path / "project-units.db"
    database = Database(str(database_path))
    project_id = database.add_project({"name": "Bulk Unit Fixture", "start_date": "2026-01-01", "end_date": "2026-12-31"})
    database.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    result = web_main.desktop_create_project_units({
        "project_id": project_id,
        "block_count": 3,
        "unit_count": 2,
        "naming": "custom",
        "custom_names": "North, South",
    })
    database = Database(str(database_path), init_mode="connection_only")
    try:
        units = database.conn.execute(
            "SELECT block_name,unit_no,floor_no,status,unit_kind FROM project_units WHERE project_id=? ORDER BY id",
            (project_id,),
        ).fetchall()
        assert [tuple(row) for row in units] == [
            ("North", "North-1", "0", "Bekliyor", "Daire"),
            ("North", "North-2", "0", "Bekliyor", "Daire"),
            ("South", "South-1", "0", "Bekliyor", "Daire"),
            ("South", "South-2", "0", "Bekliyor", "Daire"),
            ("Blok3", "Blok3-1", "0", "Bekliyor", "Daire"),
            ("Blok3", "Blok3-2", "0", "Bekliyor", "Daire"),
        ]
        assert result == {"ok": True, "project_id": project_id, "units_created": 6, "blocks": ["North", "South", "Blok3"]}
    finally:
        database.close()


def test_bulk_project_units_validate_project_and_limits(monkeypatch, tmp_path):
    database_path = tmp_path / "project-units-validation.db"
    Database(str(database_path)).close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    with pytest.raises(LookupError, match="Project was not found"):
        web_main.desktop_create_project_units({"project_id": 404, "block_count": 1, "unit_count": 5})
    with pytest.raises(ValueError, match="1-26 blocks"):
        web_main.desktop_create_project_units({"project_id": 1, "block_count": 27, "unit_count": 5})
    with pytest.raises(ValueError, match="naming mode"):
        web_main.desktop_create_project_units({"project_id": 1, "block_count": 1, "unit_count": 5, "naming": "other"})


def test_bulk_project_unit_dialog_has_desktop_controls_and_preview():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert 'data-p9-add-unit="bulk"' in app
    start = app.index("function openBulkProjectUnitsDialog(")
    end = app.index("function openProjectLifecycleDialog(", start)
    flow = app[start:end]
    for field in ("block_count", "unit_count", "naming", "custom_names"):
        assert f'name="{field}"' in flow
    assert "/api/desktop/projects/units/bulk-create" in flow


def test_single_project_unit_form_replaces_native_prompts():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function openSingleProjectUnitDialog(")
    end = app.index("function openProjectLifecycleDialog(", start)
    flow = app[start:end]
    for field in ("unit_no", "block_name", "floor_no", "unit_kind", "status", "area", "unit_price", "description"):
        assert f'name="{field}"' in flow
    handler_start = app.index('else if (addUnit) {', app.index('document.addEventListener("click", async event => {'))
    handler_end = app.index("\n", handler_start)
    assert 'openSingleProjectUnitDialog(project)' in app[handler_start:handler_end]
    assert 'prompt("Daire veya oda numarasi")' not in app[handler_start:handler_end]

