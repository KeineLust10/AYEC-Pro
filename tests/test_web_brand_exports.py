import io
import sqlite3

import openpyxl
from pypdf import PdfReader
import pytest

from Web_Arayuzu import Main as web_main


def _brand_database(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE device_brands(device_type TEXT, brand TEXT, is_active INTEGER, is_deleted INTEGER DEFAULT 0);"
        "CREATE TABLE devices(device_type TEXT, device_brand TEXT, is_deleted INTEGER DEFAULT 0);"
        "INSERT INTO device_brands VALUES('Phone','Acme',1,0);"
        "INSERT INTO device_brands VALUES('Phone','Dormant',0,0);"
        "INSERT INTO device_brands VALUES('Laptop','Acme',1,0);"
        "INSERT INTO devices VALUES('Phone','Acme',0);"
        "INSERT INTO devices VALUES('Phone','Acme',1);"
        "INSERT INTO devices VALUES('Laptop','Acme',0);"
    )
    conn.commit()
    return conn


def test_brand_workbook_respects_desktop_search_group_status_and_service_counts(monkeypatch, tmp_path):
    path = tmp_path / "tenant.sqlite3"
    _brand_database(path).close()
    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    monkeypatch.setattr(web_main, "db_connect", connect)

    payload = web_main.device_brands_export_workbook("acme", "Phone", "active")
    sheet = openpyxl.load_workbook(io.BytesIO(payload), data_only=True).active

    assert [cell.value for cell in sheet[1]] == ["Cihaz Turu", "Marka", "Iliskili Servis Kayitlari", "Durum"]
    assert list(sheet.values)[1:] == [("Phone", "Acme", 1, "Aktif")]
    pdf_payload = web_main.desktop_stock_pdf(payload, "Marka Adlari Yonetimi", allow_empty_records=True)
    pdf_text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_payload)).pages)
    assert "Marka Adlari Yonetimi" in pdf_text and "Acme" in pdf_text

    inactive = web_main.device_brands_export_workbook("", "", "inactive")
    inactive_sheet = openpyxl.load_workbook(io.BytesIO(inactive), data_only=True).active
    assert list(inactive_sheet.values)[1:] == [("Phone", "Dormant", 0, "Pasif")]


def test_brand_export_routes_require_auth_and_return_pdf_and_xlsx(monkeypatch):
    workbook_payload = b"xlsx"
    monkeypatch.setattr(web_main, "device_brands_export_workbook", lambda search, group, status: workbook_payload)
    monkeypatch.setattr(web_main, "desktop_stock_pdf", lambda payload, title, allow_empty_records=False: b"%PDF-" + payload)
    for suffix, expected_type, expected_body in (
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", workbook_payload),
        ("pdf", "application/pdf", b"%PDF-xlsx"),
    ):
        handler = object.__new__(web_main.AYECRequestHandler)
        handler.path = f"/api/desktop/device-brands/export/{suffix}?q=Acme&group=Phone&status=active"
        handler.headers = {}
        handler.current_user = lambda: {"id": 7, "role": "User"}
        sent = []
        handler.send_bytes = lambda *args, **kwargs: sent.append((args, kwargs))
        handler.do_GET()
        assert sent[0][0][0] == expected_body
        assert sent[0][0][1] == expected_type

        anonymous = object.__new__(web_main.AYECRequestHandler)
        anonymous.path = handler.path
        anonymous.headers = {}
        anonymous.current_user = lambda: None
        errors = []
        anonymous.send_json = lambda payload, status=200: errors.append((payload, status))
        anonymous.do_GET()
        assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]
