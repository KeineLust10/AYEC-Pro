import hashlib
import sqlite3
import threading
from http.server import ThreadingHTTPServer

import pytest
import requests

from Web_Arayuzu import Main as web_main
from src.services.fiscal_year_service import FiscalYearService
from tests.test_vendor_management_center import _setup_tenant


def _make_fiscal_database(path):
    with sqlite3.connect(path) as conn:
        conn.executescript(
            """
            CREATE TABLE internal_settings (key TEXT PRIMARY KEY, value TEXT);
            INSERT INTO internal_settings(key,value) VALUES ('fiscal_year_start','2020-01-01');
            CREATE TABLE accounting (
                id INTEGER PRIMARY KEY, date TEXT, type TEXT, category TEXT, amount REAL,
                currency TEXT, exchange_rate REAL, try_equivalent REAL, original_amount REAL,
                description TEXT, created_at TEXT, customer_id INTEGER, customer_name TEXT,
                bank_account_id INTEGER, selected_services TEXT
            );
            CREATE TABLE bank_accounts (
                id INTEGER PRIMARY KEY, current_balance REAL, bank_name TEXT,
                account_name TEXT, currency TEXT, is_deleted INTEGER DEFAULT 0
            );
            INSERT INTO bank_accounts(id,current_balance,bank_name,account_name,currency)
                VALUES (7,125.5,'Test Bank','Operating','TRY');
            CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
            INSERT INTO customers(id,name) VALUES (3,'Test Customer');
            CREATE TABLE customer_currency_balances (
                customer_id INTEGER, currency TEXT, balance REAL
            );
            INSERT INTO customer_currency_balances(customer_id,currency,balance)
                VALUES (3,'TRY',-42.25);
            """
        )


def _web_fiscal_service(path, archive_name="archive_2020.db"):
    adapter = web_main._FiscalDatabaseAdapter(path)
    host = type("FiscalHost", (), {"db": adapter})()
    service = FiscalYearService(host)
    service.archive_old_data = lambda _year: archive_name
    return service, adapter


def test_fiscal_rollover_requires_accountant_approval_before_opening_database(monkeypatch):
    def fail_if_opened(_user):
        pytest.fail("The tenant database must not open before approval")

    monkeypatch.setattr(web_main, "_fiscal_service_for_active_tenant", fail_if_opened)
    with pytest.raises(PermissionError, match="Accountant approval"):
        web_main.desktop_fiscal_rollover({"password": web_main.password_hash("secret")}, {})


def test_fiscal_rollover_verifies_current_user_password_before_opening_database(monkeypatch):
    def fail_if_opened(_user):
        pytest.fail("The tenant database must not open before password verification")

    monkeypatch.setattr(web_main, "_fiscal_service_for_active_tenant", fail_if_opened)
    user = {"password": web_main.password_hash("correct")}
    with pytest.raises(PermissionError, match="password is incorrect"):
        web_main.desktop_fiscal_rollover(
            user,
            {"accountant_approved": True, "password": "wrong"},
        )


def test_fiscal_rollover_archives_then_writes_selected_opening_entries(tmp_path, monkeypatch):
    path = tmp_path / "tenant.db"
    _make_fiscal_database(path)
    service, adapter = _web_fiscal_service(path)
    user = {
        "id": 4,
        "username": "accountant",
        "_tenant_id": "tenant-1",
        "password": web_main.password_hash("correct"),
    }
    monkeypatch.setattr(
        web_main,
        "_fiscal_service_for_active_tenant",
        lambda _user: (service, adapter, {}, "tenant-1"),
    )
    audit_events = []
    monkeypatch.setattr(
        web_main,
        "_support_audit",
        lambda _user, action, tenant_id, detail=None: audit_events.append(
            (action, tenant_id, detail or {})
        ),
    )

    result = web_main.desktop_fiscal_rollover(
        user,
        {
            "accountant_approved": True,
            "password": "correct",
            "selections": {"bank": True, "customer": False},
        },
    )

    assert result["ok"] is True
    assert result["archive_name"] == "archive_2020.db"
    assert result["opening_summary"]["count"] == 1
    assert result["opening_summary"]["selections"] == {"bank": True, "customer": False}
    adapter.close()
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT category, bank_account_id, amount FROM accounting"
        ).fetchall()
    assert rows == [("Banka Devir Bakiyesi", 7, 125.5)]
    assert audit_events[-1][0:2] == ("fiscal_year_rollover_completed", "tenant-1")
    adapter.close()


