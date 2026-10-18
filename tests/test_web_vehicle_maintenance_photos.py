import base64
import binascii
import os
import sqlite3
import struct
import subprocess
import threading
import zlib
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import requests

import src.database as database_module
from Web_Arayuzu import Main as web_main
from tests.test_vendor_management_center import _setup_tenant


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


def test_vehicle_photo_list_migrates_legacy_app_assets_into_tenant_storage(monkeypatch, tmp_path):
    project_root = tmp_path / "app"
    legacy_root = project_root / "assets" / "maintenance_photos"
    legacy_root.mkdir(parents=True)
    legacy_photo = legacy_root / "maintenance_9_1.png"
    legacy_bytes = b"\x89PNG\r\n\x1a\nlegacy photo"
    legacy_photo.write_bytes(legacy_bytes)
    tenant_path = tmp_path / "tenant.db"
    photo_row = {"id": 19, "card_id": 9, "photo_path": str(legacy_photo), "photo_label": "Old part"}
    commits = []

    class FakeCursor:
        rowcount = 0
        result = None

        def execute(self, query, args):
            if query.startswith("UPDATE vehicle_maintenance_photos"):
                self.rowcount = 1
                photo_row["photo_path"] = args[0]
            else:
                self.result = {"photo_path": photo_row["photo_path"]}
            return self

        def fetchone(self):
            return self.result

    class FakeConnection:
        def commit(self):
            commits.append(True)

    class FakeDatabase:
        cursor = FakeCursor()
        conn = FakeConnection()

        def __init__(self, path, init_mode):
            assert Path(path) == tenant_path

        def get_vehicle_maintenance_card(self, card_id):
            return ({"id": card_id}, [])

        def get_vehicle_maintenance_photos(self, card_id):
            return [photo_row]

        def close(self):
            pass

    monkeypatch.setattr(database_module, "Database", FakeDatabase)
    monkeypatch.setattr(web_main, "ROOT", project_root / "Web_Arayuzu")
    monkeypatch.setattr(web_main, "active_db_path", lambda: tenant_path)

    photos = web_main.vehicle_maintenance_photos(9)

    assert photos == [{"id": 19, "card_id": 9, "photo_label": "Old part", "available": True}]
    migrated_path = Path(photo_row["photo_path"])
    assert migrated_path.parent == tmp_path / "maintenance_photos"
    assert migrated_path.read_bytes() == legacy_bytes
    assert legacy_photo.read_bytes() == legacy_bytes
    assert commits == [True]
    assert web_main.vehicle_maintenance_photo(19) == (legacy_bytes, "image/png")


def test_vehicle_photo_gallery_actions_exist_in_web_page():
    source = (Path(__file__).resolve().parents[1] / "Web_Arayuzu" / "web" / "app.js").read_text(encoding="utf-8")
    assert "data-maintenance-photos" in source
    assert 'vehicle-maintenance/photos/${encodeURIComponent(row.id)}' in source
    assert 'vehicle-maintenance/photo/add' in source
    assert 'vehicle-maintenance/photo/delete' in source
    assert 'Bu eski foto\\u011fraf uygulama klas\\u00f6r\\u00fcnde bulunamad\\u0131 veya desteklenmiyor.' in source


def test_hidden_edge_serves_migrated_legacy_vehicle_photo_from_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    app_root = tmp_path / "application"
    legacy_root = app_root / "assets" / "maintenance_photos"
    legacy_root.mkdir(parents=True)
    monkeypatch.setattr(web_main, "ROOT", app_root / "Web_Arayuzu")

    def chunk(kind, payload):
        value = kind + payload
        return struct.pack(">I", len(payload)) + value + struct.pack(">I", binascii.crc32(value) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff")) + chunk(b"IEND", b"")
    legacy_photo = legacy_root / "maintenance_9_1.png"
    legacy_photo.write_bytes(png)
    with sqlite3.connect(tenant_path) as conn:
        conn.execute(
            "INSERT INTO vehicle_maintenance_cards(id,vehicle_plate) VALUES(9,'ABC-123')"
        )
        conn.execute(
            "INSERT INTO vehicle_maintenance_photos(card_id,photo_path,photo_label) VALUES(9,?,'Oil Filter')",
            (str(legacy_photo),),
        )

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "customer-admin", "password": "oldpass123", "tenant_id": "tenant-1"},
        )
        assert login.status_code == 200
        env = os.environ.copy()
        env["AYEC_AUDIT_URL"] = f"{base_url}/"
        env["AYEC_MAINTENANCE_SESSION_COOKIE"] = session.cookies.get("ayec_session")
        env["AYEC_AUDIT_CDP_PORT"] = "9266"
        audit = subprocess.run(
            ["node", "tools/quality/maintenance_photo_legacy_offscreen.cjs"],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
        assert audit.returncode == 0, audit.stderr or audit.stdout
        assert '"loaded":true' in audit.stdout
        assert '"counter":"1 / 1"' in audit.stdout
        with sqlite3.connect(tenant_path) as conn:
            migrated_path = Path(conn.execute(
                "SELECT photo_path FROM vehicle_maintenance_photos WHERE id=1"
            ).fetchone()[0])
        assert migrated_path.parent == tenant_path.parent / "maintenance_photos"
        assert migrated_path.read_bytes() == png
        assert legacy_photo.read_bytes() == png
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


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
