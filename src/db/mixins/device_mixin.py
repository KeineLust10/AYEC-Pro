# -*- coding: utf-8 -*-

"""
Device Mixin
Cihaz/Servis kayıtları ile ilgili database metodları
"""

from datetime import datetime
from src.utils.logger import logger


class DeviceMixin:
    """Cihazlar için database metodları"""

    DEVICE_SEARCHABLE_FIELDS = {
        "tracking_no",
        "customer_name",
        "device_type",
        "device_brand",
        "device_model",
        "serial_no",
        "status",
        "entry_date",
        "delivery_date",
        "technician",
        "notes",
    }

    def _safe_identifier(self, value):
        value = str(value or "").strip()
        if not value or not value.replace("_", "").isalnum():
            raise ValueError(f"Unsafe SQL identifier: {value!r}")
        return value

    def _normalize_status_key(self, status):
        text = str(status or "").strip().casefold()
        return text.replace("ı", "i")

    def _is_in_repair_status(self, status):
        return self._normalize_status_key(status) == "tamirde"

    def _resolve_customer_id_by_name(self, customer_name):
        try:
            name = str(customer_name or "").strip()
            if not name:
                return None
            self.cursor.execute(
                "SELECT id FROM customers WHERE TRIM(UPPER(name))=TRIM(UPPER(?)) LIMIT 1",
                (name,),
            )
            row = self.cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else None
        except Exception:
            return None

    def _get_service_total_amount(
        self, tracking_no, labor_cost=None, cargo_fee=None, price=None
    ):
        try:
            base_labor = float(labor_cost or 0.0)
            base_price = float(price or 0.0)
            base_cargo = float(cargo_fee or 0.0)
        except Exception:
            base_labor, base_price, base_cargo = 0.0, 0.0, 0.0

        # Eski kayıtlarda işçilik bazen price alanında tutuluyor olabilir.
        if base_labor <= 0 and base_price > 0:
            base_labor = base_price

        parts_total = 0.0
        try:
            self.cursor.execute("PRAGMA table_info(used_parts)")
            cols = [row[1] for row in (self.cursor.fetchall() or [])]
            deleted_col = (
                "is_deleted"
                if "is_deleted" in cols
                else ("is_archived" if "is_archived" in cols else None)
            )
            qty_expr = "COALESCE(quantity, 1)" if "quantity" in cols else "1"
            parts_query = f"SELECT COALESCE(SUM(COALESCE(price, 0) * {qty_expr}), 0) FROM used_parts WHERE tracking_no=?"
            if deleted_col:
                parts_query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            self.cursor.execute(parts_query, (tracking_no,))
            parts_total = float((self.cursor.fetchone() or [0])[0] or 0.0)
        except Exception:
            parts_total = 0.0

        total_amount = round(max(0.0, base_labor + base_cargo + parts_total), 2)
        return total_amount

    def _sync_service_debt_from_tracking(
        self, tracking_no, create_if_missing=False, reason=""
    ):
        """Servis DEBIT kaydını servis toplamı ile senkronize et."""
        try:
            if not tracking_no:
                return False

            self.cursor.execute("PRAGMA table_info(devices)")
            device_cols = {row[1] for row in (self.cursor.fetchall() or [])}

            select_parts = ["tracking_no"]
            if "customer_id" in device_cols:
                select_parts.append("customer_id")
            if "customer_name" in device_cols:
                select_parts.append("customer_name")
            if "status" in device_cols:
                select_parts.append("status")
            if "labor_cost" in device_cols:
                select_parts.append("labor_cost")
            if "cargo_fee" in device_cols:
                select_parts.append("cargo_fee")
            if "price" in device_cols:
                select_parts.append("price")

            self.cursor.execute(
                "SELECT {fields} FROM devices WHERE tracking_no=?".format(
                    fields=", ".join(select_parts)
                ),
                (tracking_no,),
            )
            row = self.cursor.fetchone()
            if not row:
                return False

            row_map = dict(zip(select_parts, row))
            customer_name = (row_map.get("customer_name") or "").strip()
            customer_id = row_map.get("customer_id")
            status = row_map.get("status") or ""
            labor_cost = row_map.get("labor_cost")
            cargo_fee = row_map.get("cargo_fee")
            price = row_map.get("price")

            if not customer_id and customer_name:
                customer_id = self._resolve_customer_id_by_name(customer_name)
                if customer_id and "customer_id" in device_cols:
                    try:
                        self.cursor.execute(
                            "UPDATE devices SET customer_id=? WHERE tracking_no=?",
                            (customer_id, tracking_no),
                        )
                        self.conn.commit()
                    except Exception as bind_err:
                        logger.debug(
                            "customer_id bind skipped for %s: %s", tracking_no, bind_err
                        )

            if not customer_id:
                return False

            total_amount = self._get_service_total_amount(
                tracking_no,
                labor_cost=labor_cost,
                cargo_fee=cargo_fee,
                price=price,
            )

            self.cursor.execute(
                """
                SELECT id, amount, currency, exchange_rate
                FROM currency_transactions
                WHERE customer_id=? AND tracking_no=? AND transaction_type='DEBIT'
                ORDER BY id DESC
                LIMIT 1
                """,
                (customer_id, tracking_no),
            )
            existing = self.cursor.fetchone()

            if existing:
                debt_id, _old_amount, _debt_currency, debt_rate = existing
                if total_amount <= 0:
                    return False

                debt_rate = float(debt_rate or 1.0)
                try_equivalent = round(total_amount * debt_rate, 4)

                paid_sum = 0.0
                try:
                    self.cursor.execute(
                        "SELECT COALESCE(SUM(amount), 0) FROM payment_debt_links WHERE debt_txn_id=?",
                        (debt_id,),
                    )
                    paid_sum = float((self.cursor.fetchone() or [0])[0] or 0.0)
                except Exception:
                    paid_sum = 0.0

                new_current_balance = round((-1.0 * total_amount) + paid_sum, 2)

                self.cursor.execute(
                    """
                    UPDATE currency_transactions
                    SET amount=?, try_equivalent=?, current_balance=?
                    WHERE id=?
                    """,
                    (total_amount, try_equivalent, new_current_balance, debt_id),
                )
                self.conn.commit()
                try:
                    self.recalculate_all_customer_balances()
                except Exception:
                    pass
                return True

            if not create_if_missing:
                return False

            if not self._is_in_repair_status(status):
                return False

            if total_amount <= 0:
                return False

            try:
                from src.utils.currency_helper import CurrencyHelper

                debt_currency = CurrencyHelper.get_code(self)
            except Exception:
                debt_currency = "TRY"

            debt_currency = str(debt_currency or "TRY").upper()
            if len(debt_currency) > 8:
                debt_currency = "TRY"

            debt_desc = (
                f"Servis Borcu (Tamirde): #{tracking_no} - {customer_name or 'Müşteri'}"
            )
            if reason:
                debt_desc += f" [{reason}]"

            return bool(
                self.add_currency_transaction(
                    customer_id=customer_id,
                    amount=total_amount,
                    currency=debt_currency,
                    transaction_type="DEBIT",
                    exchange_rate=1.0,
                    description=debt_desc,
                    tracking_no=tracking_no,
                )
            )
        except Exception as e:
            logger.error("Service debt sync failed for %s: %s", tracking_no, e)
            return False

    def _get_default_device_brand_pairs(self):
        return [
            ("Laptop", "Monster"),
            ("Laptop", "Lenovo"),
            ("Laptop", "ASUS"),
            ("Laptop", "HP"),
            ("Laptop", "Dell"),
            ("Laptop", "MSI"),
            ("Laptop", "Acer"),
            ("Laptop", "Casper"),
            ("Laptop", "Apple"),
            ("Masaüstü", "OEM"),
            ("Masaüstü", "ASUS"),
            ("Masaüstü", "MSI"),
            ("Masaüstü", "Gigabyte"),
            ("Masaüstü", "Dell"),
            ("Masaüstü", "HP"),
            ("All In One", "Lenovo"),
            ("All In One", "HP"),
            ("All In One", "Dell"),
            ("Monitör", "Samsung"),
            ("Monitör", "LG"),
            ("Monitör", "AOC"),
            ("Monitör", "ASUS"),
            ("Mini PC", "Intel"),
            ("Mini PC", "ASUS"),
            ("Mini PC", "HP"),
        ]

    def add_device(self, data):
        """Yeni cihaz/servis kaydı ekle"""
        try:
            try:
                self.cursor.execute("PRAGMA table_info(devices)")
                device_columns = {row[1] for row in (self.cursor.fetchall() or [])}
                if (
                    "customer_id" in device_columns
                    and not data.get("customer_id")
                    and data.get("customer_name")
                ):
                    resolved_customer_id = self._resolve_customer_id_by_name(
                        data.get("customer_name")
                    )
                    if resolved_customer_id:
                        data["customer_id"] = resolved_customer_id
            except Exception:
                pass

            safe_items = [
                (key, value)
                for key, value in data.items()
                if isinstance(key, str) and key.replace("_", "").isalnum()
            ]
            if not safe_items:
                return None
            keys = ", ".join(self._safe_identifier(key) for key, _ in safe_items)
            values_ph = ", ".join(["?"] * len(safe_items))
            values = tuple(value for _, value in safe_items)
            sql = "INSERT INTO devices ({keys}) VALUES ({values_ph})".format(
                keys=keys,
                values_ph=values_ph,
            )
            self.cursor.execute(sql, values)
            tracking_no = data.get("tracking_no")
            status = data.get("status")
            self.conn.commit()

            if tracking_no and self._is_in_repair_status(status):
                self._sync_service_debt_from_tracking(
                    tracking_no,
                    create_if_missing=True,
                    reason="status_tamirde",
                )

            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Device add error: {e}")
            return None

    def get_all_devices(self, include_archived=False):
        """Tüm cihazları getir"""
        if include_archived:
            self.cursor.execute(
                "SELECT * FROM devices WHERE COALESCE(is_deleted, 0) = 0 ORDER BY entry_date DESC"
            )
        else:
            self.cursor.execute(
                "SELECT * FROM devices WHERE COALESCE(is_deleted, 0) = 0 AND COALESCE(is_archived, 0)=0 ORDER BY entry_date DESC"
            )
        return self.cursor.fetchall()

    def get_devices_by_status(self, status):
        """Belirli durumdaki cihazları getir"""
        self.cursor.execute(
            "SELECT * FROM devices WHERE status=? AND COALESCE(is_deleted, 0) = 0",
            (status,),
        )
        return self.cursor.fetchall()

    def get_recent_services(self, limit=10):
        """Son servisleri getir"""
        try:
            safe_limit = max(1, int(limit))
        except (TypeError, ValueError):
            safe_limit = 10
        self.cursor.execute(
            "SELECT * FROM devices WHERE COALESCE(is_deleted, 0) = 0 ORDER BY entry_date DESC LIMIT ?",
            (safe_limit,),
        )
        return self.cursor.fetchall()

    def search_devices(self, query):
        """Cihaz ara"""
        q = f"%{query}%"
        self.cursor.execute(
            """
            SELECT * FROM devices 
            WHERE (customer_name LIKE ? OR tracking_no LIKE ? OR device_model LIKE ?)
            AND COALESCE(is_deleted, 0) = 0
        """,
            (q, q, q),
        )
        return self.cursor.fetchall()

    def advanced_search(self, criteria):
        """Gelişmiş arama"""
        try:
            conditions = ["COALESCE(is_deleted, 0) = 0"]
            params = []

            for key, value in criteria.items():
                if value and key in self.DEVICE_SEARCHABLE_FIELDS:
                    conditions.append(f"{key} LIKE ?")
                    params.append(f"%{value}%")

            if len(conditions) == 1:
                return self.get_all_devices()

            sql = "SELECT * FROM devices WHERE {conditions}".format(
                conditions=" AND ".join(conditions)
            )
            self.cursor.execute(sql, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Advanced search error: {e}")
            return []

    def update_status(self, tracking_no, status):
        """Cihaz durumunu güncelle"""
        try:
            self.cursor.execute(
                "UPDATE devices SET status=? WHERE tracking_no=?",
                (status, tracking_no),
            )
            self.conn.commit()

            if self._is_in_repair_status(status):
                self._sync_service_debt_from_tracking(
                    tracking_no,
                    create_if_missing=True,
                    reason="status_tamirde",
                )

            # Trigger notification if needed
            self.trigger_status_notification(tracking_no, status)
            return True
        except Exception as e:
            logger.error(f"Status update error: {e}")
            return False

    def delete_device(self, tracking_no):
        """Cihaz kaydını soft delete yap"""
        try:
            if hasattr(self, "soft_delete_record"):
                return self.soft_delete_record("devices", "tracking_no", tracking_no)
            deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "UPDATE devices SET is_deleted=1, deleted_at=? WHERE tracking_no=?",
                (deleted_at, tracking_no),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Device delete error: {e}")
            return False

    def add_device_test(self, tracking_no, test_name, result, note="", technician=""):
        """Cihaz test sonucu ekle"""
        try:
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                """
                INSERT INTO device_tests (tracking_no, test_name, result, note, technician, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (tracking_no, test_name, result, note, technician, created_at),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Device test add error: {e}")
            return False

    def get_device_tests(self, tracking_no):
        """Cihaz test sonuçlarını getir"""
        try:
            self.cursor.execute(
                "SELECT * FROM device_tests WHERE tracking_no=?", (tracking_no,)
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error("Get device tests error: %s", e)
            return []

    def save_test_results(self, tracking_no, tests, technician="Teknisyen"):
        """Test sonuçlarını kaydet"""
        for test_name, result in tests.items():
            self.add_device_test(tracking_no, test_name, result, "", technician)

    def get_test_results(self, tracking_no):
        """Test sonuçlarını getir (alias)"""
        return self.get_device_tests(tracking_no)

    def update_financials(self, tracking_no, labor_cost, repair_details):
        """Mali bilgileri güncelle"""
        self.cursor.execute(
            "UPDATE devices SET labor_cost=?, repair_details=? WHERE tracking_no=?",
            (labor_cost, repair_details, tracking_no),
        )
        self.conn.commit()
        self._sync_service_debt_from_tracking(
            tracking_no,
            create_if_missing=True,
            reason="financial_update",
        )

    def get_critical_devices(self, limit=5):
        """Kritik durumdaki cihazları getir"""
        self.cursor.execute(
            """
            SELECT * FROM devices 
            WHERE status IN ('Onay Bekliyor', 'Parça Bekliyor') 
            AND COALESCE(is_deleted, 0) = 0
            ORDER BY entry_date 
            LIMIT ?
        """,
            (limit,),
        )
        return self.cursor.fetchall()

    def create_device_brands_table(self):
        """Cihaz markaları tablosunu oluştur"""
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS device_brands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_type TEXT,
                    brand TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            for device_type, brand in self._get_default_device_brand_pairs():
                self.cursor.execute(
                    """
                    INSERT INTO device_brands (device_type, brand, is_active)
                    SELECT ?, ?, 1
                    WHERE NOT EXISTS (
                        SELECT 1 FROM device_brands
                        WHERE device_type=? AND brand=?
                    )
                    """,
                    (device_type, brand, device_type, brand),
                )
            self.conn.commit()
            logger.info("device_brands table ensured")
        except Exception as e:
            logger.error(f"Failed to create device_brands table: {e}")

    def trigger_status_notification(self, tracking_no, status):
        """Durum değiştiğinde bildirim tetikle"""
        try:
            # SMS veya WhatsApp bildirimi yapılabilir
            logger.info(f"Status notification triggered for {tracking_no}: {status}")
        except Exception as e:
            logger.error(f"Notification trigger error: {e}")
