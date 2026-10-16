import sqlite3
import threading
import json
from http.server import ThreadingHTTPServer
from pathlib import Path

import requests

import Web_Arayuzu.Main as web_main
from tests.test_vendor_management_center import _setup_tenant


def test_field_service_map_renders_all_located_personnel_markers():
    root = Path(__file__).resolve().parents[1]
    script = (root / "Web_Arayuzu/web/field-service-parity.js").read_text(encoding="utf-8")
    page = (root / "Web_Arayuzu/web/index.html").read_text(encoding="utf-8")
    assert "personnelMarkers = new Map()" in script
    assert "L.marker([point.lat, point.lng]" in script
    assert "fieldMap.fitBounds(bounds" in script
    assert "data-field-route-optimize" in script
    assert "window.L.polyline" in script
    assert "/api/desktop/field-service/geocode" in script
    assert "/api/desktop/field-service/route" in script
    assert "/api/desktop/field-service/traffic/{z}/{x}/{y}" in script
    assert "data-field-traffic-toggle" in script
    assert "/api/desktop/field-service/location" in script
    assert "navigator.geolocation.watchPosition" in script
    assert "data-field-vector-toggle" in script
    assert "field-vector-map-dist/index.html" in script
    assert "/api/desktop/field-service/vector-resource" in (root / "src/ui/widgets/tomtom_vector_map/web/src/main.js").read_text(encoding="utf-8")
    assert "fieldLocationResults" in script
    assert "field-service-parity.js" in page


def test_field_service_geocoder_falls_back_to_photon(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(self.payload).encode("utf-8")

    responses = [
        FakeResponse([]),
        FakeResponse({"features": [
            {"properties": {"name": "Center", "city": "Balikesir"},
             "geometry": {"coordinates": [27.8826, 39.6484]}},
            {"properties": {"name": "Invalid"},
             "geometry": {"coordinates": [300, 95]}},
        ]}),
    ]

    def fake_urlopen(request, timeout=0):
        assert timeout == 6
        assert request.get_header("User-agent") == "AYEC-Pro/2.0"
        return responses.pop(0)

    monkeypatch.setattr(web_main, "_FIELD_GEOCODE_NEXT_AT", 0.0)
    monkeypatch.setattr(web_main.time, "sleep", lambda _delay: None)
    monkeypatch.setattr(web_main, "urlopen", fake_urlopen)
    result = web_main.desktop_field_service_geocode("Balikesir")
    assert result["results"] == [{
        "display_name": "Center, Balikesir",
        "lat": 39.6484,
        "lon": 27.8826,
    }]
    assert responses == []


def test_field_service_road_route_uses_stored_key_and_normalizes_geometry(monkeypatch):
    import src.utils.local_secret_store as secret_store

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({"routes": [{
                "legs": [{"points": [
                    {"latitude": 39.6, "longitude": 27.8},
                    {"latitude": 39.7, "longitude": 27.9},
                ]}],
                "summary": {"lengthInMeters": 12345, "travelTimeInSeconds": 2345},
            }]}).encode("utf-8")

    seen = {}

    def fake_urlopen(request, timeout=0):
        seen["url"] = request.full_url
        seen["headers"] = request.headers
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(secret_store, "load_secret", lambda name: "server-secret" if name == "tomtom_traffic_api_key" else "")
    monkeypatch.setattr(web_main, "urlopen", fake_urlopen)
    result = web_main.desktop_field_service_road_route([
        {"lat": 39.6, "lng": 27.8},
        {"lat": 39.7, "lng": 27.9},
    ])
    assert result == {
        "ok": True,
        "geometry": [[39.6, 27.8], [39.7, 27.9]],
        "distance_meters": 12345,
        "duration_seconds": 2345,
    }
    assert "key=server-secret" in seen["url"]
    assert seen["timeout"] == 12
    assert "server-secret" not in json.dumps(result)
    assert "traffic=live" in seen["url"]


def test_field_service_traffic_proxy_uses_stored_key_and_validates_tile(monkeypatch):
    import src.utils.local_secret_store as secret_store

    png = b"\x89PNG\r\n\x1a\nmock-tile"
    seen = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return png

    def fake_urlopen(request, timeout=0):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(secret_store, "load_secret", lambda _name: "server-secret")
    monkeypatch.setattr(web_main, "urlopen", fake_urlopen)
    assert web_main.desktop_field_service_traffic_tile("12", "2310", "1400") == png
    assert "/traffic/tile/flow/12/2310/1400.png" in seen["url"]
    assert "key=server-secret" in seen["url"]
    assert seen["timeout"] == 12
    assert b"server-secret" not in png
    try:
        web_main.desktop_field_service_traffic_tile(3, 8, 0)
    except ValueError:
        pass
    else:
        raise AssertionError("Out-of-range tile coordinates must be rejected")


def test_field_service_vector_resource_proxy_keeps_key_server_side(monkeypatch):
    import src.utils.local_secret_store as secret_store

    payload = b"mock-vector-tile"
    seen = {}

    class FakeHeaders:
        def get(self, name, default=""):
            return seen.get("content_type", "application/vnd.mapbox-vector-tile") if name == "Content-Type" else default

    class FakeResponse:
        headers = FakeHeaders()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, limit):
            seen["limit"] = limit
            return payload

    def fake_urlopen(request, timeout=0):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(secret_store, "load_secret", lambda _name: "server-secret")
    monkeypatch.setattr(web_main, "urlopen", fake_urlopen)
    result = web_main.desktop_field_service_vector_resource(
        "https://api.tomtom.com/maps/orbis/map/1/style?key=browser-placeholder&language=tr-TR"
    )
    assert result == (payload, "application/vnd.mapbox-vector-tile")
    assert "key=server-secret" in seen["url"]
    assert "browser-placeholder" not in seen["url"]
    assert seen["timeout"] == 15
    assert seen["limit"] == 5 * 1024 * 1024 + 1
    assert "server-secret" not in payload.decode("ascii")

    seen["content_type"] = "image/pbf"
    assert web_main.desktop_field_service_vector_resource(
        "https://api.tomtom.com/maps/orbis/map-display/tile/16/1/1.pbf?apiVersion=1"
    ) == (payload, "image/pbf")

    for target in (
        "http://api.tomtom.com/maps/orbis/map/style",
        "https://evil.example/maps/orbis/map/style",
        "https://api.tomtom.com/maps/orbis/%2e%2e/secret",
        "https://api.tomtom.com.evil.example/maps/orbis/map/style",
    ):
        try:
            web_main.desktop_field_service_vector_resource(target)
        except ValueError:
            pass
        else:
            raise AssertionError("Unsafe vector resource URLs must be rejected")


