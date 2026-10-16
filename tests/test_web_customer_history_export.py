import io
from pathlib import Path

import openpyxl

from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_customer_history_export_matches_desktop_two_sheet_selection():
    app = (WEB / "customer-history-parity.js").read_text(encoding="utf-8")
    assert 'data-customer-history-select' in app
    assert 'customer/history/export/xlsx' in app
    assert 'item.no || ""' in app and 'item.category || ""' in app
    assert 'window.print()' in app

    payload = web_main.customer_history_workbook(
        "Example",
        [["SRV-1", "Device", "=1+1", "Done", "TRY 120", "2026-10-13"]],
        [["Sale", "@SUM(A1:A2)", "Income", "2026-10-13", "TRY 120"]],
    )
    workbook = openpyxl.load_workbook(io.BytesIO(payload), data_only=True)

    assert workbook.sheetnames == ["Servis Gecmisi", "Finansal Hareketler"]
    assert [cell.value for cell in workbook.worksheets[0][1]] == [
        "Takip No", "Cihaz", "Ariza", "Durum", "Ucret", "Tarih",
    ]
    assert [cell.value for cell in workbook.worksheets[0][2]] == [
        "SRV-1", "Device", "'=1+1", "Done", "TRY 120", "2026-10-13",
    ]
    assert [cell.value for cell in workbook.worksheets[1][1]] == [
        "Kategori", "Aciklama", "Islem Tipi", "Tarih", "Tutar",
    ]
    assert workbook.worksheets[1][2][1].value == "'@SUM(A1:A2)"


def test_customer_history_workbook_rejects_invalid_and_oversized_rows():
    try:
        web_main.customer_history_workbook("Example", [["short"]], [])
    except ValueError as error:
        assert str(error) == "Invalid export row"
    else:
        raise AssertionError("Invalid row was accepted")

    try:
        web_main.customer_history_workbook("Example", [[]] * 5001, [])
    except ValueError as error:
        assert str(error) == "Too many selected rows"
    else:
        raise AssertionError("Oversized export was accepted")


def test_customer_history_export_route_requires_authentication_and_returns_xlsx(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/customer/history/export/xlsx"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    handler.read_json = lambda: {
        "customer_name": "Example",
        "service_rows": [["SRV-1", "Device", "Fault", "Done", "TRY 1", "2026-10-13"]],
        "finance_rows": [],
    }
    sent = []
    handler.send_bytes = lambda *args, **kwargs: sent.append((args, kwargs))
    monkeypatch.setattr(web_main, "customer_history_workbook", lambda *args: b"xlsx")

    handler.do_POST()

    assert sent
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

    oversized = object.__new__(web_main.AYECRequestHandler)
    oversized.path = handler.path
    oversized.headers = {"Content-Length": str(4 * 1024 * 1024 + 1)}
    oversized.current_user = lambda: {"id": 7, "role": "User"}
    oversized.read_json = lambda: (_ for _ in ()).throw(AssertionError("Oversized body was read"))
    rejected = []
    oversized.send_json = lambda payload, status=200: rejected.append((payload, status))

    oversized.do_POST()

    assert rejected == [({"error": "Export payload is too large"}, 413)]
