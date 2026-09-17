# -*- coding: utf-8 -*-
from datetime import datetime
from src.utils.logger import logger

class MaintenanceFormsMixin:
    def get_automotive_service_form(self, device_id=None, tracking_no=None):
        try:
            if device_id is None and tracking_no:
                self.cursor.execute("SELECT id FROM devices WHERE tracking_no=?", (tracking_no,))
                row = self.cursor.fetchone()
                device_id = (row["id"] if row and hasattr(row, "keys") else (row[0] if row else None))
            if not device_id: return None
            self.cursor.execute("SELECT * FROM automotive_service_forms WHERE device_id=?", (device_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Get automotive service form error: {e}"); return None

    def upsert_automotive_service_form(self, form_data):
        try:
            self.create_vehicle_maintenance_tables()
            clean = dict(form_data or {}); device_id = clean.get("device_id")
            if not device_id: return False
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            clean["updated_at"] = now_str
            if not clean.get("created_at"): clean["created_at"] = now_str
            self.cursor.execute("PRAGMA table_info(automotive_service_forms)")
            valid_cols = {row[1] for row in (self.cursor.fetchall() or [])}
            clean = {k: v for k, v in clean.items() if k in valid_cols and k != "id"}
            self.cursor.execute("SELECT id FROM automotive_service_forms WHERE device_id=?", (device_id,))
            existing = self.cursor.fetchone()
            if existing:
                ass = ", ".join(f"{self._safe_identifier(k)}=?" for k in clean.keys())
                self.cursor.execute("UPDATE automotive_service_forms SET {a} WHERE device_id=?".format(a=ass), tuple(clean.values()) + (device_id,))
            else:
                k = ", ".join(self._safe_identifier(key) for key in clean.keys()); p = ", ".join("?" for _ in clean)
                self.cursor.execute("INSERT INTO automotive_service_forms ({k}) VALUES ({p})".format(k=k, p=p), tuple(clean.values()))
            self.conn.commit(); return True
        except Exception as e:
            logger.error(f"Upsert automotive service form error: {e}"); self.conn.rollback(); return False

    def get_automotive_checkup_form(self, device_id=None, tracking_no=None):
        if device_id is None and tracking_no:
            device = self._resolve_automotive_device_context(tracking_no=tracking_no)
            device_id = device["id"] if isinstance(device, dict) else None
        return self._get_single_automotive_record("automotive_checkup_forms", "device_id", device_id)

    def upsert_automotive_checkup_form(self, form_data):
        try:
            payload = dict(form_data or {}); device_id = payload.get("device_id")
            if not device_id: return False
            row_id = self._upsert_single_automotive_record("automotive_checkup_forms", "device_id", device_id, payload)
            self.conn.commit()
            if row_id: self.add_automotive_history_event("checkup", "Ekspertiz / Check-Up", payload.get("summary", ""), vehicle_id=payload.get("vehicle_id"), customer_id=payload.get("customer_id"), device_id=device_id, tracking_no=payload.get("tracking_no", ""), vehicle_plate=payload.get("vehicle_plate", ""))
            return bool(row_id)
        except Exception as e:
            logger.error(f"Upsert automotive checkup form error: {e}"); self.conn.rollback(); return False

    def get_automotive_delivery_form(self, device_id=None, tracking_no=None):
        if device_id is None and tracking_no:
            device = self._resolve_automotive_device_context(tracking_no=tracking_no)
            device_id = device["id"] if isinstance(device, dict) else None
        return self._get_single_automotive_record("automotive_delivery_forms", "device_id", device_id)

    def upsert_automotive_delivery_form(self, form_data):
        try:
            payload = dict(form_data or {}); device_id = payload.get("device_id")
            if not device_id: return False
            row_id = self._upsert_single_automotive_record("automotive_delivery_forms", "device_id", device_id, payload)
            if not row_id: return False
            self.cursor.execute("UPDATE devices SET status=?, invoice_ready_at=COALESCE(invoice_ready_at, ?) WHERE id=?", ("Teslim Edildi", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), device_id))
            self.conn.commit()
            self.add_automotive_history_event("delivery", "Teslim Formu", payload.get("delivery_note", "") or payload.get("work_summary", ""), vehicle_id=payload.get("vehicle_id"), customer_id=payload.get("customer_id"), device_id=device_id, tracking_no=payload.get("tracking_no", ""), vehicle_plate=payload.get("vehicle_plate", ""))
            return True
        except Exception as e:
            logger.error(f"Upsert automotive delivery form error: {e}"); self.conn.rollback(); return False
