import io
from pathlib import Path

from PIL import Image

import src.database as database_module
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"
AUTOMOTIVE = ROOT / "Web_Arayuzu" / "web" / "automotive-parity.js"


def test_automotive_technician_loads_complete_service_form_results():
    source = AUTOMOTIVE.read_text(encoding="utf-8")
    start = source.index("technicianDialog=async function(customer,service){")
    end = source.index("const damageMarks=", start)
    block = source[start:end]

    assert 'loadAllDesktopTableData("automotive_service_forms",{q:service.no||""})' in block
    assert "automotive_service_forms?limit=500" not in block


def test_maintenance_items_inputs_match_dark_dialog_theme():
    css = (ROOT / "Web_Arayuzu" / "web" / "automotive-parity.css").read_text(encoding="utf-8")
    index = (ROOT / "Web_Arayuzu" / "web" / "index.html").read_text(encoding="utf-8")
    runner = (ROOT / "tools" / "quality" / "vehicle_maintenance_items_manifest_offscreen.cjs").read_text(encoding="utf-8")

    assert '.maintenance-items-dialog-panel .maintenance-item input:not([type="checkbox"])' in css
    assert "background:var(--input-bg)" in css
    assert "color:var(--ink)" in css
    assert "color-scheme:dark" in css
    assert ".maintenance-items-dialog-panel .maintenance-item{grid-template-columns:repeat(6,minmax(0,1fr))" in css
    assert ".maintenance-items-dialog-panel .maintenance-item input[type=\"checkbox\"]{accent-color:#657483}" in css
    assert ".maintenance-items-dialog-panel .maintenance-number-steps button{width:100%;height:27px" in css
    assert 'data-maintenance-step="1"' in APP.read_text(encoding="utf-8")
    assert "dayDueUp" in runner
    assert "kmDueUp" in runner
    assert 'automotive-parity.css?v=20261026-maintenance-grid-parity-3' in index


def test_vehicle_maintenance_dialog_fixture_preserves_injected_dollar_helpers():
    runner = (ROOT / "tools" / "quality" / "vehicle_maintenance_items_manifest_offscreen.cjs").read_text(encoding="utf-8")
    fixture = (ROOT / "tools" / "quality" / "vehicle_maintenance_items_manifest_fixture.js").read_text(encoding="utf-8")

    assert 'replace("/*PRODUCTION_FUNCTIONS*/",()=>functions)' in runner
    assert 'req.url==="/assets/ayec-logo.png"' in runner
    assert 'res.setHeader("content-type","image/png")' in runner
    assert 'service_date:"2026-04-01",odometer:100000' in fixture


def test_offscreen_route_audit_covers_vehicle_maintenance_creation_and_items():
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")
    assert 'document.querySelector("[data-maintenance-add]")?.click()' in audit
    assert 'document.querySelector("[data-maintenance-items-open]")?.click()' in audit
    assert 'vehicleMaintenanceWorkflow.savedPayload.vehicle_id !== 83' in audit
    assert 'vehicleMaintenanceWorkflow.savedPayload.items.length !== 1' in audit
    assert 'vehicleMaintenanceWorkflow.photoCounterAfterAdd !== "1 / 1"' in audit
    assert 'vehicleMaintenanceWorkflow.photoCalls[1]?.photo_id !== 9901' in audit


def test_vehicle_maintenance_supports_native_keyboard_row_navigation():
    app = APP.read_text(encoding="utf-8")
    audit = (ROOT / "tools" / "quality" / "web_route_smoke_offscreen.cjs").read_text(encoding="utf-8")

    assert "function bindVehicleMaintenanceKeyboard(row)" in app
    assert 'event.key==="ArrowDown"' in app
    assert 'event.key==="ArrowUp"' in app
    assert 'event.key==="Home"' in app
    assert 'event.key==="End"' in app
    assert "bindVehicleMaintenanceKeyboard(row)" in app
    assert "maintenanceKeyboardWorkflow" in audit
    assert 'maintenanceKeyboardWorkflow?.downId !== "82"' in audit
    assert 'maintenanceKeyboardWorkflow?.homeId !== "81"' in audit
    assert 'maintenanceKeyboardWorkflow?.downAria !== "true"' in audit


