import sqlite3
import shutil
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_service_catalog_import_prevalidates_and_commits_atomically(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active,product_code) VALUES(?,?,?,?,1,?)",
            ("tenant-2", "Second Company", "Second Company.db", "2026-01-02T00:00:00", "teknik_servis"),
        )
    tenant_two_path = web_main.TENANT_ROOT / "Second Company.db"
    shutil.copy2(tenant_path, tenant_two_path)
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
        other_session = requests.Session()
        other_session.headers["Origin"] = base_url
        other_login = other_session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-2"},
        )
        assert other_login.status_code == 200

        imported = session.post(
            f"{base_url}/api/desktop/services/import",
            json={"rows": [
                {"name": "Notebook Repair", "price": 500, "currency": "TRY"},
                {"name": "Notebook Repair", "price": 20, "currency": "USD"},
            ]},
        )
        assert imported.status_code == 200
        assert imported.json()["inserted"] == 1
        assert imported.json()["updated"] == 1
        with sqlite3.connect(tenant_path) as conn:
            before = conn.execute("SELECT name,price,currency FROM services").fetchall()
            assert before == [("NOTEBOOK REPAIR", 20.0, "USD")]
        with sqlite3.connect(tenant_two_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM services WHERE name='NOTEBOOK REPAIR'").fetchone()[0] == 0

        invalid = session.post(
            f"{base_url}/api/desktop/services/import",
            json={"rows": [
                {"name": "Another Service", "price": 100, "currency": "TRY"},
                {"name": "Invalid Service", "price": "NaN", "currency": "TRY"},
            ]},
        )
        assert invalid.status_code == 400
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT name,price,currency FROM services").fetchall() == before
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_service_catalog_import_requires_authentication_and_same_origin(monkeypatch, tmp_path):
    _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        response = requests.post(f"{base_url}/api/desktop/services/import", json={"rows": [{"name": "Test"}]})
        assert response.status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        session.headers["Origin"] = "https://untrusted.example"
        rejected = session.post(f"{base_url}/api/desktop/services/import", json={"rows": [{"name": "Test"}]})
        assert rejected.status_code == 403
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_service_catalog_import_preview_mapping_is_confirmed_before_write():
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    start = source.index("async function openServiceImportPreview(")
    end = source.index("\nfunction openServiceDefinitionDialog(", start)
    importer = source[start:end]
    assert '"/api/desktop/smart-import"' in importer
    assert '"/api/desktop/services/import"' in importer
    assert '"Onayla ve Aktar"' in importer
    assert "result.suggested_mapping?.[parserKey]" in importer
    assert 'contenteditable="true"' in importer
    assert "data-service-import-row" in importer
    assert 'vehicle_plate:["vehicle_plate","plate","plaka","arac_plaka"]' in importer
    assert 'currentSector==="otomotiv"' in importer
    assert importer.index("openDialog(") < importer.index('apiFetch("/api/desktop/services/import"')
    assert "Number.isFinite(price)" in importer
