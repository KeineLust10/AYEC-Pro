import base64
import json
import os
import subprocess
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from urllib.request import Request

import pytest
import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


class FakeResponse:
    def __init__(self, payload=None):
        self.payload = payload or {"sid": "SM" + "a" * 32, "status": "queued"}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _service_database(path):
    conn = web_main._raw_connect(path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS devices (id INTEGER PRIMARY KEY,tracking_no TEXT,customer_name TEXT,customer_contact TEXT,is_deleted INTEGER DEFAULT 0,is_archived INTEGER DEFAULT 0)"
    )
    conn.execute(
        "INSERT INTO devices(tracking_no,customer_name,customer_contact) VALUES(?,?,?)",
        ("SRV-API-1", "Test Customer", "05321234567"),
    )
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?)",
        ("twilio_account_sid", "AC" + "b" * 32),
    )
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?)",
        ("twilio_auth_token", web_main.protect_sms_auth_token("test-token")),
    )
    conn.execute(
        "INSERT INTO settings(key,value) VALUES(?,?)",
        ("twilio_from_number", "+15551234567"),
    )
    conn.commit()
    conn.close()


def test_service_sms_uses_active_tenant_record_and_logs_provider_sid(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    _service_database(tenant_path)
    captured = {}

    def fake_urlopen(request, timeout):
        assert isinstance(request, Request)
        assert timeout == 20
        if request.data is None:
            captured["test_url"] = request.full_url
            captured["test_auth"] = request.get_header("Authorization")
            return FakeResponse({"friendly_name": "Demo AYEC"})
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["form"] = parse_qs(request.data.decode("ascii"))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(f"{base_url}/api/desktop/service-sms/status?tracking_no=SRV-API-1").status_code == 401
        assert anonymous.post(
            f"{base_url}/api/desktop/service-sms",
            json={"tracking_no": "SRV-API-1", "message": "No session"},
        ).status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        for key, value in (
            ("twilio_account_sid", "AC" + "b" * 32),
            ("twilio_auth_token", "test-token"),
            ("twilio_from_number", "+15551234567"),
        ):
            saved = session.post(f"{base_url}/api/desktop/table/settings", json={"key": key, "value": value})
            assert saved.status_code == 200
        settings_rows = session.get(f"{base_url}/api/desktop/table/settings?limit=500").json()["rows"]
        setting_values = {item["key"]: item["value"] for item in settings_rows}
        assert setting_values["twilio_account_sid"] == ""
        assert setting_values["twilio_auth_token"] == ""
        bootstrap = session.get(f"{base_url}/api/desktop/bootstrap").json()
        assert bootstrap["settings"]["twilio_account_sid"] == ""
        assert bootstrap["settings"]["twilio_auth_token"] == ""
        connection_test = session.post(f"{base_url}/api/desktop/service-sms/test", json={})
        assert connection_test.status_code == 200
        assert connection_test.json()["message"] == "Connected to Twilio account: Demo AYEC"
        assert captured["test_url"].endswith("/Accounts/" + "AC" + "b" * 32 + ".json")
        status = session.get(f"{base_url}/api/desktop/service-sms/status?tracking_no=SRV-API-1")
        assert status.status_code == 200
        assert status.json() == {
            "tracking_no": "SRV-API-1",
            "customer_name": "Test Customer",
            "phone": "05321234567",
            "configured": True,
        }
        response = session.post(
            f"{base_url}/api/desktop/service-sms",
            json={"tracking_no": "SRV-API-1", "message": "Repair completed"},
        )
        assert response.status_code == 200
        assert response.json()["message_id"] == "SM" + "a" * 32
        assert captured["url"].endswith("/Accounts/" + "AC" + "b" * 32 + "/Messages.json")
        assert captured["auth"] == "Basic " + base64.b64encode(("AC" + "b" * 32 + ":test-token").encode()).decode()
        assert captured["form"] == {"To": ["+905321234567"], "From": ["+15551234567"], "Body": ["Repair completed"]}
        with web_main._raw_connect(tenant_path) as conn:
            row = conn.execute("SELECT tracking_no,phone,message,twilio_sid FROM sms_log").fetchone()
            assert tuple(row) == ("SRV-API-1", "05321234567", "Repair completed", "SM" + "a" * 32)
            assert conn.execute("SELECT value FROM settings WHERE key='twilio_auth_token'").fetchone()[0].startswith("enc:v1:")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


@pytest.mark.parametrize("viewport_width", [1280, 390])
def test_authenticated_status_board_sms_action_sends_and_logs(monkeypatch, tmp_path, viewport_width):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    _service_database(tenant_path)
    with web_main._raw_connect(tenant_path) as conn:
        customer_ids = []
        for name, phone in (
            ("SMS Customer A", "05321234567"),
            ("SMS Customer B", "05329876543"),
            ("SMS Customer Without Phone", ""),
        ):
            cursor = conn.execute("INSERT INTO customers(name,phone) VALUES(?,?)", (name, phone))
            customer_ids.append(int(cursor.lastrowid))

    def fake_urlopen(request, timeout):
        assert timeout == 20
        if request.data is None:
            return FakeResponse({"friendly_name": "Demo AYEC"})
        return FakeResponse()

    send_service_sms = web_main.desktop_send_service_sms
    monkeypatch.setattr(
        web_main,
        "desktop_send_service_sms",
        lambda conn, payload, urlopen_fn=None, target_override=None: send_service_sms(
            conn,
            payload,
            urlopen_fn=urlopen_fn or fake_urlopen,
            target_override=target_override,
        ),
    )
    send_customer_sms = web_main.desktop_send_customer_sms
    monkeypatch.setattr(
        web_main,
        "desktop_send_customer_sms",
        lambda conn, payload: send_customer_sms(conn, payload, urlopen_fn=fake_urlopen),
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}/"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url.rstrip("/")
        login = session.post(
            f"{base_url.rstrip('/')}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200, login.text
        env = os.environ.copy()
        env["AYEC_SERVICE_SMS_SESSION_COOKIE"] = session.cookies.get("ayec_session", "")
        env["AYEC_CUSTOMER_SMS_IDS"] = json.dumps(customer_ids)
        env["AYEC_SMS_VIEWPORT_WIDTH"] = str(viewport_width)
        env["AYEC_SMS_VIEWPORT_HEIGHT"] = "844"
        audit = subprocess.run(
            ["node", "tools/quality/service_sms_dialog_offscreen.cjs", base_url],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        assert audit.returncode == 0, audit.stderr or audit.stdout
        result = json.loads(audit.stdout.strip().splitlines()[-1])
        assert result["page"] == "service-status"
        assert result["customer"] == "Test Customer"
        assert result["closed"] is True
        assert result["customerSmsPosts"] == 2
        assert result["viewportWidth"] == viewport_width
        assert result["dialogViewport"]["documentWidth"] <= viewport_width + 1
        assert result["browserExceptions"] == 0
        with web_main._raw_connect(tenant_path) as conn:
            rows = conn.execute(
                "SELECT tracking_no,phone,message,twilio_sid FROM sms_log ORDER BY id"
            ).fetchall()
        assert tuple(rows[0]) == ("SRV-API-1", "05321234567", "Authenticated browser SMS QA", "SM" + "a" * 32)
        assert [tuple(row) for row in rows[1:]] == [
            (f"customer:{customer_ids[1]}", "05329876543", "Bulk browser SMS QA 1", "SM" + "a" * 32),
            (f"customer:{customer_ids[0]}", "05321234567", "Bulk browser SMS QA 2", "SM" + "a" * 32),
        ]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_service_sms_rejects_invalid_phone_or_missing_configuration(tmp_path):
    path = tmp_path / "sms.db"
    conn = web_main._raw_connect(path)
    conn.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)")
    conn.execute("CREATE TABLE devices(tracking_no TEXT,customer_name TEXT,customer_contact TEXT,is_deleted INTEGER)")
    conn.execute("INSERT INTO devices VALUES('SRV-1','Customer','',0)")
    conn.commit()
    with pytest.raises(ValueError, match="not configured"):
        web_main.desktop_send_service_sms(conn, {"tracking_no": "SRV-1", "message": "Hello"})
    conn.execute("INSERT INTO settings VALUES('twilio_account_sid',?)", ("AC" + "b" * 32,))
    conn.execute("INSERT INTO settings VALUES('twilio_auth_token','plain-token')")
    conn.execute("INSERT INTO settings VALUES('twilio_from_number','+15551234567')")
    conn.commit()
    with pytest.raises(ValueError, match="phone number is invalid"):
        web_main.desktop_send_service_sms(conn, {"tracking_no": "SRV-1", "message": "Hello"})
    conn.execute("UPDATE devices SET customer_contact='05321234567'")
    with pytest.raises(ValueError, match="Enter an SMS message"):
        web_main.desktop_send_service_sms(conn, {"tracking_no": "SRV-1", "message": "   "})
    with pytest.raises(ValueError, match="1600 characters"):
        web_main.desktop_send_service_sms(conn, {"tracking_no": "SRV-1", "message": "x" * 1601})
    conn.close()


def test_service_sms_page_has_composer_and_encrypted_twilio_configuration():
    source = open("Web_Arayuzu/web/app.js", encoding="utf-8").read()
    assert 'data-status-sms' in source
    assert '/api/desktop/service-sms/status?tracking_no=' in source
    assert '/api/desktop/service-sms/test' in source
    assert 'data-twilio-sms-test' in source
    assert 'twilio_auth_token' in source
    assert 'statusSmsTemplate' in source
    assert 'statusSmsCount' in source


def test_customer_sms_uses_tenant_customer_record_and_logs_provider_sid(tmp_path):
    path = tmp_path / "customer-sms.db"
    conn = web_main._raw_connect(path)
    conn.execute("CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT)")
    conn.execute("CREATE TABLE customers(id INTEGER PRIMARY KEY,name TEXT,phone TEXT)")
    conn.execute("INSERT INTO customers VALUES(7,'Customer','05321234567')")
    conn.executemany("INSERT INTO settings VALUES(?,?)", [
        ("twilio_account_sid", "AC" + "c" * 32),
        ("twilio_auth_token", "plain-token"),
        ("twilio_from_number", "+15551234567"),
    ])
    conn.commit()

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"sid": "SM" + "d" * 32}).encode("utf-8")

    calls = []

    def fake_urlopen(request, timeout):
        calls.append((request, timeout))
        return Response()

    result = web_main.desktop_send_customer_sms(
        conn, {"customer_id": 7, "message": "Hello"}, urlopen_fn=fake_urlopen
    )
    assert result["message_id"] == "SM" + "d" * 32
    assert len(calls) == 1
    row = conn.execute("SELECT tracking_no,phone,message,twilio_sid FROM sms_log").fetchone()
    assert tuple(row) == ("customer:7", "05321234567", "Hello", "SM" + "d" * 32)
    conn.close()


