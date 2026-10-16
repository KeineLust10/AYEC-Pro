import io
from pathlib import Path

import openpyxl
from pypdf import PdfReader

from Web_Arayuzu import Main as web_main
import src.database as database_module


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_customer_context_menu_matches_desktop_actions_and_routes():
    source = (WEB / "customer-context-parity.js").read_text(encoding="utf-8")
    for action in (
        "notes", "360", "edit", "service", "invoice", "payment", "whatsapp",
        "debt-reminder", "excel", "pdf", "print", "selected-excel", "delete",
    ):
        assert f'"{action}"' in source
    assert 'customer/open-debts?customer_id=${id}&currency=TRY' in source
    assert 'customers/export/xlsx' in source
    assert 'customers/export/pdf' in source
    assert 'if (action === "pdf") return exportCustomerPdf()' in source
    assert 'if (action === "print") return printCustomerList()' in source
    assert 'customer/delete' in source
    assert 'navigate("invoices")' in source


def test_customer_list_workbook_matches_desktop_export_and_escapes_formulas():
    payload = web_main.customer_list_workbook([
        [7, "=1+1", "Company", "555", "a@example.test", "Business", "@home"],
    ])
    workbook = openpyxl.load_workbook(io.BytesIO(payload), data_only=True)
    sheet = workbook.active

    assert sheet.title == "Sheet1"
    assert [cell.value for cell in sheet[1]] == [
        "M\u00fc\u015fteri No", "Ad Soyad", "Firma", "Telefon", "E-posta", "T\u00fcr", "Adres",
    ]
    assert [cell.value for cell in sheet[2]] == [
        7, "'=1+1", "Company", "555", "a@example.test", "Business", "'@home",
    ]


def test_customer_list_pdf_is_downloadable_and_keeps_turkish_text():
    payload = web_main.customer_list_pdf([
        [7, "\u0130pek Ada", "AYEC Servis", "555 0100", "a@example.test", "Kurumsal", "\u0130stanbul"],
    ])
    reader = PdfReader(io.BytesIO(payload))

    assert payload.startswith(b"%PDF-")
    assert "\u0130pek Ada" in reader.pages[0].extract_text()
    assert "\u0130stanbul" in reader.pages[0].extract_text()


def test_customer_list_pdf_route_requires_authentication_and_returns_pdf(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/customers/export/pdf"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    handler.read_json = lambda: {"rows": [[7, "Ada", "", "555", "a@example.test", "Person", ""]]}
    sent = []
    handler.send_bytes = lambda *args, **kwargs: sent.append((args, kwargs))
    monkeypatch.setattr(web_main, "customer_list_pdf", lambda rows: b"%PDF-test")

    handler.do_POST()

    assert sent[0][0][0] == b"%PDF-test"
    assert sent[0][0][1] == "application/pdf"

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = handler.path
    unauthenticated.headers = {"Content-Length": "2"}
    unauthenticated.current_user = lambda: None
    errors = []
    unauthenticated.send_json = lambda payload, status=200: errors.append((payload, status))

    unauthenticated.do_POST()

    assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_customer_list_export_route_requires_authentication_and_returns_xlsx(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/customers/export/xlsx"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    handler.read_json = lambda: {"rows": [[7, "Ada", "", "555", "a@example.test", "Person", ""]]}
    sent = []
    handler.send_bytes = lambda *args, **kwargs: sent.append((args, kwargs))
    monkeypatch.setattr(web_main, "customer_list_workbook", lambda rows: b"xlsx")

    handler.do_POST()

    assert sent[0][0][0] == b"xlsx"
    assert sent[0][0][1] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = handler.path
    unauthenticated.headers = {"Content-Length": "2"}
    unauthenticated.current_user = lambda: None
    errors = []
    unauthenticated.send_json = lambda payload, status=200: errors.append((payload, status))

    unauthenticated.do_POST()

    assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_customer_delete_route_uses_the_active_tenant_database(monkeypatch, tmp_path):
    calls = []

    class FakeDatabase:
        def __init__(self, path, init_mode):
            calls.append(("open", Path(path), init_mode))

        def delete_customer(self, customer_id):
            calls.append(("delete", customer_id))
            return True

        def close(self):
            calls.append(("close",))

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/customer/delete"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "User", "_tenant_id": "tenant-a"}
    handler.read_json = lambda: {"id": 17}
    responses = []
    handler.send_json = lambda payload, status=200: responses.append((payload, status))

    handler.do_POST()

    assert calls == [
        ("open", tmp_path / "tenant.db", "connection_only"),
        ("delete", 17),
        ("close",),
    ]
    assert responses == [({"ok": True, "id": 17, "action": "delete"}, 200)]


def test_customer_list_workbook_rejects_malformed_and_oversized_payloads():
    try:
        web_main.customer_list_workbook([["bad"]])
    except ValueError as error:
        assert str(error) == "Invalid customer export row"
    else:
        raise AssertionError("Malformed customer row was accepted")

    try:
        web_main.customer_list_workbook([[]] * 5001)
    except ValueError as error:
        assert str(error) == "Invalid customer export rows"
    else:
        raise AssertionError("Oversized customer export was accepted")
