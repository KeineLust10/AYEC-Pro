import base64
import sqlite3

import pytest

import Web_Arayuzu.Main as web_main


def configure_tenant(monkeypatch, tmp_path, tenant_id):
    database_path = tmp_path / f"{tenant_id}.db"
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE devices ("
        "id INTEGER PRIMARY KEY, tracking_no TEXT, customer_name TEXT, device_type TEXT, "
        "brand TEXT, model TEXT, serial_no TEXT, fault_description TEXT, repair_details TEXT, "
        "status TEXT, is_deleted INTEGER DEFAULT 0, updated_at TEXT)"
    )
    connection.execute(
        "INSERT INTO devices (id,tracking_no,customer_name,device_type,status) VALUES (1,?,?,?,?)",
        ("SRV-100", "Tenant Customer", "Laptop", "Bekliyor"),
    )
    connection.execute(
        "CREATE TABLE service_logs (id INTEGER PRIMARY KEY, device_tracking_no TEXT, "
        "log_type TEXT, message TEXT, created_at TEXT, user TEXT)"
    )
    connection.commit()
    connection.close()
    web_main._TENANT_LOCAL.db_path = database_path
    web_main._TENANT_LOCAL.tenant_id = tenant_id
    monkeypatch.setattr(web_main, "db_connect", lambda: web_main._raw_connect(database_path))
    return database_path


def test_mobile_service_update_and_detail_stay_in_authenticated_tenant(monkeypatch, tmp_path):
    configure_tenant(monkeypatch, tmp_path, "tenant-a")
    user = {"id": 7, "_tenant_id": "tenant-a", "username": "tech"}

    result = web_main.mobile_service_update(user, {
        "tracking_no": "SRV-100",
        "status": "active",
        "fault_description": "No power",
        "repair_details": "Replaced power board",
    })

    assert result["ok"] is True
    assert result["tenant_id"] == "tenant-a"
    detail = web_main.mobile_service_detail(user, "SRV-100")
    assert detail["device"]["status"] == "\u0130\u015flemde"
    assert detail["device"]["repair_details"] == "Replaced power board"
    assert detail["tenant_id"] == "tenant-a"
    connection = web_main._raw_connect(web_main.active_db_path())
    assert connection.execute("SELECT COUNT(*) FROM service_logs").fetchone()[0] == 1
    connection.close()

    with pytest.raises(PermissionError, match="Tenant session mismatch"):
        web_main.mobile_service_detail({"_tenant_id": "tenant-b"}, "SRV-100")


def test_mobile_evidence_is_tenant_scoped_and_idempotent(monkeypatch, tmp_path):
    database_path = configure_tenant(monkeypatch, tmp_path, "tenant-a")
    user = {"id": 7, "_tenant_id": "tenant-a", "username": "tech"}
    png = base64.b64encode(b"\x89PNG\r\n\x1a\nmobile-test-image").decode("ascii")
    payload = {
        "tracking_no": "SRV-100",
        "evidence_type": "signature",
        "client_id": "mobile-request-001",
        "image_base64": png,
    }

    first = web_main.mobile_service_add_evidence(user, payload)
    repeated = web_main.mobile_service_add_evidence(user, payload)
    assert first["id"] == repeated["id"]
    assert repeated["duplicate"] is True
    detail = web_main.mobile_service_detail(user, "SRV-100")
    assert len(detail["evidence"]) == 1
    assert detail["evidence"][0]["evidence_type"] == "signature"
    assert web_main.mobile_service_read_evidence(user, first["id"]) == (base64.b64decode(png), "image/png")

    web_main._TENANT_LOCAL.tenant_id = "tenant-b"
    tenant_b_path = tmp_path / "tenant-b.db"
    connection = sqlite3.connect(tenant_b_path)
    connection.execute("CREATE TABLE devices (id INTEGER PRIMARY KEY, tracking_no TEXT)")
    connection.commit()
    connection.close()
    web_main._TENANT_LOCAL.db_path = tenant_b_path
    monkeypatch.setattr(web_main, "db_connect", lambda: web_main._raw_connect(tenant_b_path))
    with pytest.raises(LookupError, match="Evidence was not found"):
        web_main.mobile_service_read_evidence({"id": 8, "_tenant_id": "tenant-b"}, first["id"])

    assert database_path.is_file()
