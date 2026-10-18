import io
from pathlib import Path
from datetime import datetime as DateTime

import openpyxl
from pypdf import PdfReader

import src.database as database_module
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "Web_Arayuzu" / "web"


def test_vehicle_maintenance_page_exposes_excel_pdf_and_print_actions():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "data-maintenance-excel" in app
    assert "data-maintenance-pdf" in app
    assert "data-maintenance-print" in app
    assert 'id="maintenanceStatTotal"' in app
    assert 'id="maintenanceStatDue"' in app
    assert 'id="maintenanceStatInspection"' in app
    assert 'id="maintenanceStatJobs"' in app
    assert 'apiFetch(`/api/desktop/vehicle-maintenance/cards?q=${encodeURIComponent(query)}`)' in app
    assert 'vehicle-maintenance/export/xlsx?q=${query}' in app
    assert 'vehicle-maintenance/export/pdf?q=${query}' in app
    assert '$("[data-maintenance-pdf]").onclick=exportVehicleMaintenancePdf' in app
    assert 'if(action==="maintenance-pdf")exportVehicleMaintenancePdf();if(action==="maintenance-print")window.print()' in app
    assert '"Yaklasan KM", "Taslak Randevu", "Hatirlatma", "Foto"' in (
        ROOT / "Web_Arayuzu" / "Main.py"
    ).read_text(encoding="utf-8")


def test_vehicle_maintenance_web_matches_desktop_summary_and_initial_selection():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert "function updateVehicleMaintenanceStats(rows)" in app
    assert "maintenanceStatDue:rows.filter" in app
    assert "maintenanceStatInspection:rows.filter" in app
    assert "maintenanceStatJobs:rows.filter(row=>Boolean(row.linked_device_id))" in app
    assert "vehicleMaintenanceRows.find(row=>String(row.id)===String(selectedMaintenanceRowId))||vehicleMaintenanceRows[0]" in app


def test_vehicle_maintenance_context_menu_matches_desktop_action_order():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert r'if(kind==="vehicle-maintenance")items=[["Bak\u0131m Kart\u0131n\u0131 A\u00e7","maintenance-open"],["Foto Galeri","maintenance-photos"],["QR / Ge\u00e7mi\u015f","maintenance-history"],["","maintenance-separator"],["Excel\u0027e Aktar","maintenance-excel"],["PDF Olu\u015ftur","maintenance-pdf"],["Yazd\u0131r","maintenance-print"]]' in app


def test_vehicle_maintenance_whatsapp_prompt_uses_shared_dialog_and_desktop_message_rules():
    app = (WEB / "app.js").read_text(encoding="utf-8")
    start = app.index("function offerMaintenanceWhatsApp(")
    end = app.index("\nfunction openMaintenanceService(", start)
    flow = app[start:end]

    assert 'openDialog("Randevu Mesaj' in flow
    assert "if(!confirm(" not in flow
    assert "importantItems.slice(0,5)" in flow
    assert "kalem daha" in flow
    assert "appointmentDate" in flow
    assert "if(!phone){toast(" in flow
    assert 'phone.startsWith("0")&&phone.length===11' in flow


def test_vehicle_maintenance_web_table_matches_desktop_columns():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    for column in (
        "<th>ID</th>",
        "<th>M\\u00fc\\u015fteri</th>",
        "<th>Plaka</th>",
        "<th>Ara\\u00e7</th>",
        "<th>Bak\\u0131m Tarihi</th>",
        "<th>Yakla\\u015fan KM</th>",
        "<th>Taslak Randevu</th>",
        "<th>Hat\\u0131rlatma</th>",
        "<th>Foto</th>",
    ):
        assert column in app
    assert "row.next_due_odometer_min||0" in app
    assert "dueKm-currentKm" in app
    assert 'row.reminder_date||""' in app
    assert "row.photo_count||0" in app


