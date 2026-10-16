import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

import pytest
import requests

from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def _set_tenant_context(monkeypatch, tenant_root, database_path):
    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-a")
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)
    monkeypatch.setattr(
        web_main,
        "_tenant_record_required",
        lambda tenant_id: {
            "id": tenant_id,
            "db_filename": database_path.name,
            "product_code": "teknik_servis",
        },
    )
    monkeypatch.setattr(web_main, "configured_product_codes", lambda: {"teknik_servis"})


def test_desktop_backup_creates_integrity_checked_central_snapshot(monkeypatch, tmp_path):
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    database_path = tenant_root / "tenant-a.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute("CREATE TABLE sample (value TEXT NOT NULL)")
        conn.execute("INSERT INTO sample VALUES ('snapshot-data')")
    _set_tenant_context(monkeypatch, tenant_root, database_path)
    stored = {}
    audit = []

    def store(tenant_id, user_id, payload, filename, source, product, hardware, installation):
        stored.update(
            tenant_id=tenant_id,
            user_id=user_id,
            payload=payload,
            filename=filename,
            source=source,
            product=product,
            hardware=hardware,
            installation=installation,
        )
        return {"ok": True, "backup_id": 7, "size_bytes": len(payload), "sha256": "digest"}

    monkeypatch.setattr(web_main, "_store_support_backup_for_tenant", store)
    monkeypatch.setattr(web_main, "_support_audit", lambda *args, **kwargs: audit.append((args, kwargs)))
    actor = {"id": 4, "role": "admin", "_tenant_id": "tenant-a"}

    result = web_main.desktop_create_backup(actor)

    assert result["backup_id"] == 7
    assert stored["tenant_id"] == "tenant-a"
    assert stored["user_id"] == 4
    assert stored["source"] == "web"
    assert stored["product"] == "teknik_servis"
    assert stored["hardware"] == "web-runtime"
    assert stored["installation"] == "web-app"
    assert stored["payload"].startswith(b"SQLite format 3\x00")
    snapshot_path = tmp_path / "snapshot-check.db"
    snapshot_path.write_bytes(stored["payload"])
    with sqlite3.connect(snapshot_path) as snapshot:
        assert snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert snapshot.execute("SELECT value FROM sample").fetchone()[0] == "snapshot-data"
    assert audit


def test_database_restore_upload_is_staged_only_for_matching_company_identity(monkeypatch, tmp_path):
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    live_path = tenant_root / "tenant-a.db"
    for path, company_name in ((live_path, "Test Company"),):
        with sqlite3.connect(path) as conn:
            conn.executescript(
                "CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,email TEXT);"
                "CREATE TABLE company_info(id INTEGER PRIMARY KEY,company_name TEXT);"
                "INSERT INTO users VALUES(4,'tenant-admin','admin@example.com');"
                "INSERT INTO company_info VALUES(1,'" + company_name + "');"
                "CREATE TABLE records(value TEXT); INSERT INTO records VALUES('restored');"
            )
    _set_tenant_context(monkeypatch, tenant_root, live_path)
    monkeypatch.setattr(
        web_main,
        "_tenant_record_required",
        lambda tenant_id: {
            "id": tenant_id,
            "db_filename": live_path.name,
            "company_name": "Test Company",
            "product_code": "teknik_servis",
        },
    )
    stored = {}
    monkeypatch.setattr(
        web_main,
        "_store_support_backup_for_tenant",
        lambda *args, **kwargs: stored.update(args=args, kwargs=kwargs)
        or {"ok": True, "backup_id": 31, "sha256": "digest", "size_bytes": len(args[2])},
    )
    audit = []
    monkeypatch.setattr(web_main, "_support_audit", lambda *args, **kwargs: audit.append((args, kwargs)))
    actor = {"id": 4, "role": "Admin", "_tenant_id": "tenant-a"}

    with sqlite3.connect(live_path) as source, sqlite3.connect(tmp_path / "valid-backup.db") as snapshot:
        source.backup(snapshot)
    valid_payload = (tmp_path / "valid-backup.db").read_bytes()
    result = web_main.desktop_stage_restore_backup(
        actor, r"C:\old-backups\tenant-restore.db", valid_payload
    )

    assert result["backup_id"] == 31
    assert result["filename"] == "tenant-restore.db"
    assert result["restore_via"] == "Admin_Konsol"
    assert stored["args"][0:5] == (
        "tenant-a", 4, stored["args"][2], "tenant-restore.db", "web-restore-staging"
    )
    assert stored["args"][2].startswith(b"SQLite format 3\x00")
    assert stored["args"][5:8] == ("teknik_servis", "", "")
    assert audit[0][0][1] == "tenant_restore_backup_staged"

    foreign_path = tmp_path / "foreign.db"
    with sqlite3.connect(foreign_path) as conn:
        conn.executescript(
            "CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,email TEXT);"
            "CREATE TABLE company_info(id INTEGER PRIMARY KEY,company_name TEXT);"
            "INSERT INTO users VALUES(4,'tenant-admin','admin@example.com');"
            "INSERT INTO company_info VALUES(1,'Other Company');"
        )
    with pytest.raises(PermissionError, match="different company"):
        web_main.desktop_stage_restore_backup(actor, "foreign.db", foreign_path.read_bytes())


