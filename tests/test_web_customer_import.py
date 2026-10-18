import base64
import csv
import io
import sqlite3
import threading
from http.server import ThreadingHTTPServer

import requests
from openpyxl import Workbook

from tests.test_vendor_management_center import _setup_tenant
import Web_Arayuzu.Main as web_main


def test_customer_import_preview_supports_csv_and_xlsx_and_writes_to_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    endpoint = f"{base_url}/api/desktop/customers/import/preview"
    try:
        anonymous = requests.post(endpoint, json={"filename": "customers.csv", "data": ""})
        assert anonymous.status_code == 401

        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": web_main.VENDOR_EMAIL, "password": "operator-test-pass", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200

        csv_buffer = io.StringIO(newline="")
        writer = csv.writer(csv_buffer, delimiter=";")
        writer.writerow(["Musteri Adi", "Telefon", "E-posta", "Firma", "Adres", "Vergi No", "Sehir", "Tur", "Not"])
        writer.writerow(["Preview Buyer", "5551000", "buyer@example.test", "North Labs", "Main Street", "TX-17", "Ankara", "Kurumsal", "Lead"])
        csv_payload = base64.b64encode(csv_buffer.getvalue().encode("utf-8")).decode("ascii")
        preview = session.post(endpoint, json={"filename": "customers.csv", "data": csv_payload})
        assert preview.status_code == 200
        assert preview.json()["count"] == 1
        assert preview.json()["rows"][0] == {
            "name": "Preview Buyer", "phone": "5551000", "email": "buyer@example.test",
            "company_name": "North Labs", "address": "Main Street", "tax_no": "TX-17",
            "city": "Ankara", "type": "Kurumsal", "notes": "Lead",
        }

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Name", "Phone", "City"])
        sheet.append(["Workbook Buyer", "5552000", "Izmir"])
        excel_buffer = io.BytesIO()
        workbook.save(excel_buffer)
        excel_payload = base64.b64encode(excel_buffer.getvalue()).decode("ascii")
        excel_preview = session.post(endpoint, json={"filename": "customers.xlsx", "data": excel_payload})
        assert excel_preview.status_code == 200
        assert excel_preview.json()["rows"] == [{
            "name": "Workbook Buyer", "phone": "5552000", "email": "", "company_name": "",
            "address": "", "tax_no": "", "city": "Izmir", "type": "", "notes": "",
        }]

        inserted = session.post(f"{base_url}/api/desktop/table/customers", json=preview.json()["rows"][0])
        assert inserted.status_code in {200, 201}
        with sqlite3.connect(tenant_path) as conn:
            row = conn.execute("SELECT name,phone,email,company_name,city,type,notes FROM customers WHERE name=?", ("Preview Buyer",)).fetchone()
        assert row == ("Preview Buyer", "5551000", "buyer@example.test", "North Labs", "Ankara", "Kurumsal", "Lead")
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