def test_web_fiscal_plan_reports_integrity_and_rollover_totals(tmp_path, monkeypatch):
    path = tmp_path / "tenant.db"
    _make_fiscal_database(path)
    service, adapter = _web_fiscal_service(path)
    user = {"_tenant_id": "tenant-1"}

    monkeypatch.setattr(
        web_main,
        "_fiscal_service_for_active_tenant",
        lambda _user: (service, adapter, {}, "tenant-1"),
    )
    plan = web_main.desktop_fiscal_rollover_plan(user)

    assert plan["integrity"] == "ok"
    assert plan["bank_count"] == 1
    assert plan["customer_count"] == 1
    assert plan["entry_count"] == 2
    assert plan["total_try"] == 167.75


def test_central_fiscal_snapshots_are_not_deduplicated_against_non_fiscal_backups(
    tmp_path, monkeypatch
):
    registry_path = tmp_path / "registry.db"
    with sqlite3.connect(registry_path) as conn:
        conn.execute(
            """CREATE TABLE support_backups (
                id INTEGER PRIMARY KEY, tenant_id TEXT, filename TEXT, original_name TEXT,
                sha256 TEXT, size_bytes INTEGER, source TEXT, created_at TEXT,
                created_by_user_id INTEGER, product_code TEXT, hardware_id TEXT,
                installation_id TEXT, status TEXT DEFAULT 'available', protected_until TEXT
            )"""
        )
    payload_path = tmp_path / "snapshot.db"
    with sqlite3.connect(payload_path) as conn:
        conn.execute("CREATE TABLE sample(value TEXT)")
        conn.execute("INSERT INTO sample(value) VALUES (?)", ("x" * 400,))
    payload = payload_path.read_bytes()

    monkeypatch.setattr(web_main, "SUPPORT_BACKUP_ROOT", tmp_path / "backups")
    monkeypatch.setattr(
        web_main,
        "registry_connect",
        lambda: sqlite3.connect(registry_path),
    )
    monkeypatch.setattr(web_main, "prune_support_backups", lambda _tenant_id: {})

    ordinary = web_main._store_support_backup_for_tenant(
        "tenant-1", 4, payload, "tenant.db", "web", "teknik_servis", "web-runtime", "web-app"
    )
    fiscal = web_main._store_support_backup_for_tenant(
        "tenant-1", 4, payload, "archive_2020.db", "fiscal-rollover",
        "teknik_servis", "web-runtime", "web-app", deduplicate=False
    )

    assert ordinary["backup_id"] != fiscal["backup_id"]
    with sqlite3.connect(registry_path) as conn:
        rows = conn.execute(
            "SELECT original_name,source FROM support_backups ORDER BY id"
        ).fetchall()
    assert rows == [("tenant.db", "web"), ("archive_2020.db", "fiscal-rollover")]


def test_legacy_fiscal_archives_are_imported_only_for_matching_company(tmp_path, monkeypatch):
    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute("INSERT INTO company_info(company_name) VALUES ('Test Company')")
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-1")
    with pytest.raises(PermissionError, match="administrator"):
        web_main.desktop_import_legacy_fiscal_archives(
            {"id": 1, "_tenant_id": "tenant-1", "role": "User"}
        )
    for year in (2020, 2021):
        archive_path = tenant_path.parent / f"archive_{year}.db"
        with sqlite3.connect(tenant_path) as source, sqlite3.connect(archive_path) as archive:
            source.backup(archive)
        if year == 2021:
            with sqlite3.connect(archive_path) as conn:
                conn.execute("UPDATE company_info SET company_name='Other Company'")

    monkeypatch.setattr(web_main, "prune_support_backups", lambda _tenant_id: {})
    result = web_main.desktop_import_legacy_fiscal_archives(actor)

    assert [item["filename"] for item in result["imported"]] == ["archive_2020.db"]
    assert [(item["filename"], item["reason"]) for item in result["skipped"]] == [
        ("archive_2021.db", "Archive belongs to a different company account")
    ]
    with web_main.registry_connect() as registry:
        rows = registry.execute(
            "SELECT original_name,source,protected_until FROM support_backups WHERE tenant_id=?",
            ("tenant-1",),
        ).fetchall()
    assert len(rows) == 1
    assert rows[0][0:2] == ("archive_2020.db", "fiscal-rollover")
    assert rows[0][2].startswith("9999-")


