import base64
from pathlib import Path

import pytest

import src.database as database_module
from Web_Arayuzu import Main as web_main


def test_vehicle_photo_upload_is_stored_under_active_tenant_and_validated(monkeypatch, tmp_path):
    calls = []

    class FakeDatabase:
        def __init__(self, path, init_mode):
            assert Path(path) == tmp_path / "tenant.db"

        def get_vehicle_maintenance_card(self, card_id):
            assert card_id == 9
            return ({"id": 9}, [])

        def add_vehicle_maintenance_photo(self, card_id, photo_path, photo_label):
            calls.append((card_id, Path(photo_path), photo_label))
            return 17

        def close(self):
            pass

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    png = b"\x89PNG\r\n\x1a\nphoto"

    result = web_main.vehicle_maintenance_add_photo(
        9, "ignored.png", base64.b64encode(png).decode("ascii"), "Yag Filtresi"
    )

    assert result == {"id": 17, "card_id": 9, "photo_label": "Yag Filtresi", "available": True}
    assert calls[0][1].parent == tmp_path / "maintenance_photos"
    assert calls[0][1].read_bytes() == png
    assert calls[0][2] == "Yag Filtresi"


def test_vehicle_photo_upload_rejects_bad_type_label_and_oversize(monkeypatch, tmp_path):
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")
    data = base64.b64encode(b"not an image").decode("ascii")
    with pytest.raises(ValueError, match="JPEG"):
        web_main.vehicle_maintenance_add_photo(1, "x", data, "Yag Filtresi")
    png = base64.b64encode(b"\x89PNG\r\n\x1a\nvalid").decode("ascii")
    with pytest.raises(ValueError, match="etiketi"):
        web_main.vehicle_maintenance_add_photo(1, "x", png, "../tenant")
    too_big = base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"x" * web_main.VEHICLE_MAINTENANCE_PHOTO_LIMIT).decode("ascii")
    with pytest.raises(ValueError, match="8 MB"):
        web_main.vehicle_maintenance_add_photo(1, "x", too_big, "Yag Filtresi")


def test_vehicle_photo_serving_and_deletion_reject_paths_outside_tenant(monkeypatch, tmp_path):
    external_file = tmp_path / "outside.png"
    external_file.write_bytes(b"\x89PNG\r\n\x1a\nsecret")

    class FakeCursor:
        def execute(self, query, args):
            self.row = {"photo_path": str(external_file)}
            return self

        def fetchone(self):
            return self.row

    class FakeDatabase:
        def __init__(self, path, init_mode):
            self.cursor = FakeCursor()

        def delete_vehicle_maintenance_photo(self, photo_id):
            return True

        def close(self):
            pass

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")

    with pytest.raises(LookupError):
        web_main.vehicle_maintenance_photo(1)
    web_main.vehicle_maintenance_delete_photo(1)
    assert external_file.exists()


def test_vehicle_photo_list_redacts_legacy_paths(monkeypatch, tmp_path):
    class FakeDatabase:
        def __init__(self, path, init_mode):
            pass

        def get_vehicle_maintenance_card(self, card_id):
            return ({"id": card_id}, [])

        def get_vehicle_maintenance_photos(self, card_id):
            return [{"id": 2, "photo_path": str(tmp_path / "legacy.png"), "photo_label": "Eski Parca"}]

        def close(self):
            pass

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "active_db_path", lambda: tmp_path / "tenant.db")

    assert web_main.vehicle_maintenance_photos(3) == [
        {"id": 2, "photo_label": "Eski Parca", "available": False}
    ]


def test_vehicle_photo_gallery_actions_exist_in_web_page():
    source = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert "data-maintenance-photos" in source
    assert 'vehicle-maintenance/photos/${encodeURIComponent(row.id)}' in source
    assert 'vehicle-maintenance/photo/add' in source
    assert 'vehicle-maintenance/photo/delete' in source


def test_vehicle_photo_api_routes_authenticate_and_scope_photo_fetch(monkeypatch):
    monkeypatch.setattr(web_main, "vehicle_maintenance_photos", lambda card_id: [{"id": card_id}])
    listing = object.__new__(web_main.AYECRequestHandler)
    listing.path = "/api/desktop/vehicle-maintenance/photos/9"
    listing.headers = {}
    listing.current_user = lambda: {"id": 1}
    list_responses = []
    listing.send_json = lambda payload, status=200: list_responses.append((payload, status))
    listing.do_GET()
    assert list_responses == [({"rows": [{"id": 9}]}, 200)]

    monkeypatch.setattr(web_main, "vehicle_maintenance_photo", lambda photo_id: (b"img", "image/png"))
    image = object.__new__(web_main.AYECRequestHandler)
    image.path = "/api/desktop/vehicle-maintenance/photo/17"
    image.headers = {}
    image.current_user = lambda: {"id": 1}
    image_responses = []
    image.send_bytes = lambda payload, mime, status=200, disposition=None: image_responses.append(
        (payload, mime, status)
    )
    image.do_GET()
    assert image_responses == [(b"img", "image/png", 200)]

    denied = object.__new__(web_main.AYECRequestHandler)
    denied.path = "/api/desktop/vehicle-maintenance/photos/9"
    denied.headers = {}
    denied.current_user = lambda: None
    errors = []
    denied.send_json = lambda payload, status=200: errors.append((payload, status))
    denied.do_GET()
    assert errors[0][1] == 401
    assert errors[0][0]["code"] == "AUTH_REQUIRED"