def test_vehicle_history_returns_same_tenant_maintenance_and_service_records(monkeypatch, tmp_path):
    class FakeDatabase:
        def __init__(self, path, init_mode):
            assert Path(path) == tmp_path / "tenant.db"
            assert init_mode == "connection_only"

        def get_vehicle_maintenance_card(self, card_id):
            assert card_id == 12
            return ({"id": 12, "vehicle_plate": "10 WEB 12", "qr_token": "AYEC-AUTO-123"}, [])

        def get_vehicle_history_snapshot(self, plate):
            assert plate == "10 WEB 12"
            return ([{"id": 12, "service_date": "2026-10-13", "qr_token": "AYEC-AUTO-123"}], [
                {"tracking_no": "SRV-12", "entry_date": "2026-10-14"}
            ])

        def close(self):
            pass

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")

    result = web_main.vehicle_maintenance_history(12)

    assert result["token"] == "AYEC-AUTO-123"
    assert result["plate"] == "10 WEB 12"
    assert result["maintenance_rows"][0]["service_date"] == "2026-10-13"
    assert result["service_rows"][0]["tracking_no"] == "SRV-12"


def test_vehicle_history_qr_is_generated_locally_from_desktop_share_uri(monkeypatch):
    monkeypatch.setattr(web_main, "vehicle_maintenance_history", lambda card_id: {
        "token": "AYEC-AUTO-123", "plate": "10 WEB 12"
    })

    payload = web_main.vehicle_maintenance_history_qr(12)
    image = Image.open(io.BytesIO(payload))

    assert payload.startswith(b"\x89PNG\r\n\x1a\n")
    assert image.format == "PNG"
    assert image.width == image.height


def test_vehicle_history_api_routes_require_login_and_return_history_and_qr(monkeypatch):
    history = {"card_id": 12, "plate": "10 WEB 12", "token": "AYEC-AUTO-123", "maintenance_rows": [], "service_rows": []}
    monkeypatch.setattr(web_main, "vehicle_maintenance_history", lambda card_id: history)
    monkeypatch.setattr(web_main, "vehicle_maintenance_history_qr", lambda card_id: b"png")

    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/vehicle-maintenance/history/12"
    handler.headers = {}
    handler.current_user = lambda: {"id": 1, "role": "admin"}
    json_responses = []
    handler.send_json = lambda payload, status=200: json_responses.append((payload, status))
    handler.do_GET()
    assert json_responses == [(history, 200)]

    qr_handler = object.__new__(web_main.AYECRequestHandler)
    qr_handler.path = "/api/desktop/vehicle-maintenance/history-qr/12"
    qr_handler.headers = {}
    qr_handler.current_user = lambda: {"id": 1, "role": "admin"}
    byte_responses = []
    qr_handler.send_bytes = lambda payload, content_type, status=200, disposition=None: byte_responses.append(
        (payload, content_type, status)
    )
    qr_handler.do_GET()
    assert byte_responses == [(b"png", "image/png", 200)]

    unauthenticated = object.__new__(web_main.AYECRequestHandler)
    unauthenticated.path = "/api/desktop/vehicle-maintenance/history/12"
    unauthenticated.headers = {}
    unauthenticated.current_user = lambda: None
    errors = []
    unauthenticated.send_json = lambda payload, status=200: errors.append((payload, status))
    unauthenticated.do_GET()
    assert errors[0][0]["code"] == "AUTH_REQUIRED"
    assert errors[0][1] == 401


def test_vehicle_maintenance_cards_api_returns_desktop_derived_rows_and_requires_login(monkeypatch):
    payload = {"rows": [{
        "id": 12,
        "vehicle_plate": "10 WEB 12",
        "next_due_odometer_min": 52000,
        "photo_count": 3,
    }], "count": 1}
    queries = []
    monkeypatch.setattr(web_main, "vehicle_maintenance_cards_payload", lambda query: queries.append(query) or payload)

    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/vehicle-maintenance/cards?q=10+WEB"
    handler.headers = {}
    handler.current_user = lambda: {"id": 1, "role": "admin"}
    responses = []
    handler.send_json = lambda result, status=200: responses.append((result, status))
    handler.do_GET()
    assert responses == [(payload, 200)]
    assert queries == ["10 WEB"]

    anonymous = object.__new__(web_main.AYECRequestHandler)
    anonymous.path = "/api/desktop/vehicle-maintenance/cards"
    anonymous.headers = {}
    anonymous.current_user = lambda: None
    errors = []
    anonymous.send_json = lambda result, status=200: errors.append((result, status))
    anonymous.do_GET()
    assert errors[0][0]["code"] == "AUTH_REQUIRED"
    assert errors[0][1] == 401


