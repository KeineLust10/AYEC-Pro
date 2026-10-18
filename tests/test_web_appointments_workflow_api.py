import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_appointment_desktop_fields_and_installation_plan_persist_in_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    table_url = f"{base_url}/api/desktop/table/appointments"
    bootstrap_url = f"{base_url}/api/desktop/appointments/bootstrap"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.post(table_url, json={"description": "blocked"}).status_code == 401
        assert anonymous.post(bootstrap_url, json={}).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            assert "workflow" not in {row[1] for row in conn.execute("PRAGMA table_info(appointments)")}
        bootstrap = session.post(bootstrap_url, json={})
        assert bootstrap.status_code == 200, bootstrap.text
        with sqlite3.connect(tenant_path) as conn:
            assert {"workflow", "offer_id", "offer_no"} <= {
                row[1] for row in conn.execute("PRAGMA table_info(appointments)")
            }

        saved = session.post(
            table_url,
            json={
                "customer_id": 12,
                "customer_name": "Audit customer",
                "personnel_name": "Audit technician",
                "date": "2026-10-14",
                "time": "16:00",
                "description": "Verilen Teklif / Montaj - Notebook - Replace fan",
                "color": "#f43f5e",
                "status": "Bekliyor",
                "workflow": "teklif_montaj",
                "offer_id": 8,
                "offer_no": "Q-008",
            },
        )
        assert saved.status_code == 200, saved.text
        appointment_id = saved.json()["id"]

        prepared = session.post(
            f"{base_url}/api/desktop/appointments/montage-plan",
            json={"action": "prepare", "appointment_id": appointment_id},
        )
        assert prepared.status_code == 200, prepared.text
        changed = session.post(
            table_url,
            json={"id": appointment_id, "_action": "update", "personnel_name": "Second technician", "color": "#10b981"},
        )
        assert changed.status_code == 200, changed.text
        completed_at = "2026-10-14 16:30:00"
        completed = session.post(
            table_url,
            json={"id": appointment_id, "_action": "update", "status": "Tamamlandı", "completed_at": completed_at},
        )
        assert completed.status_code == 200, completed.text

        with sqlite3.connect(tenant_path) as conn:
            row = conn.execute(
                "SELECT personnel_name,color,workflow,offer_id,offer_no,description,status,completed_at FROM appointments WHERE id=?",
                (appointment_id,),
            ).fetchone()
            assert row == (
                "Second technician",
                "#10b981",
                "teklif_montaj",
                8,
                "Q-008",
                "Verilen Teklif / Montaj - Notebook - Replace fan",
                "Tamamlandı",
                completed_at,
            )
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_appointment_table_refresh_includes_plan_item_locations(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    table_url = f"{base_url}/api/desktop/table/appointments"
    bootstrap_url = f"{base_url}/api/desktop/appointments/bootstrap"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200, login.text
        bootstrap = session.post(bootstrap_url, json={})
        assert bootstrap.status_code == 200, bootstrap.text
        created = session.post(
            table_url,
            json={"customer_id": 12, "customer_name": "Audit customer", "date": "2026-10-14", "time": "14:00", "description": "Plan location", "status": "Bekliyor"},
        )
        assert created.status_code == 200, created.text
        appointment_id = created.json()["id"]
        with sqlite3.connect(tenant_path) as conn:
            conn.execute(
                "INSERT INTO appointment_plan_items(appointment_id,name,source_location_id,created_at,updated_at) VALUES(?,?,?,?,?)",
                (appointment_id, "Reserved part", 7, "2026-10-14 12:00:00", "2026-10-14 12:00:00"),
            )

        refreshed = session.get(table_url + "?limit=1000")
        assert refreshed.status_code == 200, refreshed.text
        row = next(item for item in refreshed.json()["rows"] if item["id"] == appointment_id)
        assert row["plan_items"] == [{"source_location_id": 7}]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
