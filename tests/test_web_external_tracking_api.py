from contextlib import closing
import base64
from http.server import ThreadingHTTPServer
import shutil
import sqlite3
import threading

import requests

import Web_Arayuzu.Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def test_external_tracking_http_crud_stays_within_authenticated_tenant(monkeypatch, tmp_path):
    _actor, tenant_one_path = _setup_tenant(monkeypatch, tmp_path)
    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active,product_code) "
            "VALUES(?,?,?,?,1,?)",
            ("tenant-2", "Second Company", "Second Company.db", "2026-01-02T00:00:00", "teknik_servis"),
        )
        registry.commit()
    tenant_two_path = web_main._tenant_path(web_main.tenant_by_id("tenant-2"))
    tenant_two_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tenant_one_path, tenant_two_path)
    with closing(sqlite3.connect(tenant_two_path)) as tenant:
        tenant.execute("UPDATE users SET email='operator2@example.com' WHERE id=2")
        tenant.commit()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    table_url = f"{base_url}/api/desktop/table/external_warranty_tracking?limit=500"
    try:
        anonymous = requests.get(table_url)
        assert anonymous.status_code == 401

        def login(identifier, tenant_id):
            session = requests.Session()
            session.headers["Origin"] = base_url
            response = session.post(
                f"{base_url}/api/auth/login",
                json={
                    "identifier": identifier,
                    "password": "operator-test-pass",
                    "tenant_id": tenant_id,
                },
            )
            assert response.status_code == 200, response.text
            return session

        tenant_one = login(web_main.VENDOR_EMAIL, "tenant-1")
        tenant_two = login("operator2@example.com", "tenant-2")
        assert tenant_one.get(table_url).json()["rows"] == []
        assert tenant_two.get(table_url).json()["rows"] == []

        first = tenant_one.post(
            table_url,
            json={
                "internal_tracking_no": "QA-EXT-T1",
                "customer_name": "Tenant One Customer",
                "product_name": "Laptop One",
                "external_service_name": "Repair One",
                "external_service_no": "EXT-T1",
                "sent_date": "2026-10-20",
                "status": "Onarimda",
                "notes": "Tenant one fixture",
            },
        )
        assert first.status_code == 200, first.text
        first_id = first.json()["id"]

        second = tenant_two.post(
            table_url,
            json={
                "internal_tracking_no": "QA-EXT-T2",
                "customer_name": "Tenant Two Customer",
                "product_name": "Laptop Two",
                "external_service_name": "Repair Two",
                "external_service_no": "EXT-T2",
                "sent_date": "2026-10-21",
                "status": "Servise Ulasti",
                "notes": "Tenant two fixture",
            },
        )
        assert second.status_code == 200, second.text
        second_id = second.json()["id"]

        rows_one = tenant_one.get(table_url).json()["rows"]
        rows_two = tenant_two.get(table_url).json()["rows"]
        assert [row["internal_tracking_no"] for row in rows_one] == ["QA-EXT-T1"]
        assert [row["internal_tracking_no"] for row in rows_two] == ["QA-EXT-T2"]

        updated = tenant_one.post(
            table_url,
            json={"_action": "update", "id": first_id, "customer_name": "Tenant One Updated"},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["action"] == "update"
        assert tenant_one.get(table_url).json()["rows"][0]["customer_name"] == "Tenant One Updated"
        assert tenant_two.get(table_url).json()["rows"][0]["customer_name"] == "Tenant Two Customer"

        deleted = tenant_one.post(table_url, json={"_action": "delete", "id": first_id})
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["action"] == "delete"
        assert tenant_one.get(table_url).json()["rows"] == []
        remaining_two = tenant_two.get(table_url).json()["rows"]
        assert len(remaining_two) == 1
        assert remaining_two[0]["id"] == second_id
        assert remaining_two[0]["internal_tracking_no"] == "QA-EXT-T2"

        import_url = f"{base_url}/api/desktop/external-tracking/import"
        csv_bytes = (
            b"Emanet No,customer,product,service,service_no,date,out cargo,notes\n"
            b"QA-EXT-IMPORT-1,Imported Customer,Imported Laptop,Repair Desk,IMPORT-1,2026-10-22,OUT-1,CSV fixture\n"
        )
        csv_data = base64.b64encode(csv_bytes).decode("ascii")
        assert requests.post(import_url, json={"filename": "QA_external.csv", "data": csv_data}).status_code == 401
        imported = tenant_one.post(
            import_url,
            json={"filename": "QA_external.csv", "data": csv_data},
        )
        assert imported.status_code == 200, imported.text
        assert imported.json() == {"success": 1, "failures": 0}
        imported_rows = tenant_one.get(table_url).json()["rows"]
        assert len(imported_rows) == 1
        assert imported_rows[0]["internal_tracking_no"] == "QA-EXT-IMPORT-1"
        assert imported_rows[0]["customer_name"] == "Imported Customer"
        assert imported_rows[0]["external_service_no"] == "IMPORT-1"
        assert tenant_two.get(table_url).json()["rows"] == remaining_two
        invalid = tenant_one.post(
            import_url,
            json={"filename": "QA_external.csv", "data": "not-base64"},
        )
        assert invalid.status_code == 400
        assert tenant_one.get(table_url).json()["rows"] == imported_rows
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_external_tracking_photos_round_trip_and_stay_within_authenticated_tenant(monkeypatch, tmp_path):
    _actor, tenant_one_path = _setup_tenant(monkeypatch, tmp_path)
    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active,product_code) "
            "VALUES(?,?,?,?,1,?)",
            ("tenant-2", "Second Company", "Second Company.db", "2026-01-02T00:00:00", "teknik_servis"),
        )
        registry.commit()
    tenant_two_path = web_main._tenant_path(web_main.tenant_by_id("tenant-2"))
    tenant_two_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tenant_one_path, tenant_two_path)
    with closing(sqlite3.connect(tenant_two_path)) as tenant:
        tenant.execute("UPDATE users SET email='operator2@example.com' WHERE id=2")
        tenant.commit()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    photos_url = f"{base_url}/api/desktop/external-tracking/photos"
    photo_query = {"tracking_no": "QA-PHOTO-T1"}
    image_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/f7sAAAAASUVORK5CYII="
    )
    try:
        assert requests.get(photos_url, params=photo_query).status_code == 401

        def login(identifier, tenant_id):
            session = requests.Session()
            session.headers["Origin"] = base_url
            response = session.post(
                f"{base_url}/api/auth/login",
                json={
                    "identifier": identifier,
                    "password": "operator-test-pass",
                    "tenant_id": tenant_id,
                },
            )
            assert response.status_code == 200, response.text
            return session

        tenant_one = login(web_main.VENDOR_EMAIL, "tenant-1")
        tenant_two = login("operator2@example.com", "tenant-2")
        uploaded = tenant_one.post(
            photos_url,
            json={"tracking_no": "QA-PHOTO-T1", "data": base64.b64encode(image_bytes).decode("ascii")},
        )
        assert uploaded.status_code == 201, uploaded.text
        photo_id = uploaded.json()["id"]
        first_rows = tenant_one.get(photos_url, params=photo_query).json()["rows"]
        assert len(first_rows) == 1
        assert first_rows[0]["id"] == photo_id
        assert first_rows[0]["available"] is True
        assert first_rows[0]["url"] == f"/api/desktop/external-tracking/photo/{photo_id}"
        assert tenant_one.get(f"{base_url}{first_rows[0]['url']}").content == image_bytes
        assert tenant_two.get(photos_url, params=photo_query).json()["rows"] == []
        assert tenant_two.get(f"{base_url}{first_rows[0]['url']}").status_code == 404

        cross_tenant_delete = tenant_two.post(photos_url, json={"_action": "delete", "id": photo_id})
        assert cross_tenant_delete.status_code == 404
        assert tenant_one.get(photos_url, params=photo_query).json()["rows"][0]["id"] == photo_id
        deleted = tenant_one.post(photos_url, json={"_action": "delete", "id": photo_id})
        assert deleted.status_code == 200, deleted.text
        assert tenant_one.get(photos_url, params=photo_query).json()["rows"] == []
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
