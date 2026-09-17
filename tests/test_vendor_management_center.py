import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import Web_Arayuzu.Main as web_main
from src.utils.web_sync_client import apply_pending_restore


def _setup_tenant(monkeypatch, tmp_path):
    registry_path = tmp_path / "registry.db"
    tenant_root = tmp_path / "Kullanicilar"
    backup_root = tmp_path / "support_backups"
    monkeypatch.setattr(web_main, "DB_PATH", registry_path)
    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    monkeypatch.setattr(web_main, "SUPPORT_BACKUP_ROOT", backup_root)
    monkeypatch.setattr(web_main, "PROGRAM_BACKUP_ROOT", tmp_path / "programs")
    web_main._SCHEMA_READY_PATHS.clear()

    registry = web_main.registry_connect()
    registry.execute(
        "INSERT INTO tenants(id,company_name,db_filename,created_at,active) VALUES(?,?,?,?,1)",
        ("tenant-1", "Test Company", "Test Company.db", "2026-01-01T00:00:00"),
    )
    registry.commit()
    registry.close()

    tenant_path = tenant_root / "Test Company.db"
    tenant_root.mkdir(parents=True, exist_ok=True)
    tenant = sqlite3.connect(tenant_path)
    web_main.ensure_operational_schema(tenant)
    web_main.ensure_web_schema(tenant)
    tenant.execute(
        "INSERT INTO users(username,password,email,phone,role,active) VALUES(?,?,?,?,?,1)",
        ("customer-admin", web_main.password_hash("oldpass123"), "customer@example.com", "05340000000", "Admin"),
    )
    tenant.execute(
        "INSERT INTO users(username,password,email,phone,role,active) VALUES(?,?,?,?,?,1)",
        ("vendor-operator", web_main.password_hash("operator-test-pass"),
         web_main.VENDOR_EMAIL, "", "Admin"),
    )
    tenant.commit()
    tenant.close()

    registry = web_main.registry_connect()
    registry.execute(
        "INSERT INTO control_admins(tenant_id,user_id,created_at) VALUES(?,?,?)",
        ("tenant-1", 2, "2026-01-01T00:00:00"),
    )
    registry.commit()
    registry.close()
    return {"id": 2, "_tenant_id": "tenant-1", "role": "Admin"}, tenant_path


def test_vendor_reset_is_single_use_and_never_reads_password(monkeypatch, tmp_path):
    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    reset = web_main.control_create_reset_link(actor, {"tenant_id": "tenant-1", "user_id": 1})
    token = reset["reset_url"].split("reset=", 1)[1]

    assert web_main.complete_password_reset({"token": token, "password": "newpass1234"}) == {"ok": True}
    assert web_main.password_matches(
        "newpass1234",
        sqlite3.connect(tenant_path).execute("SELECT password FROM users WHERE id=1").fetchone()[0],
    )
    try:
        web_main.complete_password_reset({"token": token, "password": "another1234"})
    except ValueError as error:
        assert "expired" in str(error).lower() or "invalid" in str(error).lower()
    else:
        raise AssertionError("A reset token must not be reusable")


def test_admin_can_reset_tenant_user_password(monkeypatch, tmp_path):
    _, tenant_path = _setup_tenant(monkeypatch, tmp_path)

    result = web_main.admin_reset_user_password("tenant-1", 1, "temporary-pass-42")

    assert result == {"ok": True, "user_id": 1}
    with sqlite3.connect(tenant_path) as conn:
        stored_password = conn.execute(
            "SELECT password FROM users WHERE id=1"
        ).fetchone()[0]
    assert web_main.password_matches("temporary-pass-42", stored_password)
    assert stored_password != "temporary-pass-42"


