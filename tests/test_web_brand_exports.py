import io
import sqlite3
from pathlib import Path

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

def test_brand_catalog_refresh_requires_auth_and_uses_active_tenant_database(monkeypatch, tmp_path):
    calls = []
    class FakeDatabase:
        def __init__(self, path, init_mode):
            calls.append(("init", path, init_mode))
            self.cursor = self
        def refresh_device_model_catalog(self):
            calls.append(("refresh",))
        def get_device_model_catalog(self):
            return [("profile", "Phone", "Acme", "Model X", 2026, "reviewed")]
        def execute(self, sql):
            assert sql == "SELECT COUNT(*) FROM device_brands"
            return self
        def fetchone(self):
            return (2,)
        def close(self):
            calls.append(("close",))

    tenant_path = tmp_path / "active-tenant.sqlite3"
    monkeypatch.setattr("src.database.Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/device-brands/refresh-catalog"
    handler.headers = {}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    sent = []
    handler.send_json = lambda payload, status=200: sent.append((payload, status))
    handler.do_POST()

    assert sent == [({"ok": True, "model_count": 1, "brand_count": 2}, 200)]
    assert calls == [("init", str(tenant_path), "connection_only"), ("refresh",), ("close",)]

    anonymous = object.__new__(web_main.AYECRequestHandler)
    anonymous.path = handler.path
    anonymous.headers = {}
    anonymous.current_user = lambda: None
    errors = []
    anonymous.send_json = lambda payload, status=200: errors.append((payload, status))
    anonymous.do_POST()
    assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_brand_refresh_button_calls_reviewed_catalog_endpoint():
    source = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "brand-export-parity.js").read_text(encoding="utf-8")
    assert '/api/desktop/device-brands/refresh-catalog' in source
    assert 'window.loadGenericModule(window.currentGenericMeta' in source


def test_brand_print_uses_filtered_authenticated_pdf_preview():
    source = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "brand-export-parity.js").read_text(encoding="utf-8")
    assert 'format === "print"' in source
    assert 'window.open("about:blank", "_blank")' in source
    assert 'credentials: "same-origin"' in source
    assert 'printWindow.location = url' in source
    assert 'device-brands/export/${extension}?${query}' in source

def test_device_model_catalog_route_is_authenticated_and_tenant_scoped(monkeypatch, tmp_path):
    calls = []
    class FakeDatabase:
        def __init__(self, path, init_mode):
            calls.append(("init", path, init_mode))
        def get_device_model_catalog(self, profiles=None, device_type=None, brand=None):
            calls.append(("query", profiles, device_type, brand))
            return [("laptop", "Laptop", "Acme", "Model X", 2026, "reviewed")]
        def close(self):
            calls.append(("close",))

    tenant_path = tmp_path / "active-tenant.sqlite3"
    monkeypatch.setattr("src.database.Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/device-model-catalog?profile=laptop&device_type=Laptop&brand=Acme"
    handler.headers = {}
    handler.current_user = lambda: {"id": 7, "role": "User"}
    sent = []
    handler.send_json = lambda payload, status=200: sent.append((payload, status))
    handler.do_GET()

    assert sent == [({"rows": [{"business_profile": "laptop", "device_type": "Laptop", "brand": "Acme", "model": "Model X", "release_year": 2026, "source": "reviewed"}], "count": 1, "seeded": False}, 200)]
    assert calls == [("init", str(tenant_path), "connection_only"), ("query", ["laptop"], "Laptop", "Acme"), ("close",)]

    anonymous = object.__new__(web_main.AYECRequestHandler)
    anonymous.path = handler.path
    anonymous.headers = {}
    anonymous.current_user = lambda: None
    errors = []
    anonymous.send_json = lambda payload, status=200: errors.append((payload, status))
    anonymous.do_GET()
    assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_service_intake_uses_device_model_catalog_suggestions():
    app = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert '/api/desktop/device-model-catalog' in app
    assert 'serviceDeviceTypeOptions' in app and 'serviceDeviceBrandOptions' in app and 'serviceDeviceModelOptions' in app
    parity = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "service-catalog-context-parity.js").read_text(encoding="utf-8")
    assert "baseServiceDialog.apply(this, args)" in parity and "loadServiceDeviceModelSuggestions()" in parity

