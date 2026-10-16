import io
from pathlib import Path

from PIL import Image

import src.database as database_module
from Web_Arayuzu import Main as web_main


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Web_Arayuzu" / "web" / "app.js"


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

