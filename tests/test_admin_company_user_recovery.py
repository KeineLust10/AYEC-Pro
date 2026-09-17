import sqlite3

from Web_Arayuzu import Main as web_main


def _connect(path):
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def test_missing_company_users_restore_from_latest_pre_wipe_backup(
    tmp_path, monkeypatch
):
    registry_path = tmp_path / "registry.db"
    tenant_root = tmp_path / "tenants"
    backup_root = tmp_path / "support_backups"
    tenant_root.mkdir()
    tenant_id = "tenant-1"
    tenant_db = tenant_root / "tenant.db"
    backup_dir = backup_root / tenant_id
    backup_dir.mkdir(parents=True)
    backup_db = backup_dir / "pre-wipe.db"

    with _connect(registry_path) as registry:
        registry.executescript(
            """
            CREATE TABLE tenants (id TEXT PRIMARY KEY, db_filename TEXT);
            CREATE TABLE support_backups (
                id INTEGER PRIMARY KEY,
                tenant_id TEXT,
                filename TEXT,
                source TEXT,
                status TEXT,
                created_at TEXT
            );
            """
        )
        registry.execute(
            "INSERT INTO tenants(id,db_filename) VALUES (?,?)",
            (tenant_id, tenant_db.name),
        )
        registry.execute(
            "INSERT INTO support_backups VALUES (1,?,?,?,?,?)",
            (
                tenant_id,
                backup_db.name,
                "pre-wipe",
                "available",
                "2026-08-24T17:00:00",
            ),
        )
        registry.commit()

    schema = (
        "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT, "
        "email TEXT, role TEXT, full_name TEXT, active INTEGER)"
    )
    with _connect(tenant_db) as tenant:
        tenant.execute(schema)
        tenant.commit()
    with _connect(backup_db) as backup:
        backup.execute(schema)
        backup.execute(
            "INSERT INTO users VALUES (1,'owner','hash-value','owner@example.com',"
            "'Admin','Owner Name',1)"
        )
        backup.commit()

    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    monkeypatch.setattr(web_main, "SUPPORT_BACKUP_ROOT", backup_root)
    monkeypatch.setattr(web_main, "registry_connect", lambda: _connect(registry_path))
    monkeypatch.setattr(web_main, "_ensure_path_schema", lambda conn, path: None)
    monkeypatch.setattr(web_main, "_support_audit", lambda *args, **kwargs: None)

    result = web_main.admin_repair_company_users(tenant_id, {"id": 99})

    assert result["restored_users"] == 1
    with _connect(tenant_db) as tenant:
        restored = tenant.execute(
            "SELECT username,password,email FROM users"
        ).fetchone()
    assert tuple(restored) == ("owner", "hash-value", "owner@example.com")


def test_existing_company_users_are_not_overwritten(tmp_path, monkeypatch):
    registry_path = tmp_path / "registry.db"
    tenant_root = tmp_path / "tenants"
    backup_root = tmp_path / "support_backups"
    tenant_root.mkdir()
    backup_dir = backup_root / "tenant-1"
    backup_dir.mkdir(parents=True)
    tenant_db = tenant_root / "tenant.db"
    backup_db = backup_dir / "pre-wipe.db"

    with _connect(registry_path) as registry:
        registry.executescript(
            """
            CREATE TABLE tenants (id TEXT PRIMARY KEY, db_filename TEXT);
            CREATE TABLE support_backups (
                id INTEGER PRIMARY KEY, tenant_id TEXT, filename TEXT,
                source TEXT, status TEXT, created_at TEXT
            );
            INSERT INTO tenants VALUES ('tenant-1','tenant.db');
            INSERT INTO support_backups VALUES (
                1,'tenant-1','pre-wipe.db','pre-wipe','available','2026-08-24T17:00:00'
            );
            """
        )
    schema = "CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password TEXT)"
    with _connect(tenant_db) as tenant:
        tenant.execute(schema)
        tenant.execute("INSERT INTO users VALUES (1,'current','current-hash')")
        tenant.commit()
    with _connect(backup_db) as backup:
        backup.execute(schema)
        backup.execute("INSERT INTO users VALUES (1,'old','old-hash')")
        backup.commit()

    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    monkeypatch.setattr(web_main, "SUPPORT_BACKUP_ROOT", backup_root)
    monkeypatch.setattr(web_main, "registry_connect", lambda: _connect(registry_path))
    monkeypatch.setattr(web_main, "_ensure_path_schema", lambda conn, path: None)

    result = web_main.admin_repair_company_users("tenant-1", {"id": 99})

    assert result["already_present"] is True
    with _connect(tenant_db) as tenant:
        username = tenant.execute("SELECT username FROM users").fetchone()[0]
    assert username == "current"