def test_vendor_backup_catalog_and_restore_queue(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    source = tmp_path / "source.db"
    conn = sqlite3.connect(source)
    conn.execute("CREATE TABLE sample(value INTEGER)")
    conn.execute("INSERT INTO sample(value) VALUES(7)")
    conn.commit()
    conn.close()

    result = web_main.support_store_backup(actor, source.read_bytes(), "Firma.db")
    assert result["ok"] is True
    tenant_backup_dir = web_main.SUPPORT_BACKUP_ROOT / "tenant-1"
    assert tenant_backup_dir.is_dir()
    assert len(list(tenant_backup_dir.glob("*.db"))) == 1
    queued = web_main.control_queue_restore(
        actor,
        {"tenant_id": "tenant-1", "backup_id": result["backup_id"]},
    )
    assert queued["ok"] is True
    registry = web_main.registry_connect()
    row = registry.execute("SELECT command_type,status FROM desktop_commands WHERE id=?", (queued["command_id"],)).fetchone()
    registry.close()
    assert tuple(row) == ("restore_backup", "pending")


def test_support_backup_retention_protects_pending_restore(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    monkeypatch.setattr(web_main, "SUPPORT_BACKUP_KEEP", 3)
    stored = []
    payloads = []
    command_id = 0
    for value in range(5):
        source = tmp_path / f"source-{value}.db"
        with sqlite3.connect(source) as conn:
            conn.execute("CREATE TABLE sample(value INTEGER)")
            conn.execute("INSERT INTO sample(value) VALUES(?)", (value,))
        payload = source.read_bytes()
        payloads.append(payload)
        stored.append(web_main.support_store_backup(actor, payload, "Firma.db"))
        if value == 0:
            command_id = web_main.control_queue_restore(
                actor,
                {"tenant_id": "tenant-1", "backup_id": stored[0]["backup_id"]},
            )["command_id"]

    with web_main.registry_connect() as registry:
        available_ids = {
            row[0]
            for row in registry.execute(
                "SELECT id FROM support_backups WHERE tenant_id=?",
                ("tenant-1",),
            ).fetchall()
        }
    assert stored[0]["backup_id"] in available_ids
    assert len(available_ids) == 4
    assert len(list((web_main.SUPPORT_BACKUP_ROOT / "tenant-1").glob("*.db"))) == 4

    duplicate = web_main.support_store_backup(actor, payloads[-1], "Firma.db")
    assert duplicate["duplicate"] is True
    assert len(list((web_main.SUPPORT_BACKUP_ROOT / "tenant-1").glob("*.db"))) == 4

    with web_main.registry_connect() as registry:
        registry.execute(
            "UPDATE desktop_commands SET status='completed' WHERE id=?",
            (command_id,),
        )
        registry.commit()
    cleanup = web_main.control_prune_backups(actor, {"tenant_id": "tenant-1"})
    assert cleanup["removed_count"] == 1
    with web_main.registry_connect() as registry:
        remaining = registry.execute(
            "SELECT COUNT(*) FROM support_backups WHERE tenant_id=?",
            ("tenant-1",),
        ).fetchone()[0]
    assert remaining == 3
    assert len(list((web_main.SUPPORT_BACKUP_ROOT / "tenant-1").glob("*.db"))) == 3


def test_company_wipe_increments_sync_epoch_and_protects_backup(monkeypatch, tmp_path):
    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    actor["role"] = "Admin"
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO customers(name,phone,email) VALUES(?,?,?)",
            ("Reset Customer", "", ""),
        )
    web_main.set_tenant_context(
        {
            "id": "tenant-1",
            "company_name": "Test Company",
            "db_filename": "Test Company.db",
        }
    )
    try:
        result = web_main.wipe_user_data(
            actor,
            "operator-test-pass",
            "T\u00dcM VER\u0130LER\u0130 S\u0130L",
        )
        assert result["sync_epoch"] == 2
        assert result["backup_id"] > 0
        assert result["protected_until"]
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0
        with web_main.registry_connect() as registry:
            backup = registry.execute(
                "SELECT source,protected_until FROM support_backups WHERE id=?",
                (result["backup_id"],),
            ).fetchone()
            epoch = registry.execute(
                "SELECT sync_epoch FROM tenants WHERE id='tenant-1'"
            ).fetchone()[0]
        assert tuple(backup)[0] == "pre-wipe"
        assert tuple(backup)[1]
        assert epoch == 2
        with pytest.raises(ValueError, match="SYNC_RESET_REQUIRED"):
            web_main.validate_sync_epoch({"sync_epoch": 1})
    finally:
        web_main.clear_tenant_context()


def test_create_tenant_creates_a_company_named_database(monkeypatch, tmp_path):
    _setup_tenant(monkeypatch, tmp_path)

    tenant = web_main.create_tenant("North Star Service")

    assert tenant["db_filename"] == "North Star Service.db"
    assert (web_main.TENANT_ROOT / tenant["db_filename"]).is_file()


def test_pending_restore_keeps_a_before_backup(monkeypatch, tmp_path):
    target = tmp_path / "ayecpro.db"
    staged = target.with_suffix(target.suffix + ".pending-restore")
    for path, value in ((target, 1), (staged, 2)):
        conn = sqlite3.connect(path)
        conn.execute("CREATE TABLE sample(value INTEGER)")
        conn.execute("INSERT INTO sample(value) VALUES(?)", (value,))
        conn.commit()
        conn.close()
    marker = target.with_suffix(target.suffix + ".pending-restore.json")
    marker.write_text(
        json.dumps(
            {
                "command_id": 4,
                "backup_id": 9,
                "sha256": hashlib.sha256(staged.read_bytes()).hexdigest(),
                "staged_path": str(staged),
            }
        ),
        encoding="utf-8",
    )

    result = apply_pending_restore(target)
    assert result["applied"] is True
    assert sqlite3.connect(target).execute("SELECT value FROM sample").fetchone()[0] == 2
    assert result["before_backup"]


def test_public_user_includes_menu_permissions(monkeypatch, tmp_path):
    _setup_tenant(monkeypatch, tmp_path)
    user = {
        "id": 1,
        "username": "customer-admin",
        "role": "User",
        "permissions": '{"pages":[40,50]}',
        "_tenant_id": "tenant-1",
    }

    assert web_main.public_user(user)["permissions"] == '{"pages":[40,50]}'


def test_vendor_owner_is_registered_in_each_matching_tenant(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    registry = web_main.registry_connect()
    registry.execute("DELETE FROM control_admins")
    registry.execute(
        "INSERT INTO tenants(id,company_name,db_filename,created_at,active) VALUES(?,?,?,?,1)",
        ("tenant-2", "Second Company", "Second Company.db", "2026-01-02T00:00:00"),
    )
    registry.commit()
    registry.close()

    for tenant_id, filename in (("tenant-1", "Test Company.db"), ("tenant-2", "Second Company.db")):
        path = web_main.TENANT_ROOT / filename
        conn = sqlite3.connect(path)
        web_main.ensure_operational_schema(conn)
        web_main.ensure_web_schema(conn)
        existing = conn.execute(
            "SELECT id FROM users WHERE lower(email)=?",
            (web_main.VENDOR_EMAIL,),
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO users(username,password,email,role,active) VALUES(?,?,?,?,1)",
                ("vendor-" + tenant_id, web_main.password_hash("vendor-pass"), web_main.VENDOR_EMAIL, "Admin"),
            )
        conn.commit()
        conn.close()

    web_main.ensure_control_owner()
    registry = web_main.registry_connect()
    rows = registry.execute(
        "SELECT tenant_id FROM control_admins ORDER BY tenant_id"
    ).fetchall()
    registry.close()

    assert [row[0] for row in rows] == ["tenant-1", "tenant-2"]


def test_vendor_account_authenticates_without_tenant_selection(monkeypatch, tmp_path):
    _, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute("DELETE FROM users WHERE email=?", (web_main.VENDOR_EMAIL,))
        cursor = conn.execute(
            "INSERT INTO users(username,password,email,role,active) VALUES(?,?,?,?,1)",
            (
                "vendor-owner",
                web_main.password_hash("vendor-secret-42"),
                web_main.VENDOR_EMAIL,
                "Admin",
            ),
        )
        vendor_user_id = cursor.lastrowid
        conn.commit()

    web_main.ensure_control_owner()
    authenticated = web_main.authenticate_account(
        web_main.VENDOR_EMAIL,
        "vendor-secret-42",
        None,
    )

    assert authenticated is not None
    assert authenticated["id"] == vendor_user_id
    assert authenticated["_tenant_id"] == "tenant-1"
    assert web_main.is_control_admin(authenticated) is True


def test_admin_remote_sql_is_read_only_and_bounded(monkeypatch, tmp_path):
    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)

    result = web_main.admin_execute_query(
        "tenant-1",
        "SELECT id, username FROM users ORDER BY id;",
        actor,
    )

    assert result["columns"] == ["id", "username"]
    assert result["rows"] == [(1, "customer-admin"), (2, "vendor-operator")]
    assert result["truncated"] is False

    with pytest.raises(PermissionError, match="yalnizca SELECT"):
        web_main.admin_execute_query(
            "tenant-1",
            "DELETE FROM users",
            actor,
        )
    with pytest.raises(PermissionError, match="yalnizca bir sorgu"):
        web_main.admin_execute_query(
            "tenant-1",
            "SELECT 1; DELETE FROM users;",
            actor,
        )
    with sqlite3.connect(tenant_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2


def test_admin_privileged_actions_are_audited(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)

    web_main.admin_reset_user_password(
        "tenant-1", 1, "temporary-pass-43", actor
    )
    web_main.admin_update_license(
        "tenant-1",
        {
            "license_type": "Premium",
            "license_start": "2026-08-17T12:00:00",
            "license_end": "2027-08-17T12:00:00",
        },
        actor,
    )
    web_main.admin_send_notification(
        {"target": "tenant-1", "title": "Test", "body": "Test body"},
        actor,
    )
    web_main.admin_deploy_update(
        {
            "version": "2.0.1",
            "targets": ["tenant-1"],
            "changelog": "Test release",
            "channel": "pilot",
        },
        actor,
    )
    with web_main.registry_connect() as registry:
        update_command = registry.execute(
            "SELECT command_type,status,payload_json FROM desktop_commands "
            "WHERE tenant_id=? AND command_type='deploy_update' ORDER BY id DESC LIMIT 1",
            ("tenant-1",),
        ).fetchone()
    assert update_command[0:2] == ("deploy_update", "pending")
    assert json.loads(update_command[2])["channel"] == "pilot"

    logs = web_main.admin_audit_logs("tenant-1", 20)
    actions = {item["action"] for item in logs}
    assert {
        "admin_password_reset",
        "admin_license_updated",
        "admin_notification_sent",
        "admin_update_deployed",
    }.issubset(actions)


def test_admin_backup_catalog_queues_support_restore(monkeypatch, tmp_path):
    actor, _ = _setup_tenant(monkeypatch, tmp_path)
    source = tmp_path / "customer-backup.db"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE sample(value INTEGER)")
        conn.execute("INSERT INTO sample(value) VALUES(9)")
    stored = web_main.support_store_backup(
        actor, source.read_bytes(), "Customer.db"
    )

    catalog = web_main.admin_list_backups("tenant-1")
    support_item = next(
        item for item in catalog if item.get("backup_id") == stored["backup_id"]
    )
    queued = web_main.admin_restore_backup(
        "tenant-1",
        support_item["index"],
        actor,
        support_item["backup_id"],
    )

    assert queued["ok"] is True
    with web_main.registry_connect() as registry:
        command = registry.execute(
            "SELECT command_type,status FROM desktop_commands WHERE id=?",
            (queued["command_id"],),
        ).fetchone()
    assert tuple(command) == ("restore_backup", "pending")

    current_queued = web_main.admin_restore_backup(
        "tenant-1", -1, actor
    )
    assert current_queued["ok"] is True


def test_admin_console_navigation_includes_operational_pages():
    main_source = (ROOT / "Admin_Konsol" / "main_window.py").read_text(
        encoding="utf-8"
    )
    api_source = (ROOT / "Admin_Konsol" / "api_client.py").read_text(
        encoding="utf-8"
    )

    for page_id in ("backups", "updates", "audit_logs"):
        assert f'("{page_id}"' in main_source
    assert 'def audit_logs(' in api_source
    assert 'def readonly_query(' in api_source

    sync_source = (ROOT / "src" / "utils" / "desktop_web_sync.py").read_text(
        encoding="utf-8"
    )
    window_source = (ROOT / "src" / "ui" / "main_window.py").read_text(
        encoding="utf-8"
    )
    assert 'command.get("command_type") == "deploy_update"' in sync_source
    assert 'self.update_manager.check_for_updates()' in window_source
