import json
import sqlite3
from pathlib import Path

from Web_Arayuzu import Main as web_main


def _invoice_db(path: Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE accounting (
            id INTEGER PRIMARY KEY, customer_id INTEGER, type TEXT, category TEXT,
            is_invoiced INTEGER, date TEXT, description TEXT, amount REAL,
            is_deleted INTEGER DEFAULT 0
        );
        CREATE TABLE currency_transactions (
            id INTEGER PRIMARY KEY, customer_id INTEGER, transaction_type TEXT,
            is_invoiced INTEGER, created_at TEXT, description TEXT, amount REAL,
            currency TEXT, try_equivalent REAL
        );
        INSERT INTO customers VALUES (1, 'Customer One');
        INSERT INTO customers VALUES (2, 'Customer Two');
        INSERT INTO accounting VALUES (11, 1, 'Gelir', 'Sat\u0131\u015f', 0, '2026-10-10', 'TRY sale', 100, 0);
        INSERT INTO accounting VALUES (12, 1, 'Gelir', 'Sat\u0131\u015f', 1, '2026-10-09', 'Already invoiced', 50, 0);
        INSERT INTO accounting VALUES (13, 1, 'Gelir', 'Sat\u0131\u015f', 0, '2026-10-08', 'Deleted sale', 40, 1);
        INSERT INTO accounting VALUES (14, 2, 'Gelir', 'Sat\u0131\u015f', 0, '2026-10-07', 'Other customer', 25, 0);
        INSERT INTO currency_transactions VALUES (21, 1, 'DEBIT', 0, '2026-10-06', 'USD sale', 2, 'USD', 80);
        INSERT INTO currency_transactions VALUES (22, 1, 'DEBIT', 1, '2026-10-05', 'Invoiced USD', 1, 'USD', 40);
        INSERT INTO currency_transactions VALUES (23, 2, 'DEBIT', 0, '2026-10-04', 'Other USD', 5, 'USD', 200);
        """
    )
    conn.commit()
    conn.close()


def test_service_invoice_query_is_customer_scoped_and_uses_try_equivalent(tmp_path):
    path = tmp_path / "tenant.db"
    _invoice_db(path)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        found = web_main.service_invoice_transactions(conn, 1)
    finally:
        conn.close()

    assert {(item["source"], item["id"]) for item in found} == {
        ("accounting", 11), ("currency", 21)
    }
    foreign = next(item for item in found if item["source"] == "currency")
    assert foreign["try_equivalent"] == 80
    assert foreign["date"] == "2026-10-06"


def test_service_invoice_marking_updates_only_selected_sources_and_customer(tmp_path, monkeypatch):
    path = tmp_path / "tenant.db"
    _invoice_db(path)

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(web_main, "db_connect", connect)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/service-invoices/1"
    handler.headers = {"X-AYEC-Fiscal-Archive": ""}
    handler.command = "POST"
    handler.current_user = lambda: {"id": 7, "role": "Admin", "_tenant_id": "tenant-a"}
    handler.read_json = lambda: {"transactions": [
        {"id": 11, "source": "accounting"},
        {"id": 21, "source": "currency"},
    ]}
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_POST()

    assert replies == [({"marked": 2}, 200)]
    conn = connect()
    try:
        assert conn.execute("SELECT is_invoiced FROM accounting WHERE id=11").fetchone()[0] == 1
        assert conn.execute("SELECT is_invoiced FROM currency_transactions WHERE id=21").fetchone()[0] == 1
        assert conn.execute("SELECT is_invoiced FROM accounting WHERE id=14").fetchone()[0] == 0
    finally:
        conn.close()


def test_service_invoice_api_rejects_stale_or_cross_customer_selection(tmp_path, monkeypatch):
    path = tmp_path / "tenant.db"
    _invoice_db(path)

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(web_main, "db_connect", connect)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/service-invoices/1"
    handler.headers = {"X-AYEC-Fiscal-Archive": ""}
    handler.command = "POST"
    handler.current_user = lambda: {"id": 7, "role": "Admin", "_tenant_id": "tenant-a"}
    handler.read_json = lambda: {"transactions": [{"id": 14, "source": "accounting"}]}
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_POST()

    assert replies == [({"error": "Some selected transactions are no longer available"}, 409)]
    conn = connect()
    try:
        assert conn.execute("SELECT is_invoiced FROM accounting WHERE id=14").fetchone()[0] == 0
    finally:
        conn.close()


def test_service_invoice_get_api_is_authenticated_and_tenant_scoped(tmp_path, monkeypatch):
    path = tmp_path / "tenant.db"
    _invoice_db(path)

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    monkeypatch.setattr(web_main, "db_connect", connect)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/service-invoices/1"
    handler.headers = {}
    handler.current_user = lambda: {"id": 7, "role": "Admin", "_tenant_id": "tenant-a"}
    replies = []
    handler.send_json = lambda payload, status=200: replies.append((payload, status))

    handler.do_GET()

    assert replies[0][1] == 200
    assert replies[0][0]["customer_id"] == 1
    assert replies[0][0]["customer_name"] == "Customer One"
    assert {(item["source"], item["id"]) for item in replies[0][0]["transactions"]} == {
        ("accounting", 11), ("currency", 21)
    }
    assert replies[0][0]["currency"] == "TRY"

    denied = object.__new__(web_main.AYECRequestHandler)
    denied.path = handler.path
    denied.headers = {}
    denied.current_user = lambda: None
    denials = []
    denied.send_json = lambda payload, status=200: denials.append((payload, status))
    denied.do_GET()
    assert denials[0][1] == 401
    assert denials[0][0]["code"] == "AUTH_REQUIRED"


def test_service_invoice_pdf_uses_selected_customer_transactions(tmp_path, monkeypatch):
    from src.utils import pdf_manager

    path = tmp_path / "tenant.db"
    _invoice_db(path)

    def connect():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn

    class FakePdfManager:
        def __init__(self, settings):
            self.settings = settings

        def create_invoice(self, **kwargs):
            Path(kwargs["save_path"]).write_bytes(b"pdf-bytes")
            self.kwargs = kwargs
            return True, kwargs["save_path"]

    monkeypatch.setattr(web_main, "db_connect", connect)
    monkeypatch.setattr(web_main, "ensure_packaged_source", lambda: None)
    monkeypatch.setattr(pdf_manager, "PDFManagerQt", FakePdfManager)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/service-invoices/1/pdf"
    handler.headers = {"X-AYEC-Fiscal-Archive": ""}
    handler.command = "POST"
    handler.current_user = lambda: {"id": 7, "role": "Admin", "_tenant_id": "tenant-a"}
    handler.read_json = lambda: {
        "template": "corporate",
        "transactions": [{"id": 21, "source": "currency"}],
    }
    replies = []
    handler.send_json = lambda payload, status=200: replies.append(("json", payload, status))
    handler.send_bytes = lambda payload, content_type, status=200, disposition=None: replies.append(
        ("bytes", payload, content_type, disposition)
    )

    handler.do_POST()

    assert replies == [("bytes", b"pdf-bytes", "application/pdf", 'attachment; filename="service-invoice-1.pdf"')]
