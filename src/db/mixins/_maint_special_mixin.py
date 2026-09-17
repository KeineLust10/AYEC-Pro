# -*- coding: utf-8 -*-
from datetime import datetime
from src.utils.logger import logger

class MaintenanceSpecialMixin:
    # Templates
    def get_automotive_maintenance_templates(self):
        try:
            self.cursor.execute("SELECT * FROM automotive_maintenance_templates WHERE COALESCE(is_active, 1)=1 ORDER BY is_default DESC, name COLLATE NOCASE ASC")
            templates = self.cursor.fetchall() or []
            rows = []
            for t in templates:
                tid = (t["id"] if hasattr(t, "keys") else t[0])
                self.cursor.execute("SELECT * FROM automotive_maintenance_template_items WHERE template_id=? ORDER BY id ASC", (tid,))
                rows.append({"template": t, "items": self.cursor.fetchall() or []})
            return rows
        except Exception as e:
            logger.error(f"Get automotive maintenance templates error: {e}"); return []

    def save_automotive_maintenance_template(self, template_data, items=None):
        try:
            payload = dict(template_data or {}); tid = payload.pop("id", None)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            payload["updated_at"] = now
            if not payload.get("created_at"): payload["created_at"] = now
            if tid:
                ass = ", ".join(f"{self._safe_identifier(k)}=?" for k in payload.keys())
                self.cursor.execute("UPDATE automotive_maintenance_templates SET {a} WHERE id=?".format(a=ass), tuple(payload.values()) + (tid,))
            else:
                k = ", ".join(self._safe_identifier(key) for key in payload.keys()); p = ", ".join("?" for _ in payload)
                self.cursor.execute("INSERT INTO automotive_maintenance_templates ({k}) VALUES ({p})".format(k=k, p=p), tuple(payload.values())); tid = self.cursor.lastrowid
            self.cursor.execute("DELETE FROM automotive_maintenance_template_items WHERE template_id=?", (tid,))
            for i in items or []:
                self.cursor.execute("INSERT INTO automotive_maintenance_template_items (template_id, item_group, item_label, interval_days, interval_km, default_status, note) VALUES (?, ?, ?, ?, ?, ?, ?)", (tid, i.get("item_group", ""), i.get("item_label", ""), int(i.get("interval_days") or 0), int(i.get("interval_km") or 0), i.get("default_status", ""), i.get("note", "")))
            self.conn.commit(); return tid
        except Exception as e:
            logger.error(f"Save automotive maintenance template error: {e}"); self.conn.rollback(); return None

    def delete_automotive_maintenance_template(self, template_id):
        try:
            self.cursor.execute("DELETE FROM automotive_maintenance_templates WHERE id=?", (template_id,))
            self.cursor.execute("DELETE FROM automotive_maintenance_template_items WHERE template_id=?", (template_id,))
            self.conn.commit(); return True
        except Exception as e:
            logger.error(f"Delete automotive maintenance template error: {e}"); self.conn.rollback(); return False

    # Warranty
    def save_automotive_warranty_campaign(self, payload):
        try:
            clean = dict(payload or {}); now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean["updated_at"] = now
            if not clean.get("created_at"): clean["created_at"] = now
            k = ", ".join(clean.keys()); p = ", ".join("?" for _ in clean)
            self.cursor.execute(f"INSERT INTO automotive_warranty_campaigns ({k}) VALUES ({p})", tuple(clean.values()))
            self.conn.commit(); self.add_automotive_history_event("warranty_campaign", clean.get("campaign_name", "Garanti / Kampanya"), clean.get("notes", ""), vehicle_id=clean.get("vehicle_id"), device_id=clean.get("device_id"), vehicle_plate=clean.get("vehicle_plate", ""))
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Save automotive warranty campaign error: {e}"); self.conn.rollback(); return None

    def get_automotive_warranty_campaigns(self, vehicle_id=None, plate=""):
        try:
            if vehicle_id: self.cursor.execute("SELECT * FROM automotive_warranty_campaigns WHERE vehicle_id=? ORDER BY created_at DESC, id DESC", (vehicle_id,))
            else: self.cursor.execute("SELECT * FROM automotive_warranty_campaigns WHERE UPPER(TRIM(vehicle_plate))=? ORDER BY created_at DESC, id DESC", (str(plate or "").strip().upper(),))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get automotive warranty campaigns error: {e}"); return []

    # Tires
    def save_automotive_tire_suspension_record(self, payload):
        try:
            clean = dict(payload or {}); now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean["updated_at"] = now
            if not clean.get("created_at"): clean["created_at"] = now
            k = ", ".join(clean.keys()); p = ", ".join("?" for _ in clean)
            self.cursor.execute(f"INSERT INTO automotive_tire_suspension_records ({k}) VALUES ({p})", tuple(clean.values()))
            self.conn.commit(); self.add_automotive_history_event("tire_suspension", "Lastik ve Yuruyen Aksam", clean.get("notes", ""), vehicle_id=clean.get("vehicle_id"), device_id=clean.get("device_id"), vehicle_plate=clean.get("vehicle_plate", ""))
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Save automotive tire suspension record error: {e}"); self.conn.rollback(); return None

    def get_automotive_tire_suspension_records(self, vehicle_id=None, plate=""):
        try:
            if vehicle_id: self.cursor.execute("SELECT * FROM automotive_tire_suspension_records WHERE vehicle_id=? ORDER BY created_at DESC, id DESC", (vehicle_id,))
            else: self.cursor.execute("SELECT * FROM automotive_tire_suspension_records WHERE UPPER(TRIM(vehicle_plate))=? ORDER BY created_at DESC, id DESC", (str(plate or "").strip().upper(),))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get automotive tire suspension records error: {e}"); return []

    # Battery
    def save_automotive_battery_electrical_test(self, payload):
        try:
            clean = dict(payload or {}); now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean["updated_at"] = now
            if not clean.get("created_at"): clean["created_at"] = now
            k = ", ".join(clean.keys()); p = ", ".join("?" for _ in clean)
            self.cursor.execute(f"INSERT INTO automotive_battery_electrical_tests ({k}) VALUES ({p})", tuple(clean.values()))
            self.conn.commit(); self.add_automotive_history_event("battery_electrical", "Aku / Elektrik Testi", clean.get("notes", "") or clean.get("obd_codes", ""), vehicle_id=clean.get("vehicle_id"), customer_id=clean.get("customer_id"), device_id=clean.get("device_id"), tracking_no=clean.get("tracking_no", ""), vehicle_plate=clean.get("vehicle_plate", ""))
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Save automotive battery electrical test error: {e}"); self.conn.rollback(); return None

    def get_automotive_battery_electrical_tests(self, device_id=None, plate=""):
        try:
            if device_id: self.cursor.execute("SELECT * FROM automotive_battery_electrical_tests WHERE device_id=? ORDER BY created_at DESC, id DESC", (device_id,))
            else: self.cursor.execute("SELECT * FROM automotive_battery_electrical_tests WHERE UPPER(TRIM(vehicle_plate))=? ORDER BY created_at DESC, id DESC", (str(plate or "").strip().upper(),))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get automotive battery electrical tests error: {e}"); return []

    # Parts Requests
    def save_automotive_parts_request(self, payload, items=None):
        try:
            clean = dict(payload or {}); rid = clean.pop("id", None)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean["updated_at"] = now
            if not clean.get("created_at"): clean["created_at"] = now
            if rid:
                ass = ", ".join(f"{k}=?" for k in clean.keys())
                self.cursor.execute(f"UPDATE automotive_parts_requests SET {ass} WHERE id=?", tuple(clean.values()) + (rid,))
            else:
                k = ", ".join(clean.keys()); p = ", ".join("?" for _ in clean)
                self.cursor.execute(f"INSERT INTO automotive_parts_requests ({k}) VALUES ({p})", tuple(clean.values())); rid = self.cursor.lastrowid
            self.cursor.execute("DELETE FROM automotive_parts_request_items WHERE request_id=?", (rid,))
            for i in items or []:
                self.cursor.execute("INSERT INTO automotive_parts_request_items (request_id, part_name, qty, oem_no, unit_cost, note) VALUES (?, ?, ?, ?, ?, ?)", (rid, i.get("part_name", ""), float(i.get("qty") or 1), i.get("oem_no", ""), float(i.get("unit_cost") or 0), i.get("note", "")))
            self.conn.commit(); self.add_automotive_history_event("parts_request", "Parca Talep / Satin Alma", clean.get("request_note", ""), vehicle_id=clean.get("vehicle_id"), customer_id=clean.get("customer_id"), device_id=clean.get("device_id"), tracking_no=clean.get("tracking_no", ""), vehicle_plate=clean.get("vehicle_plate", ""))
            return rid
        except Exception as e:
            logger.error(f"Save automotive parts request error: {e}"); self.conn.rollback(); return None

    def get_automotive_parts_requests(self, device_id=None, plate=""):
        try:
            if device_id: self.cursor.execute("SELECT * FROM automotive_parts_requests WHERE device_id=? ORDER BY created_at DESC, id DESC", (device_id,))
            else: self.cursor.execute("SELECT * FROM automotive_parts_requests WHERE UPPER(TRIM(vehicle_plate))=? ORDER BY created_at DESC, id DESC", (str(plate or "").strip().upper(),))
            rows = self.cursor.fetchall() or []; results = []
            for r in rows:
                rid = (r["id"] if hasattr(r, "keys") else r[0])
                self.cursor.execute("SELECT * FROM automotive_parts_request_items WHERE request_id=? ORDER BY id ASC", (rid,))
                results.append({"request": r, "items": self.cursor.fetchall() or []})
            return results
        except Exception as e:
            logger.error(f"Get automotive parts requests error: {e}"); return []

    # Damage Marks
    def replace_automotive_damage_marks(self, payload, items=None):
        try:
            clean = dict(payload or {}); dev_id = clean.get("device_id"); tr = clean.get("tracking_no", "")
            if dev_id: self.cursor.execute("DELETE FROM automotive_damage_marks WHERE device_id=?", (dev_id,))
            else: self.cursor.execute("DELETE FROM automotive_damage_marks WHERE tracking_no=?", (tr,))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for i in items or []:
                self.cursor.execute("INSERT INTO automotive_damage_marks (device_id, tracking_no, vehicle_id, vehicle_plate, side_name, zone_name, x, y, mark_status, note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (dev_id, tr, clean.get("vehicle_id"), clean.get("vehicle_plate", ""), i.get("side_name", ""), i.get("zone_name", ""), float(i.get("x") or 0), float(i.get("y") or 0), i.get("mark_status", ""), i.get("note", ""), now, now))
            self.conn.commit(); self.add_automotive_history_event("damage_schema", "Arac Kabul Semasi", f"{len(items or [])} hasar isaretlemesi kaydedildi.", vehicle_id=clean.get("vehicle_id"), customer_id=clean.get("customer_id"), device_id=dev_id, tracking_no=tr, vehicle_plate=clean.get("vehicle_plate", ""))
            return True
        except Exception as e:
            logger.error(f"Replace automotive damage marks error: {e}"); self.conn.rollback(); return False

    def get_automotive_damage_marks(self, device_id=None, tracking_no=None, plate=""):
        try:
            if device_id: self.cursor.execute("SELECT * FROM automotive_damage_marks WHERE device_id=? ORDER BY id ASC", (device_id,))
            elif tracking_no: self.cursor.execute("SELECT * FROM automotive_damage_marks WHERE tracking_no=? ORDER BY id ASC", (tracking_no,))
            else: self.cursor.execute("SELECT * FROM automotive_damage_marks WHERE UPPER(TRIM(vehicle_plate))=? ORDER BY id ASC", (str(plate or "").strip().upper(),))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get automotive damage marks error: {e}"); return []

    # Photos
    def get_vehicle_maintenance_photos(self, card_id):
        try:
            self.cursor.execute("SELECT * FROM vehicle_maintenance_photos WHERE card_id=? ORDER BY id ASC", (card_id,))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get vehicle maintenance photos error: {e}"); return []

    def get_vehicle_maintenance_photo_count(self, card_id):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM vehicle_maintenance_photos WHERE card_id=?", (card_id,))
            row = self.cursor.fetchone(); return int((row[0] if row else 0) or 0)
        except Exception: return 0

    def add_vehicle_maintenance_photo(self, card_id, photo_path, photo_label=""):
        try:
            self.cursor.execute("INSERT INTO vehicle_maintenance_photos (card_id, photo_path, photo_label) VALUES (?, ?, ?)", (card_id, photo_path, photo_label or ""))
            self.conn.commit(); return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Add vehicle maintenance photo error: {e}"); self.conn.rollback(); return None

    def delete_vehicle_maintenance_photo(self, photo_id):
        try:
            self.cursor.execute("DELETE FROM vehicle_maintenance_photos WHERE id=?", (photo_id,))
            self.conn.commit(); return True
        except Exception as e:
            logger.error(f"Delete vehicle maintenance photo error: {e}"); self.conn.rollback(); return False