def test_http_legacy_fiscal_archive_import_is_authenticated_and_centralized(tmp_path, monkeypatch):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute("INSERT INTO company_info(company_name) VALUES ('Test Company')")
    archive_path = tenant_path.parent / "archive_2020.db"
    with sqlite3.connect(tenant_path) as source, sqlite3.connect(archive_path) as archive:
        source.backup(archive)

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
        assert login.json()["user"]["is_admin"] is True
        imported = session.post(f"{base_url}/api/desktop/fiscal/archives/import", json={})
        assert imported.status_code == 200, imported.text
        imported_backup = imported.json()["imported"]
        assert len(imported_backup) == 1
        assert imported_backup[0]["filename"] == "archive_2020.db"
        archives = session.get(f"{base_url}/api/desktop/fiscal/archives")
        assert archives.status_code == 200
        assert [item["filename"] for item in archives.json()["archives"]] == ["archive_2020.db"]
        with web_main.registry_connect() as registry:
            row = registry.execute(
                "SELECT source,protected_until FROM support_backups WHERE id=? AND tenant_id=?",
                (imported_backup[0]["backup_id"], "tenant-1"),
            ).fetchone()
        assert row[0] == "fiscal-rollover"
        assert row[1].startswith("9999-")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_fiscal_archive_read_only_view_is_scoped_to_active_tenant(tmp_path, monkeypatch):
    tenant_root = tmp_path / "backups" / "tenant-1"
    tenant_root.mkdir(parents=True)
    archive_path = tenant_root / "archive_2020.db"
    with sqlite3.connect(archive_path) as conn:
        conn.execute(
            "CREATE TABLE accounting (id INTEGER PRIMARY KEY,date TEXT,type TEXT,"
            "category TEXT,amount REAL,currency TEXT,description TEXT,is_deleted INTEGER)"
        )
        conn.execute(
            "INSERT INTO accounting VALUES (1,'2020-01-02','Gelir','Devir',25,'TRY','opening',0)"
        )
        conn.execute(
            "INSERT INTO accounting VALUES (2,'2020-01-03','Gider','Deleted',10,'TRY','deleted',1)"
        )
    archive_digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    registry_path = tmp_path / "registry.db"
    with sqlite3.connect(registry_path) as conn:
        conn.execute(
            "CREATE TABLE support_backups (id INTEGER,tenant_id TEXT,product_code TEXT,"
            "source TEXT,status TEXT,filename TEXT,original_name TEXT,sha256 TEXT,"
            "created_at TEXT,size_bytes INTEGER)"
        )
        conn.execute(
            "INSERT INTO support_backups VALUES "
            "(11,'tenant-1','teknik_servis','fiscal-rollover','available',"
            "'archive_2020.db','archive_2020.db','" + archive_digest + "','2026-01-01',100)"
        )
        conn.execute(
            "INSERT INTO support_backups VALUES "
            "(12,'tenant-1','teknik_servis','web','available',"
            "'other.db','other.db','digest2','2026-01-01',100)"
        )
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-1")
    monkeypatch.setattr(
        web_main, "_tenant_record_required", lambda _tenant_id: {"product_code": "teknik_servis"}
    )
    monkeypatch.setattr(web_main, "configured_product_codes", lambda: {"teknik_servis"})
    monkeypatch.setattr(web_main, "SUPPORT_BACKUP_ROOT", tmp_path / "backups")

    def registry_connect():
        conn = sqlite3.connect(registry_path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(web_main, "registry_connect", registry_connect)

    archives = web_main.desktop_fiscal_archive_list({"_tenant_id": "tenant-1"})
    result = web_main.desktop_fiscal_archive_finance({"_tenant_id": "tenant-1"}, 11)

    assert [item["id"] for item in archives] == [11]
    assert result["archive"]["filename"] == "archive_2020.db"
    assert result["rows"] == [
        {
            "id": 1,
            "date": "2020-01-02",
            "type": "Gelir",
            "category": "Devir",
            "amount": 25.0,
            "currency": "TRY",
            "description": "opening",
            "is_deleted": 0,
        }
    ]
    web_main.activate_fiscal_archive_context({"_tenant_id": "tenant-1"}, 11)
    assert web_main.active_db_path() == archive_path.resolve()
    with web_main.db_connect() as archive_conn:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            archive_conn.execute("UPDATE accounting SET amount=30 WHERE id=1")
    web_main.clear_tenant_context()

    with pytest.raises(PermissionError, match="active company"):
        web_main.desktop_fiscal_archive_finance({"_tenant_id": "tenant-2"}, 11)

    archive_path.write_bytes(archive_path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        web_main.desktop_fiscal_archive_finance({"_tenant_id": "tenant-1"}, 11)


def test_fiscal_snapshot_uses_active_tenant_path_and_central_protected_registry(
    tmp_path, monkeypatch
):
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    database_path = tenant_root / "tenant.db"
    _make_fiscal_database(database_path)
    support_root = tmp_path / "support-backups"
    registry_path = tmp_path / "registry.db"
    with sqlite3.connect(registry_path) as conn:
        conn.execute(
            """CREATE TABLE support_backups (
                id INTEGER PRIMARY KEY, tenant_id TEXT NOT NULL, filename TEXT NOT NULL,
                original_name TEXT, sha256 TEXT NOT NULL, size_bytes INTEGER,
                source TEXT, created_at TEXT, created_by_user_id INTEGER,
                product_code TEXT, hardware_id TEXT, installation_id TEXT,
                status TEXT DEFAULT 'available', protected_until TEXT
            )"""
        )
    monkeypatch.setattr(web_main, "TENANT_ROOT", tenant_root)
    monkeypatch.setattr(web_main, "SUPPORT_BACKUP_ROOT", support_root)
    monkeypatch.setattr(web_main, "active_tenant_id", lambda: "tenant-1")
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)
    monkeypatch.setattr(
        web_main,
        "_tenant_record_required",
        lambda _tenant_id: {"db_filename": "tenant.db", "product_code": "teknik_servis"},
    )
    monkeypatch.setattr(web_main, "configured_product_codes", lambda: {"teknik_servis"})
    monkeypatch.setattr(web_main, "registry_connect", lambda: sqlite3.connect(registry_path))
    monkeypatch.setattr(web_main, "prune_support_backups", lambda _tenant_id: {})
    audit_events = []
    monkeypatch.setattr(
        web_main,
        "_support_audit",
        lambda _user, action, tenant_id, detail=None: audit_events.append(
            (action, tenant_id, detail or {})
        ),
    )

    service, adapter, _tenant, tenant_id = web_main._fiscal_service_for_active_tenant(
        {"id": 9, "_tenant_id": "tenant-1"}
    )
    try:
        archive_name = service.archive_old_data(2020)
    finally:
        adapter.close()

    assert tenant_id == "tenant-1"
    assert archive_name == "archive_2020.db"
    with sqlite3.connect(registry_path) as conn:
        row = conn.execute(
            "SELECT original_name,source,protected_until,filename FROM support_backups"
        ).fetchone()
    assert row[:2] == ("archive_2020.db", "fiscal-rollover")
    assert row[2].startswith("9999-")
    with sqlite3.connect(support_root / "tenant-1" / row[3]) as conn:
        assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert audit_events[0][:2] == ("fiscal_archive_created", "tenant-1")


def test_http_archive_context_reads_snapshot_and_rejects_every_business_write(
    tmp_path, monkeypatch
):
    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        cursor = conn.execute("INSERT INTO customers(name) VALUES ('Live Customer')")
        customer_id = int(cursor.lastrowid)
    snapshot_path = tmp_path / "archive_snapshot.db"
    with sqlite3.connect(tenant_path) as source, sqlite3.connect(snapshot_path) as target:
        source.backup(target)
    with sqlite3.connect(snapshot_path) as conn:
        conn.execute("UPDATE customers SET name='Archived Customer' WHERE id=?", (customer_id,))
    stored = web_main._store_support_backup_for_tenant(
        "tenant-1",
        int(actor["id"]),
        snapshot_path.read_bytes(),
        "archive_2020.db",
        "fiscal-rollover",
        "teknik_servis",
        "web-runtime",
        "web-app",
        deduplicate=False,
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
            json={
                "identifier": "customer@example.com",
                "password": "oldpass123",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200

        live = session.get(f"{base_url}/api/desktop/table/customers?limit=20")
        archive_headers = {"X-AYEC-Fiscal-Archive": str(stored["backup_id"])}
        bootstrap = session.get(f"{base_url}/api/desktop/bootstrap", headers=archive_headers)
        assert bootstrap.status_code == 200
        assert [
            row["name"] for row in bootstrap.json()["customers"] if row["id"] == customer_id
        ] == ["Archived Customer"]
        archived = session.get(
            f"{base_url}/api/desktop/table/customers?limit=20", headers=archive_headers
        )
        assert archived.status_code == 200
        assert [row["name"] for row in live.json()["rows"] if row["id"] == customer_id] == ["Live Customer"]
        assert [row["name"] for row in archived.json()["rows"] if row["id"] == customer_id] == ["Archived Customer"]

        write = session.post(
            f"{base_url}/api/desktop/table/customers",
            headers=archive_headers,
            json={"name": "Forbidden Write", "_action": "insert"},
        )
        assert write.status_code == 403
        after_write = session.get(
            f"{base_url}/api/desktop/table/customers?limit=20", headers=archive_headers
        )
        assert after_write.status_code == 200
        assert all(row["name"] != "Forbidden Write" for row in after_write.json()["rows"])
        returned_live = session.get(f"{base_url}/api/desktop/table/customers?limit=20")
        assert [
            row["name"] for row in returned_live.json()["rows"] if row["id"] == customer_id
        ] == ["Live Customer"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
