# -*- coding: utf-8 -*-

"""
Appointments Mixin
Randevu yönetimi ile ilgili database metodları
"""

from datetime import datetime, timedelta
from src.utils.logger import logger


class AppointmentsMixin:
    """Randevular için database metodları"""

    def _safe_identifier(self, value):
        value = str(value or "").strip()
        if not value or not value.replace("_", "").isalnum():
            raise ValueError(f"Unsafe SQL identifier: {value!r}")
        return value

    def ensure_appointment_workflow_schema(self):
        """Add planning and offer-link columns without changing existing appointments."""
        self.cursor.execute("PRAGMA table_info(appointments)")
        columns = {row[1] for row in (self.cursor.fetchall() or [])}
        additions = [
            ("customer_id", "INTEGER"),
            ("workflow", "TEXT"),
            ("offer_id", "INTEGER"),
            ("offer_no", "TEXT"),
            ("completed_at", "TEXT"),
        ]
        for name, definition in additions:
            if name not in columns:
                self.cursor.execute(
                    "ALTER TABLE appointments ADD COLUMN {} {}".format(name, definition)
                )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_appointments_workflow_plan "
            "ON appointments (workflow, date, status)"
        )
        self.conn.commit()

    def ensure_appointment_montage_schema(self):
        self.ensure_appointment_workflow_schema()
        self.cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS appointment_plan_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_id INTEGER NOT NULL,
                offer_item_id INTEGER,
                part_id INTEGER,
                item_type TEXT,
                item_role TEXT NOT NULL DEFAULT 'service',
                name TEXT NOT NULL,
                brand TEXT,
                unit TEXT,
                planned_qty REAL NOT NULL DEFAULT 0,
                loaded_qty REAL NOT NULL DEFAULT 0,
                used_qty REAL NOT NULL DEFAULT 0,
                returned_qty REAL NOT NULL DEFAULT 0,
                unit_price REAL NOT NULL DEFAULT 0,
                line_total REAL NOT NULL DEFAULT 0,
                source_location_id INTEGER,
                vehicle_location_id INTEGER,
                payload_json TEXT,
                status TEXT NOT NULL DEFAULT 'planned',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_appointment_plan_appointment
                ON appointment_plan_items(appointment_id, item_role, status);
            """
        )
        self.conn.commit()

    @staticmethod
    def _appointment_plan_role(item_type, part_id):
        # A linked stock card is authoritative even when legacy offer rows
        # contain a service-like item_type value.
        if part_id:
            return "material"
        normalized = str(item_type or "").strip().casefold()
        if normalized in ("service", "hizmet"):
            return "service"
        return "manual_material"

    def create_appointment_offer_plan(self, appointment_id, offer_id, replace=False):
        self.ensure_appointment_montage_schema()
        appointment_id = int(appointment_id)
        offer_id = int(offer_id)
        existing = self.cursor.execute(
            "SELECT COUNT(*) FROM appointment_plan_items WHERE appointment_id=?",
            (appointment_id,),
        ).fetchone()[0]
        if existing and not replace:
            return int(existing)
        if replace:
            self.cursor.execute(
                "DELETE FROM appointment_plan_items WHERE appointment_id=?",
                (appointment_id,),
            )
        if hasattr(self, "get_offer_items_detailed"):
            offer_items = self.get_offer_items_detailed(offer_id)
        else:
            offer_items = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for row in offer_items:
            (
                offer_item_id, _offer_id, part_id, item_type, service, description,
                brand, qty, unit_price, line_total, payload_json,
            ) = row
            name = str(description or service or "Plan item")
            role = self._appointment_plan_role(item_type, part_id)
            unit = "Adet"
            if part_id:
                part_row = self.cursor.execute(
                    "SELECT COALESCE(unit, 'Adet') FROM parts WHERE id=?", (part_id,)
                ).fetchone()
                if part_row and part_row[0]:
                    unit = str(part_row[0])
            self.cursor.execute(
                """
                INSERT INTO appointment_plan_items (
                    appointment_id, offer_item_id, part_id, item_type, item_role,
                    name, brand, unit, planned_qty, unit_price, line_total,
                    payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    appointment_id, offer_item_id, part_id, item_type, role,
                    name, brand, unit, float(qty or 0), float(unit_price or 0),
                    float(line_total or 0), payload_json, now, now,
                ),
            )
        self.conn.commit()
        return int(len(offer_items))

    def get_appointment_offer_plan(self, appointment_id):
        self.ensure_appointment_montage_schema()
        rows = self.cursor.execute(
            """
            SELECT id, appointment_id, offer_item_id, part_id, item_type, item_role,
                   name, brand, unit, planned_qty, loaded_qty, used_qty, returned_qty,
                   unit_price, line_total, source_location_id, vehicle_location_id,
                   status
            FROM appointment_plan_items
            WHERE appointment_id=?
            ORDER BY CASE item_role WHEN 'material' THEN 0 WHEN 'manual_material' THEN 1 ELSE 2 END, id
            """,
            (int(appointment_id),),
        ).fetchall()
        keys = (
            "id", "appointment_id", "offer_item_id", "part_id", "item_type", "item_role",
            "name", "brand", "unit", "planned_qty", "loaded_qty", "used_qty", "returned_qty",
            "unit_price", "line_total", "source_location_id", "vehicle_location_id", "status",
        )
        return [dict(zip(keys, row)) for row in rows]

    def load_appointment_offer_plan(self, appointment_id, source_location_id, vehicle_location_id, lines):
        self.ensure_appointment_montage_schema()
        appointment_id = int(appointment_id)
        source_location_id = int(source_location_id)
        vehicle_location_id = int(vehicle_location_id)
        plan_by_id = {row["id"]: row for row in self.get_appointment_offer_plan(appointment_id)}
        transfer_lines = []
        updates = []
        for line in lines or []:
            plan_id = int(line.get("plan_id") or 0)
            quantity = float(line.get("quantity") or 0)
            plan = plan_by_id.get(plan_id)
            if not plan or plan.get("item_role") != "material" or quantity <= 0:
                continue
            remaining = float(plan["planned_qty"] or 0) - float(plan["loaded_qty"] or 0)
            if quantity > remaining + 0.000001:
                raise ValueError("Planlanan miktardan fazla yükleme yapılamaz.")
            transfer_lines.append({"part_id": plan["part_id"], "quantity": quantity, "unit": plan["unit"]})
            updates.append((quantity, source_location_id, vehicle_location_id, plan_id))
        if not transfer_lines:
            raise ValueError(
                "Araca yüklemek için en az bir malzeme miktarı girilmelidir."
            )
        if not hasattr(self, "transfer_stock"):
            raise RuntimeError("Stok transfer servisi kullanılamıyor.")
        target_location = self.cursor.execute(
            "SELECT name, vehicle_plate FROM stock_locations WHERE id=?",
            (vehicle_location_id,),
        ).fetchone()
        vehicle_label = str(target_location[0] or "Ara\u00e7") if target_location else "Ara\u00e7"
        if target_location and target_location[1]:
            vehicle_label += " ({})".format(target_location[1])
        transfer_note = "Randevu araca yukleme {} - {}".format(appointment_id, vehicle_label)
        _transfer_id, reference = self.transfer_stock(
            source_location_id,
            vehicle_location_id,
            transfer_lines,
            note=transfer_note,
        )
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for quantity, source_id, vehicle_id, plan_id in updates:
            self.cursor.execute(
                """
                UPDATE appointment_plan_items
                SET loaded_qty=loaded_qty+?, source_location_id=?, vehicle_location_id=?,
                    status='loaded', updated_at=?
                WHERE id=?
                """,
                (quantity, source_id, vehicle_id, now, plan_id),
            )
        self.cursor.execute(
            "UPDATE appointments SET status='Araca Yuklendi' WHERE id=?",
            (appointment_id,),
        )
        self.conn.commit()
        return reference

    def complete_appointment_offer_plan(self, appointment_id, lines):
        self.ensure_appointment_montage_schema()
        appointment_id = int(appointment_id)
        plan_by_id = {row["id"]: row for row in self.get_appointment_offer_plan(appointment_id)}
        consume_by_vehicle = {}
        return_by_route = {}
        updates = []
        for line in lines or []:
            plan_id = int(line.get("plan_id") or 0)
            used_qty = float(line.get("used_qty") or 0)
            plan = plan_by_id.get(plan_id)
            if not plan or plan.get("item_role") != "material":
                continue
            loaded_qty = float(plan["loaded_qty"] or 0)
            if used_qty < 0 or used_qty > loaded_qty + 0.000001:
                raise ValueError("Used quantity must be between zero and loaded quantity.")
            returned_qty = max(0.0, loaded_qty - used_qty)
            vehicle_id = int(plan.get("vehicle_location_id") or 0)
            source_id = int(plan.get("source_location_id") or 0)
            if used_qty and vehicle_id:
                consume_by_vehicle.setdefault(vehicle_id, []).append(
                    {"part_id": plan["part_id"], "quantity": used_qty}
                )
            if returned_qty and vehicle_id and source_id:
                return_by_route.setdefault((vehicle_id, source_id), []).append(
                    {"part_id": plan["part_id"], "quantity": returned_qty, "unit": plan["unit"]}
                )
            updates.append((used_qty, returned_qty, plan_id))
        for vehicle_id, consume_lines in consume_by_vehicle.items():
            self.consume_location_stock(
                vehicle_id, consume_lines, source_type="appointment", source_id=appointment_id
            )
        for (vehicle_id, source_id), return_lines in return_by_route.items():
            vehicle_row = self.cursor.execute(
                "SELECT name, vehicle_plate FROM stock_locations WHERE id=?",
                (vehicle_id,),
            ).fetchone()
            vehicle_label = str(vehicle_row[0] or "Ara\u00e7") if vehicle_row else "Ara\u00e7"
            if vehicle_row and vehicle_row[1]:
                vehicle_label += " ({})".format(vehicle_row[1])
            self.transfer_stock(
                vehicle_id,
                source_id,
                return_lines,
                note="Randevu iade {} - {}".format(appointment_id, vehicle_label),
            )
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for used_qty, returned_qty, plan_id in updates:
            self.cursor.execute(
                """
                UPDATE appointment_plan_items
                SET used_qty=?, returned_qty=?, status='completed', updated_at=?
                WHERE id=?
                """,
                (used_qty, returned_qty, now, plan_id),
            )
        self.cursor.execute(
            """
            UPDATE appointment_plan_items
            SET status='completed', updated_at=?
            WHERE appointment_id=? AND item_role != 'material'
            """,
            (now, appointment_id),
        )
        self.conn.commit()
        return True

    def reconcile_vehicle_count(self, location_id, part_id, quantity_delta):
        """Sync appointment plans when a vehicle stock count removes stock."""
        delta = float(quantity_delta or 0)
        if delta >= -0.000001:
            return
        remaining = abs(delta)
        rows = self.cursor.execute(
            """
            SELECT id, loaded_qty, used_qty, returned_qty
            FROM appointment_plan_items
            WHERE vehicle_location_id=? AND part_id=? AND item_role='material'
              AND loaded_qty > COALESCE(used_qty, 0) + COALESCE(returned_qty, 0)
            ORDER BY updated_at DESC, id DESC
            """,
            (int(location_id), int(part_id)),
        ).fetchall()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for plan_id, loaded, used, returned in rows:
            available = max(0.0, float(loaded or 0) - float(used or 0) - float(returned or 0))
            moved = min(remaining, available)
            if moved <= 0:
                continue
            new_returned = float(returned or 0) + moved
            status = "completed" if new_returned + float(used or 0) >= float(loaded or 0) - 0.000001 else "loaded"
            self.cursor.execute(
                """
                UPDATE appointment_plan_items
                SET returned_qty=?, status=?, updated_at=?
                WHERE id=?
                """,
                (new_returned, status, now, int(plan_id)),
            )
            remaining -= moved
            if remaining <= 0.000001:
                break

    def reconcile_appointment_vehicle_stock(self, appointment_id):
        """Repair plan quantities after a vehicle count changed its balance."""
        plans = [
            row for row in self.get_appointment_offer_plan(appointment_id)
            if row.get("item_role") == "material" and row.get("vehicle_location_id")
        ]
        grouped = {}
        for plan in plans:
            key = (int(plan["vehicle_location_id"]), int(plan["part_id"]))
            grouped.setdefault(key, 0.0)
            grouped[key] += max(
                0.0,
                float(plan.get("loaded_qty") or 0)
                - float(plan.get("used_qty") or 0)
                - float(plan.get("returned_qty") or 0),
            )
        for (vehicle_id, part_id), outstanding in grouped.items():
            row = self.cursor.execute(
                """
                SELECT COALESCE(quantity, 0) FROM stock_location_balances
                WHERE location_id=? AND part_id=?
                """,
                (vehicle_id, part_id),
            ).fetchone()
            actual = float(row[0] or 0) if row else 0.0
            deficit = actual - outstanding
            if deficit < -0.000001:
                self.reconcile_vehicle_count(vehicle_id, part_id, deficit)
        self.conn.commit()
    
    def add_appointment(self, customer_name, phone, date, time, description):
        """Basit randevu ekle"""
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO appointments (customer_name, phone, date, time, description, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'Bekliyor', ?)
            """, (customer_name, phone, date, time, description, created_at))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Appointment add error: {e}")
            return False
    
    def add_appointment_extended(self, data):
        """Genişletilmiş alanlarda randevu ekle"""
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            keys = ", ".join(self._safe_identifier(key) for key in data.keys())
            values_ph = ", ".join(["?"] * len(data))
            values = tuple(data.values())
            sql = "INSERT INTO appointments ({keys}, created_at) VALUES ({values_ph}, ?)".format(
                keys=keys,
                values_ph=values_ph,
            )
            self.cursor.execute(sql, values + (created_at,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Appointment extended add error: {e}")
            return False
    
    def get_appointments(self):
        """Tüm randevuları getir"""
        try:
            self.cursor.execute("SELECT * FROM appointments ORDER BY date, time")
            return self.cursor.fetchall()
        except Exception as e:
            logger.error("Get appointments error: %s", e)
            return []
    
    def get_upcoming_appointments(self, minutes=15):
        """Yaklaşan randevuları getir"""
        try:
            now = datetime.now()
            upcoming_time = now + timedelta(minutes=minutes)
            today = now.strftime("%Y-%m-%d")
            current_time = now.strftime("%H:%M")
            upcoming_time_str = upcoming_time.strftime("%H:%M")
            
            self.cursor.execute("""
                SELECT * FROM appointments 
                WHERE date = ? 
                AND time BETWEEN ? AND ?
                AND status != 'Tamamlandı'
                ORDER BY time
            """, (today, current_time, upcoming_time_str))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Get upcoming appointments error: {e}")
            return []
    
    def delete_appointment(self, appt_id):
        """Randevu sil"""
        try:
            self.cursor.execute("DELETE FROM appointments WHERE id=?", (appt_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Appointment delete error: {e}")
            return False
    
    def update_appointment_status(self, appt_id, status):
        """Randevu durumunu güncelle"""
        try:
            self.cursor.execute("UPDATE appointments SET status=? WHERE id=?", (status, appt_id))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Appointment status update error: {e}")
            return False
