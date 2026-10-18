import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_job_profitability_uses_tenant_ledger_and_rejects_missing_fx(monkeypatch, tmp_path):
    _, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO currency_transactions(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,description,tracking_no,created_at,current_balance) "
            "VALUES(NULL,'DEBIT',100,'TRY',1,100,'job charge','JOB-1','2026-06-10T12:00:00',0)"
        )
        conn.execute(
            "INSERT INTO accounting(type,category,amount,try_equivalent,currency,date,customer_id,description) VALUES(?,?,?,?,?,?,?,?)",
            ("Gelir", "Consulting", 50, 50, "TRY", "2026-06-12", None, "manual income"),
        )
        conn.execute(
            "INSERT INTO accounting(type,category,amount,try_equivalent,currency,date,customer_id,description) VALUES(?,?,?,?,?,?,?,?)",
            ("Gelir", "Tahsilat", 7, 7, "TRY", "2026-06-13", 1, "mirrored receipt"),
        )
        conn.execute(
            "INSERT INTO accounting(type,category,amount,try_equivalent,currency,date,customer_id,description) VALUES(?,?,?,?,?,?,?,?)",
            ("Gider", "Supplies", 30, 30, "TRY", "2026-06-14", None, "expense"),
        )
        conn.execute(
            "INSERT INTO accounting(type,category,amount,try_equivalent,currency,date,customer_id,description) VALUES(?,?,?,?,?,?,?,?)",
            ("Gelir", "Consulting", 900, 900, "TRY", "2026-07-01", None, "outside period"),
        )
        conn.commit()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/job-reports/profitability"
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
        response = session.get(endpoint, params={"period": "range", "start": "2026-06-01", "end": "2026-06-30"})
        assert response.status_code == 200
        assert response.json() == {
            "period": "2026-06-01 - 2026-06-30",
            "revenue": 150.0,
            "expenses": 30.0,
            "net": 120.0,
            "net_ratio": 80.0,
            "status": "Mevcut finans hesaplamas\u0131 kullan\u0131ld\u0131. Tahsilat / sat\u0131\u015f yans\u0131malar\u0131 \u00e7ift say\u0131lmaz; deftere yazma i\u015flemi yap\u0131lmad\u0131.",
        }
        annual = session.get(endpoint, params={"period": "year"})
        assert annual.status_code == 200
        assert annual.json()["period"] == "2026-01-01 - 2026-12-31"
        assert (annual.json()["revenue"], annual.json()["expenses"], annual.json()["net"]) == (1050.0, 30.0, 1020.0)
        fiscal = session.get(endpoint, params={"period": "fiscal"})
        assert fiscal.status_code == 200
        assert len(fiscal.json()["period"]) == 23
        assert session.get(endpoint, params={"period": "range", "start": "2026-07-01", "end": "2026-06-30"}).status_code == 400

        with sqlite3.connect(tenant_path) as conn:
            conn.execute(
                "INSERT INTO currency_transactions(customer_id,transaction_type,amount,currency,exchange_rate,try_equivalent,description,tracking_no,created_at,current_balance) "
                "VALUES(NULL,'DEBIT',5,'USD',0,NULL,'missing rate','JOB-FX','2026-06-15T12:00:00',0)"
            )
            conn.commit()
        missing_fx = session.get(endpoint, params={"period": "range", "start": "2026-06-01", "end": "2026-06-30"})
        assert missing_fx.status_code == 400
        assert "TRY equivalents" in missing_fx.json()["error"]
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
