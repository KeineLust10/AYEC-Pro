import sqlite3

from Web_Arayuzu.Main import (
    load_web_service_sector_extensions,
    save_web_service_sector_extension,
)


def _connection():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("CREATE TABLE devices (id INTEGER PRIMARY KEY)")
    conn.executemany("INSERT INTO devices (id) VALUES (?)", [(1,), (2,)])
    return conn


def test_automotive_service_extension_saves_and_updates_only_allowed_fields():
    conn = _connection()

    save_web_service_sector_extension(
        conn,
        1,
        "otomotiv",
        {
            "vehicle_plate": "34 ABC 123",
            "vehicle_vin": "VIN-001",
            "current_km": 0,
            "service_type": "Periyodik Bakim",
            "device_type": "MUST-NOT-SAVE",
        },
    )
    row = conn.execute(
        "SELECT vehicle_plate,vehicle_vin,current_km,service_type "
        "FROM service_automotive_extension WHERE device_id=1"
    ).fetchone()
    assert row == ("34 ABC 123", "VIN-001", "0", "Periyodik Bakim")

    save_web_service_sector_extension(
        conn,
        1,
        "otomotiv",
        {"vehicle_plate": "34 ABC 123", "vehicle_vin": "VIN-001", "current_km": 45000, "service_type": "Motor Ariza"},
    )
    assert conn.execute(
        "SELECT current_km,service_type FROM service_automotive_extension WHERE device_id=1"
    ).fetchone() == ("45000", "Motor Ariza")
    assert conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='service_technical_service_extension'"
    ).fetchone()[0] == 0
    conn.close()


def test_technical_service_extension_is_isolated_and_loads_only_active_sector():
    conn = _connection()
    save_web_service_sector_extension(
        conn,
        1,
        "teknik_servis",
        {"device_type": "Laptop", "serial_no": "SERIAL-01", "warranty_status": "Garantili", "service_type": "DROP"},
    )
    save_web_service_sector_extension(
        conn,
        1,
        "otomotiv",
        {"vehicle_plate": "06 XYZ 456", "current_km": 12000, "service_type": "Fren Sistemi"},
    )

    assert load_web_service_sector_extensions(conn, [1, 2], "teknik_servis") == {
        1: {"device_type": "Laptop", "serial_no": "SERIAL-01", "warranty_status": "Garantili"}
    }
    assert load_web_service_sector_extensions(conn, [1, 2], "otomotiv") == {
        1: {"vehicle_plate": "06 XYZ 456", "vehicle_vin": "", "current_km": "12000", "service_type": "Fren Sistemi"}
    }
    assert load_web_service_sector_extensions(conn, [1], "unknown") == {}
    conn.close()

