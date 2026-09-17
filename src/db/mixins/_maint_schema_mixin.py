# -*- coding: utf-8 -*-
from datetime import datetime
from src.utils.logger import logger

class MaintenanceSchemaMixin:
    def create_vehicle_maintenance_tables(self):
        try:
            # Tables creation
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS customer_vehicles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    plate TEXT NOT NULL UNIQUE,
                    brand TEXT, model TEXT, year TEXT, vehicle_type TEXT,
                    engine_type TEXT, fuel_type TEXT, inspection_due_date TEXT,
                    inspection_notice_date TEXT, inspection_notified_at TEXT,
                    qr_token TEXT, last_known_odometer INTEGER DEFAULT 0,
                    notes TEXT, is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_maintenance_cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id INTEGER, customer_id INTEGER,
                    customer_name TEXT, customer_phone TEXT,
                    vehicle_plate TEXT, vehicle_brand TEXT, vehicle_model TEXT,
                    vehicle_year TEXT, vehicle_type TEXT, engine_type TEXT,
                    fuel_type TEXT, inspection_due_date TEXT,
                    inspection_notice_date TEXT, inspection_notified_at TEXT,
                    qr_token TEXT, odometer INTEGER DEFAULT 0,
                    service_date TEXT, next_maintenance_date TEXT,
                    manual_appointment_date TEXT, appointment_date TEXT,
                    appointment_time TEXT DEFAULT '09:00', notes TEXT,
                    reminder_date TEXT, whatsapp_sent_at TEXT,
                    draft_appointment_id INTEGER, linked_device_tracking_no TEXT,
                    linked_device_id INTEGER, created_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(vehicle_id) REFERENCES customer_vehicles(id)
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_maintenance_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id INTEGER NOT NULL, item_type TEXT NOT NULL,
                    item_label TEXT NOT NULL, performed INTEGER DEFAULT 1,
                    interval_days INTEGER DEFAULT 90, interval_km INTEGER DEFAULT 0,
                    next_due_date TEXT, next_due_odometer INTEGER DEFAULT 0,
                    km_whatsapp_sent_at TEXT, notes TEXT,
                    FOREIGN KEY(card_id) REFERENCES vehicle_maintenance_cards(id) ON DELETE CASCADE
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_maintenance_photos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    card_id INTEGER NOT NULL, photo_path TEXT NOT NULL,
                    photo_label TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(card_id) REFERENCES vehicle_maintenance_cards(id) ON DELETE CASCADE
                )
            """)
            # ... (More tables: forms, checkup, quote, delivery, history, warranty, tires, battery, templates, requests, damage)
            # I will include them to ensure completeness
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS automotive_service_forms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER NOT NULL UNIQUE,
                    tracking_no TEXT, customer_id INTEGER, vehicle_id INTEGER,
                    vehicle_plate TEXT, vehicle_vin TEXT, engine_code TEXT,
                    entry_odometer INTEGER DEFAULT 0, exit_odometer INTEGER DEFAULT 0,
                    fuel_level_entry TEXT, fuel_level_exit TEXT, acceptance_notes TEXT,
                    checklist_json TEXT, damage_marks_json TEXT, customer_approval INTEGER DEFAULT 0,
                    kvkk_approval INTEGER DEFAULT 0, customer_approval_text TEXT, kvkk_text TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(device_id) REFERENCES devices(id) ON DELETE CASCADE
                )
            """)
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_checkup_forms (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER UNIQUE, tracking_no TEXT, customer_id INTEGER, vehicle_id INTEGER, vehicle_plate TEXT, template_key TEXT, summary TEXT, checklist_json TEXT, recommended_items_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_quote_forms (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER UNIQUE, tracking_no TEXT, customer_id INTEGER, vehicle_id INTEGER, vehicle_plate TEXT, quote_no TEXT, approval_status TEXT, approval_note TEXT, discount_amount REAL DEFAULT 0, subtotal REAL DEFAULT 0, total_amount REAL DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_quote_items (id INTEGER PRIMARY KEY AUTOINCREMENT, quote_form_id INTEGER NOT NULL, item_type TEXT, item_name TEXT, qty REAL DEFAULT 1, unit_price REAL DEFAULT 0, approved INTEGER DEFAULT 1, source_status TEXT, note TEXT, FOREIGN KEY(quote_form_id) REFERENCES automotive_quote_forms(id) ON DELETE CASCADE)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_delivery_forms (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER UNIQUE, tracking_no TEXT, customer_id INTEGER, vehicle_id INTEGER, vehicle_plate TEXT, exit_odometer INTEGER DEFAULT 0, fuel_level_exit TEXT, work_summary TEXT, delivery_note TEXT, delivered_to TEXT, delivered_at TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_vehicle_history_events (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, customer_id INTEGER, device_id INTEGER, tracking_no TEXT, vehicle_plate TEXT, event_type TEXT, title TEXT, summary TEXT, payload_json TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_warranty_campaigns (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, device_id INTEGER, vehicle_plate TEXT, campaign_type TEXT, campaign_name TEXT, status TEXT, start_date TEXT, end_date TEXT, provider TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_tire_suspension_records (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, device_id INTEGER, vehicle_plate TEXT, tire_size TEXT, front_left_depth REAL DEFAULT 0, front_right_depth REAL DEFAULT 0, rear_left_depth REAL DEFAULT 0, rear_right_depth REAL DEFAULT 0, alignment_status TEXT, balance_status TEXT, shock_absorber_status TEXT, brake_history TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_battery_electrical_tests (id INTEGER PRIMARY KEY AUTOINCREMENT, vehicle_id INTEGER, device_id INTEGER, tracking_no TEXT, vehicle_plate TEXT, battery_voltage REAL DEFAULT 0, charging_voltage REAL DEFAULT 0, starter_status TEXT, warning_lights TEXT, obd_codes TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_maintenance_templates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, template_type TEXT, source_key TEXT, is_default INTEGER DEFAULT 0, is_active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_maintenance_template_items (id INTEGER PRIMARY KEY AUTOINCREMENT, template_id INTEGER NOT NULL, item_group TEXT, item_label TEXT, interval_days INTEGER DEFAULT 0, interval_km INTEGER DEFAULT 0, default_status TEXT, note TEXT, FOREIGN KEY(template_id) REFERENCES automotive_maintenance_templates(id) ON DELETE CASCADE)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_parts_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER, tracking_no TEXT, customer_id INTEGER, vehicle_id INTEGER, vehicle_plate TEXT, supplier_name TEXT, status TEXT, expected_date TEXT, request_note TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_parts_request_items (id INTEGER PRIMARY KEY AUTOINCREMENT, request_id INTEGER NOT NULL, part_name TEXT, qty REAL DEFAULT 1, oem_no TEXT, unit_cost REAL DEFAULT 0, note TEXT, FOREIGN KEY(request_id) REFERENCES automotive_parts_requests(id) ON DELETE CASCADE)")
            self.cursor.execute("CREATE TABLE IF NOT EXISTS automotive_damage_marks (id INTEGER PRIMARY KEY AUTOINCREMENT, device_id INTEGER, tracking_no TEXT, vehicle_id INTEGER, vehicle_plate TEXT, side_name TEXT, zone_name TEXT, x REAL DEFAULT 0, y REAL DEFAULT 0, mark_status TEXT, note TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)")

            # Migrations
            self._maint_run_migrations()
            self.conn.commit()
        except Exception as e:
            logger.error(f"Vehicle maintenance schema error: {e}")

    def _maint_run_migrations(self):
        # Migrations logic from 364 to 501
        for table, items in [
            ("vehicle_maintenance_cards", [("vehicle_id", "INTEGER"), ("customer_phone", "TEXT"), ("whatsapp_sent_at", "TEXT"), ("vehicle_type", "TEXT"), ("engine_type", "TEXT"), ("fuel_type", "TEXT"), ("linked_device_tracking_no", "TEXT"), ("linked_device_id", "INTEGER"), ("inspection_due_date", "TEXT"), ("inspection_notice_date", "TEXT"), ("inspection_notified_at", "TEXT"), ("qr_token", "TEXT")]),
            ("vehicle_maintenance_items", [("interval_km", "INTEGER DEFAULT 0"), ("next_due_odometer", "INTEGER DEFAULT 0"), ("km_whatsapp_sent_at", "TEXT")]),
            ("appointments", [("source_type", "TEXT"), ("source_ref_id", "INTEGER"), ("is_auto_created", "INTEGER DEFAULT 0")]),
            ("devices", [("vehicle_plate", "TEXT"), ("vehicle_vin", "TEXT"), ("vehicle_maintenance_card_id", "INTEGER"), ("service_source", "TEXT"), ("fault_codes", "TEXT"), ("obd_notes", "TEXT"), ("inspection_summary", "TEXT"), ("delivery_method", "TEXT"), ("service_location", "TEXT"), ("other_info", "TEXT"), ("approval_requested_at", "TEXT"), ("approval_decision_at", "TEXT"), ("invoice_ready_at", "TEXT")]),
            ("customer_vehicles", [("inspection_due_date", "TEXT"), ("inspection_notice_date", "TEXT"), ("inspection_notified_at", "TEXT"), ("qr_token", "TEXT")]),
            ("automotive_service_forms", [("tracking_no", "TEXT"), ("customer_id", "INTEGER"), ("vehicle_id", "INTEGER"), ("vehicle_plate", "TEXT"), ("vehicle_vin", "TEXT"), ("engine_code", "TEXT"), ("entry_odometer", "INTEGER DEFAULT 0"), ("exit_odometer", "INTEGER DEFAULT 0"), ("fuel_level_entry", "TEXT"), ("fuel_level_exit", "TEXT"), ("acceptance_notes", "TEXT"), ("checklist_json", "TEXT"), ("damage_marks_json", "TEXT"), ("customer_approval", "INTEGER DEFAULT 0"), ("kvkk_approval", "INTEGER DEFAULT 0"), ("customer_approval_text", "TEXT"), ("kvkk_text", "TEXT"), ("updated_at", "TEXT")])
        ]:
            self.cursor.execute(f"PRAGMA table_info({self._safe_identifier(table)})")
            cols = {row[1] for row in (self.cursor.fetchall() or [])}
            for cname, ctype in items:
                if cname not in cols:
                    self.cursor.execute(f"ALTER TABLE {self._safe_identifier(table)} ADD COLUMN {self._safe_identifier(cname)} {ctype}")

        for tname in ["automotive_checkup_forms", "automotive_quote_forms", "automotive_quote_items", "automotive_delivery_forms", "automotive_vehicle_history_events", "automotive_warranty_campaigns", "automotive_tire_suspension_records", "automotive_battery_electrical_tests", "automotive_maintenance_templates", "automotive_maintenance_template_items", "automotive_parts_requests", "automotive_parts_request_items", "automotive_damage_marks"]:
            self.cursor.execute(f"PRAGMA table_info({self._safe_identifier(tname)})")
            tcols = {row[1] for row in (self.cursor.fetchall() or [])}
            if "created_at" in tcols:
                self.cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{self._safe_identifier(tname)}_created_at ON {self._safe_identifier(tname)}(created_at)")