def test_vehicle_maintenance_selection_summary_uses_detail_and_history_apis():
    app = (WEB / "app.js").read_text(encoding="utf-8")

    assert 'id="maintenanceSelection"' in app
    assert 'data-maintenance-open-service disabled' in app
    assert "async function selectVehicleMaintenance(row,element)" in app
    assert 'vehicle-maintenance/detail/${encodeURIComponent(row.id)}' in app
    assert 'vehicle-maintenance/history/${encodeURIComponent(row.id)}' in app
    assert "data-maintenance-summary" in app
    assert "data-maintenance-history" in app
    assert "openService.onclick=()=>openMaintenanceService(card)" in app


def test_vehicle_maintenance_workbook_matches_desktop_export_columns(monkeypatch, tmp_path):
    class FakeDatabase:
        queries = []

        def __init__(self, path, init_mode):
            assert Path(path) == tmp_path / "tenant.db"
            assert init_mode == "connection_only"

        def get_vehicle_maintenance_cards(self, query):
            self.queries.append(query)
            return [{
                "id": 12,
                "customer_name": "=1+1",
                "vehicle_plate": "10 WEB 12",
                "vehicle_brand": "Ayec",
                "vehicle_model": "Van",
                "service_date": "2026-10-13",
                "next_maintenance_date": "2027-10-13",
                "inspection_due_date": "2027-01-01",
                "next_due_odometer_min": 52000,
                "odometer": 50000,
                "appointment_date": "2026-10-20",
                "reminder_date": "2026-10-19",
                "photo_count": 3,
            }]

        def close(self):
            pass

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")

    payload = web_main.vehicle_maintenance_workbook("10 WEB")
    workbook = openpyxl.load_workbook(io.BytesIO(payload), data_only=True)
    sheet = workbook.active

    assert FakeDatabase.queries == ["10 WEB"]
    assert [cell.value for cell in sheet[1]] == [
        "ID", "Musteri", "Plaka", "Arac", "Bakim Tarihi", "Sonraki Bakim",
        "Muayene", "Yaklasan KM", "Taslak Randevu", "Hatirlatma", "Foto",
    ]
    assert [cell.value for cell in sheet[2]] == [
        12, "'=1+1", "10 WEB 12", "Ayec Van", "2026-10-13", "2027-10-13",
        "2027-01-01", "2000 KM", "2026-10-20", "2026-10-19", 3,
    ]


def test_vehicle_maintenance_pdf_matches_desktop_report_fields(monkeypatch, tmp_path):
    class FakeDatabase:
        queries = []

        def __init__(self, path, init_mode):
            assert Path(path) == tmp_path / "tenant.db"
            assert init_mode == "connection_only"

        def get_vehicle_maintenance_cards(self, query):
            self.queries.append(query)
            return [{
                "id": 12, "customer_name": "<QA Customer>", "vehicle_plate": "10 WEB 12",
                "vehicle_brand": "Ayec", "vehicle_model": "Van", "service_date": "2026-10-13",
                "next_maintenance_date": "2027-10-13", "inspection_due_date": "2027-01-01",
                "next_due_odometer_min": 52000, "odometer": 50000, "appointment_date": "2026-10-20",
                "reminder_date": "2026-10-19", "photo_count": 3,
            }]

        def get_setting(self, key, default=""):
            return {"company_name": "QA Fleet", "logo_path": ""}.get(key, default)

        def close(self):
            pass

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")

    payload = web_main.vehicle_maintenance_pdf("10 WEB")
    text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(payload)).pages)

    assert payload.startswith(b"%PDF-")
    assert FakeDatabase.queries == ["10 WEB"]
    assert "QA Fleet - Arac Bakim Listesi" in text and "Arac Bakim Raporu" in text
    assert "Toplam Kart" in text and "Yaklasan Bakim" in text and "Acik Is Emri" in text
    assert "<QA Customer>" in text and "10 WEB 12" in text and "2000 KM" in text


