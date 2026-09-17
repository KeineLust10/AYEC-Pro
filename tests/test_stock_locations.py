import sqlite3

import pytest

from src.db.mixins.stock_location_mixin import StockLocationMixin


class LocationDatabase(StockLocationMixin):
    def __init__(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(
            """
            CREATE TABLE parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                code TEXT,
                barcode TEXT,
                unit TEXT DEFAULT 'Adet',
                stock REAL DEFAULT 0,
                min_stock REAL DEFAULT 0,
                is_deleted INTEGER DEFAULT 0
            );
            CREATE TABLE stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_id INTEGER,
                movement_type TEXT,
                amount REAL,
                new_stock REAL,
                description TEXT,
                created_at TEXT
            );
            CREATE TABLE used_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT
            );
            """
        )

    def add_part(self, name="Kamera", stock=10.0, unit="Adet"):
        cursor = self.conn.execute(
            "INSERT INTO parts(name, stock, unit) VALUES (?, ?, ?)",
            (name, stock, unit),
        )
        self.conn.commit()
        return int(cursor.lastrowid)


@pytest.fixture
def location_db():
    database = LocationDatabase()
    yield database
    database.conn.close()


def balances(database, part_id):
    return {
        row["location_id"]: float(row["quantity"])
        for row in database.conn.execute(
            "SELECT location_id, quantity FROM stock_location_balances WHERE part_id=?",
            (part_id,),
        )
    }


def test_vehicle_transfer_preserves_total_stock(location_db):
    part_id = location_db.add_part(stock=10)
    location_db.ensure_stock_location_schema()
    main_id = location_db.get_stock_locations()[0]["id"]
    vehicle_id = location_db.create_stock_location(
        "Servis Araci 1", "vehicle", "34 ABC 123"
    )

    transfer_id, reference = location_db.transfer_stock(
        main_id,
        vehicle_id,
        [{"part_id": part_id, "quantity": 4, "unit": "Adet"}],
        "Arac yukleme",
    )

    assert transfer_id > 0
    assert reference.startswith("TRF-")
    assert balances(location_db, part_id) == {main_id: 6.0, vehicle_id: 4.0}
    assert location_db.conn.execute(
        "SELECT stock FROM parts WHERE id=?", (part_id,)
    ).fetchone()[0] == 10.0
    assert location_db.conn.execute(
        "SELECT COUNT(*) FROM stock_movements"
    ).fetchone()[0] == 0


def test_main_balance_sync_does_not_double_after_repeated_updates(location_db):
    part_id = location_db.add_part(stock=10)
    location_db.ensure_stock_location_schema()
    main_id = location_db.get_stock_locations()[0]["id"]
    vehicle_id = location_db.create_stock_location("Servis Araci", "vehicle")
    location_db.transfer_stock(
        main_id,
        vehicle_id,
        [{"part_id": part_id, "quantity": 3, "unit": "Adet"}],
    )

    location_db.conn.execute(
        "UPDATE parts SET stock=? WHERE id=?", (20.0, part_id)
    )
    location_db.apply_main_location_delta(part_id)
    location_db.apply_main_location_delta(part_id)

    current = balances(location_db, part_id)
    assert current == {main_id: 17.0, vehicle_id: 3.0}
    assert sum(current.values()) == 20.0


def test_vehicle_consumption_and_count_update_total(location_db):
    part_id = location_db.add_part(stock=10)
    location_db.ensure_stock_location_schema()
    main_id = location_db.get_stock_locations()[0]["id"]
    vehicle_id = location_db.create_stock_location("Servis Araci", "vehicle")
    location_db.transfer_stock(
        main_id,
        vehicle_id,
        [{"part_id": part_id, "quantity": 4, "unit": "Adet"}],
    )

    location_db.consume_location_stock(
        vehicle_id,
        [{"part_id": part_id, "quantity": 1}],
        source_type="service",
        source_id="SRV-1",
    )
    assert balances(location_db, part_id) == {main_id: 6.0, vehicle_id: 3.0}
    assert location_db.conn.execute(
        "SELECT stock FROM parts WHERE id=?", (part_id,)
    ).fetchone()[0] == 9.0

    location_db.save_stock_count(
        vehicle_id,
        [{"part_id": part_id, "counted_quantity": 2}],
        "Haftalik arac sayimi",
    )
    assert balances(location_db, part_id) == {main_id: 6.0, vehicle_id: 2.0}
    assert location_db.conn.execute(
        "SELECT stock FROM parts WHERE id=?", (part_id,)
    ).fetchone()[0] == 8.0


def test_insufficient_transfer_rolls_back(location_db):
    part_id = location_db.add_part(stock=2)
    location_db.ensure_stock_location_schema()
    main_id = location_db.get_stock_locations()[0]["id"]
    vehicle_id = location_db.create_stock_location("Servis Araci", "vehicle")

    with pytest.raises(ValueError, match="Yetersiz"):
        location_db.transfer_stock(
            main_id,
            vehicle_id,
            [{"part_id": part_id, "quantity": 3}],
        )

    assert balances(location_db, part_id) == {main_id: 2.0}


def test_stock_kit_round_trip(location_db):
    camera_id = location_db.add_part("Kamera", 8)
    switch_id = location_db.add_part("PoE Switch", 10)
    location_db.ensure_stock_location_schema()

    kit_id = location_db.save_stock_kit(
        "Sekizli Kamera Kiti",
        [
            {"part_id": camera_id, "quantity": 8},
            {"part_id": switch_id, "quantity": 1},
        ],
    )

    assert location_db.get_stock_kits() == [
        {"id": kit_id, "name": "Sekizli Kamera Kiti", "active": 1}
    ]
    lines = location_db.get_stock_kit_lines(kit_id)
    assert {(line["name"], line["quantity"]) for line in lines} == {
        ("Kamera", 8.0),
        ("PoE Switch", 1.0),
    }
