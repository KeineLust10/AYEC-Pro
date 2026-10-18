from pathlib import Path
import sqlite3
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from src.database import Database
from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


ROOT = Path(__file__).resolve().parents[1]


def _database(path, sector):
    database = Database(str(path))
    database.set_internal_setting("current_sector", sector)
    database.conn.execute(
        "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, 1, 0)",
        ("Unrelated category", "Keep this note"),
    )
    database.conn.commit()
    database.close()


def test_technical_profile_replaces_only_its_profile_categories(tmp_path, monkeypatch):
    database_path = tmp_path / "technical-notes.db"
    _database(database_path, "teknik_servis")
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    result = web_main.desktop_apply_fast_note_profile("Cep Telefonu")

    category = "Teknik Servis::Cep Telefonu::Arıza Hızlı Seçimi"
    database = Database(str(database_path), init_mode="connection_only")
    notes = database.conn.execute(
            "SELECT label, is_active, display_order FROM fast_notes WHERE category=? ORDER BY display_order",
            (category,),
    ).fetchall()
    unrelated = database.conn.execute(
            "SELECT label FROM fast_notes WHERE category='Unrelated category'"
    ).fetchone()
    database.close()
    assert result["profile"] == "Cep Telefonu"
    assert result["sector"] == "teknik_servis"
    assert len(notes) == 8
    assert notes[0][0] == "EKRAN KIRIK"
    assert all(row[1] == 1 for row in notes)
    assert [row[2] for row in notes] == list(range(8))
    assert unrelated[0] == "Keep this note"


def test_automotive_profile_uses_automotive_categories(tmp_path, monkeypatch):
    database_path = tmp_path / "automotive-notes.db"
    _database(database_path, "otomotiv")
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    result = web_main.desktop_apply_fast_note_profile("Otomotiv")

    database = Database(str(database_path), init_mode="connection_only")
    labels = database.conn.execute(
            "SELECT label FROM fast_notes WHERE category='Otomotiv Araç Kabul' ORDER BY display_order"
    ).fetchall()
    database.close()
    assert result["sector"] == "otomotiv"
    assert len(labels) == 6
    assert labels[0][0] == "RUHSAT"


def test_invalid_profile_and_failed_insert_leave_existing_notes_unchanged(tmp_path, monkeypatch):
    database_path = tmp_path / "profile-rollback.db"
    _database(database_path, "teknik_servis")
    category = "Teknik Servis::Bilgisayar::Arıza Hızlı Seçimi"
    database = Database(str(database_path), init_mode="connection_only")
    database.conn.execute(
        "INSERT INTO fast_notes (category, label, is_active, display_order) VALUES (?, ?, 1, 7)",
        (category, "Existing note"),
    )
    database.conn.commit()
    database.conn.execute(
        "CREATE TRIGGER reject_profile_note BEFORE INSERT ON fast_notes "
        "WHEN NEW.label='GÖRÜNTÜ YOK' BEGIN SELECT RAISE(ABORT, 'forced'); END"
    )
    database.conn.commit()
    database.close()
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)

    with pytest.raises(ValueError):
        web_main.desktop_apply_fast_note_profile("Unknown")
    with pytest.raises(sqlite3.IntegrityError):
        web_main.desktop_apply_fast_note_profile("Bilgisayar")

    database = Database(str(database_path), init_mode="connection_only")
    existing = database.conn.execute(
            "SELECT label, display_order FROM fast_notes WHERE category=?",
            (category,),
    ).fetchone()
    database.close()
    assert tuple(existing) == ("Existing note", 7)


def test_profile_apply_route_requires_a_web_session():
    source = (ROOT / "Web_Arayuzu" / "Main.py").read_text(encoding="utf-8")
    start = source.index('if path == "/api/desktop/fast-notes/apply-profile":')
    route = source[start:source.index('if path == "/api/desktop/projects/unit-sales":', start)]

    assert route.index("if not self.current_user()") < route.index("self.read_json()")
    assert 'desktop_apply_fast_note_profile(payload.get("profile"))' in route


def test_quick_notes_manager_exposes_sector_profiles_and_confirms_replacement():
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = app.index("function applyQuickNoteProfile(")
    end = app.index("\nfunction showQuickNoteContext", start)
    flow = app[start:end]

    assert 'id="quickNoteProfile"' in app
    assert 'id="quickNoteApplyProfile"' in app
    assert '"Otomotiv"' in app and '"Bilgisayar"' in app
    assert "mevcut h\u0131zl\u0131 notlar\u0131 yenileriyle de\u011fi\u015ftirir" in flow
    assert '"/api/desktop/fast-notes/apply-profile"' in flow
    assert 'submit.classList.add("danger")' in flow


def test_profile_apply_http_route_requires_login_and_writes_active_tenant(
    tmp_path, monkeypatch
):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as connection:
        connection.execute(
            "INSERT OR REPLACE INTO internal_settings (key, value) VALUES (?, ?)",
            ("current_sector", "teknik_servis"),
        )
        connection.commit()
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/fast-notes/apply-profile"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.post(endpoint, json={"profile": "Bilgisayar"}).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200, login.text
        response = session.post(endpoint, json={"profile": "Bilgisayar"})
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["ok"] is True
        assert result["sector"] == "teknik_servis"
        with sqlite3.connect(tenant_path) as connection:
            labels = connection.execute(
                "SELECT label FROM fast_notes WHERE category=? ORDER BY display_order",
                ("Teknik Servis::Bilgisayar::Arıza Hızlı Seçimi",),
            ).fetchall()
        assert len(labels) == 8
        assert labels[0][0] == "GÖRÜNTÜ YOK"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
