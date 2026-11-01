import io
import sqlite3
import threading
from http.server import ThreadingHTTPServer

from openpyxl import load_workbook
import requests
import pytest

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_bank_transaction_export_is_scoped_to_tenant_and_account(monkeypatch, tmp_path):
    actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    conn = sqlite3.connect(tenant_path)
    conn.execute(
        "INSERT INTO bank_accounts(id,bank_name,account_holder,currency) VALUES(?,?,?,?)",
        (71, "QA Bank", "Operating", "TRY"),
    )
    conn.execute(
        "INSERT INTO bank_accounts(id,bank_name,account_holder,currency) VALUES(?,?,?,?)",
        (72, "Other Bank", "Other", "TRY"),
    )
    conn.execute(
        "INSERT INTO accounting(type,category,amount,description,date,created_at,payment_method,bank_account_id,customer_name) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        ("Gelir", "Sales", 125.5, "QA bank receipt", "2026-10-21", "2026-10-21 09:30:00", "Havale", 71, "QA Customer"),
    )
    conn.execute(
        "INSERT INTO accounting(type,category,amount,description,date,bank_account_id) VALUES(?,?,?,?,?,?)",
        ("Gider", "Other", 50, "Other account expense", "2026-10-20", 72),
    )
    conn.commit()
    conn.close()

    web_main.set_tenant_context({"id": "tenant-1", "company_name": "Test Company", "db_filename": "Test Company.db"})
    try:
        payload = web_main.desktop_bank_transactions_workbook(
            actor,
            71,
            {
                "search": "QA bank",
                "type": "Gelir",
                "filter_date": True,
                "date_from": "2026-10-21",
                "date_to": "2026-10-21",
                "minimum": "100",
                "maximum": "200",
            },
        )
        workbook = load_workbook(filename=io.BytesIO(payload), read_only=True)
        rows = list(workbook.active.values)
        assert rows[0] == ("Tarih", "Saat", "Ref", "T\u00fcr", "A\u00e7\u0131klama", "Tutar", "Y\u00f6ntem", "G\u00f6nderen/Alan")
        assert len(rows) == 2
        assert rows[1][0:2] == ("2026-10-21", "09:30")
        assert rows[1][4:8] == ("QA bank receipt", 125.5, "Havale", "QA Customer")
        with pytest.raises(ValueError, match="date range"):
            web_main.desktop_bank_transactions_workbook(actor, 71, {"filter_date": True, "date_from": "2026-99-99", "date_to": "2026-10-21"})
    finally:
        web_main.clear_tenant_context()


def test_bank_transaction_export_endpoints_require_auth_and_return_files(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    conn = sqlite3.connect(tenant_path)
    conn.execute(
        "INSERT INTO bank_accounts(id,bank_name,account_holder,currency) VALUES(?,?,?,?)",
        (81, "QA Export Bank", "QA Finance", "TRY"),
    )
    conn.execute(
        "INSERT INTO accounting(type,category,amount,description,date,created_at,bank_account_id) "
        "VALUES(?,?,?,?,?,?,?)",
        ("Gelir", "Sales", 90, "Endpoint export row", "2026-10-21", "2026-10-21 10:15:00", 81),
    )
    conn.commit()
    conn.close()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = "http://127.0.0.1:{}".format(server.server_address[1])
    try:
        endpoint = base_url + "/api/desktop/bank-accounts/81/transactions/export/{}"
        anonymous = requests.Session()
        anonymous.headers["Origin"] = base_url
        assert anonymous.post(endpoint.format("xlsx"), json={}).status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            base_url + "/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200

        workbook_response = session.post(
            endpoint.format("xlsx"),
            json={"search": "Endpoint export", "type": "Gelir", "filter_date": True, "date_from": "2026-10-21", "date_to": "2026-10-21"},
        )
        assert workbook_response.status_code == 200
        workbook = load_workbook(filename=io.BytesIO(workbook_response.content), read_only=True)
        assert list(workbook.active.values)[1][4:6] == ("Endpoint export row", 90)
        pdf_response = session.post(endpoint.format("pdf"), json={})
        assert pdf_response.status_code == 200
        assert pdf_response.headers["Content-Type"] == "application/pdf"
        assert pdf_response.content.startswith(b"%PDF-")
        invalid_filter = session.post(
            endpoint.format("xlsx"),
            json={"filter_date": True, "date_from": "2026-99-99", "date_to": "2026-10-21"},
        )
        assert invalid_filter.status_code == 400
        assert session.post(endpoint.format("xlsx").replace("/81/", "/999/"), json={}).status_code == 404
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