def test_vehicle_maintenance_save_api_requires_authentication(monkeypatch):
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/vehicle-maintenance/save"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: None
    handler.read_json = lambda: {}
    calls = []
    responses = []
    monkeypatch.setattr(web_main, "save_vehicle_maintenance_web", lambda payload: calls.append(payload) or {"ok": True})
    handler.send_json = lambda payload, status=200: responses.append((payload, status))

    handler.do_POST()

    assert calls == []
    assert len(responses) == 1
    assert responses[0][0]["code"] == "AUTH_REQUIRED"
    assert responses[0][1] == 401


def test_authenticated_vehicle_maintenance_save_api_persists_workflow(tmp_path, monkeypatch):
    database_path = tmp_path / "vehicle-maintenance-http.db"
    db = database_module.Database(str(database_path))
    customer_id = db.add_customer({"name": "HTTP Maintenance Customer"})
    db.close()
    web_main.clear_tenant_context()
    monkeypatch.setattr(web_main, "DB_PATH", database_path)

    payload = {
        "customer_id": customer_id,
        "vehicle_plate": "35HTTP35",
        "vehicle_brand": "Ford",
        "vehicle_model": "Focus",
        "items": [{"item_type": "oil_change", "item_label": "Oil change", "performed": True}],
    }
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/vehicle-maintenance/save"
    handler.headers = {"Content-Length": "2"}
    handler.current_user = lambda: {"id": 1, "role": "admin"}
    handler.read_json = lambda: payload
    responses = []
    handler.send_json = lambda result, status=200: responses.append((result, status))

    handler.do_POST()

    assert responses[0][1] == 200
    assert responses[0][0]["ok"] is True
    assert responses[0][0]["vehicle_plate"] == "35HTTP35"
    db = database_module.Database(str(database_path))
    assert db.conn.execute("SELECT COUNT(*) FROM vehicle_maintenance_cards").fetchone()[0] == 1
    assert db.conn.execute("SELECT COUNT(*) FROM customer_vehicles").fetchone()[0] == 1
    assert db.conn.execute("SELECT COUNT(*) FROM devices").fetchone()[0] == 1
    assert db.conn.execute("SELECT COUNT(*) FROM automotive_service_forms").fetchone()[0] == 1
    db.close()
    web_main.clear_tenant_context()


def test_vehicle_maintenance_page_has_qr_history_action_and_local_qr_image():
    app = APP.read_text(encoding="utf-8")

    assert "data-maintenance-history" in app
    assert 'vehicle-maintenance/history/${encodeURIComponent(row.id)}' in app
    assert 'vehicle-maintenance/history-qr/${encodeURIComponent(row.id)}' in app
    assert 'ayec://vehicle-history/${token}' in app
    assert 'navigator.clipboard?.writeText' in app


def test_vehicle_maintenance_card_payload_uses_desktop_rows_and_derived_columns(monkeypatch, tmp_path):
    class FakeDatabase:
        def __init__(self, path, init_mode):
            assert Path(path) == tmp_path / "tenant.db"
            assert init_mode == "connection_only"

        def get_vehicle_maintenance_cards(self, query):
            assert query == "10 WEB"
            return [
                {"id": index, "vehicle_plate": f"10 WEB {index}", "next_due_odometer_min": 52000,
                 "photo_count": 3, "next_due_item_date": "2027-10-13"}
                for index in range(1, 502)
            ]

        def close(self):
            pass

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")

    payload = web_main.vehicle_maintenance_cards_payload(" 10 WEB ")

    assert payload["count"] == 501
    assert payload["rows"][0]["next_due_odometer_min"] == 52000
    assert payload["rows"][0]["photo_count"] == 3
    assert payload["rows"][-1]["id"] == 501


def test_vehicle_maintenance_detail_route_requires_login(monkeypatch):
    payload = {"ok": True, "card": {"id": 12}, "items": []}
    monkeypatch.setattr(web_main, "vehicle_maintenance_detail", lambda card_id: payload)
    handler = object.__new__(web_main.AYECRequestHandler)
    handler.path = "/api/desktop/vehicle-maintenance/detail/12"
    handler.headers = {}
    handler.current_user = lambda: {"id": 1, "role": "admin"}
    responses = []
    handler.send_json = lambda body, status=200: responses.append((body, status))
    handler.do_GET()
    assert responses == [(payload, 200)]

    denied = object.__new__(web_main.AYECRequestHandler)
    denied.path = "/api/desktop/vehicle-maintenance/detail/12"
    denied.headers = {}
    denied.current_user = lambda: None
    errors = []
    denied.send_json = lambda body, status=200: errors.append((body, status))
    denied.do_GET()
    assert errors[0][1] == 401

