import sqlite3
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_personnel_daily_wage_flow_updates_accounting_and_is_authenticated(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        web_main.desktop_personnel_daily_wages(conn, "2026", "2")
        conn.execute(
            "INSERT INTO personnel(name,role,active,employment_type,daily_wage) VALUES(?,?,?,?,?)",
            ("Daily Worker", "Technician", 1, "daily", 1250.0),
        )
        person_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO settings(key,value) VALUES(?,?)", ("admin_pass", web_main.password_hash("tenant-admin-pass")))
        conn.execute(
            "INSERT INTO users(username,password,email,phone,role,active) VALUES(?,?,?,?,?,1)",
            ("manager-test", web_main.password_hash("manager-pass-123"), "manager@example.test", "", "Manager"),
        )
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    path = f"{base_url}/api/desktop/personnel/daily-wages"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(f"{path}?year=2026&month=2").status_code == 401
        assert anonymous.post(path, json={}).status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        payload = {"personnel_id": person_id, "work_year": 2026, "work_month": 2, "work_days": 3.5, "note": "First pass"}
        manager = requests.Session()
        manager.headers["Origin"] = base_url
        manager_login = manager.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "manager@example.test", "password": "manager-pass-123", "tenant_id": "tenant-1"},
        )
        assert manager_login.status_code == 200
        assert manager.post(path, json=payload).status_code == 403
        saved = session.post(path, json=payload)
        assert saved.status_code == 201
        record_id = saved.json()["id"]
        assert saved.json()["total_amount"] == 4375.0
        assert saved.json()["payment_date"] == "2026-02-28"
        payload["work_days"] = 4
        payload["note"] = "Updated"
        updated = session.post(path, json=payload)
        assert updated.status_code == 201
        assert updated.json()["id"] == record_id
        listing = session.get(f"{path}?year=2026&month=2").json()
        assert len(listing["rows"]) == 1
        assert listing["rows"][0]["total_amount"] == 5000
        assert listing["rows"][0]["note"] == "Updated"
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM accounting WHERE category='Yevmiye'").fetchone()[0] == 1
            assert conn.execute("SELECT amount FROM accounting WHERE category='Yevmiye'").fetchone()[0] == 5000
        removed = session.post(f"{path}/delete", json={"id": record_id})
        assert removed.status_code == 200
        assert session.get(f"{path}?year=2026&month=2").json()["rows"] == []
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM accounting WHERE category='Yevmiye'").fetchone()[0] == 0
        assert session.post(path, json={**payload, "work_days": 31.1}).status_code == 400
        with sqlite3.connect(tenant_path) as conn:
            conn.execute("INSERT INTO accounting(date,type,category,description,amount) VALUES(?,?,?,?,?)", ("2026-02-28", "expense", "Yevmiye", "Linked wage", 5000))
            accounting_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            conn.execute("INSERT INTO personnel_daily_wages(personnel_id,work_year,work_month,work_days,daily_wage,total_amount,payment_date,accounting_id) VALUES(?,?,?,?,?,?,?,?)", (person_id, 2026, 2, 4, 1250, 5000, "2026-02-28", accounting_id))
        remove_path = f"{base_url}/api/desktop/personnel/delete"
        assert manager.post(remove_path, json={"id": person_id, "admin_password": "tenant-admin-pass"}).status_code == 403
        assert session.post(remove_path, json={"id": person_id, "admin_password": "wrong"}).status_code == 403
        removed_person = session.post(remove_path, json={"id": person_id, "admin_password": "tenant-admin-pass"})
        assert removed_person.status_code == 200
        with sqlite3.connect(tenant_path) as conn:
            assert conn.execute("SELECT COUNT(*) FROM personnel WHERE id=?", (person_id,)).fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM personnel_daily_wages WHERE personnel_id=?", (person_id,)).fetchone()[0] == 0
            assert conn.execute("SELECT COUNT(*) FROM accounting WHERE id=?", (accounting_id,)).fetchone()[0] == 0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
