# -*- coding: utf-8 -*-
from datetime import datetime
from src.utils.logger import logger

class MaintenanceQuotesMixin:
    def get_automotive_quote_form(self, device_id=None, tracking_no=None):
        if device_id is None and tracking_no:
            device = self._resolve_automotive_device_context(tracking_no=tracking_no)
            device_id = device["id"] if isinstance(device, dict) else None
        return self._get_single_automotive_record("automotive_quote_forms", "device_id", device_id)

    def get_automotive_quote_items(self, quote_form_id):
        try:
            if not quote_form_id: return []
            self.cursor.execute("SELECT * FROM automotive_quote_items WHERE quote_form_id=? ORDER BY id ASC", (quote_form_id,))
            return self.cursor.fetchall() or []
        except Exception as e:
            logger.error(f"Get automotive quote items error: {e}"); return []

    def upsert_automotive_quote_form(self, form_data, items=None):
        try:
            payload = dict(form_data or {}); device_id = payload.get("device_id")
            if not device_id: return False
            quote_form_id = self._upsert_single_automotive_record("automotive_quote_forms", "device_id", device_id, payload)
            if not quote_form_id: return False
            self.cursor.execute("DELETE FROM automotive_quote_items WHERE quote_form_id=?", (quote_form_id,))
            subtotal = 0.0; approved_names = []
            for item in items or []:
                name = str(item.get("item_name") or "").strip()
                if not name: continue
                qty = float(item.get("qty") or 1); unit_price = float(item.get("unit_price") or 0)
                app = 1 if item.get("approved", True) else 0; subtotal += qty * unit_price
                self.cursor.execute("INSERT INTO automotive_quote_items (quote_form_id, item_type, item_name, qty, unit_price, approved, source_status, note) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (quote_form_id, item.get("item_type", "islem"), name, qty, unit_price, app, item.get("source_status", ""), item.get("note", "")))
                if app: approved_names.append(name)
            
            disc = float(payload.get("discount_amount") or 0); total = max(0.0, subtotal - disc)
            self.cursor.execute("UPDATE automotive_quote_forms SET subtotal=?, total_amount=?, updated_at=? WHERE id=?", (subtotal, total, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), quote_form_id))
            if approved_names:
                self.cursor.execute("UPDATE devices SET approval_status=?, repair_details=COALESCE(repair_details, '') || ? WHERE id=?", (str(payload.get("approval_status") or "Onaylandi"), f"\n[TEKLIF ONAY]: {', '.join(approved_names[:8])}", device_id))
            self.conn.commit()
            self.add_automotive_history_event("quote", "Teklif / Onay", f"Durum: {payload.get('approval_status') or '-'} | Toplam: {total:.2f} TL", vehicle_id=payload.get("vehicle_id"), customer_id=payload.get("customer_id"), device_id=device_id, tracking_no=payload.get("tracking_no", ""), vehicle_plate=payload.get("vehicle_plate", ""))
            return True
        except Exception as e:
            logger.error(f"Upsert automotive quote form error: {e}"); self.conn.rollback(); return False