def test_automotive_service_extension_round_trips_through_tenant_api(tmp_path, monkeypatch):
    import json
    import sqlite3
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer

    import Web_Arayuzu.Main as web

    monkeypatch.setattr(web, "DB_PATH", tmp_path / "registry.sqlite")
    tenant_root = tmp_path / "tenants"
    tenant_root.mkdir()
    monkeypatch.setattr(web, "TENANT_ROOT", tenant_root)
    tenants = [
        web.create_tenant("Service Extension A", email="a@example.invalid"),
        web.create_tenant("Service Extension B", email="b@example.invalid"),
    ]
    sessions = []
    customer_ids = []
    service_ids = []
    for index, tenant in enumerate(tenants):
        with sqlite3.connect(web._tenant_path(tenant)) as conn:
            conn.execute(
                "INSERT INTO users(username,password,email,role,active,full_name) "
                "VALUES(?,?,?,?,1,?)",
                ("qa", web.password_hash("test-password"), f"{index}@example.invalid", "Admin", "QA User"),
            )
            sector = "otomotiv" if index == 0 else "teknik_servis"
            conn.execute(
                "INSERT INTO internal_settings(key,value) VALUES('current_sector',?)",
                (sector,),
            )
        sessions.append(web.create_session(1, False, "Extension API", "127.0.0.1", tenant["id"])[0])

    server = ThreadingHTTPServer(("127.0.0.1", 0), web.AYECRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        for index, (tenant, token) in enumerate(zip(tenants, sessions)):
            customer_request = urllib.request.Request(
                base_url + "/api/desktop/table/customers",
                data=json.dumps({"name": f"Tenant {index} Customer", "phone": "5550100000"}).encode("utf-8"),
                headers={"Content-Type": "application/json", "Cookie": f"{web.SESSION_COOKIE}={token}"},
                method="POST",
            )
            with urllib.request.urlopen(customer_request, timeout=10) as response:
                customer_id = json.loads(response.read())["id"]
            customer_ids.append(customer_id)
            request = urllib.request.Request(
                base_url + "/api/desktop/table/devices",
                data=json.dumps({
                    "tracking_no": f"QA-SERVICE-EXT-{index}",
                    "customer_id": customer_id,
                    "customer_name": f"Tenant {index} Customer",
                    "device_type": "Arac" if index == 0 else "Laptop",
                    "device_brand": "Toyota" if index == 0 else "Acer",
                    "device_model": "Corolla" if index == 0 else "Aspire",
                    "vehicle_plate": f"QA-{index}" if index == 0 else "",
                    "service_source": "Web Otomotiv" if index == 0 else "Web Teknik Servis",
                    "sector_extension": (
                        {
                            "vehicle_plate": f"QA-{index}",
                            "vehicle_vin": f"VIN-{index}",
                            "current_km": 50000 + index,
                            "service_type": "Motor Ariza",
                        }
                        if index == 0
                        else {
                            "device_type": "Laptop",
                            "serial_no": f"SERIAL-{index}",
                            "warranty_status": "Garantili",
                        }
                    ),
                }).encode("utf-8"),
                headers={"Content-Type": "application/json", "Cookie": f"{web.SESSION_COOKIE}={token}"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=10) as response:
                    assert response.status == 200
                    service_ids.append(json.loads(response.read())["id"])
            except urllib.error.HTTPError as error:
                raise AssertionError(error.read().decode("utf-8", errors="replace")) from error

        replacement_request = urllib.request.Request(
            base_url + "/api/desktop/table/customers",
            data=json.dumps({"name": "Replacement Customer", "phone": "5550100999"}).encode("utf-8"),
            headers={"Content-Type": "application/json", "Cookie": f"{web.SESSION_COOKIE}={sessions[0]}"},
            method="POST",
        )
        with urllib.request.urlopen(replacement_request, timeout=10) as response:
            replacement_customer_id = json.loads(response.read())["id"]

        update_request = urllib.request.Request(
            base_url + "/api/desktop/table/devices",
            data=json.dumps({
                "id": service_ids[0],
                "_action": "update",
                "customer_id": replacement_customer_id,
                "customer_name": "Replacement Customer",
                "device_brand": "Toyota",
                "device_model": "Corolla Cross",
                "serial_no": "ENGINE-0",
                "vehicle_plate": "QA-UPDATED",
                "vehicle_vin": "VIN-UPDATED",
                "sector_extension": {
                    "vehicle_plate": "QA-UPDATED",
                    "vehicle_vin": "VIN-UPDATED",
                    "current_km": 62000,
                    "service_type": "Fren Sistemi",
                },
            }).encode("utf-8"),
            headers={"Content-Type": "application/json", "Cookie": f"{web.SESSION_COOKIE}={sessions[0]}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(update_request, timeout=10) as response:
                assert response.status == 200
        except urllib.error.HTTPError as error:
            raise AssertionError(error.read().decode("utf-8", errors="replace")) from error

        request = urllib.request.Request(
            base_url + "/api/desktop/bootstrap",
            headers={"Cookie": f"{web.SESSION_COOKIE}={sessions[0]}"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read())
        customers = payload.get("customers", [])
        service = next(
            item
            for customer in customers
            for item in customer.get("services", [])
            if item.get("no") == "QA-SERVICE-EXT-0"
        )
        assert service["plate"] == "QA-UPDATED"
        assert service["serial"] == "ENGINE-0"
        assert service["sector_extension"] == {
            "vehicle_plate": "QA-UPDATED",
            "vehicle_vin": "VIN-UPDATED",
            "current_km": "62000",
            "service_type": "Fren Sistemi",
        }
        assert all(
            item.get("no") != "QA-SERVICE-EXT-1"
            for customer in customers
            for item in customer.get("services", [])
        )
        request = urllib.request.Request(
            base_url + "/api/desktop/bootstrap",
            headers={"Cookie": f"{web.SESSION_COOKIE}={sessions[1]}"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            second_payload = json.loads(response.read())
        second_customers = second_payload.get("customers", [])
        second_service = next(
            item
            for customer in second_customers
            for item in customer.get("services", [])
            if item.get("no") == "QA-SERVICE-EXT-1"
        )
        assert second_service["sector_extension"] == {
            "device_type": "Laptop",
            "serial_no": "SERIAL-1",
            "warranty_status": "Garantili",
        }
        assert all(
            item.get("no") != "QA-SERVICE-EXT-0"
            for customer in second_customers
            for item in customer.get("services", [])
        )
        with sqlite3.connect(web._tenant_path(tenants[0])) as conn:
            assert conn.execute(
                "SELECT vehicle_plate FROM service_automotive_extension"
            ).fetchone() == ("QA-UPDATED",)
            linked = conn.execute(
                "SELECT d.vehicle_maintenance_card_id,f.vehicle_id,f.customer_id,f.vehicle_plate,f.vehicle_vin,f.entry_odometer "
                "FROM devices d JOIN automotive_service_forms f ON f.device_id=d.id WHERE d.id=?",
                (service_ids[0],),
            ).fetchone()
            assert linked[0] and linked[1]
            assert linked[2:] == (replacement_customer_id, "QA-UPDATED", "VIN-UPDATED", 62000)
            vehicle = conn.execute(
                "SELECT customer_id,plate,brand,model,last_known_odometer FROM customer_vehicles WHERE id=?",
                (linked[1],),
            ).fetchone()
            assert vehicle == (replacement_customer_id, "QA-UPDATED", "Toyota", "Corolla Cross", 62000)
            card = conn.execute(
                "SELECT vehicle_id,customer_id,customer_name,customer_phone,vehicle_plate,vehicle_brand,vehicle_model,odometer "
                "FROM vehicle_maintenance_cards WHERE id=?",
                (linked[0],),
            ).fetchone()
            assert card == (
                linked[1], replacement_customer_id, "Replacement Customer", "5550100999",
                "QA-UPDATED", "Toyota", "Corolla Cross", 62000,
            )
        with sqlite3.connect(web._tenant_path(tenants[1])) as conn:
            assert conn.execute(
                "SELECT serial_no FROM service_technical_service_extension"
            ).fetchone() == ("SERIAL-1",)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        for token in sessions:
            web.delete_session(token)


