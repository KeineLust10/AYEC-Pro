import sqlite3
import threading
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_monthly_job_report_returns_the_tenant_scoped_last_twelve_months(monkeypatch, tmp_path):
    _, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    today = date.today()
    current_start = date(today.year, today.month, 1)
    previous_month_end = current_start - timedelta(days=1)
    previous_month_start = date(previous_month_end.year, previous_month_end.month, 1)
    current_date = today.strftime("%Y-%m-%d")
    previous_date = previous_month_start.strftime("%Y-%m-%d")
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO devices(tracking_no,customer_name,status,entry_date,exit_date,delivered_at) VALUES(?,?,?,?,?,?)",
            ("SRV-NEW", "Monthly Fixture", "Bekliyor", current_date, None, None),
        )
        conn.execute(
            "INSERT INTO devices(tracking_no,customer_name,status,entry_date,exit_date,delivered_at) VALUES(?,?,?,?,?,?)",
            ("SRV-DONE", "Monthly Fixture", "Tamir Edildi", previous_date, current_date, current_date),
        )
        conn.execute(
            "INSERT INTO accounting(type,category,amount,date,description) VALUES(?,?,?,?,?)",
            ("Gelir", "Tahsilat", 40, current_date, "Current receipt"),
        )
        conn.execute(
            "INSERT INTO accounting(type,category,amount,date,description) VALUES(?,?,?,?,?)",
            ("Gelir", "Tahsilat", 20, current_date, "Second current receipt"),
        )
        conn.execute(
            "INSERT INTO accounting(type,category,amount,date,description) VALUES(?,?,?,?,?)",
            ("Gelir", "Tahsilat", 90, previous_date, "Previous receipt"),
        )
        conn.commit()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/job-reports/monthly"
    try:
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.get(endpoint).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        response = session.get(endpoint)
        assert response.status_code == 200
        payload = response.json()
        assert len(payload["months"]) == 12
        assert payload["current"] == payload["months"][0]
        assert payload["current"] == {
            "month": datetime(today.year, today.month, 1).strftime("%m.%Y"),
            "new_services": 1,
            "completed_services": 1,
            "paid_jobs": 2,
            "collection_total": 60.0,
        }
        assert payload["months"][1]["month"] == datetime(previous_month_start.year, previous_month_start.month, 1).strftime("%m.%Y")
        assert payload["months"][1]["collection_total"] == 90.0
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