def test_http_database_restore_upload_is_authenticated_and_staged_for_admin_console(
    monkeypatch, tmp_path
):
    _actor, live_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(live_path) as conn:
        conn.execute("INSERT INTO company_info(company_name) VALUES ('Test Company')")
        conn.execute("CREATE TABLE restore_sample(value TEXT)")
        conn.execute("INSERT INTO restore_sample VALUES ('from backup')")
    upload_path = tmp_path / "tenant-restore.db"
    with sqlite3.connect(live_path) as source, sqlite3.connect(upload_path) as snapshot:
        source.backup(snapshot)
    monkeypatch.setattr(web_main, "prune_support_backups", lambda _tenant_id: {})

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
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
        assert login.status_code == 200
        response = session.post(
            f"{base_url}/api/desktop/backups/import",
            data=upload_path.read_bytes(),
            headers={"X-AYEC-Backup-Name": "tenant-restore.db"},
        )
        assert response.status_code == 201, response.text
        result = response.json()
        assert result["filename"] == "tenant-restore.db"
        assert result["restore_via"] == "Admin_Konsol"
        backups = session.get(f"{base_url}/api/desktop/backups")
        assert backups.status_code == 200
        imported = next(item for item in backups.json()["backups"] if item["id"] == result["backup_id"])
        assert imported["source"] == "web-restore-staging"
        assert imported["sha256"] == result["sha256"]
        registry = web_main.registry_connect()
        try:
            stored_filename = registry.execute(
                "SELECT filename FROM support_backups WHERE id=? AND tenant_id=?",
                (result["backup_id"], "tenant-1"),
            ).fetchone()[0]
        finally:
            registry.close()
        with sqlite3.connect(web_main.SUPPORT_BACKUP_ROOT / "tenant-1" / stored_filename) as staged:
            assert staged.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert staged.execute("SELECT value FROM restore_sample").fetchone()[0] == "from backup"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_desktop_backup_rejects_cross_tenant_and_non_admin_access(monkeypatch, tmp_path):
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    database_path = tenant_root / "tenant-a.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute("CREATE TABLE sample (value TEXT)")
    _set_tenant_context(monkeypatch, tenant_root, database_path)

    try:
        web_main._desktop_backup_context({"id": 4, "role": "admin", "_tenant_id": "tenant-b"})
    except PermissionError:
        pass
    else:
        raise AssertionError("cross-tenant backup access was accepted")

    try:
        web_main._desktop_backup_context({"id": 4, "role": "staff", "_tenant_id": "tenant-a"})
    except PermissionError:
        pass
    else:
        raise AssertionError("non-admin backup access was accepted")


