import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests
import pytest

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"


def test_announcement_page_matches_desktop_columns_and_actions():
    source = APP.read_text(encoding="utf-8")
    reference = (ROOT / "Web_Arayuzu" / "web" / "announcements-reference.js").read_text(encoding="utf-8")
    start = source.index("function renderAnnouncements()")
    end = source.index("const ayecRenderBeforeAnnouncements=render;", start)
    page = source[start:end]
    assert "data-announcement-add" in page
    assert "data-announcement-refresh" in page
    assert 'data-kind="announcement"' in page
    assert '<th>Tarih</th>' in page
    assert '<th>\\u00d6ncelik</th>' in page
    assert '<th>\\u00dc' in page or '<th>\\u0130\\u00e7erik</th>' in page
    assert 'announcement-edit' in page and 'announcement-delete' in page
    assert 'loadAllDesktopTableData("announcements")' in source
    assert '\\u270f D\\u00fczenle' in page
    assert '\\u{1f5d1} Sil' in page
    assert 'name="title"' in page and 'name="priority"' in page and 'name="content"' in page
    assert 'duyurusu listeden kald\\u0131r\\u0131lacak. Onayl\\u0131yorum.' in reference
    assert 'geri al\\u0131namaz' not in reference
    delete_start = source.index("function ayecConfirmAnnouncementDelete")
    delete_end = source.index("\n", delete_start)
    assert 'duyurusu listeden kald\\u0131r\\u0131lacak m\\u0131?' in source[delete_start:delete_end]
    assert 'geri al\\u0131namaz' not in source[delete_start:delete_end]


@pytest.mark.parametrize("legacy_delete_column", [None, "is_archived"])
def test_announcement_create_update_and_delete_use_tenant_table(monkeypatch, tmp_path, legacy_delete_column):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    archived_column = ", is_archived INTEGER DEFAULT 0" if legacy_delete_column else ""
    with sqlite3.connect(tenant_path) as conn:
        conn.execute("DROP TABLE IF EXISTS announcements")
        conn.execute(
            f"""
            CREATE TABLE announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                priority TEXT,
                title TEXT,
                content TEXT,
                author TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
                {archived_column}
            )
            """
        )
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
        assert login.status_code == 200
        created = session.post(
            f"{base_url}/api/desktop/table/announcements",
            json={
                "date": "13.10.2026",
                "priority": "Y\u00fcksek",
                "title": "Maintenance notice",
                "content": "Service unavailable at midnight",
                "author": "Web Admin",
            },
        )
        assert created.status_code == 200
        announcement_id = created.json()["id"]
        updated = session.post(
            f"{base_url}/api/desktop/table/announcements",
            json={"id": announcement_id, "_action": "update", "title": "Updated notice", "content": "Updated text"},
        )
        assert updated.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            row = conn.execute(
                "SELECT date,priority,title,content,author FROM announcements WHERE id=?",
                (announcement_id,),
            ).fetchone()
        assert row == ("13.10.2026", "Y\u00fcksek", "Updated notice", "Updated text", "Web Admin")
        deleted = session.post(
            f"{base_url}/api/desktop/table/announcements",
            json={"id": announcement_id, "_action": "delete"},
        )
        assert deleted.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(announcements)")}
            deleted_column = legacy_delete_column or "is_deleted"
            assert {deleted_column, "deleted_at"}.issubset(columns)
            deleted_row = conn.execute(
                f'SELECT title,"{deleted_column}",deleted_at FROM announcements WHERE id=?',
                (announcement_id,),
            ).fetchone()
        assert deleted_row is not None
        assert deleted_row[:2] == ("Updated notice", 1)
        assert deleted_row[2]
        listed = session.get(f"{base_url}/api/desktop/table/announcements")
        assert listed.status_code == 200
        assert all(int(row["id"]) != announcement_id for row in listed.json()["rows"])
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_announcement_context_menu_preserves_desktop_order_and_page_gate():
    source = APP.read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "pages" / "announcements_page.py").read_text(encoding="utf-8")
    menu_start = source.index('showContext=function(event,kind,id){if(kind!=="announcement")')
    menu_end = source.index("\n", menu_start)
    web_menu = source[menu_start:menu_end]
    desktop_start = desktop.index("def show_context_menu(self, position):")
    desktop_end = desktop.index("def delete_announcement_from_table", desktop_start)
    desktop_menu = desktop[desktop_start:desktop_end]
    expected = ["announcement-edit", "announcement-delete"]
    positions = [web_menu.index('"' + action + '"') for action in expected]

    assert positions == sorted(positions)
    assert 'announcements:"rc_announcements"' in source
    assert "ayecContextMenuEnabled()" in web_menu
    assert '"\\u270f D\\u00fczenle"' in web_menu
    assert '"\\u{1f5d1} Sil"' in web_menu
    assert 'context_menu.addAction("\u270f D\u00fczenle")' in desktop_menu
    assert 'context_menu.addAction("\U0001f5d1 Sil")' in desktop_menu



def test_offscreen_route_audit_covers_announcement_crud_and_write_failure_recovery():
    route_smoke = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "result.announcementCrudWorkflow" in route_smoke
    assert "announcement.failureKeptDialog" in route_smoke
    assert "announcement.failureToast" in route_smoke
    assert "announcement.deleteFailureKeptDialog" in route_smoke
    assert "announcement.deleteFailureToast" in route_smoke
    assert 'announcement.writes.length !== 5' in route_smoke
    assert 'announcement.writes[2]._action !== "update"' in route_smoke
    assert 'announcement.writes[3]._action !== "delete"' in route_smoke
    assert 'announcement.deleteConfirmText.includes("QA Updated Notice")' in route_smoke
    assert 'announcement.deleteConfirmText.includes("listeden kald\\u0131r\\u0131lacak")' in route_smoke
    assert 'announcement.deleteConfirmText.includes("geri al\\u0131namaz")' in route_smoke