def test_field_service_personnel_and_finish_duty_use_active_tenant(monkeypatch, tmp_path):
    _actor, tenant_path = _setup_tenant(monkeypatch, tmp_path)
    with sqlite3.connect(tenant_path) as connection:
        connection.execute("DROP TABLE IF EXISTS personnel")
        connection.execute(
            "CREATE TABLE personnel (id INTEGER PRIMARY KEY,name TEXT,role TEXT,lat REAL,lng REAL,"
            "status TEXT,last_seen TEXT,username TEXT,is_active INTEGER DEFAULT 1,is_deleted INTEGER DEFAULT 0)"
        )
        user_columns = {row[1] for row in connection.execute('PRAGMA table_info("users")')}
        if "personnel_id" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN personnel_id INTEGER")
        connection.execute("UPDATE users SET personnel_id=93001 WHERE id=2")
        connection.executemany(
            "INSERT INTO personnel(id,name,role,lat,lng,status,last_seen,is_active,is_deleted) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            [
                (93001, "Field Tech", "Teknisyen", 39.6484, 27.8826, "G\u00f6revde", "10:15", 1, 0),
                (93002, "Office Staff", "Muhasebe", None, None, "Bo\u015fta", "", 1, 0),
                (93003, "Inactive Tech", "Teknisyen", 39.0, 27.0, "G\u00f6revde", "", 0, 0),
                (93004, "Deleted Tech", "Teknisyen", 39.0, 27.0, "G\u00f6revde", "", 1, 1),
            ],
        )
    second_tenant_path = web_main.TENANT_ROOT / "Second Company.db"
    with sqlite3.connect(second_tenant_path) as connection:
        connection.execute(
            "CREATE TABLE personnel (id INTEGER PRIMARY KEY,name TEXT,role TEXT,lat REAL,lng REAL,"
            "status TEXT,last_seen TEXT,is_active INTEGER,is_deleted INTEGER)"
        )
        connection.execute(
            "INSERT INTO personnel VALUES(93001,'Other Tenant Tech','Teknisyen',38.0,26.0,'Bo\u015fta','',1,0)"
        )
    registry = web_main.registry_connect()
    registry.execute(
        "INSERT INTO tenants(id,company_name,db_filename,created_at,active) VALUES(?,?,?,?,1)",
        ("tenant-2", "Second Company", second_tenant_path.name, "2026-01-01T00:00:00"),
    )
    registry.commit()
    registry.close()

    server = ThreadingHTTPServer(("127.0.0.1", 0), web_main.AYECRequestHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    personnel_url = base_url + "/api/desktop/field-service/personnel"
    finish_url = base_url + "/api/desktop/field-service/finish"
    assign_url = base_url + "/api/desktop/field-service/assign"
    location_url = base_url + "/api/desktop/field-service/location"
    geocode_url = base_url + "/api/desktop/field-service/geocode"
    reverse_geocode_url = base_url + "/api/desktop/field-service/reverse-geocode"
    route_url = base_url + "/api/desktop/field-service/route"
    traffic_url = base_url + "/api/desktop/field-service/traffic/12/2310/1400"
    vector_url = base_url + "/api/desktop/field-service/vector-resource/maps/orbis/style?language=tr-TR"
    try:
        assert requests.get(personnel_url).status_code == 401
        assert requests.post(finish_url, json={"id": 93001}).status_code == 401
        assert requests.post(assign_url, json={"id": 93001, "lat": 39.67, "lng": 27.90}).status_code == 401
        assert requests.post(location_url, json={"lat": 39.65, "lng": 27.88}).status_code == 401
        assert requests.post(geocode_url, json={"query": "Balikesir"}).status_code == 401
        assert requests.post(reverse_geocode_url, json={"lat": 39.65, "lon": 27.88}).status_code == 401
        assert requests.post(route_url, json={"points": []}).status_code == 401
        assert requests.get(traffic_url).status_code == 401
        assert requests.get(vector_url).status_code == 401
        session = requests.Session()
        session.headers["Origin"] = base_url
        login = session.post(
            base_url + "/api/auth/login",
            json={
                "identifier": web_main.VENDOR_EMAIL,
                "password": "operator-test-pass",
                "tenant_id": "tenant-1",
            },
        )
        assert login.status_code == 200
        vector_page = session.get(base_url + "/field-vector-map-dist/index.html")
        assert vector_page.status_code == 200
        assert "qrc:///qtwebchannel/qwebchannel.js" not in vector_page.text
        assert "./assets/index-" in vector_page.text
        vector_target = {}

        def fake_vector_resource(target_url):
            vector_target["url"] = target_url
            return b"map-resource", "application/json"

        monkeypatch.setattr(web_main, "desktop_field_service_vector_resource", fake_vector_resource)
        vector_response = session.get(vector_url)
        assert vector_response.status_code == 200
        assert vector_response.headers["Content-Type"] == "application/json"
        assert vector_response.content == b"map-resource"
        assert vector_target["url"] == "https://api.tomtom.com/maps/orbis/style?language=tr-TR"
        with sqlite3.connect(tenant_path) as connection:
            connection.execute("UPDATE personnel SET username=? WHERE id=93001", ("vendor-operator",))
            connection.commit()
        initial_data = session.get(personnel_url).json()
        assert initial_data["can_share_location"] is True
        location = session.post(location_url, json={"lat": 39.66, "lng": 27.89})
        assert location.status_code == 200, location.text
        assert location.json()["personnel_id"] == 93001
        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                return json.dumps([{
                    "display_name": "Balikesir, Turkey",
                    "lat": "39.6484",
                    "lon": "27.8826",
                }]).encode("utf-8")

        monkeypatch.setattr(web_main, "_FIELD_GEOCODE_NEXT_AT", 0.0)
        monkeypatch.setattr(web_main, "urlopen", lambda _request, timeout=0: FakeResponse())
        geocoded = session.post(geocode_url, json={"query": "Balikesir"})
        assert geocoded.status_code == 200, geocoded.text
        assert geocoded.json()["results"] == [{
            "display_name": "Balikesir, Turkey",
            "lat": 39.6484,
            "lon": 27.8826,
        }]
        assert session.post(geocode_url, json={"query": " "}).status_code == 400
        monkeypatch.setattr(
            web_main,
            "desktop_field_service_road_route",
            lambda points: {"ok": True, "count": len(points)},
        )
        routed = session.post(route_url, json={"points": [{"lat": 39.6, "lng": 27.8}]})
        assert routed.status_code == 200
        assert routed.json() == {"ok": True, "count": 1}
        tile_bytes = b"\x89PNG\r\n\x1a\nmock-tile"
        monkeypatch.setattr(web_main, "desktop_field_service_traffic_tile", lambda *_args: tile_bytes)
        tile_response = session.get(traffic_url)
        assert tile_response.status_code == 200
        assert tile_response.headers["Content-Type"] == "image/png"
        assert tile_response.content == tile_bytes
        data = session.get(personnel_url).json()
        assert [person["id"] for person in data["personnel"]] == [93001]
        assert data["personnel"][0]["lat"] == 39.66
        assert data["personnel"][0]["lng"] == 27.89
        assert data["personnel"][0]["last_seen"]
        assert data["personnel"][0]["status"] == "G\u00f6revde"
        assigned = session.post(assign_url, json={"id": 93001, "lat": 39.67, "lng": 27.90})
        assert assigned.status_code == 200, assigned.text
        assert assigned.json()["personnel_id"] == 93001
        assert session.post(assign_url, json={"id": 93002, "lat": 39.67, "lng": 27.90}).status_code == 404
        assert session.post(assign_url, json={"id": 93001, "lat": 91, "lng": 27.90}).status_code == 400
        with sqlite3.connect(tenant_path) as connection:
            assert connection.execute(
                "SELECT lat,lng,status FROM personnel WHERE id=93001"
            ).fetchone()[:3] == (39.67, 27.90, "G\u00f6revde")
        with sqlite3.connect(second_tenant_path) as connection:
            assert connection.execute(
                "SELECT lat,lng,status FROM personnel WHERE id=93001"
            ).fetchone() == (38.0, 26.0, "Bo\u015fta")
        result = session.post(finish_url, json={"id": 93001})
        assert result.status_code == 200, result.text
        assert result.json()["personnel"]["status"] == "Bo\u015fta"
        with sqlite3.connect(tenant_path) as connection:
            assert connection.execute(
                "SELECT status FROM personnel WHERE id=93001"
            ).fetchone()[0] == "Bo\u015fta"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)
