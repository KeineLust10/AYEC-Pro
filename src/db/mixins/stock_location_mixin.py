from datetime import datetime

from src.utils.logger import logger


class StockLocationMixin:
    """Location based inventory, transfers, counts and service consumption."""

    def ensure_stock_location_schema(self, commit=True):
        try:
            cur = self.conn.cursor()
            schema_statements = (
                """
                CREATE TABLE IF NOT EXISTS stock_locations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    location_type TEXT NOT NULL DEFAULT 'warehouse',
                    vehicle_plate TEXT,
                    personnel_id INTEGER,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stock_location_balances (
                    part_id INTEGER NOT NULL,
                    location_id INTEGER NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    reserved_quantity REAL NOT NULL DEFAULT 0,
                    min_quantity REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (part_id, location_id)
                );
                CREATE TABLE IF NOT EXISTS stock_transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    reference_no TEXT NOT NULL UNIQUE,
                    source_location_id INTEGER NOT NULL,
                    target_location_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'completed',
                    note TEXT,
                    source_type TEXT,
                    source_id INTEGER,
                    created_by TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stock_transfer_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transfer_id INTEGER NOT NULL,
                    part_id INTEGER NOT NULL,
                    quantity REAL NOT NULL,
                    unit TEXT,
                    serial_no TEXT
                );
                CREATE TABLE IF NOT EXISTS stock_counts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    location_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'completed',
                    note TEXT,
                    created_by TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stock_count_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    count_id INTEGER NOT NULL,
                    part_id INTEGER NOT NULL,
                    expected_quantity REAL NOT NULL,
                    counted_quantity REAL NOT NULL,
                    difference REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stock_kits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stock_kit_lines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kit_id INTEGER NOT NULL,
                    part_id INTEGER NOT NULL,
                    quantity REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_location_balance_location
                    ON stock_location_balances(location_id);
                CREATE INDEX IF NOT EXISTS idx_transfer_created
                    ON stock_transfers(created_at DESC);
                """,
            )
            # Do not use executescript here: sqlite3 implicitly commits an
            # active transaction before executescript(), which breaks the
            # stock/finance rollback boundary.
            for schema_sql in schema_statements:
                for statement in schema_sql.split(";"):
                    statement = statement.strip()
                    if statement:
                        cur.execute(statement)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                """
                INSERT OR IGNORE INTO stock_locations
                    (name, location_type, active, created_at)
                VALUES ('Ana Depo', 'main', 1, ?)
                """,
                (now,),
            )
            main_id = cur.execute(
                "SELECT id FROM stock_locations WHERE location_type='main' ORDER BY id LIMIT 1"
            ).fetchone()[0]
            used_parts_table = cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='used_parts'"
            ).fetchone()
            if used_parts_table:
                used_columns = {
                    row[1] for row in cur.execute("PRAGMA table_info(used_parts)").fetchall()
                }
                if "stock_location_id" not in used_columns:
                    cur.execute(
                        "ALTER TABLE used_parts ADD COLUMN stock_location_id INTEGER"
                    )
            cur.execute(
                """
                INSERT OR IGNORE INTO stock_location_balances
                    (part_id, location_id, quantity, updated_at)
                SELECT id, ?, COALESCE(stock, 0), ?
                FROM parts
                WHERE COALESCE(is_deleted, 0)=0
                """,
                (main_id, now),
            )
            if commit:
                self.conn.commit()
            return True
        except Exception as exc:
            logger.error(f"ensure_stock_location_schema error: {exc}")
            return False

    def get_stock_locations(self, active_only=True):
        self.ensure_stock_location_schema()
        sql = "SELECT id, name, location_type, vehicle_plate, personnel_id, active FROM stock_locations"
        if active_only:
            sql += " WHERE active=1"
        sql += " ORDER BY CASE location_type WHEN 'main' THEN 0 WHEN 'vehicle' THEN 1 ELSE 2 END, name"
        return [dict(row) for row in self.conn.execute(sql).fetchall()]

    def create_stock_location(self, name, location_type="warehouse", vehicle_plate=None, personnel_id=None):
        clean_name = str(name or "").strip()
        if not clean_name:
            raise ValueError("Konum adi zorunludur.")
        self.ensure_stock_location_schema()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.execute(
            """
            INSERT INTO stock_locations
                (name, location_type, vehicle_plate, personnel_id, active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
            """,
            (clean_name, str(location_type or "warehouse"), vehicle_plate, personnel_id, now),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def get_stock_kits(self, active_only=True):
        self.ensure_stock_location_schema()
        sql = "SELECT id, name, active FROM stock_kits"
        if active_only:
            sql += " WHERE active=1"
        sql += " ORDER BY name"
        return [dict(row) for row in self.conn.execute(sql).fetchall()]

    def get_stock_kit_lines(self, kit_id):
        self.ensure_stock_location_schema()
        rows = self.conn.execute(
            """
            SELECT l.part_id, p.name, COALESCE(p.unit, 'Adet') AS unit,
                   l.quantity
            FROM stock_kit_lines l
            JOIN parts p ON p.id=l.part_id
            WHERE l.kit_id=?
            ORDER BY p.name
            """,
            (int(kit_id),),
        ).fetchall()
        return [dict(row) for row in rows]

    def save_stock_kit(self, name, lines):
        clean_name = str(name or "").strip()
        valid_lines = [line for line in lines if float(line.get("quantity") or 0)>0]
        if not clean_name or not valid_lines:
            raise ValueError("Kit adi ve en az bir urun zorunludur.")
        self.ensure_stock_location_schema(commit=False)
        cur = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO stock_kits(name, active, created_at)
            VALUES (?, 1, ?)
            ON CONFLICT(name) DO UPDATE SET active=1
            """,
            (clean_name, now),
        )
        kit_id = cur.execute(
            "SELECT id FROM stock_kits WHERE name=?", (clean_name,)
        ).fetchone()[0]
        cur.execute("DELETE FROM stock_kit_lines WHERE kit_id=?", (kit_id,))
        cur.executemany(
            "INSERT INTO stock_kit_lines(kit_id, part_id, quantity) VALUES (?, ?, ?)",
            [
                (kit_id, int(line["part_id"]), float(line["quantity"]))
                for line in valid_lines
            ],
        )
        self.conn.commit()
        return int(kit_id)

    def get_location_inventory(self, location_id, search=""):
        self.ensure_stock_location_schema()
        params = [int(location_id)]
        search_sql = ""
        if str(search or "").strip():
            term = f"%{str(search).strip()}%"
            search_sql = " AND (p.name LIKE ? OR p.code LIKE ? OR p.barcode LIKE ?)"
            params.extend([term, term, term])
        rows = self.conn.execute(
            """
            SELECT p.id AS part_id, p.name, p.code, p.barcode,
                   COALESCE(p.unit, 'Adet') AS unit,
                   COALESCE(b.quantity, 0) AS quantity,
                   COALESCE(b.reserved_quantity, 0) AS reserved_quantity,
                   COALESCE(b.min_quantity, 0) AS min_quantity
            FROM parts p
            LEFT JOIN stock_location_balances b
              ON b.part_id=p.id AND b.location_id=?
            WHERE COALESCE(p.is_deleted, 0)=0
            """ + search_sql + " ORDER BY p.name",
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def _set_location_balance(self, cur, part_id, location_id, quantity, now):
        cur.execute(
            """
            INSERT INTO stock_location_balances(part_id, location_id, quantity, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(part_id, location_id) DO UPDATE SET
                quantity=excluded.quantity, updated_at=excluded.updated_at
            """,
            (int(part_id), int(location_id), float(quantity), now),
        )

    def apply_main_location_delta(self, part_id, quantity_delta=0, commit=True):
        """Synchronize the main balance with the authoritative part total."""
        if not part_id:
            return True
        self.ensure_stock_location_schema(commit=False)
        cur = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        main_row = cur.execute(
            "SELECT id FROM stock_locations WHERE location_type='main' ORDER BY id LIMIT 1"
        ).fetchone()
        if not main_row:
            return False
        main_id = int(main_row[0])
        total_row = cur.execute(
            "SELECT COALESCE(stock, 0) FROM parts WHERE id=?",
            (int(part_id),),
        ).fetchone()
        if not total_row:
            return False
        other_row = cur.execute(
            """
            SELECT COALESCE(SUM(quantity), 0)
            FROM stock_location_balances
            WHERE part_id=? AND location_id<>?
            """,
            (int(part_id), main_id),
        ).fetchone()
        total_stock = float(total_row[0] or 0)
        other_stock = float(other_row[0] or 0)
        self._set_location_balance(
            cur,
            part_id,
            main_id,
            max(0.0, total_stock - other_stock),
            now,
        )
        if commit:
            self.conn.commit()
        return True

    def apply_location_delta(self, part_id, location_id, quantity_delta, commit=True):
        """Apply a physical change to one non-aggregate location balance."""
        delta = float(quantity_delta or 0)
        if not part_id or not location_id or abs(delta) < 0.000001:
            return True
        self.ensure_stock_location_schema(commit=False)
        cur = self.conn.cursor()
        row = cur.execute(
            """
            SELECT COALESCE(quantity, 0)
            FROM stock_location_balances
            WHERE part_id=? AND location_id=?
            """,
            (int(part_id), int(location_id)),
        ).fetchone()
        current = float(row[0] if row else 0)
        new_quantity = current + delta
        if new_quantity < -0.000001:
            raise ValueError("Secilen konumda yeterli stok yok.")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._set_location_balance(
            cur,
            part_id,
            location_id,
            max(0.0, new_quantity),
            now,
        )
        if commit:
            self.conn.commit()
        return True

    def transfer_stock(self, source_location_id, target_location_id, lines, note="", created_by=""):
        source_id = int(source_location_id)
        target_id = int(target_location_id)
        if source_id == target_id:
            raise ValueError("Kaynak ve hedef konum ayni olamaz.")
        clean_lines = []
        for line in lines or []:
            part_id = int(line.get("part_id") or 0)
            quantity = float(line.get("quantity") or 0)
            if part_id > 0 and quantity > 0:
                clean_lines.append((part_id, quantity, str(line.get("unit") or "Adet")))
        if not clean_lines:
            raise ValueError("Transfer icin urun ve miktar girin.")
        self.ensure_stock_location_schema()
        cur = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        source_row = cur.execute(
            "SELECT name, vehicle_plate FROM stock_locations WHERE id=?", (source_id,)
        ).fetchone()
        target_row = cur.execute(
            "SELECT name, vehicle_plate FROM stock_locations WHERE id=?", (target_id,)
        ).fetchone()
        source_label = str(source_row[0] or source_id) if source_row else str(source_id)
        target_label = str(target_row[0] or target_id) if target_row else str(target_id)
        if source_row and source_row[1]:
            source_label += " ({})".format(source_row[1])
        if target_row and target_row[1]:
            target_label += " ({})".format(target_row[1])
        reference = datetime.now().strftime("TRF-%Y%m%d-%H%M%S-%f")
        try:
            cur.execute("BEGIN IMMEDIATE")
            for part_id, quantity, _unit in clean_lines:
                row = cur.execute(
                    "SELECT COALESCE(quantity, 0) FROM stock_location_balances WHERE part_id=? AND location_id=?",
                    (part_id, source_id),
                ).fetchone()
                available = float(row[0] if row else 0)
                if quantity > available + 0.000001:
                    name_row = cur.execute("SELECT name FROM parts WHERE id=?", (part_id,)).fetchone()
                    name = name_row[0] if name_row else str(part_id)
                    raise ValueError(f"Yetersiz konum stogu: {name} ({available:g})")
            header = cur.execute(
                """
                INSERT INTO stock_transfers
                    (reference_no, source_location_id, target_location_id, note, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (reference, source_id, target_id, str(note or ""), str(created_by or ""), now),
            )
            transfer_id = int(header.lastrowid)
            for part_id, quantity, unit in clean_lines:
                source_qty = float(cur.execute(
                    "SELECT quantity FROM stock_location_balances WHERE part_id=? AND location_id=?",
                    (part_id, source_id),
                ).fetchone()[0])
                target_row = cur.execute(
                    "SELECT quantity FROM stock_location_balances WHERE part_id=? AND location_id=?",
                    (part_id, target_id),
                ).fetchone()
                target_qty = float(target_row[0] if target_row else 0)
                self._set_location_balance(cur, part_id, source_id, source_qty - quantity, now)
                self._set_location_balance(cur, part_id, target_id, target_qty + quantity, now)
                cur.execute(
                    "INSERT INTO stock_transfer_lines(transfer_id, part_id, quantity, unit) VALUES (?, ?, ?, ?)",
                    (transfer_id, part_id, quantity, unit),
                )
            self.conn.commit()
            return transfer_id, reference
        except Exception:
            self.conn.rollback()
            raise

    def consume_location_stock(self, location_id, lines, source_type="service", source_id=None, created_by=""):
        location_id = int(location_id)
        self.ensure_stock_location_schema()
        cur = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            cur.execute("BEGIN IMMEDIATE")
            for line in lines or []:
                part_id = int(line.get("part_id") or 0)
                quantity = float(line.get("quantity") or 0)
                if part_id <= 0 or quantity <= 0:
                    continue
                row = cur.execute(
                    "SELECT quantity FROM stock_location_balances WHERE part_id=? AND location_id=?",
                    (part_id, location_id),
                ).fetchone()
                available = float(row[0] if row else 0)
                if quantity > available + 0.000001:
                    raise ValueError("Secilen konumda yeterli stok yok.")
                self._set_location_balance(cur, part_id, location_id, available - quantity, now)
                total = float(cur.execute("SELECT COALESCE(stock, 0) FROM parts WHERE id=?", (part_id,)).fetchone()[0])
                new_total = total - quantity
                cur.execute("UPDATE parts SET stock=? WHERE id=?", (new_total, part_id))
                cur.execute(
                    """
                    INSERT INTO stock_movements(part_id, movement_type, amount, new_stock, description, created_at)
                    VALUES (?, 'Cikis', ?, ?, ?, ?)
                    """,
                    (part_id, quantity, new_total, f"{source_type}:{source_id or ''} konum:{location_id}", now),
                )
            self.conn.commit()
            return True
        except Exception:
            self.conn.rollback()
            raise

    def save_stock_count(self, location_id, counted_lines, note="", created_by=""):
        self.ensure_stock_location_schema()
        location_id = int(location_id)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur = self.conn.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
            count_id = int(cur.execute(
                "INSERT INTO stock_counts(location_id, note, created_by, created_at) VALUES (?, ?, ?, ?)",
                (location_id, str(note or ""), str(created_by or ""), now),
            ).lastrowid)
            for line in counted_lines or []:
                part_id = int(line.get("part_id") or 0)
                counted = float(line.get("counted_quantity") or 0)
                row = cur.execute(
                    "SELECT quantity FROM stock_location_balances WHERE part_id=? AND location_id=?",
                    (part_id, location_id),
                ).fetchone()
                expected = float(row[0] if row else 0)
                difference = counted - expected
                self._set_location_balance(cur, part_id, location_id, counted, now)
                if hasattr(self, "reconcile_vehicle_count"):
                    self.reconcile_vehicle_count(location_id, part_id, difference)
                cur.execute(
                    """
                    INSERT INTO stock_count_lines
                        (count_id, part_id, expected_quantity, counted_quantity, difference)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (count_id, part_id, expected, counted, difference),
                )
            self._rebuild_part_totals(cur)
            self.conn.commit()
            return count_id
        except Exception:
            self.conn.rollback()
            raise

    def _rebuild_part_totals(self, cur=None):
        cur = cur or self.conn.cursor()
        cur.execute(
            """
            UPDATE parts SET stock=COALESCE((
                SELECT SUM(quantity) FROM stock_location_balances b WHERE b.part_id=parts.id
            ), 0)
            """
        )

    def get_stock_transfer_history(self, limit=250):
        self.ensure_stock_location_schema()
        rows = self.conn.execute(
            """
            SELECT t.id, t.reference_no,
                   s.name || CASE WHEN s.vehicle_plate IS NOT NULL AND s.vehicle_plate != ''
                                  THEN ' (' || s.vehicle_plate || ')' ELSE '' END AS source_name,
                   d.name || CASE WHEN d.vehicle_plate IS NOT NULL AND d.vehicle_plate != ''
                                  THEN ' (' || d.vehicle_plate || ')' ELSE '' END AS target_name,
                   t.note, t.created_by, t.created_at,
                   COUNT(l.id) AS line_count, COALESCE(SUM(l.quantity), 0) AS total_quantity,
                   GROUP_CONCAT(p.name, ', ') AS product_names
            FROM stock_transfers t
            JOIN stock_locations s ON s.id=t.source_location_id
            JOIN stock_locations d ON d.id=t.target_location_id
            LEFT JOIN stock_transfer_lines l ON l.transfer_id=t.id
            LEFT JOIN parts p ON p.id=l.part_id
            GROUP BY t.id ORDER BY t.id DESC LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
        return [dict(row) for row in rows]
