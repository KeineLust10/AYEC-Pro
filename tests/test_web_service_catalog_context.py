from pathlib import Path
import io
import sqlite3

import openpyxl
import pytest

from Web_Arayuzu import Main as web_main
import src.database as database_module


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_service_catalog_context_menu_matches_desktop_commands():
    desktop = (ROOT / "src" / "ui" / "pages" / "services_page.py").read_text(encoding="utf-8")
    method = desktop[desktop.index("def show_context_menu(self, pos):"):desktop.index("@staticmethod", desktop.index("def show_context_menu(self, pos):"))]
    web = (WEB / "service-catalog-context-parity.js").read_text(encoding="utf-8")

    for label in ("Yeni Hizmet", "D\u00fczenle", "Sil", "Excel Aktar", "PDF Olarak Kaydet", "Yazd\u0131r"):
        assert label in method
    for action in ("add", "edit", "delete", "excel", "pdf", "print"):
        assert f'"{action}"' in web
    assert '[data-generic-add]' in web
    assert 'generic-edit' in web and 'service-definition/delete' in web
    assert '[data-labor-export]' in web
    assert '[data-labor-pdf]' in web and '[data-labor-print]' in web
    assert '/api/desktop/services/export/xlsx' in web
    assert '/api/desktop/services/export/pdf' in web
    assert '/api/desktop/service-definition/delete' in web


def test_service_catalog_more_menu_supports_multi_select_edit_and_delete():
    web = (WEB / "service-catalog-context-parity.js").read_text(encoding="utf-8")

    for action in ("multi", "edit", "delete"):
        assert f'data-service-more="{action}"' in web
    assert "laborSelectedIds" in web
    assert "laborMultiSelect" in web
    assert "window.openGenericDialog(window.currentGenericMeta, rows[0], data.columns)" in web
    assert 'window.apiFetch("/api/desktop/service-definition/delete"' in web
    assert r"Se\u00e7ileni D\u00fczenle" in web
    assert r"Se\u00e7ileni Sil" in web
    assert r"Ak\u0131ll\u0131 \u0130\u00e7e Aktar" in web
    assert r"Excel \u0130\u00e7e Aktar" in web
    assert '"/api/desktop/service-definition/import"' in web


def _install_service_import_database(monkeypatch, database_path):
    class FakeDatabase:
        def __init__(self, path, init_mode):
            assert Path(path) == database_path
            assert init_mode == "connection_only"
            self.conn = sqlite3.connect(database_path)
            self.cursor = self.conn.cursor()
            self.conn.execute(
                """CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, price REAL DEFAULT 0,
                    currency TEXT DEFAULT 'TRY', description TEXT, barcode TEXT, created_at TEXT,
                    is_deleted INTEGER DEFAULT 0, deleted_at TEXT, price_try REAL DEFAULT 0,
                    price_usd REAL DEFAULT 0, price_eur REAL DEFAULT 0, is_active INTEGER DEFAULT 1,
                    service_category TEXT DEFAULT 'General', duration_minutes INTEGER DEFAULT 60,
                    vat_rate REAL DEFAULT 20
                )"""
            )
            self.conn.commit()

        def get_setting(self, key, default=""):
            return "TRY" if key in ("currency", "default_currency") else default

        def _ensure_services_management_schema(self):
            self.conn.commit()

        @staticmethod
        def _normalize_service_prices(price, currency, price_try, price_usd, price_eur):
            values = {"TRY": price_try, "USD": price_usd, "EUR": price_eur}
            for code in values:
                if values[code] is None:
                    values[code] = price if code == currency else 0
            return values

        def close(self):
            self.conn.close()

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: database_path)


def test_service_catalog_import_persists_all_rows_and_automotive_details_atomically(monkeypatch, tmp_path):
    database_path = tmp_path / "service-import.db"
    _install_service_import_database(monkeypatch, database_path)
    result = web_main.service_catalog_import([
        {"name": "Fan Cleaning", "price": "125,50", "currency": "TRY", "description": "Clean", "barcode": "SV-1"},
        {"name": "Brake Check", "price": "240", "currency": "TRY", "vehicle_plate": "34ABC123", "vehicle_brand": "AYEC"},
    ], is_automotive=True)

    assert result == {"ok": True, "imported": 2}
    connection = sqlite3.connect(database_path)
    rows = connection.execute("SELECT name, price, description, barcode, price_try FROM services ORDER BY id").fetchall()
    connection.close()
    assert rows == [
        ("FAN CLEANING", 125.5, "Clean", "SV-1", 125.5),
        ("BRAKE CHECK", 240.0, "Plaka: 34ABC123 | Marka: AYEC", "", 240.0),
    ]