def test_empty_device_model_catalog_is_lazily_seeded_for_active_tenant(monkeypatch, tmp_path):
    calls = []
    class FakeDatabase:
        def __init__(self, path, init_mode):
            calls.append(("init", path, init_mode))
            self.seeded = False
            self.cursor = self
        def execute(self, sql):
            calls.append(("ensure-device-brands", "CREATE TABLE IF NOT EXISTS device_brands" in sql))
        def get_device_model_catalog(self, profiles=None, device_type=None, brand=None):
            calls.append(("query", profiles, device_type, brand))
            if not self.seeded:
                return []
            return [("laptop", "Laptop", "Acme", "Model X", 2026, "reviewed")]
        def refresh_device_model_catalog(self):
            calls.append(("refresh",))
            self.seeded = True
        def close(self):
            calls.append(("close",))

    tenant_path = tmp_path / "empty-tenant.sqlite3"
    monkeypatch.setattr("src.database.Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/device-model-catalog"
    handler.headers = {}
    handler.current_user = lambda: {"id": 8, "role": "User"}
    sent = []
    handler.send_json = lambda payload, status=200: sent.append((payload, status))
    handler.do_GET()

    assert sent == [({"rows": [{"business_profile": "laptop", "device_type": "Laptop", "brand": "Acme", "model": "Model X", "release_year": 2026, "source": "reviewed"}], "count": 1, "seeded": True}, 200)]
    assert calls == [
        ("init", str(tenant_path), "connection_only"),
        ("query", None, None, None),
        ("ensure-device-brands", True),
        ("refresh",),
        ("query", None, None, None),
        ("close",),
    ]


def test_legacy_tenant_catalog_seeds_when_device_brands_table_is_missing(monkeypatch, tmp_path):
    import sqlite3

    tenant_path = tmp_path / "legacy-tenant.sqlite3"
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/device-model-catalog"
    handler.headers = {}
    handler.current_user = lambda: {"id": 9, "role": "User"}
    sent = []
    handler.send_json = lambda payload, status=200: sent.append((payload, status))

    handler.do_GET()

    assert sent and sent[0][1] == 200
    assert sent[0][0]["seeded"] is True
    with sqlite3.connect(tenant_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert {"device_models", "device_brands"} <= tables

def test_automotive_vehicle_catalog_route_requires_auth_and_returns_reviewed_values():
    from src.utils.vehicle_catalog import ENGINE_TYPES, FUEL_TYPES, VEHICLE_BRAND_MODELS, VEHICLE_TYPES, get_vehicle_brands, get_vehicle_years

    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/automotive/vehicle-catalog"
    handler.headers = {}
    handler.current_user = lambda: {"id": 9, "role": "User"}
    responses = []
    handler.send_json = lambda payload, status=200: responses.append((payload, status))
    handler.do_GET()

    assert responses == [({"brands": get_vehicle_brands(), "models": VEHICLE_BRAND_MODELS, "years": get_vehicle_years(), "vehicle_types": VEHICLE_TYPES, "engine_types": ENGINE_TYPES, "fuel_types": FUEL_TYPES}, 200)]

    anonymous = object.__new__(web_main.AYECRequestHandler)
    anonymous.path = handler.path
    anonymous.headers = {}
    anonymous.current_user = lambda: None
    errors = []
    anonymous.send_json = lambda payload, status=200: errors.append((payload, status))
    anonymous.do_GET()
    assert errors == [({"error": "Oturum a\u00e7man\u0131z gerekiyor.", "code": "AUTH_REQUIRED"}, 401)]


def test_vehicle_choice_catalog_matches_desktop_vehicle_dialog():
    from src.ui.dialogs.customer_vehicle_dialog import CustomerVehicleDialog
    from src.utils.vehicle_catalog import ENGINE_TYPES, FUEL_TYPES, VEHICLE_TYPES

    assert CustomerVehicleDialog.VEHICLE_TYPES == VEHICLE_TYPES
    assert CustomerVehicleDialog.ENGINE_TYPES == ENGINE_TYPES
    assert CustomerVehicleDialog.FUEL_TYPES == FUEL_TYPES
