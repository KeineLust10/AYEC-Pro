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

    def _get_device_columns(self):
        try:
            cached = getattr(self, "_device_columns_cache", None)
            if cached:
                return cached
            self.cursor.execute("PRAGMA table_info(devices)")
            columns = {row[1] for row in (self.cursor.fetchall() or [])}
            self._device_columns_cache = columns
            return columns
        except Exception:
            return set()

    def _device_select_clause(self, columns=None):
        if not columns:
            return "*"
        available = self._get_device_columns()
        selected = []
        for column in columns:
            safe_column = self._safe_identifier(column)
            if not available or safe_column in available:
                selected.append(safe_column)
        return ", ".join(selected) if selected else "*"

    def _normalize_query_limit(self, limit, default=None, maximum=1000):
        if limit is None:
            return default
        try:
            value = int(limit)
        except (TypeError, ValueError):
            return default
        if value <= 0:
            return default
        return min(value, maximum)

    def _normalize_status_key(self, status):
        text = str(status or "").strip().casefold()
        return text.replace("ı", "i")

    def _is_in_repair_status(self, status):
        return self._normalize_status_key(status) == "tamirde"

    def _should_create_service_debt(self, status):
        normalized = self._normalize_status_key(status)
        # Once a part/labor is attached, an open service must become a debit
        # even before the technician changes the status to "tamirde". This
        # keeps collection allocation consistent with the service total while
        # the over-collection guard still rejects payments after settlement.
        return normalized in {"bekliyor", "acik", "tamirde", "teslim edildi"}

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

        parts_total = self._get_used_parts_total_try(tracking_no)

        total_amount = round(max(0.0, base_labor + base_cargo + parts_total), 2)
        return total_amount

    def _get_used_parts_total_try(self, tracking_no):
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
            currency_expr = (
                "COALESCE(currency, 'TRY')" if "currency" in cols else "'TRY'"
            )
            rate_expr = (
                "COALESCE(exchange_rate, 1)" if "exchange_rate" in cols else "1"
            )
            price_try_expr = (
                "COALESCE(price_try, 0)" if "price_try" in cols else "0"
            )
            parts_query = (
                "SELECT COALESCE(price, 0), {qty}, {currency}, {rate}, "
                "{price_try} FROM used_parts WHERE tracking_no=?"
            ).format(
                qty=qty_expr,
                currency=currency_expr,
                rate=rate_expr,
                price_try=price_try_expr,
            )
            if deleted_col:
                parts_query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            self.cursor.execute(parts_query, (tracking_no,))
            from src.utils.currency_helper import CurrencyHelper

            for price, quantity, currency, stored_rate, stored_price_try in (
                self.cursor.fetchall() or []
            ):
                price = float(price or 0.0)
                quantity = float(quantity or 1.0)
                currency = str(currency or "TRY").upper()
                stored_rate = float(stored_rate or 0.0)
                unit_try = float(stored_price_try or 0.0)
                if unit_try <= 0:
                    if currency == "TRY":
                        unit_try = price
                    elif stored_rate > 0:
                        unit_try = price * stored_rate
                    else:
                        current_rate = CurrencyHelper.require_rate(self, currency)
                        unit_try = price * current_rate
                parts_total += unit_try * quantity
        except Exception as exc:
            logger.error(
                "Used-parts total could not be calculated for %s: %s",
                tracking_no,
                exc,
            )
            raise
        return round(parts_total, 4)

    def _get_used_parts_totals_by_currency(self, tracking_no):
        """Return used-part totals in their original currencies and rates."""
        totals = {}
        self.cursor.execute("PRAGMA table_info(used_parts)")
        cols = {row[1] for row in (self.cursor.fetchall() or [])}
        qty_expr = "COALESCE(quantity, 1)" if "quantity" in cols else "1"
        cur_expr = "COALESCE(currency, 'TRY')" if "currency" in cols else "'TRY'"
        rate_expr = "COALESCE(exchange_rate, 1)" if "exchange_rate" in cols else "1"
        deleted = " AND (is_deleted=0 OR is_deleted IS NULL)" if "is_deleted" in cols else ""
        rows = self.cursor.execute(
            f"SELECT COALESCE(price,0), {qty_expr}, {cur_expr}, {rate_expr} FROM used_parts WHERE tracking_no=?{deleted}",
            (tracking_no,),
        ).fetchall()
        for price, qty, currency, rate in rows:
            code = str(currency or "TRY").upper()
            totals[code] = totals.get(code, 0.0) + round(float(price or 0) * float(qty or 1), 4)
            totals.setdefault(f"{code}_RATE", float(rate or 1.0))
        return {code: round(value, 4) for code, value in totals.items()}

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
            if not self.create_payment_debt_links_table():
                raise RuntimeError("Payment allocation schema is unavailable")

            total_amount = self._get_service_total_amount(
                tracking_no,
                labor_cost=labor_cost,
                cargo_fee=cargo_fee,
                price=price,
            )
            part_totals = self._get_used_parts_totals_by_currency(tracking_no)
            service_currency = "TRY"
            non_try = [code for code in ("USD", "EUR") if part_totals.get(code, 0) > 0]
            if len(non_try) == 1 and not float(labor_cost or 0) and not float(cargo_fee or 0):
                service_currency = non_try[0]
                total_amount = part_totals[service_currency]
                debt_rate = part_totals.get(f"{service_currency}_RATE", 1.0)
            else:
                debt_rate = 1.0

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

                try_equivalent = round(total_amount, 4)

                paid_sum = 0.0
                self.cursor.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM payment_debt_links WHERE debt_txn_id=?",
                    (debt_id,),
                )
                paid_sum = float((self.cursor.fetchone() or [0])[0] or 0.0)
                if paid_sum <= 0:
                    self.cursor.execute(
                        """
                        SELECT COALESCE(SUM(amount), 0)
                        FROM currency_transactions
                        WHERE customer_id=?
                          AND (tracking_no=? OR tracking_no=? || '-PAY')
                          AND transaction_type='CREDIT'
                          AND currency=?
                        """,
                        (customer_id, tracking_no, tracking_no, _debt_currency or "TRY"),
                    )
                    paid_sum = float((self.cursor.fetchone() or [0])[0] or 0.0)

                new_current_balance = round((-1.0 * total_amount) + paid_sum, 2)

                self.cursor.execute(
                    """
                    UPDATE currency_transactions
                    SET amount=?, currency=?, exchange_rate=?,
                        try_equivalent=?, current_balance=?
                    WHERE id=?
                    """,
                    (total_amount, service_currency, debt_rate, round(total_amount * debt_rate, 4), new_current_balance, debt_id),
                )
                self.conn.commit()
                _debt_currency = service_currency
                if hasattr(self, "auto_allocate_unlinked_customer_payments"):
                    self.auto_allocate_unlinked_customer_payments(
                        customer_id=customer_id,
                        currency=_debt_currency,
                    )
                self.recalculate_customer_currency_balance(
                    customer_id,
                    _debt_currency,
                )
                return True

            if not create_if_missing:
                return False

            if not self._should_create_service_debt(status):
                return False

            if total_amount <= 0:
                return False

            debt_currency = service_currency

            debt_desc = (
                f"Servis Borcu (Tamirde): #{tracking_no} - {customer_name or 'Müşteri'}"
            )
            if reason:
                debt_desc += f" [{reason}]"

            created = bool(
                self.add_currency_transaction(
                    customer_id=customer_id,
                    amount=total_amount,
                    currency=debt_currency,
                    transaction_type="DEBIT",
                    exchange_rate=debt_rate,
                    description=debt_desc,
                    tracking_no=tracking_no,
                )
            )
            if not created:
                return False

            paid_sum = 0.0
            self.cursor.execute(
                """
                SELECT COALESCE(SUM(amount), 0)
                FROM currency_transactions
                WHERE customer_id=?
                  AND tracking_no=?
                  AND transaction_type='CREDIT'
                  AND currency=?
                """,
                (customer_id, tracking_no, tracking_no, debt_currency),
            )
            paid_sum = float((self.cursor.fetchone() or [0])[0] or 0.0)

            if paid_sum > 0:
                debt_txn_id = self.get_last_currency_transaction_id()
                if debt_txn_id:
                    self.cursor.execute(
                        """
                        UPDATE currency_transactions
                        SET current_balance=?
                        WHERE id=?
                        """,
                        (round((-1.0 * total_amount) + paid_sum, 2), debt_txn_id),
                    )
                    self.conn.commit()

            if hasattr(self, "auto_allocate_unlinked_customer_payments"):
                self.auto_allocate_unlinked_customer_payments(
                    customer_id=customer_id,
                    currency=debt_currency,
                )

            self.recalculate_customer_currency_balance(
                customer_id,
                debt_currency,
            )
            return True
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

    def _get_default_device_model_rows(self):
        """Return the maintained 2021-2026 device catalog seed rows."""
        return [
            ("bilgisayar", "Laptop", "Apple", "MacBook Air M2", 2022, "apple.com"),
            ("bilgisayar", "Laptop", "Apple", "MacBook Air M3", 2024, "apple.com"),
            ("bilgisayar", "Laptop", "Apple", "MacBook Air M4", 2025, "apple.com"),
            ("bilgisayar", "Laptop", "Lenovo", "ThinkPad E14 Gen 5", 2023, "lenovo.com"),
            ("bilgisayar", "Laptop", "Lenovo", "ThinkPad T14 Gen 5", 2024, "lenovo.com"),
            ("bilgisayar", "Laptop", "Lenovo", "LOQ 15", 2024, "lenovo.com"),
            ("bilgisayar", "Laptop", "ASUS", "Zenbook 14", 2024, "asus.com"),
            ("bilgisayar", "Laptop", "ASUS", "ROG Strix G16", 2024, "asus.com"),
            ("bilgisayar", "Laptop", "HP", "Pavilion Plus 14", 2024, "hp.com"),
            ("bilgisayar", "Laptop", "HP", "Victus 15", 2024, "hp.com"),
            ("bilgisayar", "Laptop", "Dell", "Latitude 5450", 2024, "dell.com"),
            ("bilgisayar", "Laptop", "Dell", "Inspiron 15", 2024, "dell.com"),
            ("bilgisayar", "Laptop", "Acer", "Aspire 5", 2024, "acer.com"),
            ("bilgisayar", "Laptop", "Acer", "Nitro V 15", 2024, "acer.com"),
            ("bilgisayar", "Laptop", "MSI", "Katana 15", 2024, "msi.com"),
            ("bilgisayar", "Masa\u00fcst\u00fc PC", "Apple", "Mac mini M4", 2024, "apple.com"),
            ("bilgisayar", "Masa\u00fcst\u00fc PC", "Lenovo", "IdeaCentre Tower", 2024, "lenovo.com"),
            ("bilgisayar", "Masa\u00fcst\u00fc PC", "ASUS", "ROG G22", 2024, "asus.com"),
            ("bilgisayar", "Monit\u00f6r", "Samsung", "Odyssey G5", 2024, "samsung.com"),
            ("bilgisayar", "Monit\u00f6r", "LG", "UltraGear", 2024, "lg.com"),
            ("bilgisayar", "Monit\u00f6r", "ASUS", "TUF Gaming VG27", 2024, "asus.com"),
            ("cep_telefonu", "Cep Telefonu", "Apple", "iPhone 13", 2021, "apple.com"),
            ("cep_telefonu", "Cep Telefonu", "Apple", "iPhone 14", 2022, "apple.com"),
            ("cep_telefonu", "Cep Telefonu", "Apple", "iPhone 15", 2023, "apple.com"),
            ("cep_telefonu", "Cep Telefonu", "Apple", "iPhone 16", 2024, "apple.com"),
            ("cep_telefonu", "Cep Telefonu", "Apple", "iPhone 17", 2025, "apple.com"),
            ("cep_telefonu", "Cep Telefonu", "Samsung", "Galaxy S21", 2021, "samsung.com"),
            ("cep_telefonu", "Cep Telefonu", "Samsung", "Galaxy S23", 2023, "samsung.com"),
            ("cep_telefonu", "Cep Telefonu", "Samsung", "Galaxy S24", 2024, "samsung.com"),
            ("cep_telefonu", "Cep Telefonu", "Samsung", "Galaxy S25", 2025, "samsung.com"),
            ("cep_telefonu", "Cep Telefonu", "Samsung", "Galaxy A55", 2024, "samsung.com"),
            ("cep_telefonu", "Cep Telefonu", "Samsung", "Galaxy A56", 2025, "samsung.com"),
            ("cep_telefonu", "Cep Telefonu", "Xiaomi", "Redmi Note 13", 2024, "mi.com"),
            ("cep_telefonu", "Cep Telefonu", "Xiaomi", "Redmi Note 14", 2025, "mi.com"),
            ("cep_telefonu", "Cep Telefonu", "Xiaomi", "Xiaomi 14T", 2024, "mi.com"),
            ("cep_telefonu", "Cep Telefonu", "Google", "Pixel 8", 2023, "store.google.com"),
            ("cep_telefonu", "Cep Telefonu", "Google", "Pixel 9", 2024, "store.google.com"),
            ("cep_telefonu", "Cep Telefonu", "OPPO", "Reno 12", 2024, "oppo.com"),
            ("cep_telefonu", "Cep Telefonu", "HONOR", "HONOR 200", 2024, "honor.com"),
            ("cep_telefonu", "Tablet", "Apple", "iPad 10. nesil", 2022, "apple.com"),
            ("cep_telefonu", "Tablet", "Apple", "iPad Air M2", 2024, "apple.com"),
            ("cep_telefonu", "Tablet", "Samsung", "Galaxy Tab S9", 2023, "samsung.com"),
            ("cep_telefonu", "Tablet", "Samsung", "Galaxy Tab S10", 2024, "samsung.com"),
            ("cep_telefonu", "Tablet", "Xiaomi", "Pad 6", 2023, "mi.com"),
            ("cep_telefonu", "Ak\u0131ll\u0131 Saat", "Apple", "Apple Watch Series 10", 2024, "apple.com"),
            ("cep_telefonu", "Ak\u0131ll\u0131 Saat", "Samsung", "Galaxy Watch7", 2024, "samsung.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Ev Merkezi", "Tapo", "H100", 2023, "tp-link.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Ev Merkezi", "Tapo", "H200", 2024, "tp-link.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Ev Merkezi", "Tapo", "H500", 2024, "tp-link.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Ev Merkezi", "Aqara", "Hub M2", 2021, "aqara.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Ev Merkezi", "Aqara", "Hub M3", 2024, "aqara.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Priz", "Tapo", "P110", 2021, "tp-link.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Kamera", "Tapo", "C210", 2021, "tp-link.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Kamera", "Tapo", "C520WS", 2023, "tp-link.com"),
            ("akilli_ev", "Sens\u00f6r", "Tapo", "T100", 2023, "tp-link.com"),
            ("akilli_ev", "Sens\u00f6r", "Tapo", "T110", 2023, "tp-link.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Ayd\u0131nlatma", "Tapo", "L530E", 2023, "tp-link.com"),
            ("akilli_ev", "Termostat", "Google", "Nest Thermostat", 2021, "store.google.com"),
            ("akilli_ev", "Ak\u0131ll\u0131 Ev Merkezi", "Google", "Nest Hub 2nd Gen", 2021, "store.google.com"),
            ("akilli_ev", "Robot S\u00fcp\u00fcrge", "Roborock", "Qrevo", 2023, "roborock.com"),
            ("akilli_ev", "Robot S\u00fcp\u00fcrge", "Roborock", "S8", 2023, "roborock.com"),
        ]

    def create_device_model_catalog_table(self):
        """Ensure the user-managed brand/model catalog schema and defaults."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS device_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_profile TEXT NOT NULL,
                device_type TEXT NOT NULL,
                brand TEXT NOT NULL,
                model TEXT NOT NULL,
                release_year INTEGER,
                source TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(business_profile, device_type, brand, model)
            )
            """
        )
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_device_models_lookup "
            "ON device_models (business_profile, device_type, brand, is_active)"
        )

    def refresh_device_model_catalog(self):
        """Upsert the reviewed catalog and expose its brands in brand management."""
        self.create_device_model_catalog_table()
        for profile, device_type, brand, model, year, source in self._get_default_device_model_rows():
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO device_models
                    (business_profile, device_type, brand, model, release_year, source, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                """,
                (profile, device_type, brand, model, year, source),
            )
            self.cursor.execute(
                """
                INSERT INTO device_brands (device_type, brand, is_active)
                SELECT ?, ?, 1
                WHERE NOT EXISTS (
                    SELECT 1 FROM device_brands WHERE device_type=? AND brand=?
                )
                """,
                (device_type, brand, device_type, brand),
            )
        self.conn.commit()

    def get_device_model_catalog(self, profiles=None, device_type=None, brand=None):
        """Return active catalog rows filtered by business profile, type, and brand."""
        self.create_device_model_catalog_table()
        clauses = ["is_active=1"]
        params = []
        profiles = [str(item).strip() for item in (profiles or []) if str(item).strip()]
        if profiles:
            clauses.append("business_profile IN ({})".format(",".join("?" for _ in profiles)))
            params.extend(profiles)
        if device_type:
            clauses.append("device_type=?")
            params.append(str(device_type).strip())
        if brand:
            clauses.append("brand=?")
            params.append(str(brand).strip())
        sql = (
            "SELECT business_profile, device_type, brand, model, release_year, source "
            "FROM device_models WHERE {} ORDER BY brand, model".format(" AND ".join(clauses))
        )
        self.cursor.execute(sql, tuple(params))
        return self.cursor.fetchall() or []

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

            if tracking_no and self._should_create_service_debt(status):
                self._sync_service_debt_from_tracking(
                    tracking_no,
                    create_if_missing=True,
                    reason=f"status_{self._normalize_status_key(status)}",
                )

            return self.cursor.lastrowid
        except Exception as e:
            logger.error(f"Device add error: {e}")
            return None

    def get_all_devices(self, include_archived=False, columns=None, limit=None, offset=0):
        """Tüm cihazları getir"""
        select_clause = self._device_select_clause(columns)
        where = ["COALESCE(is_deleted, 0) = 0"]
        if not include_archived:
            where.append("COALESCE(is_archived, 0)=0")
        sql = "SELECT {fields} FROM devices WHERE {where} ORDER BY entry_date DESC".format(
            fields=select_clause,
            where=" AND ".join(where),
        )
        params = []
        safe_limit = self._normalize_query_limit(limit)
        if safe_limit:
            sql += " LIMIT ?"
            params.append(safe_limit)
            try:
                safe_offset = max(0, int(offset or 0))
            except (TypeError, ValueError):
                safe_offset = 0
            if safe_offset:
                sql += " OFFSET ?"
                params.append(safe_offset)
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def get_devices_by_status(self, status, columns=None, limit=None, include_archived=False):
        """Belirli durumdaki cihazları getir"""
        select_clause = self._device_select_clause(columns)
        where = ["status=?", "COALESCE(is_deleted, 0) = 0"]
        if not include_archived:
            where.append("COALESCE(is_archived, 0)=0")
        sql = "SELECT {fields} FROM devices WHERE {where} ORDER BY entry_date DESC".format(
            fields=select_clause,
            where=" AND ".join(where),
        )
        params = [status]
        safe_limit = self._normalize_query_limit(limit)
        if safe_limit:
            sql += " LIMIT ?"
            params.append(safe_limit)
        self.cursor.execute(sql, params)
        return self.cursor.fetchall()

    def get_recent_services(self, limit=10, columns=None):
        """Son servisleri getir"""
        try:
            safe_limit = max(1, int(limit))
        except (TypeError, ValueError):
            safe_limit = 10
        select_clause = self._device_select_clause(columns)
        self.cursor.execute(
            "SELECT {fields} FROM devices WHERE COALESCE(is_deleted, 0) = 0 AND COALESCE(is_archived, 0)=0 ORDER BY entry_date DESC LIMIT ?".format(
                fields=select_clause
            ),
            (safe_limit,),
        )
        return self.cursor.fetchall()

    def search_devices(self, query, columns=None, limit=100):
        """Cihaz ara"""
        q = f"%{query}%"
        select_clause = self._device_select_clause(columns)
        safe_limit = self._normalize_query_limit(limit, default=100)
        self.cursor.execute(
            """
            SELECT {fields} FROM devices
            WHERE (customer_name LIKE ? OR tracking_no LIKE ? OR device_model LIKE ?)
            AND COALESCE(is_deleted, 0) = 0 AND COALESCE(is_archived, 0)=0
            ORDER BY entry_date DESC
            LIMIT ?
        """.format(fields=select_clause),
            (q, q, q, safe_limit),
        )
        return self.cursor.fetchall()

    def advanced_search(self, criteria, columns=None, limit=200):
        """Gelişmiş arama"""
        try:
            conditions = ["COALESCE(is_deleted, 0) = 0"]
            params = []

            for key, value in criteria.items():
                if value and key in self.DEVICE_SEARCHABLE_FIELDS:
                    conditions.append(f"{key} LIKE ?")
                    params.append(f"%{value}%")

            if len(conditions) == 1:
                return self.get_all_devices(columns=columns, limit=limit)

            select_clause = self._device_select_clause(columns)
            sql = "SELECT {fields} FROM devices WHERE {conditions} ORDER BY entry_date DESC".format(
                fields=select_clause,
                conditions=" AND ".join(conditions),
            )
            safe_limit = self._normalize_query_limit(limit, default=200)
            if safe_limit:
                sql += " LIMIT ?"
                params.append(safe_limit)
            self.cursor.execute(sql, params)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Advanced search error: {e}")
            return []

    def get_device_by_tracking_no(self, tracking_no, columns=None, include_deleted=False):
        select_clause = self._device_select_clause(columns)
        where = ["tracking_no=?"]
        if not include_deleted:
            where.append("COALESCE(is_deleted, 0) = 0")
        sql = "SELECT {fields} FROM devices WHERE {where} LIMIT 1".format(
            fields=select_clause,
            where=" AND ".join(where),
        )
        self.cursor.execute(sql, (tracking_no,))
        return self.cursor.fetchone()

    def update_status(self, tracking_no, status):
        """Cihaz durumunu güncelle"""
        try:
            self.cursor.execute(
                "UPDATE devices SET status=? WHERE tracking_no=?",
                (status, tracking_no),
            )
            self.conn.commit()

            if self._should_create_service_debt(status):
                self._sync_service_debt_from_tracking(
                    tracking_no,
                    create_if_missing=True,
                    reason=f"status_{self._normalize_status_key(status)}",
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
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS product_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT,
                    updated_at TEXT
                )
                """
            )
            self.create_device_model_catalog_table()
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
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO product_groups (
                    name, is_active, created_at, updated_at
                )
                SELECT DISTINCT
                    TRIM(device_type),
                    1,
                    ?,
                    ?
                FROM device_brands
                WHERE TRIM(COALESCE(device_type, '')) <> ''
                """,
                (now, now),
            )
            self.refresh_device_model_catalog()
            self.cursor.execute(
                """
                INSERT OR IGNORE INTO product_groups (
                    name, is_active, created_at, updated_at
                )
                SELECT DISTINCT TRIM(device_type), 1, ?, ?
                FROM device_brands
                WHERE TRIM(COALESCE(device_type, '')) <> ''
                """,
                (now, now),
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