def test_service_catalog_import_invalid_or_failed_rows_do_not_partially_write(monkeypatch, tmp_path):
    database_path = tmp_path / "service-import-atomic.db"
    _install_service_import_database(monkeypatch, database_path)
    database_module.Database(str(database_path), init_mode="connection_only").close()
    with pytest.raises(ValueError, match="duplicate service name"):
        web_main.service_catalog_import([
            {"name": "Same Service", "price": 10},
            {"name": "same service", "price": 20},
        ])

    connection = sqlite3.connect(database_path)
    connection.execute(
        "CREATE TRIGGER fail_service BEFORE INSERT ON services WHEN NEW.name='FAIL SERVICE' BEGIN SELECT RAISE(ABORT, 'fixture failure'); END"
    )
    connection.commit()
    connection.close()
    with pytest.raises(sqlite3.IntegrityError, match="fixture failure"):
        web_main.service_catalog_import([
            {"name": "First Service", "price": 10},
            {"name": "Fail Service", "price": 20},
        ])
    connection = sqlite3.connect(database_path)
    count = connection.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    connection.close()
    assert count == 0


def test_service_catalog_import_route_requires_authentication(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/service-definition/import"
    handler.headers = {"Content-Length": "20"}
    handler.current_user = lambda: None
    responses = []
    handler.send_json = lambda payload, status=200: responses.append((payload, status))

    handler.do_POST()

    assert responses == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_service_catalog_workbook_uses_tenant_service_columns_and_hides_deleted(monkeypatch, tmp_path):
    database_path = tmp_path / "tenant.db"
    setup = sqlite3.connect(database_path)
    setup.execute(
        "CREATE TABLE services (id INTEGER, name TEXT, price_try REAL, price_usd REAL, price_eur REAL, is_active INTEGER, barcode TEXT, description TEXT, is_deleted INTEGER)"
    )
    setup.execute(
        "INSERT INTO services VALUES (1, 'Clean', 12.5, 4.5, 4.0, 1, '=1+1', 'Details', 0)"
    )
    setup.execute(
        "INSERT INTO services VALUES (2, 'Hidden', 99, 0, 0, 0, '', '', 1)"
    )
    setup.commit()
    setup.close()

    def connect_tenant():
        connection = sqlite3.connect(database_path)
        connection.row_factory = sqlite3.Row
        return connection

    monkeypatch.setattr(web_main, "db_connect", connect_tenant)
    payload = web_main.service_catalog_workbook()
    workbook = openpyxl.load_workbook(io.BytesIO(payload), data_only=True)
    sheet = workbook.active

    assert sheet.title == "Sheet1"
    assert [cell.value for cell in sheet[1]] == [
        "\u0130\u015f\u00e7ilik Ad\u0131", "TL", "USD", "EURO", "Durum", "Barkod", "A\u00e7\u0131klama",
    ]
    assert [cell.value for cell in sheet[2]] == ["Clean", 12.5, 4.5, 4, "Aktif", "'=1+1", "Details"]
    assert sheet.max_row == 2


def test_service_catalog_export_route_requires_login_and_returns_xlsx(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/services/export/xlsx"
    handler.headers = {}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    sent = []
    handler.send_bytes = lambda *args, **kwargs: sent.append((args, kwargs))
    monkeypatch.setattr(web_main, "service_catalog_workbook", lambda: b"xlsx")

    handler.do_GET()

    assert sent[0][0][0] == b"xlsx"
    assert sent[0][0][1] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = handler.path
    unauthenticated.headers = {}
    unauthenticated.current_user = lambda: None
    errors = []
    unauthenticated.send_json = lambda payload, status=200: errors.append((payload, status))

    unauthenticated.do_GET()

    assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]



def test_service_catalog_pdf_export_route_requires_login_and_returns_pdf(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/services/export/pdf"
    handler.headers = {}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    sent = []
    handler.send_bytes = lambda *args, **kwargs: sent.append((args, kwargs))
    monkeypatch.setattr(web_main, "service_catalog_workbook", lambda: b"xlsx")
    monkeypatch.setattr(web_main, "desktop_stock_pdf", lambda payload, title: b"%PDF-" + payload)

    handler.do_GET()

    assert sent[0][0][0] == b"%PDF-xlsx"
    assert sent[0][0][1] == "application/pdf"
    assert "Hizmet_Listesi_" in sent[0][1]["disposition"]

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = handler.path
    unauthenticated.headers = {}
    unauthenticated.current_user = lambda: None
    errors = []
    unauthenticated.send_json = lambda payload, status=200: errors.append((payload, status))

    unauthenticated.do_GET()

    assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]

def test_service_definition_delete_route_uses_tenant_database_delete_method(monkeypatch, tmp_path):
    calls = []

    class FakeDatabase:
        def __init__(self, path, init_mode):
            calls.append(("open", Path(path), init_mode))

        def delete_service(self, service_id):
            calls.append(("delete", service_id))
            return True

        def close(self):
            calls.append(("close",))

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/service-definition/delete"
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
