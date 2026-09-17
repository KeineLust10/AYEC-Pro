# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import hashlib
from src.utils.logger import logger

class MaintenanceCoreMixin:
    def get_customer_vehicles(self, customer_id):
        try:
            self.cursor.execute("SELECT * FROM customer_vehicles WHERE customer_id=? AND COALESCE(is_active, 1)=1 ORDER BY plate COLLATE NOCASE ASC, id ASC", (customer_id,))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get customer vehicles error: {e}"); return []

    def get_customer_vehicle(self, vehicle_id):
        try:
            self.cursor.execute("SELECT * FROM customer_vehicles WHERE id=?", (vehicle_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Get customer vehicle error: {e}"); return None

    def get_customer_vehicle_by_plate(self, plate):
        try:
            plate_clean = str(plate or "").strip().upper()
            if not plate_clean: return None
            self.cursor.execute("SELECT * FROM customer_vehicles WHERE UPPER(TRIM(plate))=? LIMIT 1", (plate_clean,))
            row = self.cursor.fetchone()
            if row: return row
            self.cursor.execute("SELECT NULL AS id, customer_id, vehicle_plate AS plate, vehicle_brand AS brand, vehicle_model AS model, vehicle_year AS year, vehicle_type, engine_type, fuel_type, odometer AS last_known_odometer, notes, 1 AS is_active, created_at, updated_at FROM vehicle_maintenance_cards WHERE UPPER(TRIM(vehicle_plate))=? ORDER BY id DESC LIMIT 1", (plate_clean,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Get customer vehicle by plate error: {e}"); return None

    def save_customer_vehicle(self, vehicle_data):
        try:
            clean = dict(vehicle_data or {})
            clean["plate"] = str(clean.get("plate", "") or "").strip().upper()
            clean["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not clean.get("created_at"): clean["created_at"] = clean["updated_at"]
            vehicle_id = clean.pop("id", None)
            if vehicle_id:
                assignments = ", ".join(f"{self._safe_identifier(k)}=?" for k in clean.keys())
                self.cursor.execute("UPDATE customer_vehicles SET {a} WHERE id=?".format(a=assignments), tuple(clean.values()) + (vehicle_id,))
            else:
                keys = ", ".join(self._safe_identifier(k) for k in clean.keys())
                placeholders = ", ".join("?" for _ in clean)
                self.cursor.execute("INSERT INTO customer_vehicles ({k}) VALUES ({p})".format(k=keys, p=placeholders), tuple(clean.values()))
                vehicle_id = self.cursor.lastrowid
            self.conn.commit(); return vehicle_id
        except Exception as e:
            logger.error(f"Save customer vehicle error: {e}"); self.conn.rollback(); return None

    def get_vehicle_maintenance_cards(self, search_query=""):
        try:
            query = "SELECT c.*, COALESCE((SELECT COUNT(*) FROM vehicle_maintenance_photos p WHERE p.card_id = c.id), 0) AS photo_count, (SELECT MIN(i.next_due_odometer) FROM vehicle_maintenance_items i WHERE i.card_id = c.id AND COALESCE(i.performed, 1)=1 AND COALESCE(i.next_due_odometer, 0) > 0) AS next_due_odometer_min, (SELECT MIN(i.next_due_date) FROM vehicle_maintenance_items i WHERE i.card_id = c.id AND COALESCE(i.performed, 1)=1 AND COALESCE(TRIM(i.next_due_date), '') != '') AS next_due_item_date FROM vehicle_maintenance_cards c WHERE 1=1"
            params = []
            if search_query:
                query += " AND (c.customer_name LIKE ? OR c.vehicle_plate LIKE ? OR c.vehicle_brand LIKE ? OR c.vehicle_model LIKE ?)"
                w = f"%{search_query.strip()}%"; params.extend([w]*4)
            query += " ORDER BY COALESCE(c.next_maintenance_date, c.service_date) DESC, c.id DESC"
            self.cursor.execute(query, tuple(params)); return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get vehicle maintenance cards error: {e}"); return []

    def get_vehicle_maintenance_card(self, card_id):
        try:
            self.cursor.execute("SELECT * FROM vehicle_maintenance_cards WHERE id=?", (card_id,))
            card = self.cursor.fetchone()
            if not card: return None, []
            self.cursor.execute("SELECT * FROM vehicle_maintenance_items WHERE card_id=? ORDER BY id ASC", (card_id,))
            return card, self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get vehicle maintenance card error: {e}"); return None, []

    def get_vehicle_maintenance_card_summary(self, card_id):
        try:
            self.cursor.execute("SELECT COUNT(*) AS selected_count, SUM(CASE WHEN COALESCE(performed, 1)=1 THEN 1 ELSE 0 END) AS performed_count, MIN(next_due_date) AS nearest_due_date, MIN(CASE WHEN COALESCE(next_due_odometer, 0) > 0 THEN next_due_odometer END) AS nearest_due_odometer FROM vehicle_maintenance_items WHERE card_id=?", (card_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Get vehicle maintenance card summary error: {e}"); return None

    def save_vehicle_maintenance_card(self, card_data, items, username=""):
        try:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean = dict(card_data or {})
            if clean.get("customer_id") and not clean.get("customer_phone"):
                self.cursor.execute("SELECT phone FROM customers WHERE id=?", (clean.get("customer_id"),))
                phone_row = self.cursor.fetchone()
                if phone_row: clean["customer_phone"] = (phone_row["phone"] if hasattr(phone_row, "keys") else phone_row[0])
            
            v_p = {"id": clean.get("vehicle_id"), "customer_id": clean.get("customer_id"), "plate": clean.get("vehicle_plate"), "brand": clean.get("vehicle_brand"), "model": clean.get("vehicle_model"), "year": clean.get("vehicle_year"), "vehicle_type": clean.get("vehicle_type"), "engine_type": clean.get("engine_type"), "fuel_type": clean.get("fuel_type"), "inspection_due_date": clean.get("inspection_due_date"), "inspection_notice_date": clean.get("inspection_notice_date"), "inspection_notified_at": clean.get("inspection_notified_at"), "qr_token": clean.get("qr_token") or self._build_vehicle_qr_token(clean), "last_known_odometer": int(clean.get("odometer") or 0), "notes": clean.get("notes", ""), "is_active": 1, "created_at": now_str}
            vehicle_id = self.save_customer_vehicle(v_p)
            if vehicle_id: clean["vehicle_id"] = vehicle_id
            
            clean["created_by"] = username or clean.get("created_by", "")
            clean["updated_at"] = now_str
            if not clean.get("created_at"): clean["created_at"] = now_str
            
            card_id = clean.pop("id", None)
            if card_id:
                ass = ", ".join(f"{self._safe_identifier(k)}=?" for k in clean.keys())
                self.cursor.execute("UPDATE vehicle_maintenance_cards SET {a} WHERE id=?".format(a=ass), tuple(clean.values()) + (card_id,))
                self.cursor.execute("DELETE FROM vehicle_maintenance_items WHERE card_id=?", (card_id,))
            else:
                k = ", ".join(self._safe_identifier(key) for key in clean.keys()); p = ", ".join("?" for _ in clean)
                self.cursor.execute("INSERT INTO vehicle_maintenance_cards ({k}) VALUES ({p})".format(k=k, p=p), tuple(clean.values())); card_id = self.cursor.lastrowid
            
            for item in items or []:
                self.cursor.execute("INSERT INTO vehicle_maintenance_items (card_id, item_type, item_label, performed, interval_days, interval_km, next_due_date, next_due_odometer, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (card_id, item.get("item_type"), item.get("item_label"), 1 if item.get("performed", True) else 0, int(item.get("interval_days") or 90), int(item.get("interval_km") or 0), item.get("next_due_date"), int(item.get("next_due_odometer") or 0), item.get("notes", "")))
            
            app_id = self._upsert_vehicle_maintenance_appointment(card_id)
            tr, dev_id = self._create_service_record_from_vehicle_maintenance(card_id=card_id, card_data=clean, items=items, username=username, now_str=now_str)
            self.cursor.execute("UPDATE vehicle_maintenance_cards SET draft_appointment_id=?, linked_device_tracking_no=?, linked_device_id=?, updated_at=? WHERE id=?", (app_id, tr, dev_id, now_str, card_id))
            self.conn.commit(); return card_id
        except Exception as e:
            logger.error(f"Save vehicle maintenance card error: {e}"); self.conn.rollback(); return None

    def save_vehicle_maintenance_plan_from_service(self, service_payload, items, username=""):
        try:
            if not items: return None
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean = dict(service_payload or {})
            if clean.get("customer_id") and not clean.get("customer_phone"):
                self.cursor.execute("SELECT phone FROM customers WHERE id=?", (clean.get("customer_id"),))
                phone_row = self.cursor.fetchone()
                if phone_row: clean["customer_phone"] = (phone_row["phone"] if hasattr(phone_row, "keys") else phone_row[0])
            
            v_p = {"id": clean.get("vehicle_id"), "customer_id": clean.get("customer_id"), "plate": clean.get("vehicle_plate"), "brand": clean.get("vehicle_brand"), "model": clean.get("vehicle_model"), "year": clean.get("vehicle_year"), "vehicle_type": clean.get("vehicle_type"), "engine_type": clean.get("engine_type"), "fuel_type": clean.get("fuel_type"), "inspection_due_date": clean.get("inspection_due_date"), "inspection_notice_date": clean.get("inspection_notice_date"), "inspection_notified_at": clean.get("inspection_notified_at"), "qr_token": clean.get("qr_token") or self._build_vehicle_qr_token(clean), "last_known_odometer": int(clean.get("odometer") or 0), "notes": clean.get("notes", ""), "is_active": 1, "created_at": now_str}
            vehicle_id = self.save_customer_vehicle(v_p)
            if vehicle_id: clean["vehicle_id"] = vehicle_id
            
            next_dates = sorted(str(i.get("next_due_date") or "").strip() for i in (items or []) if str(i.get("next_due_date") or "").strip())
            next_date = next_dates[0] if next_dates else str(clean.get("service_date") or datetime.now().strftime("%Y-%m-%d"))
            rem_date = clean.get("reminder_date")
            if not rem_date and next_date:
                try: rem_date = (datetime.strptime(next_date, "%Y-%m-%d") - timedelta(days=3)).strftime("%Y-%m-%d")
                except Exception: rem_date = next_date
            
            card_rec = {"vehicle_id": clean.get("vehicle_id"), "customer_id": clean.get("customer_id"), "customer_name": clean.get("customer_name", ""), "customer_phone": clean.get("customer_phone", ""), "vehicle_plate": clean.get("vehicle_plate", ""), "vehicle_brand": clean.get("vehicle_brand", ""), "vehicle_model": clean.get("vehicle_model", ""), "vehicle_year": clean.get("vehicle_year", ""), "vehicle_type": clean.get("vehicle_type", ""), "engine_type": clean.get("engine_type", ""), "fuel_type": clean.get("fuel_type", ""), "inspection_due_date": clean.get("inspection_due_date"), "inspection_notice_date": clean.get("inspection_notice_date"), "inspection_notified_at": clean.get("inspection_notified_at"), "qr_token": clean.get("qr_token") or self._build_vehicle_qr_token(clean), "odometer": int(clean.get("odometer") or 0), "service_date": clean.get("service_date") or datetime.now().strftime("%Y-%m-%d"), "next_maintenance_date": next_date, "manual_appointment_date": clean.get("manual_appointment_date") or next_date, "appointment_date": clean.get("appointment_date") or next_date, "appointment_time": clean.get("appointment_time") or "09:00", "notes": clean.get("notes", ""), "reminder_date": rem_date, "linked_device_tracking_no": clean.get("linked_device_tracking_no", ""), "linked_device_id": clean.get("linked_device_id"), "created_by": username or clean.get("created_by", ""), "updated_at": now_str}
            if not clean.get("created_at"): card_rec["created_at"] = now_str
            
            existing = None
            if clean.get("linked_device_id"):
                self.cursor.execute("SELECT id FROM vehicle_maintenance_cards WHERE linked_device_id=? ORDER BY id DESC LIMIT 1", (clean.get("linked_device_id"),))
                existing = self.cursor.fetchone()
            if not existing and clean.get("linked_device_tracking_no"):
                self.cursor.execute("SELECT id FROM vehicle_maintenance_cards WHERE linked_device_tracking_no=? ORDER BY id DESC LIMIT 1", (clean.get("linked_device_tracking_no"),))
                existing = self.cursor.fetchone()
            
            if existing:
                card_id = (existing["id"] if hasattr(existing, "keys") else existing[0])
                ass = ", ".join(f"{self._safe_identifier(k)}=?" for k in card_rec.keys())
                self.cursor.execute("UPDATE vehicle_maintenance_cards SET {a} WHERE id=?".format(a=ass), tuple(card_rec.values()) + (card_id,))
                self.cursor.execute("DELETE FROM vehicle_maintenance_items WHERE card_id=?", (card_id,))
            else:
                k = ", ".join(self._safe_identifier(key) for key in card_rec.keys()); p = ", ".join("?" for _ in card_rec)
                self.cursor.execute("INSERT INTO vehicle_maintenance_cards ({k}) VALUES ({p})".format(k=k, p=p), tuple(card_rec.values())); card_id = self.cursor.lastrowid
            
            for item in items or []:
                self.cursor.execute("INSERT INTO vehicle_maintenance_items (card_id, item_type, item_label, performed, interval_days, interval_km, next_due_date, next_due_odometer, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (card_id, item.get("item_type"), item.get("item_label"), 1 if item.get("performed", True) else 0, int(item.get("interval_days") or 90), int(item.get("interval_km") or 0), item.get("next_due_date"), int(item.get("next_due_odometer") or 0), item.get("notes", "")))
            
            app_id = self._upsert_vehicle_maintenance_appointment(card_id)
            self.cursor.execute("UPDATE vehicle_maintenance_cards SET draft_appointment_id=?, linked_device_tracking_no=?, linked_device_id=?, updated_at=? WHERE id=?", (app_id, clean.get("linked_device_tracking_no", ""), clean.get("linked_device_id"), now_str, card_id))
            self.conn.commit(); return card_id
        except Exception as e:
            logger.error(f"Save vehicle maintenance plan from service error: {e}"); self.conn.rollback(); return None

    def _build_vehicle_qr_token(self, card_data):
        seed = "|".join([str((card_data or {}).get("vehicle_plate", "") or ""), str((card_data or {}).get("customer_id", "") or ""), str((card_data or {}).get("vehicle_brand", "") or ""), str((card_data or {}).get("vehicle_model", "") or "")])
        digest = hashlib.sha256(seed.encode("utf-8", errors="ignore")).hexdigest()[:16].upper()
        return f"AYEC-AUTO-{digest}"

    def calculate_next_maintenance_date(self, service_date, interval_days=90):
        try:
            from datetime import timedelta
            base = datetime.strptime(str(service_date), "%Y-%m-%d")
            return (base + timedelta(days=int(interval_days or 90))).strftime("%Y-%m-%d")
        except Exception: return str(service_date)