def test_vehicle_maintenance_pdf_route_requires_login_and_downloads_pdf(monkeypatch, tmp_path):
    class FixedDateTime(DateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 13)

    monkeypatch.setattr(web_main, "datetime", FixedDateTime)
    monkeypatch.setattr(web_main, "vehicle_maintenance_pdf", lambda query: b"pdf:" + query.encode())
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/vehicle-maintenance/export/pdf?q=10+WEB"
    handler.headers = {}
    sent = []
    handler.current_user = lambda: {"id": 1, "role": "admin"}
    handler.send_bytes = lambda payload, content_type, status=200, disposition=None: sent.append(
        (payload, content_type, status, disposition)
    )

    handler.do_GET()

    assert sent == [(
        b"pdf:10 WEB", "application/pdf", 200,
        'attachment; filename="arac_bakim_20261013.pdf"',
    )]

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = "/api/desktop/vehicle-maintenance/export/pdf"
    unauthenticated.headers = {}
    errors = []
    unauthenticated.current_user = lambda: None
    unauthenticated.send_json = lambda payload, status=200: errors.append((payload, status))

    unauthenticated.do_GET()

    assert len(errors) == 1
    assert errors[0][0]["code"] == "AUTH_REQUIRED"
    assert errors[0][1] == 401


def test_vehicle_maintenance_export_route_requires_login_and_returns_xlsx(monkeypatch):
    class FixedDateTime(DateTime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 13)

    monkeypatch.setattr(web_main, "datetime", FixedDateTime)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/vehicle-maintenance/export/xlsx?q=10+WEB"
    handler.headers = {}
    sent = []
    handler.current_user = lambda: {"id": 1, "role": "admin"}
    handler.send_bytes = lambda payload, content_type, status=200, disposition=None: sent.append(
        (payload, content_type, status, disposition)
    )
    monkeypatch.setattr(web_main, "vehicle_maintenance_workbook", lambda query: b"xlsx:" + query.encode())

    handler.do_GET()

    assert sent == [(
        b"xlsx:10 WEB",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        200,
        'attachment; filename="arac_bakim_20261013.xlsx"',
    )]

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = "/api/desktop/vehicle-maintenance/export/xlsx"
    unauthenticated.headers = {}
    errors = []
    unauthenticated.current_user = lambda: None
    unauthenticated.send_json = lambda payload, status=200: errors.append((payload, status))

    unauthenticated.do_GET()

    assert len(errors) == 1
    assert errors[0][0]["code"] == "AUTH_REQUIRED"
    assert errors[0][1] == 401


def test_vehicle_maintenance_form_selects_existing_customer_vehicles_and_plate_lookup():
    script = (ROOT / "Web_Arayuzu" / "web" / "automotive-parity.js").read_text(encoding="utf-8")
    desktop = (ROOT / "src" / "ui" / "dialogs" / "vehicle_maintenance_dialog.py").read_text(encoding="utf-8")
    app = (ROOT / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")

    assert 'name="vehicle_id"' in script
    assert 'customer_vehicles?limit=500' in script
    assert 'data-maintenance-add-vehicle' in script
    assert 'data-maintenance-add-customer' in script
    assert 'draft._draftItems=' in script
    assert 'refreshCustomer:false' in script
    assert 'customerSelect.addEventListener("change"' in script
    assert 'plateInput?.addEventListener("blur"' in script
    assert "maintenanceVehicleCatalog" in script
    assert 'replaceWithChoices(maintenanceField("vehicle_year")' in script
    assert 'replaceWithChoices(maintenanceField("engine_type"),maintenanceEngineTypes)' in script
    assert "_reload_customer_vehicles" in desktop
    assert "openMaintenanceItemsDialog" in app
    assert 'name="maintenance_items_json"' in app
    assert 'data-maintenance-gallery' in app
    assert 'data-maintenance-history' in app
    assert 'if(!payload.items.length){toast("En az bir bakim kalemi secin."' in app
    assert "_apply_vehicle_row" in desktop
    assert "_lookup_plate" in desktop