def test_backup_list_and_download_are_scoped_to_active_product(monkeypatch, tmp_path):
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    database_path = tenant_root / "tenant-a.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute("CREATE TABLE sample (value TEXT)")
    _set_tenant_context(monkeypatch, tenant_root, database_path)

    def registry():
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE support_backups (id INTEGER, original_name TEXT, size_bytes INTEGER, "
            "source TEXT, created_at TEXT, product_code TEXT, hardware_id TEXT, "
            "installation_id TEXT, sha256 TEXT, tenant_id TEXT, status TEXT)"
        )
        conn.execute(
            "INSERT INTO support_backups VALUES (7,'tenant-a.db',512,'web','2026-10-13',"
            "'teknik_servis','web-runtime','web-app','digest','tenant-a','available')"
        )
        conn.execute(
            "INSERT INTO support_backups VALUES (8,'other.db',64,'web','2026-10-13',"
            "'other-product','web-runtime','web-app','other','tenant-a','available')"
        )
        conn.commit()
        return conn

    monkeypatch.setattr(web_main, "registry_connect", registry)
    download_args = []
    monkeypatch.setattr(
        web_main,
        "support_backup_file",
        lambda user, backup_id, product, hardware, installation: (
            download_args.append((backup_id, product, hardware, installation)) or b"sqlite-bytes",
            "digest",
            "tenant-a.db",
        ),
    )
    actor = {"id": 4, "role": "admin", "_tenant_id": "tenant-a"}

    backups = web_main.desktop_list_backups(actor)
    payload, digest, filename = web_main.desktop_download_backup(actor, 7)

    assert [item["id"] for item in backups] == [7]
    assert download_args == [(7, "teknik_servis", "web-runtime", "web-app")]
    assert (payload, digest, filename) == (b"sqlite-bytes", "digest", "tenant-a.db")


def test_web_backup_page_uses_central_archive_create_and_download_routes():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    web_root = Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web"
    reference = (web_root / "backup-reference.js").read_text(encoding="utf-8")
    html = (web_root / "index.html").read_text(encoding="utf-8")

    assert 'apiFetch("/api/desktop/backups")' in app
    assert 'apiFetch("/api/desktop/backups",{method:"POST"' in app
    assert '/api/desktop/backups/${encodeURIComponent(id)}/download' in app
    assert "Sunucu Yedek Ar\\u015fivi" in app
    assert "Bu web oturumunda listelenebilir bir sunucu arşivi bulunmuyor." not in app
    assert 'backup-reference.js?v=' in html
    assert 'apiFetch("/api/desktop/backups")' in reference
    assert 'apiFetch("/api/desktop/backups", { method: "POST", body: "{}" })' in reference
    assert '"/api/desktop/backups/" + encodeURIComponent(id) + "/download"' in reference
    assert 'data-backup-create' in reference
    assert 'data-backup-stage' in reference
    assert '"/api/desktop/backups/import"' in reference
    assert 'if (dailyTime) dailyTime.disabled = !dailyEnabled || !dailyEnabled.checked;' in reference
    assert 'value: timezoneName' in reference
    assert '"backup_auto_morning"' not in app
    assert '"backup_auto_evening"' not in app


def test_tenant_backup_schedule_creates_one_daily_central_backup(monkeypatch, tmp_path):
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    database_path = tenant_root / "tenant-a.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, role TEXT, active INTEGER)")
        conn.executemany("INSERT INTO settings VALUES (?,?)", [
            ("backup_daily_enabled", "1"),
            ("backup_daily_time", "08:30"),
            ("backup_timezone", "America/New_York"),
        ])
        conn.execute("INSERT INTO users VALUES (4,'admin','Tenant Admin','Admin',1)")

    tenant = {"id": "tenant-a", "db_filename": database_path.name, "company_name": "Tenant A"}
    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    monkeypatch.setattr(web_main, "tenant_records", lambda: [tenant])
    monkeypatch.setattr(web_main, "_tenant_record_required", lambda tenant_id: tenant)
    monkeypatch.setattr(web_main, "configured_product_codes", lambda: {"teknik_servis"})
    backups = []

    def create(actor, source):
        backups.append((actor.copy(), source, web_main.active_tenant_id()))
        return {"backup_id": 31}

    monkeypatch.setattr(web_main, "desktop_create_backup", create)
    now = datetime(2026, 10, 13, 12, 45, tzinfo=timezone.utc)

    result = web_main.run_tenant_backup_schedule_once(now)
    repeated = web_main.run_tenant_backup_schedule_once(now)

    assert result == [{"tenant_id": "tenant-a", "backup_id": 31, "ok": True}]
    assert repeated == []
    assert len(backups) == 1
    assert backups[0][0]["id"] == 4
    assert backups[0][0]["_tenant_id"] == "tenant-a"
    assert backups[0][1:] == ("web-scheduler", "tenant-a")
    with sqlite3.connect(database_path) as conn:
        assert conn.execute(
            "SELECT value FROM settings WHERE key='backup_last_run_morning'"
        ).fetchone()[0] == "2026-10-13"


