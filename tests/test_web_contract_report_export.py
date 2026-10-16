import csv
import io
import sqlite3
import threading
from datetime import date, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def create_contract_db(path):
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, is_deleted INTEGER DEFAULT 0);"
        "CREATE TABLE contracts (id INTEGER PRIMARY KEY, customer_id INTEGER, title TEXT, "
        "contract_type TEXT, start_date TEXT, end_date TEXT, status TEXT, price REAL, description TEXT);"
        "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);"
    )
    today = date.today()
    conn.executemany(
        "INSERT INTO customers(id,name,is_deleted) VALUES(?,?,0)",
        [(1, "Acme Servis"), (2, "Beta Servis"), (3, "Gamma Servis")],
    )
    conn.executemany(
        "INSERT INTO contracts VALUES(?,?,?,?,?,?,?,?,?)",
        [
            (11, 1, "Onsite", "Gold SLA", today.isoformat(), (today + timedelta(days=45)).isoformat(), "Aktif", 1234.5, "Sunucu bakimi"),
            (12, 2, "Renewal", "Gold SLA", today.isoformat(), (today + timedelta(days=10)).isoformat(), "Aktif", 2000, "Ag bakimi"),
            (13, 3, "Expired", "Silver", today.isoformat(), (today - timedelta(days=1)).isoformat(), "Aktif", 3000, "Arsiv"),
        ],
    )
    conn.executemany(
        "INSERT INTO settings(key,value) VALUES(?,?)",
        [("currency", "TRY"), ("currency_precision", "2")],
    )
    conn.commit()
    conn.close()


def read_report(payload):
    return list(csv.reader(io.StringIO(payload.decode("utf-8-sig")), delimiter=";"))


def test_contract_report_export_matches_desktop_columns_and_filter_scope(monkeypatch, tmp_path):
    database_path = tmp_path / "tenant.db"
    create_contract_db(database_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)
    user = {"id": 7, "_tenant_id": "tenant-a"}

    all_rows = read_report(web_main.desktop_contract_report_csv(user, {}))
    assert all_rows[0] == [
        "S\u00f6zle\u015fme No", "M\u00fc\u015fteri / Kurum", "SLA", "Ge\u00e7erlilik",
        "Kalan S\u00fcre", "Y\u0131ll\u0131k Hacim", "Cihaz / Park", "Periyodik", "Durum",
    ]
    assert len(all_rows) == 4
    onsite = next(row for row in all_rows[1:] if row[0].endswith("-011"))
    assert onsite == [
        "AGR-{}-011".format(date.today().year), "Acme Servis\nOnsite", "Gold SLA",
        "{}\n{}".format(date.today().isoformat(), (date.today() + timedelta(days=45)).isoformat()),
        "45 G\u00fcn Kald\u0131", "1,234.50 \u20ba", "Sunucu bakimi", "-", "Aktif",
    ]
    renewal_rows = read_report(web_main.desktop_contract_report_csv(user, {"status": "renewal"}))
    assert [row[1] for row in renewal_rows[1:]] == ["Beta Servis\nRenewal"]
    query_rows = read_report(web_main.desktop_contract_report_csv(user, {"search": "acme", "type": "Gold"}))
    assert [row[0] for row in query_rows[1:]] == ["AGR-{}-011".format(date.today().year)]
    assert [row[0] for row in read_report(web_main.desktop_contract_report_csv(user, {"status": "expired"}))[1:]] == ["AGR-{}-013".format(date.today().year)]


def test_contract_report_export_requires_company_session_and_valid_status(monkeypatch, tmp_path):
    database_path = tmp_path / "tenant.db"
    create_contract_db(database_path)
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)
    with pytest.raises(PermissionError):
        web_main.desktop_contract_report_csv(None, {})
    with pytest.raises(ValueError):
        web_main.desktop_contract_report_csv({"_tenant_id": "tenant-a"}, {"status": "unknown"})


def test_contract_report_endpoint_is_authenticated_and_uses_active_tenant(monkeypatch, tmp_path):
    _, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    today = date.today()
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS contracts (id INTEGER PRIMARY KEY, customer_id INTEGER, "
            "title TEXT, contract_type TEXT, start_date TEXT, end_date TEXT, status TEXT, price REAL, description TEXT)"
        )
        conn.executemany(
            "INSERT INTO contracts(customer_id,title,contract_type,start_date,end_date,status,price,description) "
            "VALUES(NULL,?,?,?,?,?,?,?)",
            [
                ("Tenant report {}".format(index), "Gold SLA", today.isoformat(), (today + timedelta(days=60 + index)).isoformat(), "Aktif", 50 + index, "Tenant-only row" if index == 0 else "Other row")
                for index in range(5)
            ],
        )
        conn.commit()
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/contracts/export.csv"
    try:
        assert requests.get(endpoint).status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        page = session.get(f"{base_url}/api/desktop/table/contracts", params={"limit": 2, "offset": 1})
        assert page.status_code == 200
        page_data = page.json()
        assert page_data["count"] == 5
        assert page_data["limit"] == 2
        assert page_data["offset"] == 1
        assert len(page_data["rows"]) == 2
        response = session.get(endpoint, params={"search": "Tenant-only", "type": "Gold"})
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("text/csv")
        report = read_report(response.content)
        assert report[0][0] == "S\u00f6zle\u015fme No"
        assert report[1][1] == "-\nTenant report 0"
        assert len(report) == 2
        invalid = session.get(endpoint, params={"status": "invalid"})
        assert invalid.status_code == 400
    finally:
        server.shutdown()
        server.server_close()