def test_customer_sms_rejects_missing_customer_and_ui_is_manifest_wired(tmp_path):
    conn = web_main._raw_connect(tmp_path / "missing-customer.db")
    conn.execute("CREATE TABLE customers(id INTEGER PRIMARY KEY,name TEXT,phone TEXT)")
    with pytest.raises(LookupError, match="Customer not found"):
        web_main.desktop_customer_sms_target(conn, 123)
    conn.close()
    source = open("Web_Arayuzu/web/app.js", encoding="utf-8").read()
    assert "send_sms_dialog:()=>openCustomerSMSManifestDialog()" in source
    assert "/api/desktop/customer-sms" in source
    assert "customerSmsTemplate" in source


def test_web_sms_template_lists_load_all_tenant_templates():
    source = Path("Web_Arayuzu/web/app.js").read_text(encoding="utf-8")
    list_start = source.index("async function loadPart9SmsTemplateRows")
    list_end = source.index("\n", list_start)
    provider_start = source.index("async function loadPart9SmsProviderTemplates")
    provider_end = source.index("\n", provider_start)
    assert 'loadAllDesktopTableRows("whatsapp_templates")' in source[list_start:list_end]
    assert 'loadAllDesktopTableRows("whatsapp_templates")' in source[provider_start:provider_end]