def test_tenant_backup_schedule_skips_disabled_invalid_and_future_preferences(monkeypatch, tmp_path):
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    tenants = []
    for tenant_id, enabled, backup_time in (
        ("disabled", "0", "08:00"),
        ("invalid", "1", "29:70"),
        ("future", "1", "09:00"),
    ):
        filename = tenant_id + ".db"
        with sqlite3.connect(tenant_root / filename) as conn:
            conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
            conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, full_name TEXT, role TEXT, active INTEGER)")
            conn.executemany("INSERT INTO settings VALUES (?,?)", [
                ("backup_daily_enabled", enabled), ("backup_daily_time", backup_time),
            ])
            conn.execute("INSERT INTO users VALUES (1,'admin','Tenant Admin','Admin',1)")
        tenants.append({"id": tenant_id, "db_filename": filename, "company_name": tenant_id})

    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    monkeypatch.setattr(web_main, "tenant_records", lambda: tenants)
    monkeypatch.setattr(web_main, "desktop_create_backup", lambda *args, **kwargs: pytest.fail("unexpected backup"))

    assert web_main.run_tenant_backup_schedule_once(datetime(2026, 10, 13, 8, 45)) == []


def test_web_logout_backup_follows_tenant_preference(monkeypatch, tmp_path):
    database_path = tmp_path / "tenant.db"
    with sqlite3.connect(database_path) as conn:
        conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        conn.execute("INSERT INTO settings VALUES ('backup_on_exit','1')")
    monkeypatch.setattr(web_main, "db_connect", lambda: sqlite3.connect(database_path))
    created = []
    monkeypatch.setattr(
        web_main,
        "desktop_create_backup",
        lambda user, source: created.append((user["id"], source)) or {"backup_id": 55},
    )
    admin = {"id": 8, "role": "Admin", "_tenant_id": "tenant-a"}

    assert web_main.desktop_create_logout_backup(admin) == {"backup_id": 55}
    assert created == [(8, "web-logout")]
    assert web_main.desktop_create_logout_backup({"id": 9, "role": "User"}) is None

    with sqlite3.connect(database_path) as conn:
        conn.execute("UPDATE settings SET value='0' WHERE key='backup_on_exit'")
    assert web_main.desktop_create_logout_backup(admin) is None
    with sqlite3.connect(database_path) as conn:
        conn.execute("DELETE FROM settings WHERE key='backup_on_exit'")
    assert web_main.desktop_create_logout_backup(admin) == {"backup_id": 55}
    assert created[-1] == (8, "web-logout")


def test_logout_route_returns_on_exit_backup_without_skipping_logout(monkeypatch):
    monkeypatch.setattr(web_main, "desktop_create_logout_backup", lambda user: {"backup_id": 55})
    monkeypatch.setattr(web_main, "delete_session", lambda token: None)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/auth/logout"
    handler.headers = {}
    handler.current_user = lambda: {"id": 8, "role": "Admin"}
    handler.session_token = lambda: "tenant-a.token"
    handler.session_cookie_header = lambda token: "ayec_session=; Max-Age=0"
    responses = []
    handler.send_json = lambda payload, status=200, headers=None: responses.append((payload, status, headers))

    handler.do_POST()

    assert responses[0][0] == {"ok": True, "backup": {"backup_id": 55}}
    assert responses[0][1] == 200
    assert "Set-Cookie" in responses[0][2]
