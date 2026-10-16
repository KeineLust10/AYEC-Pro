import io
import sqlite3

import openpyxl
from pypdf import PdfReader

from Web_Arayuzu import Main as web_main


def _group_database(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        "CREATE TABLE product_groups(name TEXT, is_active INTEGER);"
        "CREATE TABLE device_brands(id INTEGER, device_type TEXT, brand TEXT, is_active INTEGER);"
        "INSERT INTO product_groups VALUES('Laptop',1);"
        "INSERT INTO product_groups VALUES('Phone',0);"
        "INSERT INTO device_brands VALUES(1,'Laptop','Acme',1);"
        "INSERT INTO device_brands VALUES(2,'Laptop','Acme',1);"
        "INSERT INTO device_brands VALUES(3,'Laptop','Old Brand',0);"
    )
    conn.commit()
    return conn


def test_product_group_exports_match_desktop_filter_and_linked_brands(monkeypatch, tmp_path):
    path = tmp_path / "tenant.sqlite3"
    _group_database(path).close()

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(web_main, "db_connect", connect)
    payload = web_main.product_groups_export_workbook("Lap")
    sheet = openpyxl.load_workbook(io.BytesIO(payload), data_only=True).active
    assert [cell.value for cell in sheet[1]] == ["Urun Grubu", "Bagli Marka / Kategori", "Durum"]
    assert list(sheet.values)[1:] == [("Laptop", "Acme", "Aktif")]

    pdf_payload = web_main.desktop_stock_pdf(payload, "Urun Grubu Yonetimi", allow_empty_records=True)
    pdf_text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf_payload)).pages)
    assert "Urun Grubu Yonetimi" in pdf_text and "Acme" in pdf_text


def test_product_group_export_route_requires_auth_and_downloads_xlsx(monkeypatch):
    monkeypatch.setattr(web_main, "product_groups_export_workbook", lambda search: b"xlsx")
    monkeypatch.setattr(web_main, "desktop_stock_pdf", lambda payload, title, allow_empty_records=False: b"%PDF-" + payload)
    for extension, expected_type, expected_payload in (
        ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", b"xlsx"),
        ("pdf", "application/pdf", b"%PDF-xlsx"),
    ):
        handler = object.__new__(web_main.AYECRequestHandler)
        handler.path = f"/api/desktop/product-groups/export/{extension}?q=Lap"
        handler.headers = {}
        handler.current_user = lambda: {"id": 9, "role": "User"}
        sent = []
        handler.send_bytes = lambda *args, **kwargs: sent.append((args, kwargs))
        handler.do_GET()
        assert sent[0][0][0] == expected_payload
        assert sent[0][0][1] == expected_type

        anonymous = object.__new__(web_main.AYECRequestHandler)
        anonymous.path = handler.path
        anonymous.headers = {}
        anonymous.current_user = lambda: None
        errors = []
        anonymous.send_json = lambda payload, status=200: errors.append((payload, status))
        anonymous.do_GET()
        assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_product_group_export_toolbar_keeps_print_separate():
    root = __import__("pathlib").Path(__file__).resolve().parents[1]
    web = (root / "Web_Arayuzu" / "web" / "product-groups-export-parity.js").read_text(encoding="utf-8")
    assert "/api/desktop/product-groups/export/" in web
    assert '"#groupExport, #groupPdf"' in web
    assert 'button.id === "groupPdf" ? "pdf" : "xlsx"' in web
