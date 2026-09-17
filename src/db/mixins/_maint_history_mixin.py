# -*- coding: utf-8 -*-
import json
from datetime import datetime
from src.utils.logger import logger

class MaintenanceHistoryMixin:
    def _resolve_automotive_device_context(self, device_id=None, tracking_no=None):
        try:
            self.cursor.execute("PRAGMA table_info(devices)")
            cols = {row[1] for row in (self.cursor.fetchall() or []) if len(row) > 1}
            del_cl = " AND COALESCE(is_deleted, 0)=0" if "is_deleted" in cols else ""
            if not device_id and tracking_no:
                self.cursor.execute(f"SELECT * FROM devices WHERE tracking_no=?{del_cl}", (tracking_no,))
                row = self.cursor.fetchone()
            elif device_id:
                self.cursor.execute(f"SELECT * FROM devices WHERE id=?{del_cl}", (device_id,))
                row = self.cursor.fetchone()
            else: row = None
            return dict(row) if row and hasattr(row, "keys") else (row or None)
        except Exception: return None

    def _get_single_automotive_record(self, table_name, key_column, key_value):
        try:
            if not key_value: return None
            self.cursor.execute(f"SELECT * FROM {self._safe_identifier(table_name)} WHERE {self._safe_identifier(key_column)}=?", (key_value,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Get single automotive record error ({table_name}): {e}"); return None

    def _upsert_single_automotive_record(self, table_name, key_column, key_value, payload):
        try:
            self.create_vehicle_maintenance_tables()
            clean = dict(payload or {}); clean[key_column] = key_value
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean["updated_at"] = now
            if not clean.get("created_at"): clean["created_at"] = now
            self.cursor.execute("PRAGMA table_info({t})".format(t=self._safe_identifier(table_name)))
            vcols = {row[1] for row in (self.cursor.fetchall() or [])}
            clean = {k: v for k, v in clean.items() if k in vcols and k != "id"}
            self.cursor.execute(f"SELECT id FROM {self._safe_identifier(table_name)} WHERE {self._safe_identifier(key_column)}=?", (key_value,))
            ex = self.cursor.fetchone()
            if ex:
                a = ", ".join(f"{self._safe_identifier(k)}=?" for k in clean.keys())
                self.cursor.execute(f"UPDATE {self._safe_identifier(table_name)} SET {a} WHERE {self._safe_identifier(key_column)}=?", tuple(clean.values()) + (key_value,))
                return (ex["id"] if hasattr(ex, "keys") else ex[0])
            safe_table = self._safe_identifier(table_name)
            k = ", ".join(self._safe_identifier(col) for col in clean.keys()); p = ", ".join("?" for _ in clean)
            self.cursor.execute(f"INSERT INTO {safe_table} ({k}) VALUES ({p})", tuple(clean.values()))
            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Upsert single automotive record error ({table_name}): {e}"); self.conn.rollback(); return None

    def add_automotive_history_event(self, event_type, title, summary="", *, vehicle_id=None, customer_id=None, device_id=None, tracking_no="", vehicle_plate="", payload_json=""):
        try:
            self.cursor.execute("INSERT INTO automotive_vehicle_history_events (vehicle_id, customer_id, device_id, tracking_no, vehicle_plate, event_type, title, summary, payload_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (vehicle_id, customer_id, device_id, tracking_no, str(vehicle_plate or "").strip().upper(), event_type, title, summary, payload_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.conn.commit(); return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Add automotive history event error: {e}"); self.conn.rollback(); return None

    def get_vehicle_history_snapshot(self, plate="", vehicle_id=None):
        try:
            params = []; plate_clean = str(plate or "").strip().upper()
            vsql = "vehicle_id=?" if vehicle_id else "UPPER(TRIM(vehicle_plate))=?"
            params.append(vehicle_id if vehicle_id else plate_clean)
            self.cursor.execute(f"SELECT id, service_date, next_maintenance_date, inspection_due_date, customer_name, vehicle_plate, vehicle_brand, vehicle_model, notes, linked_device_tracking_no, qr_token FROM vehicle_maintenance_cards WHERE {vsql} ORDER BY service_date DESC, id DESC", tuple(params))
            m_rows = self.cursor.fetchall() or []
            self.cursor.execute("SELECT tracking_no, entry_date, status, approval_status, fault_description, repair_details, labor_cost, vehicle_plate FROM devices WHERE UPPER(TRIM(vehicle_plate))=? AND COALESCE(is_deleted, 0)=0 ORDER BY entry_date DESC, id DESC", (plate_clean,))
            s_rows = self.cursor.fetchall() or []
            return m_rows, s_rows
        except Exception as e:
            logger.error(f"Get vehicle history snapshot error: {e}"); return [], []

    def get_automotive_vehicle_history_360(self, plate="", vehicle_id=None, customer_id=None):
        try:
            m_rows, s_rows = self.get_vehicle_history_snapshot(plate=plate, vehicle_id=vehicle_id); plate_clean = str(plate or "").strip().upper()
            self.cursor.execute("SELECT * FROM automotive_vehicle_history_events WHERE ((? IS NOT NULL AND vehicle_id=?) OR (? != '' AND UPPER(TRIM(vehicle_plate))=?) OR (? IS NOT NULL AND customer_id=?)) ORDER BY created_at DESC, id DESC", (vehicle_id, vehicle_id, plate_clean, plate_clean, customer_id, customer_id))
            ev = self.cursor.fetchall() or []
            self.cursor.execute("SELECT * FROM automotive_quote_forms WHERE UPPER(TRIM(vehicle_plate))=? ORDER BY updated_at DESC, id DESC", (plate_clean,))
            q = self.cursor.fetchall() or []
            self.cursor.execute("SELECT * FROM automotive_delivery_forms WHERE UPPER(TRIM(vehicle_plate))=? ORDER BY updated_at DESC, id DESC", (plate_clean,))
            de = self.cursor.fetchall() or []
            return {"maintenance_rows": m_rows, "service_rows": s_rows, "events": ev, "quotes": q, "deliveries": de, "warranties": self.get_automotive_warranty_campaigns(vehicle_id=vehicle_id, plate=plate_clean), "tire_rows": self.get_automotive_tire_suspension_records(vehicle_id=vehicle_id, plate=plate_clean), "battery_rows": self.get_automotive_battery_electrical_tests(plate=plate_clean), "parts_requests": self.get_automotive_parts_requests(plate=plate_clean), "damage_rows": self.get_automotive_damage_marks(plate=plate_clean)}
        except Exception as e:
            logger.error(f"Get automotive vehicle history 360 error: {e}"); return {"maintenance_rows": [], "service_rows": [], "events": [], "quotes": [], "deliveries": [], "warranties": [], "tire_rows": [], "battery_rows": [], "parts_requests": [], "damage_rows": []}

    def _create_service_record_from_vehicle_maintenance(self, card_id, card_data, items, username="", now_str=""):
        try:
            tr = None
            if hasattr(self, "get_next_service_number"):
                try: tr = self.get_next_service_number()
                except Exception: tr = None
            if not tr: tr = f"SRV{datetime.now().strftime('%H%M%S%f')[-9:]}"
            br = str(card_data.get("vehicle_brand", "") or "").strip(); mo = str(card_data.get("vehicle_model", "") or "").strip()
            no = str(card_data.get("notes", "") or "").strip(); desc = self._build_vehicle_maintenance_service_description(card_data, items)
            app_st = "Musteri Onayi Bekliyor" if desc else "Bekleme"
            srv = {"tracking_no": tr, "customer_id": card_data.get("customer_id"), "customer_name": card_data.get("customer_name"), "device_type": "Arac", "device_brand": br or "Arac", "device_model": mo or (card_data.get("vehicle_plate") or "Bakim Karti"), "serial_no": card_data.get("vehicle_plate") or "", "vehicle_plate": card_data.get("vehicle_plate") or "", "vehicle_vin": card_data.get("vehicle_vin") or "", "vehicle_maintenance_card_id": card_id, "service_source": "vehicle_maintenance", "urgency": "Normal", "status": "Bekliyor", "approval_status": app_st, "entry_date": datetime.now().strftime("%Y-%m-%d"), "fault_description": desc, "repair_details": no, "internal_notes": f"Otomotiv bakim kartindan otomatik servis kaydi olusturuldu. Kart ID: {card_id}", "inspection_summary": desc, "technician": username or "", "is_archived": 0, "is_deleted": 0, "created_at": now_str or datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "updated_at": now_str or datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
            self.cursor.execute("PRAGMA table_info(devices)"); ex_cols = {row[1] for row in (self.cursor.fetchall() or [])}
            safe = [(k, v) for k, v in srv.items() if v is not None and k in ex_cols]
            k = ", ".join(self._safe_identifier(key) for key, _ in safe); p = ", ".join("?" for _ in safe); v = tuple(val for _, val in safe)
            self.cursor.execute("INSERT INTO devices ({keys}) VALUES ({pl})".format(keys=k, pl=p), v); dev_id = self.cursor.lastrowid
            try: self.upsert_automotive_service_form({"device_id": dev_id, "tracking_no": tr, "customer_id": card_data.get("customer_id"), "vehicle_id": card_data.get("vehicle_id"), "vehicle_plate": card_data.get("vehicle_plate") or "", "vehicle_vin": card_data.get("vehicle_vin") or "", "entry_odometer": int(card_data.get("odometer") or 0), "acceptance_notes": no, "customer_approval_text": "Yukaridaki islemlerin yapilmasini onayliyorum.", "kvkk_text": "Verileriniz servis surecinin yurutulmesi amaciyla AYEC Pro sisteminde islenir."})
            except Exception as fe: logger.warning(f"Seed automotive service form warning: {fe}")
            return tr, dev_id
        except Exception as e:
            logger.error(f"Create service from vehicle maintenance error: {e}"); raise

    def _upsert_vehicle_maintenance_appointment(self, card_id):
        self.cursor.execute("SELECT * FROM vehicle_maintenance_cards WHERE id=?", (card_id,))
        card = self.cursor.fetchone()
        if not card: return None
        ad = card["manual_appointment_date"] or card["appointment_date"] or card["next_maintenance_date"]
        if not ad: return None
        at = card["appointment_time"] or "09:00"; desc = f"Otomotiv Bakim Takibi - {card['vehicle_plate'] or '-'} | Yag / Filtre / Cam Suyu / Antifriz kontrolu"; no = card["notes"] or ""
        self.cursor.execute("SELECT id FROM appointments WHERE source_type='vehicle_maintenance' AND source_ref_id=? ORDER BY id DESC LIMIT 1", (card_id,))
        ex = self.cursor.fetchone()
        vals = (card["customer_name"] or "", card["customer_name"] or "", card["customer_id"], ad, at, desc, "Taslak", "Bakim", no, card["vehicle_plate"] or "", card["vehicle_brand"] or "", card["vehicle_model"] or "", "vehicle_maintenance", card_id, 1)
        if ex:
            self.cursor.execute("UPDATE appointments SET customer_name=?, customer=?, customer_id=?, date=?, time=?, description=?, status=?, type=?, notes=?, device=?, brand=?, model=?, source_type=?, source_ref_id=?, is_auto_created=? WHERE id=?", vals + (ex["id"],))
            return ex["id"]
        c_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO appointments (customer_name, customer, customer_id, date, time, description, status, type, notes, device, brand, model, source_type, source_ref_id, is_auto_created, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", vals + (c_at,))
        return self.cursor.lastrowid

    def _build_vehicle_maintenance_service_description(self, card_data, items):
        lb = [str((i or {}).get("item_label", "")).strip() for i in (items or [])]; lb = [x for x in lb if x]
        parts = []
        if lb:
            parts.append("Bakim kalemleri:")
            parts.extend(f"- {label}" for label in lb)
        no = str((card_data or {}).get("notes", "") or "").strip()
        if no: parts.append(f"Bakim notu: {no}")
        return "\n".join(parts).strip() or "Otomotiv bakim kaydi"
