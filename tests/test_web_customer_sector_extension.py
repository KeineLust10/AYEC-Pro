import sqlite3

from Web_Arayuzu.Main import (
    load_web_customer_sector_extensions,
    save_web_customer_sector_extension,
)


def test_customer_sector_extension_saves_only_active_sector_fields():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO customers (id) VALUES (7)")

    save_web_customer_sector_extension(
        conn,
        7,
        "teknik_servis",
        {"device_type": "Laptop", "device_brand": "Fixture", "device_model": "Model A", "vehicle_plate": "SHOULD-NOT-SAVE"},
    )
    row = conn.execute(
        "SELECT device_type,device_brand,device_model FROM customer_technical_service_extension WHERE customer_id=7"
    ).fetchone()
    assert row == ("Laptop", "Fixture", "Model A")

    save_web_customer_sector_extension(
        conn,
        7,
        "teknik_servis",
        {"device_type": "Tablet", "device_brand": "Fixture", "device_model": "Model B"},
    )
    assert conn.execute(
        "SELECT device_type,device_model FROM customer_technical_service_extension WHERE customer_id=7"
    ).fetchone() == ("Tablet", "Model B")
    assert conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='customer_automotive_extension'"
    ).fetchone()[0] == 0
    conn.close()


def test_customer_sector_extension_persists_automotive_profile_fields():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY)")
    conn.execute("INSERT INTO customers (id) VALUES (9)")

    save_web_customer_sector_extension(
        conn,
        9,
        "otomotiv",
        {
            "vehicle_plate": "34 ABC 123",
            "vehicle_vin": "VIN-001",
            "vehicle_brand": "Fixture",
            "vehicle_model": "Model C",
            "vehicle_year": "2022",
            "vehicle_engine": "1.6",
        },
    )
    assert conn.execute(
        "SELECT vehicle_plate,vehicle_vin,vehicle_brand,vehicle_model,vehicle_year,vehicle_engine "
        "FROM customer_automotive_extension WHERE customer_id=9"
    ).fetchone() == ("34 ABC 123", "VIN-001", "Fixture", "Model C", "2022", "1.6")
    conn.close()


def test_customer_sector_extension_reads_only_the_active_sector():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE customers (id INTEGER PRIMARY KEY)")
    conn.executemany("INSERT INTO customers (id) VALUES (?)", [(11,), (12,)])
    save_web_customer_sector_extension(
        conn,
        11,
        "otomotiv",
        {"vehicle_plate": "34 ABC 123", "vehicle_brand": "Fixture"},
    )
    save_web_customer_sector_extension(
        conn,
        11,
        "teknik_servis",
        {"device_type": "Laptop", "device_brand": "Fixture"},
    )

    assert load_web_customer_sector_extensions(conn, [11, 12], "otomotiv") == {
        11: {
            "vehicle_plate": "34 ABC 123",
            "vehicle_vin": "",
            "vehicle_brand": "Fixture",
            "vehicle_model": "",
            "vehicle_year": "",
            "vehicle_engine": "",
        }
    }
    assert load_web_customer_sector_extensions(conn, [11], "teknik_servis") == {
        11: {"device_type": "Laptop", "device_brand": "Fixture", "device_model": ""}
    }
    assert load_web_customer_sector_extensions(conn, [11], "unknown") == {}
    conn.close()


def test_customer_reverse_geocode_normalizes_address_fields(monkeypatch):
    import json

    from Web_Arayuzu import Main as web_main

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "display_name": "10 Test Street, Istanbul",
                "address": {
                    "state": "Istanbul",
                    "county": "Kadikoy",
                    "neighbourhood": "Moda",
                    "road": "Test Street",
                    "house_number": "10",
                    "postcode": "34710",
                },
            }).encode()

    captured = {}

    def fake_urlopen(request, timeout=0):
        captured["url"] = request.full_url
        captured["agent"] = request.get_header("User-agent")
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(web_main, "_FIELD_GEOCODE_NEXT_AT", 0.0)
    monkeypatch.setattr(web_main.time, "sleep", lambda _delay: None)
    monkeypatch.setattr(web_main, "urlopen", fake_urlopen)
    result = web_main.desktop_customer_reverse_geocode(41.0, 29.0)

    assert result == {
        "display_name": "10 Test Street, Istanbul",
        "city": "Istanbul",
        "district": "Kadikoy",
        "neighborhood": "Moda",
        "street": "Test Street 10",
        "zip_code": "34710",
    }
    assert "/reverse?" in captured["url"]
    assert captured["agent"] == "AYEC-Pro/2.0"
    assert captured["timeout"] == 6

