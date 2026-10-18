import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_web_service_sms import _service_database
from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_service_tracking_qr_is_authenticated_and_tenant_scoped(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    _service_database(tenant_path)
    issued = {}
    issue_token = web_main.service_tracking_token

    def capture_tenant_scope(tracking_no, tenant_id=""):
        issued["tenant_id"] = tenant_id
        return issue_token(tracking_no, tenant_id=tenant_id)

    monkeypatch.setattr(web_main, "service_tracking_token", capture_tenant_scope)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(
            f"{base_url}/api/desktop/service-tracking/qr?tracking_no=SRV-API-1"
        ).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200

        response = session.get(
            f"{base_url}/api/desktop/service-tracking/qr?tracking_no=SRV-API-1"
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("image/svg+xml")
        assert "<svg" in response.text
        assert "SRV-API-1" not in response.text
        assert issued["tenant_id"] == "tenant-1"
        token = web_main.service_tracking_token("SRV-API-1")
        assert web_main.service_tracking_token_value(token) == "SRV-API-1"
        legacy_public = requests.get(f"{base_url}/api/public/service/{token}")
        assert legacy_public.status_code == 200
        assert legacy_public.json()["tracking_no"] == "SRV-API-1"

        missing = session.get(
            f"{base_url}/api/desktop/service-tracking/qr?tracking_no=OTHER-TENANT-ONLY"
        )
        assert missing.status_code == 404
        invalid = session.get(f"{base_url}/api/desktop/service-tracking/qr?tracking_no=")
        assert invalid.status_code == 400
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


def test_public_service_tracking_token_is_tenant_bound_and_redacts_contacts(monkeypatch, tmp_path):
    _actor, tenant_one_path = _setup_tenant(monkeypatch, tmp_path)
    _service_database(tenant_one_path)
    with web_main._raw_connect(tenant_one_path) as conn:
        conn.execute(
            "UPDATE devices SET customer_name=?,customer_contact=?,device_brand=?,device_model=?,status=? WHERE tracking_no=?",
            ("Tenant One Customer", "111111", "Tenant One", "Unit One", "Tamirde", "SRV-API-1"),
        )
        conn.commit()

    with web_main.registry_connect() as registry:
        registry.execute(
            "INSERT INTO tenants(id,company_name,db_filename,created_at,active) VALUES(?,?,?,?,1)",
            ("tenant-2", "Second Company", "Second Company.db", "2026-01-02T00:00:00"),
        )
        registry.commit()
    tenant_two_path = web_main.TENANT_ROOT / "Second Company.db"
    with web_main._raw_connect(tenant_two_path) as conn:
        web_main.ensure_operational_schema(conn)
        web_main.ensure_web_schema(conn)
        conn.execute(
            "INSERT INTO devices(tracking_no,customer_name,customer_contact,device_brand,device_model,status) VALUES(?,?,?,?,?,?)",
            ("SRV-API-1", "Tenant Two Customer", "222222", "Tenant Two", "Unit Two", "Teslim Edildi"),
        )
        conn.commit()

    token = web_main.service_tracking_token("SRV-API-1", tenant_id="tenant-1")
    assert web_main.service_tracking_token_scope(token) == ("tenant-1", "SRV-API-1")
    legacy_token = web_main.service_tracking_token("SRV-API-1")

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        api_response = requests.get(f"{base_url}/api/public/service/{token}")
        assert api_response.status_code == 200
        public_data = api_response.json()
        assert set(public_data) == {"tracking_no", "status", "device", "received_at", "delivery_status"}
        assert public_data["tracking_no"] == "SRV-API-1"
        assert public_data["status"] == "Tamirde"
        assert public_data["device"] == "Tenant One Unit One"
        html_response = requests.get(f"{base_url}/servis/takip/{token}")
        assert html_response.status_code == 200
        assert "Tenant One Unit One" in html_response.text
        assert "Tenant One Customer" not in html_response.text
        assert "111111" not in html_response.text
        assert "Tenant Two" not in html_response.text

        ambiguous = requests.get(f"{base_url}/api/public/service/{legacy_token}")
        assert ambiguous.status_code == 404
        with web_main._raw_connect(tenant_one_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM service_tracking_access WHERE tracking_no=?",
                ("SRV-API-1",),
            ).fetchone()[0] == 2
        with web_main._raw_connect(tenant_two_path) as conn:
            assert conn.execute(
                "SELECT COUNT(*) FROM service_tracking_access WHERE tracking_no=?",
                ("SRV-API-1",),
            ).fetchone()[0] == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
