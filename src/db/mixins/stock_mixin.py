# -*- coding: utf-8 -*-

"""
Stock Mixin
Stok ve parça yönetimi ile ilgili veritabanı metotları.
"""

from datetime import datetime
from src.utils.logger import logger


class StockMixin:
    @staticmethod
    def _safe_identifier(name):
        cleaned = str(name or "").strip()
        if not cleaned or not cleaned.replace("_", "").isalnum():
            raise ValueError(f"Invalid SQL identifier: {name!r}")
        return cleaned

    """Stok yönetimi için veritabanı metotları."""

    def update_parts_schema(self, commit=True):
        """Ensure the parts table contains all stock columns."""
        try:
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    brand TEXT,
                    stock REAL,
                    price REAL,
                    code TEXT,
                    barcode TEXT,
                    category TEXT DEFAULT 'Genel'
                )
                """
            )
            self.cursor.execute("PRAGMA table_info(parts)")
            columns = {str(col[1]).lower() for col in (self.cursor.fetchall() or [])}
            for col_name, col_type in (
                ("min_stock", "REAL DEFAULT 5"),
                ("purchase_price", "REAL DEFAULT 0"),
                ("currency", "TEXT DEFAULT 'TRY'"),
                ("description", "TEXT"),
                ("shelf_number", "TEXT"),
                ("photo_path", "TEXT"),
                ("oem_code", "TEXT"),
                ("equivalent_code", "TEXT"),
                ("compatible_models", "TEXT"),
                ("is_deleted", "INTEGER DEFAULT 0"),
                ("created_at", "TEXT"),
                ("unit", "TEXT DEFAULT 'Adet'"),
            ):
                if col_name.lower() not in columns:
                    safe_col = self._safe_identifier(col_name)
                    self.cursor.execute(
                        "ALTER TABLE parts ADD COLUMN {column} {ddl}".format(
                            column=safe_col,
                            ddl=col_type,
                        )
                    )
            if commit:
                self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"update_parts_schema error: {e}")
            return False

    def apply_stock_price_increase(self, percentage, category=None):
        """Tüm stok kartlarının satış fiyatına toplu zam uygular."""
        try:
            pct = int(float(percentage or 0))
            if pct <= 0:
                return False

            cur = self.conn.cursor()
            params = [1 + (pct / 100.0)]
            where_sql = "WHERE COALESCE(is_deleted, 0) = 0"

            if (
                category
                and str(category).strip()
                and str(category).strip().lower() not in {"tumu", "tümü", "all"}
            ):
                where_sql += " AND category = ?"
                params.append(str(category).strip())

            cur.execute(
                f"""
                UPDATE parts
                SET price = ROUND(COALESCE(price, 0) * ?, 2)
                {where_sql}
                """,
                tuple(params),
            )
            affected = int(cur.rowcount or 0)

            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                cur.execute(
                    """
                    INSERT INTO audit_logs (action, details, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        "STOCK_PRICE_BULK_UPDATE",
                        f"Toplu fiyat güncellemesi uygulandı: %{pct} zam, etkilenen kart: {affected}",
                        created_at,
                    ),
                )
            except Exception as audit_error:
                logger.warning(
                    "Stock price update audit could not be written: %s",
                    audit_error,
                )

            self.conn.commit()
            return affected > 0
        except Exception as e:
            logger.error(f"apply_stock_price_increase error: {e}")
            return False

    def _ensure_stock_movements_schema(self, commit=True):
        """Guarantee required stock movement columns exist on older installations."""
        try:
            # Use a separate cursor because another thread may use self.cursor.
            cur = self.conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    part_id INTEGER,
                    movement_type TEXT,
                    amount REAL DEFAULT 0,
                    new_stock REAL DEFAULT 0,
                    description TEXT,
                    created_at TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    deleted_at TEXT
                )
                """
            )

            cur.execute("PRAGMA table_info(stock_movements)")
            columns = {str(col[1]).lower() for col in (cur.fetchall() or [])}

            if "movement_type" not in columns:
                if "type" in columns:
                    cur.execute(
                        "ALTER TABLE stock_movements RENAME COLUMN type TO movement_type"
                    )
                else:
                    cur.execute(
                        "ALTER TABLE stock_movements ADD COLUMN movement_type TEXT"
                    )
                columns.add("movement_type")

            if "new_stock" not in columns:
                cur.execute(
                    "ALTER TABLE stock_movements ADD COLUMN new_stock REAL DEFAULT 0"
                )
                try:
                    cur.execute(
                        """
                        UPDATE stock_movements
                        SET new_stock = COALESCE(new_stock, 0)
                        WHERE new_stock IS NULL
                        """
                    )
                except Exception as normalize_error:
                    logger.warning(
                        "Stock movement normalization could not be completed: %s",
                        normalize_error,
                    )

            if "description" not in columns:
                cur.execute("ALTER TABLE stock_movements ADD COLUMN description TEXT")

            if "created_at" not in columns:
                if "date" in columns:
                    cur.execute(
                        "ALTER TABLE stock_movements RENAME COLUMN date TO created_at"
                    )
                else:
                    cur.execute(
                        "ALTER TABLE stock_movements ADD COLUMN created_at TEXT"
                    )

            if commit:
                self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"_ensure_stock_movements_schema error: {e}")
            return False

    def get_parts_paginated(
        self, limit=50, offset=0, search_query="", category="T\u00fcm\u00fc", critical_only=False,
        metric_filter="all",
    ):
        """Sayfalı parça listesi döndürür: (rows, total_count)."""
        try:
            cur = self.conn.cursor()
            where = ["is_deleted = 0"]
            aliased_where = ["p.is_deleted = 0"]
            params = []

            if search_query:
                search_text = search_query.strip()
                like = f"%{search_text}%"
                where.append(
                    "(barcode = ? OR code = ? OR name LIKE ? OR code LIKE ? "
                    "OR barcode LIKE ?)"
                )
                aliased_where.append(
                    "(p.barcode = ? OR p.code = ? OR p.name LIKE ? OR "
                    "p.code LIKE ? OR p.barcode LIKE ?)"
                )
                params.extend(
                    [search_text, search_text, like, like, like]
                )

            if isinstance(category, (list, tuple, set)):
                category_values = [
                    str(cat).strip() for cat in category if str(cat).strip()
                ]
                if category_values:
                    placeholders = ", ".join(["?"] * len(category_values))
                    where.append(f"category IN ({placeholders})")
                    aliased_where.append(f"p.category IN ({placeholders})")
                    params.extend(category_values)
            elif category and category not in ("Tümü", "Tumu", "Hepsi", "All"):
                where.append("category = ?")
                aliased_where.append("p.category = ?")
                params.append(category)

            if critical_only:
                where.append(
                    "COALESCE(stock, 0) <= COALESCE(min_stock, 0)"
                )
                aliased_where.append(
                    "COALESCE(p.stock, 0) <= COALESCE(p.min_stock, 0)"
                )

            if metric_filter == "value":
                where.append("COALESCE(stock, 0) * COALESCE(purchase_price, 0) > 0")
                aliased_where.append(
                    "COALESCE(p.stock, 0) * COALESCE(p.purchase_price, 0) > 0"
                )
            elif metric_filter == "profit":
                where.append(
                    "COALESCE(stock, 0) * (COALESCE(price, 0) - COALESCE(purchase_price, 0)) > 0"
                )
                aliased_where.append(
                    "COALESCE(p.stock, 0) * (COALESCE(p.price, 0) - COALESCE(p.purchase_price, 0)) > 0"
                )

            where_sql = (
                " WHERE {clause}".format(clause=" AND ".join(where)) if where else ""
            )
            aliased_where_sql = (
                " WHERE {clause}".format(clause=" AND ".join(aliased_where))
                if aliased_where
                else ""
            )

            cur.execute(
                "SELECT COUNT(*) FROM parts{where_sql}".format(where_sql=where_sql),
                tuple(params),
            )
            total_row = cur.fetchone()
            total = int(
                (
                    total_row["COUNT(*)"]
                    if hasattr(total_row, "keys") and "COUNT(*)" in total_row.keys()
                    else total_row[0]
                )
                or 0
            )

            page_params = list(params) + [int(limit), int(offset)]
            cur.execute(
                f"""
                SELECT
                    p.*,
                    COALESCE(sae.oem_code, p.oem_code) AS oem_code,
                    COALESCE(sae.equivalent_code, p.equivalent_code) AS equivalent_code,
                    COALESCE(sae.compatible_models, p.compatible_models) AS compatible_models
                FROM parts p
                LEFT JOIN stock_automotive_extension sae ON sae.part_id = p.id
                {aliased_where_sql}
                ORDER BY p.name COLLATE NOCASE ASC
                LIMIT ? OFFSET ?
                """,
                tuple(page_params),
            )
            return cur.fetchall() or [], total
        except Exception as e:
            logger.error(f"get_parts_paginated error: {e}")
            return [], 0

    def get_stock_stats(self):
        """Returns inventory statistics using purchase-cost based valuation."""
        try:
            cur = self.conn.cursor()
            cur.execute(
                """
                SELECT
                    UPPER(COALESCE(currency,'TRY')) AS currency,
                    COUNT(*) AS item_count,
                    COALESCE(SUM(COALESCE(stock, 0)), 0) AS total_stock,
                    COALESCE(
                        SUM(COALESCE(stock, 0) * COALESCE(price, 0)),
                        0
                    ) AS sale_value,
                    COALESCE(
                        SUM(
                            COALESCE(stock, 0) *
                            COALESCE(purchase_price, 0)
                        ),
                        0
                    ) AS purchase_value,
                    COALESCE(
                        SUM(
                            CASE
                                WHEN COALESCE(min_stock, 0) > 0
                                 AND COALESCE(stock, 0) <= COALESCE(min_stock, 0)
                                THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS critical_count
                FROM parts
                WHERE is_deleted = 0
                GROUP BY UPPER(COALESCE(currency, 'TRY'))
                """
            )
            rows = cur.fetchall() or []
            if not rows:
                return {
                    "total_items": 0,
                    "total_types": 0,
                    "total_stock": 0,
                    "total_sale_value": 0.0,
                    "total_value": 0.0,
                    "total_purchase_value": 0.0,
                    "critical_items": 0,
                    "critical_count": 0,
                    "display_currency": "TRY",
                    "total_value_try": 0.0,
                    "potential_profit_try": 0.0,
                }

            from src.utils.currency_helper import CurrencyHelper

            def _val(row, key, idx):
                try:
                    if hasattr(row, "keys") and key in row.keys():
                        return row[key]
                except Exception:
                    pass
                try:
                    return row[idx]
                except Exception:
                    return 0

            total_items = 0
            total_stock = 0.0
            total_sale_try = 0.0
            total_purchase_try = 0.0
            critical_items = 0

            def _to_try(amount, currency):
                if currency == "TRY":
                    return float(amount)
                rate = float(CurrencyHelper._get_rate(self, currency) or 0)
                if rate <= 0:
                    try:
                        result = self.conn.execute(
                            """
                            SELECT exchange_rate
                            FROM accounting
                            WHERE UPPER(COALESCE(currency, 'TRY')) = ?
                              AND COALESCE(exchange_rate, 0) > 0
                            ORDER BY id DESC
                            LIMIT 1
                            """,
                            (currency,),
                        ).fetchone()
                        rate = float(result[0] or 0) if result else 0
                    except Exception:
                        rate = 0
                if rate <= 0:
                    rate = 1.0
                    logger.warning(
                        "Stock valuation rate missing for %s; using 1.0",
                        currency,
                    )
                return float(amount) * rate

            for row in rows:
                currency = str(_val(row, "currency", 0) or "TRY").upper()
                item_count = int(_val(row, "item_count", 1) or 0)
                stock = float(_val(row, "total_stock", 2) or 0)
                sale_value = float(_val(row, "sale_value", 3) or 0)
                purchase_value = float(_val(row, "purchase_value", 4) or 0)
                critical_count = int(_val(row, "critical_count", 5) or 0)

                total_items += item_count
                total_stock += stock
                total_sale_try += _to_try(sale_value, currency)
                total_purchase_try += _to_try(purchase_value, currency)
                critical_items += critical_count

            display_currency = CurrencyHelper.get_code(self)
            if display_currency == "TRY":
                display_value = total_purchase_try
            else:
                display_rate = float(
                    CurrencyHelper._get_rate(self, display_currency) or 0
                )
                display_value = (
                    total_purchase_try / display_rate
                    if display_rate > 0
                    else total_purchase_try
                )

            return {
                "total_items": total_items,
                "total_stock": total_stock,
                "total_sale_value": total_sale_try,
                "total_purchase_value": total_purchase_try,
                "critical_items": critical_items,
                "total_types": total_items,
                "total_value": display_value,
                "total_value_try": total_purchase_try,
                "potential_profit_try": max(
                    0.0, total_sale_try - total_purchase_try
                ),
                "display_currency": display_currency,
                "critical_count": critical_items,
            }
        except Exception as e:
            logger.error(f"get_stock_stats error: {e}")
            return {
                "total_items": 0,
                "total_types": 0,
                "total_stock": 0,
                "total_sale_value": 0.0,
                "total_value": 0.0,
                "total_purchase_value": 0.0,
                "critical_items": 0,
                "critical_count": 0,
                "display_currency": "TRY",
                "total_value_try": 0.0,
                "potential_profit_try": 0.0,
            }

    def record_stock_movement(
        self,
        part_id,
        delta,
        current_stock=0,
        type_val=None,
        desc="",
        commit=True,
        location_id=None,
    ):
        """Stok hareketi kaydı + parts.stock güncellemesi."""
        try:
            self._ensure_stock_movements_schema(commit=commit)
            delta_f = float(delta or 0)
            old_stock = float(current_stock or 0)
            new_stock = old_stock + delta_f
            movement_type = type_val or (
                "Giri\u015f" if delta_f >= 0 else "\u00c7\u0131k\u0131\u015f"
            )
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.cursor.execute(
                """
                INSERT INTO stock_movements (part_id, movement_type, amount, new_stock, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    part_id,
                    movement_type,
                    abs(delta_f),
                    new_stock,
                    desc or "",
                    created_at,
                ),
            )
            self.cursor.execute(
                "UPDATE parts SET stock=? WHERE id=?", (new_stock, part_id)
            )
            if location_id and hasattr(self, "apply_location_delta"):
                self.apply_location_delta(
                    part_id,
                    location_id,
                    delta_f,
                    commit=False,
                )
            elif hasattr(self, "apply_main_location_delta"):
                self.apply_main_location_delta(part_id, delta_f, commit=False)
            if commit:
                self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"record_stock_movement error: {e}")
            if commit:
                try:
                    self.conn.rollback()
                except Exception as rollback_error:
                    logger.error(
                        "Stock movement rollback failed: %s",
                        rollback_error,
                    )
            return False

    def adjust_stock(
        self,
        part_id,
        delta,
        description="",
        type_val=None,
        commit=True,
    ):
        """Stok düzeltme metodu (Database.add_part/update_part çağrıları için)."""
        try:
            self.cursor.execute("SELECT stock FROM parts WHERE id=?", (part_id,))
            row = self.cursor.fetchone()
            if not row:
                return False
            current_stock = float(
                (
                    row["stock"]
                    if hasattr(row, "keys") and "stock" in row.keys()
                    else row[0]
                )
                or 0
            )
            return self.record_stock_movement(
                part_id,
                delta,
                current_stock,
                type_val,
                description,
                commit=commit,
            )
        except Exception as e:
            logger.error(f"adjust_stock error: {e}")
            return False

    def get_all_parts(self):
        """Tüm parçaları getir"""
        try:
            self.cursor.execute(
                """
                SELECT
                    p.*,
                    COALESCE(sae.oem_code, p.oem_code) AS oem_code,
                    COALESCE(sae.equivalent_code, p.equivalent_code) AS equivalent_code,
                    COALESCE(sae.compatible_models, p.compatible_models) AS compatible_models
                FROM parts p
                LEFT JOIN stock_automotive_extension sae ON sae.part_id = p.id
                WHERE COALESCE(p.is_deleted, 0) = 0
                ORDER BY p.name
                """
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"get_all_parts error: {e}")
            return []

    def add_part(
        self,
        name,
        category,
        stock,
        price,
        desc="",
        min_stock=5,
        code=None,
        shelf=None,
        purchase_price=0,
        currency="TRY",
        photo_path=None,
        brand="",
        oem_code="",
        equivalent_code="",
        compatible_models="",
        unit="Adet",
        commit=True,
    ):
        """Add a part and its initial stock movement."""
        try:
            self._last_part_error = ""
            self.update_parts_schema(commit=commit)
            self._ensure_stock_movements_schema(commit=commit)
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                """
                INSERT INTO parts (
                    name, brand, category, stock, price, purchase_price, currency,
                    description, min_stock, code, shelf_number, created_at, photo_path,
                    oem_code, equivalent_code, compatible_models, unit
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    brand,
                    category,
                    float(stock or 0),
                    price,
                    purchase_price,
                    currency,
                    desc,
                    min_stock,
                    code,
                    shelf,
                    created_at,
                    photo_path,
                    oem_code,
                    equivalent_code,
                    compatible_models,
                    unit or "Adet",
                ),
            )
            part_id = self.cursor.lastrowid
            if hasattr(self, "apply_main_location_delta"):
                self.apply_main_location_delta(
                    part_id,
                    float(stock or 0),
                    commit=False,
                )
            if float(stock or 0) > 0:
                movement_desc = desc or f"Yeni stok kartı açılışı: {name}"
                self.cursor.execute(
                    """
                    INSERT INTO stock_movements (part_id, movement_type, amount, new_stock, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        part_id,
                        "Giriş",
                        float(stock or 0),
                        float(stock or 0),
                        movement_desc,
                        created_at,
                    ),
                )
            extension_data = {
                "oem_code": oem_code,
                "equivalent_code": equivalent_code,
                "compatible_models": compatible_models,
            }
            if (
                hasattr(self, "upsert_sector_extension")
                and any(str(value or "").strip() for value in extension_data.values())
            ):
                extension_ok = self.upsert_sector_extension(
                    "stock",
                    part_id,
                    extension_data,
                    sector_id="otomotiv",
                    commit=commit,
                )
                if not extension_ok:
                    logger.warning(
                        "Automotive stock extension was skipped for part %s",
                        part_id,
                    )
            if commit:
                self.conn.commit()
            return part_id
        except Exception as e:
            self._last_part_error = str(e)
            logger.exception("Part add error")
            if commit:
                self.conn.rollback()
            return None

    def update_part(
        self,
        part_id,
        name,
        category,
        stock,
        price,
        desc,
        min_stock,
        code,
        shelf,
        purchase_price=0,
        currency="TRY",
        photo_path=None,
        brand="",
        oem_code="",
        equivalent_code="",
        compatible_models="",
        unit="Adet",
        bank_account_id=None,
        payment_method="Nakit",
        commit=True,
    ):
        """Parca bilgilerini guncelle."""
        try:
            self.update_parts_schema(commit=commit)
            self.cursor.execute(
                "SELECT stock, purchase_price, currency, name, photo_path FROM parts WHERE id=?",
                (part_id,),
            )
            row = self.cursor.fetchone()
            if row:
                if hasattr(row, "keys"):
                    old_stock = float(row["stock"] or 0)
                    old_purchase_price = float(row["purchase_price"] or 0)
                    old_currency = str(row["currency"] or "TRY").upper()
                    old_name = str(row["name"] or "")
                    existing_photo = row["photo_path"]
                else:
                    old_stock = float(row[0] or 0)
                    old_purchase_price = float(row[1] or 0)
                    old_currency = str(row[2] or "TRY").upper()
                    old_name = str(row[3] or "")
                    existing_photo = row[4]

                if photo_path is None:
                    photo_path = existing_photo
            else:
                old_stock = 0.0
                old_purchase_price = 0.0
                old_currency = "TRY"
                old_name = ""

            new_stock = old_stock if stock in (None, "") else float(stock)
            delta = new_stock - old_stock

            new_purchase_price = float(purchase_price or 0)
            new_currency = str(currency or "TRY").upper()
            price_changed = (abs(new_purchase_price - old_purchase_price) > 0.001) or (
                new_currency != old_currency
            )

            self.cursor.execute(
                """
                UPDATE parts
                SET name=?, brand=?, category=?, price=?, purchase_price=?, currency=?,
                    description=?, min_stock=?, code=?, shelf_number=?, photo_path=?,
                    oem_code=?, equivalent_code=?, compatible_models=?, unit=?
                WHERE id=?
            """,
                (
                    name,
                    brand,
                    category,
                    price,
                    purchase_price,
                    currency,
                    desc,
                    min_stock,
                    code,
                    shelf,
                    photo_path,
                    oem_code,
                    equivalent_code,
                    compatible_models,
                    unit or "Adet",
                    part_id,
                ),
            )
            if hasattr(self, "upsert_sector_extension"):
                extension_ok = self.upsert_sector_extension(
                    "stock",
                    part_id,
                    {
                        "oem_code": oem_code,
                        "equivalent_code": equivalent_code,
                        "compatible_models": compatible_models,
                    },
                    sector_id="otomotiv",
                    commit=False,
                )
                if not extension_ok:
                    raise RuntimeError(
                        "Automotive stock extension could not be updated"
                    )

            # 1. Stok Hareketi Kaydi (Miktar veya Fiyat degistiyse)
            if delta != 0 or price_changed:
                move_type = (
                    "Giris" if delta > 0 else ("Cikis" if delta < 0 else "Guncelleme")
                )
                move_desc = f"Bilgi Guncelleme - {name}"
                if price_changed and delta == 0:
                    move_desc = f"Fiyat Guncelleme ({old_purchase_price} -> {new_purchase_price} {new_currency}) - {name}"

                movement_ok = self.record_stock_movement(
                    part_id=part_id,
                    delta=delta,
                    current_stock=old_stock,
                    type_val=move_type,
                    desc=move_desc,
                    commit=False,
                )
                if not movement_ok:
                    raise RuntimeError("Stock movement could not be recorded")

            # 2. Finansal Kayit / Duzeltme
            if delta != 0:
                try:
                    unit_cost = new_purchase_price
                    qty = abs(delta)
                    if delta > 0:
                        self.add_transaction(
                            t_type="Gider",
                            category="Stok Alimi",
                            amount=unit_cost * qty,
                            description=f"Stok Artisi (Guncelleme): {qty} {unit} x {name}",
                            payment_method=payment_method,
                            bank_account_id=bank_account_id,
                            currency=new_currency,
                            original_amount=unit_cost * qty,
                            selected_services=[
                                {
                                    "kind": "stock_purchase",
                                    "name": name,
                                    "quantity": qty,
                                    "unit_price": unit_cost,
                                    "currency": new_currency,
                                    "line_total": unit_cost * qty,
                                }
                            ],
                            commit=False,
                        )
                    else:
                        self.add_transaction(
                            t_type="Gider",
                            category="Stok Dusum / Fire",
                            amount=unit_cost * qty,
                            description=f"Stok Azalisi (Guncelleme): {qty} {unit} x {name}",
                            payment_method=payment_method,
                            bank_account_id=bank_account_id,
                            currency=new_currency,
                            original_amount=unit_cost * qty,
                            commit=False,
                        )
                except Exception as e:
                    raise RuntimeError(
                        f"Stock quantity accounting failed: {e}"
                    ) from e

            elif price_changed and old_stock > 0:
                try:
                    price_difference = new_purchase_price - old_purchase_price
                    total_adj = price_difference * old_stock

                    if abs(total_adj) > 0.001:
                        t_type = "Gider"
                        if total_adj > 0:
                            adj_category = "Stok Deger Duzeltme - Artis"
                        else:
                            adj_category = "Stok Deger Duzeltme - Dusus"
                        adj_desc = f"Fiyat Duzeltme ({old_purchase_price} -> {new_purchase_price}): {old_stock} {unit} {name}"

                        self.add_transaction(
                            t_type=t_type,
                            category=adj_category,
                            amount=abs(total_adj),
                            description=adj_desc,
                            payment_method=payment_method,
                            bank_account_id=bank_account_id,
                            currency=new_currency,
                            original_amount=abs(total_adj),
                            commit=False,
                        )
                except Exception as e:
                    raise RuntimeError(
                        f"Stock price accounting failed: {e}"
                    ) from e

            if commit:
                self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Part update error: {e}")
            if commit:
                self.conn.rollback()
            return False

    def merge_imported_part(
        self,
        part_id,
        quantity,
        purchase_price,
        sale_price,
        currency,
        name=None,
        category=None,
        brand=None,
        description=None,
        code=None,
        shelf=None,
        oem_code=None,
        equivalent_code=None,
        compatible_models=None,
    ):
        """Merge an imported stock row into an existing product card."""
        try:
            self.update_parts_schema(commit=False)
            self._ensure_stock_movements_schema(commit=False)
            self.cursor.execute(
                """
                SELECT name, category, brand, stock, price, purchase_price,
                       currency, description, code, shelf_number, oem_code,
                       equivalent_code, compatible_models
                FROM parts
                WHERE id=? AND COALESCE(is_deleted, 0)=0
                """,
                (part_id,),
            )
            row = self.cursor.fetchone()
            if not row:
                return None
            columns = [item[0] for item in self.cursor.description]
            current = dict(zip(columns, row))
            incoming_quantity = max(0.0, float(quantity or 0))
            old_stock = float(current.get("stock") or 0)
            final_purchase = (
                float(purchase_price)
                if purchase_price not in (None, "")
                else float(current.get("purchase_price") or 0)
            )
            final_sale = (
                float(sale_price)
                if sale_price not in (None, "")
                else float(current.get("price") or 0)
            )
            final_currency = str(
                currency or current.get("currency") or "TRY"
            ).upper()
            values = {
                "name": name or current.get("name") or "",
                "category": category or current.get("category") or "Genel",
                "brand": brand or current.get("brand") or "",
                "description": (
                    description
                    if description not in (None, "")
                    else current.get("description") or ""
                ),
                "code": code or current.get("code") or "",
                "shelf": shelf or current.get("shelf_number") or "",
                "oem_code": oem_code or current.get("oem_code") or "",
                "equivalent_code": (
                    equivalent_code or current.get("equivalent_code") or ""
                ),
                "compatible_models": (
                    compatible_models or current.get("compatible_models") or ""
                ),
            }
            self.cursor.execute(
                """
                UPDATE parts
                SET name=?, category=?, brand=?, price=?, purchase_price=?,
                    currency=?, description=?, code=?, shelf_number=?,
                    oem_code=?, equivalent_code=?, compatible_models=?
                WHERE id=?
                """,
                (
                    values["name"],
                    values["category"],
                    values["brand"],
                    final_sale,
                    final_purchase,
                    final_currency,
                    values["description"],
                    values["code"],
                    values["shelf"],
                    values["oem_code"],
                    values["equivalent_code"],
                    values["compatible_models"],
                    part_id,
                ),
            )
            if incoming_quantity:
                movement_ok = self.record_stock_movement(
                    part_id=part_id,
                    delta=incoming_quantity,
                    current_stock=old_stock,
                    type_val="Giri\u015f",
                    desc=(
                        "Ak\u0131ll\u0131 i\u00e7e aktar\u0131m "
                        f"birle\u015ftirme: {values['name']}"
                    ),
                    commit=False,
                )
                if not movement_ok:
                    raise RuntimeError("Imported stock movement could not be saved")
            self.conn.commit()
            return part_id
        except Exception as exc:
            logger.error("Imported part merge error: %s", exc)
            try:
                self.conn.rollback()
            except Exception:
                pass
            return None

    def delete_part(self, part_id):
        """Parça soft delete"""
        try:
            if hasattr(self, "soft_delete_record"):
                return self.soft_delete_record("parts", "id", part_id)
            deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "UPDATE parts SET is_deleted=1, deleted_at=? WHERE id=?",
                (deleted_at, part_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Part delete error: {e}")
            return False

    def get_part_by_barcode(self, barcode):
        """Barkod ile parça ara"""
        try:
            self.cursor.execute(
                "SELECT * FROM parts WHERE barcode=? AND COALESCE(is_deleted, 0) = 0",
                (barcode,),
            )
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"get_part_by_barcode error: {e}")
            return None

    def add_stock(
        self, name, category, quantity, purchase_price, sale_price, currency="TRY"
    ):
        """Yeni stok kartı oluşturur ve giriş hareketi kaydeder."""
        try:
            self._ensure_stock_movements_schema()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                """
                INSERT INTO parts (name, category, stock, price, purchase_price, currency, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    category,
                    quantity,
                    sale_price,
                    purchase_price,
                    currency,
                    created_at,
                ),
            )
            part_id = self.cursor.lastrowid
            if hasattr(self, "apply_main_location_delta"):
                self.apply_main_location_delta(
                    part_id,
                    float(quantity or 0),
                    commit=False,
                )
            if float(quantity or 0) > 0:
                self.cursor.execute(
                    """
                    INSERT INTO stock_movements (part_id, movement_type, amount, new_stock, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        part_id,
                        "Giriş",
                        float(quantity or 0),
                        float(quantity or 0),
                        f"Yeni stok kartı açılışı: {name}",
                        created_at,
                    ),
                )
            self.conn.commit()
            return part_id
        except Exception as e:
            logger.error(f"Stock add error: {e}")
            return None

    def use_part(
        self,
        part_id,
        quantity=1,
        tracking_no=None,
        commit=True,
        **kwargs,
    ):
        """Parca kullan - stok dusum, used_parts kaydi eklenir."""
        try:
            location_id = kwargs.get("location_id")
            # Mevcut stoku kontrol et
            self.cursor.execute(
                "SELECT name, stock, price, purchase_price, COALESCE(currency, 'TRY') FROM parts WHERE id=?",
                (part_id,),
            )
            result = self.cursor.fetchone()
            if not result:
                return False

            part_name = result[0] or f"Parca #{part_id}"
            current_stock = float(result[1] or 0)
            sell_price = float(result[2] or 0)
            purchase_price = float(result[3] or 0)
            part_currency = str(result[4] or "TRY").upper()
            from src.utils.currency_helper import CurrencyHelper

            if part_currency == "TRY":
                exchange_rate = 1.0
            else:
                exchange_rate = CurrencyHelper.require_rate(self, part_currency)
            price_try = round(sell_price * exchange_rate, 4)

            if current_stock < quantity:
                logger.warning(f"Insufficient stock for part {part_id}")
                return False

            if location_id and hasattr(self, "get_location_inventory"):
                location_rows = self.get_location_inventory(location_id)
                location_stock = next(
                    (
                        float(row.get("quantity") or 0)
                        for row in location_rows
                        if int(row.get("part_id") or 0) == int(part_id)
                    ),
                    0.0,
                )
                if location_stock < float(quantity or 0):
                    logger.warning(
                        "Insufficient location stock for part %s at %s",
                        part_id,
                        location_id,
                    )
                    return False

            # Stok dus ve hareketi kaydet
            movement_recorded = self.record_stock_movement(
                part_id=part_id,
                delta=-quantity,
                current_stock=current_stock,
                type_val="\u00c7\u0131k\u0131\u015f",
                desc=f"Servis Kullanimi: {tracking_no or '-'}",
                commit=False,
                location_id=location_id,
            )
            if not movement_recorded:
                raise RuntimeError("Stock movement could not be recorded")

            # Store the usage record together with its currency.
            if tracking_no:
                self.cursor.execute(
                    """
                    INSERT INTO used_parts (
                        tracking_no, part_id, part_name, price, quantity,
                        purchase_price_snapshot, currency, exchange_rate,
                        price_try, stock_location_id, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """,
                    (
                        tracking_no,
                        part_id,
                        part_name,
                        sell_price,
                        quantity,
                        purchase_price,
                        part_currency,
                        exchange_rate,
                        price_try,
                        location_id,
                    ),
                )

            if commit:
                self.conn.commit()
            if (
                commit
                and tracking_no
                and hasattr(self, "_sync_service_debt_from_tracking")
            ):
                try:
                    self._sync_service_debt_from_tracking(
                        tracking_no,
                        create_if_missing=True,
                        reason="used_part_add",
                    )
                except Exception as sync_err:
                    logger.debug(
                        "Service debt sync skipped after use_part (%s): %s",
                        tracking_no,
                        sync_err,
                    )
            return True
        except Exception as e:
            logger.error(f"Use part error: {e}")
            if commit:
                try:
                    self.conn.rollback()
                except Exception as rollback_error:
                    logger.error("Use part rollback failed: %s", rollback_error)
            return False

    def add_used_part(self, tracking_no, part_name, price, **kwargs):
        """Kullanılan parça ekle (manuel ürün/hizmet)."""
        try:
            self.cursor.execute("PRAGMA table_info(used_parts)")
            columns = [row[1] for row in self.cursor.fetchall()]

            if "currency" in columns and "quantity" in columns:
                self.cursor.execute(
                    """
                    INSERT INTO used_parts (tracking_no, part_name, price, currency, quantity, created_at)
                    VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                    """,
                    (tracking_no, part_name, price, "TRY", 1),
                )
            elif "currency" in columns:
                self.cursor.execute(
                    """
                    INSERT INTO used_parts (tracking_no, part_name, price, currency, created_at)
                    VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
                    """,
                    (tracking_no, part_name, price, "TRY"),
                )
            else:
                self.cursor.execute(
                    "INSERT INTO used_parts (tracking_no, part_name, price, created_at) VALUES (?, ?, ?, datetime('now', 'localtime'))",
                    (tracking_no, part_name, price),
                )
            self.conn.commit()
            if tracking_no and hasattr(self, "_sync_service_debt_from_tracking"):
                try:
                    self._sync_service_debt_from_tracking(
                        tracking_no,
                        create_if_missing=True,
                        reason="used_part_add",
                    )
                except Exception as sync_err:
                    logger.debug(
                        "Service debt sync skipped after add_used_part (%s): %s",
                        tracking_no,
                        sync_err,
                    )
        except Exception as e:
            logger.error(f"Add used part error: {e}")

    def remove_used_part(self, used_part_id):
        """Kullanılan parça kaydını soft delete yap ve stok kartlıysa stoğu geri yaz."""
        try:
            self.cursor.execute("PRAGMA table_info(used_parts)")
            columns = [row[1] for row in self.cursor.fetchall()]
            deleted_col = (
                "is_deleted"
                if "is_deleted" in columns
                else ("is_archived" if "is_archived" in columns else None)
            )

            location_select = (
                "stock_location_id" if "stock_location_id" in columns else "NULL"
            )
            query = (
                "SELECT id, tracking_no, part_id, part_name, "
                f"COALESCE(quantity, 1), {location_select} "
                "FROM used_parts WHERE id=?"
            )
            if deleted_col:
                query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            self.cursor.execute(query, (used_part_id,))
            row = self.cursor.fetchone()
            if not row:
                return False

            tracking_no = row[1]
            stock_part_id = row[2]
            part_name = row[3] or "-"
            quantity = float(row[4] or 1)
            location_id = row[5]

            if hasattr(self, "soft_delete_record"):
                if not self.soft_delete_record("used_parts", "id", used_part_id):
                    return False
            else:
                self.cursor.execute(
                    "DELETE FROM used_parts WHERE id=?", (used_part_id,)
                )
                self.conn.commit()

            if stock_part_id:
                self.cursor.execute(
                    "SELECT COALESCE(stock, 0) FROM parts WHERE id=?", (stock_part_id,)
                )
                stock_row = self.cursor.fetchone()
                current_stock = float(stock_row[0] or 0) if stock_row else 0
                self.record_stock_movement(
                    part_id=stock_part_id,
                    delta=quantity,
                    current_stock=current_stock,
                    location_id=location_id,
                    type_val="Giriş",
                    desc=f"Servis parça iadesi / silme: {tracking_no} - {part_name}",
                )

            if tracking_no and hasattr(self, "_sync_service_debt_from_tracking"):
                try:
                    self._sync_service_debt_from_tracking(
                        tracking_no,
                        create_if_missing=True,
                        reason="used_part_remove",
                    )
                except Exception as sync_err:
                    logger.debug(
                        "Service debt sync skipped after remove_used_part (%s): %s",
                        tracking_no,
                        sync_err,
                    )

            return True
        except Exception as e:
            logger.error(f"Remove used part error: {e}")
            return False

    def get_used_parts(self, tracking_no):
        """Kullanılan parçaları getir"""
        try:
            self.cursor.execute("PRAGMA table_info(used_parts)")
            columns = [row[1] for row in self.cursor.fetchall()]
            deleted_col = (
                "is_deleted"
                if "is_deleted" in columns
                else ("is_archived" if "is_archived" in columns else None)
            )

            query = "SELECT * FROM used_parts WHERE tracking_no=?"
            if deleted_col:
                query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            query += " ORDER BY id DESC"

            self.cursor.execute(query, (tracking_no,))
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"get_used_parts error: {e}")
            return []

    def get_popular_parts(self):
        """En çok kullanılan parçaları getir"""
        try:
            self.cursor.execute("PRAGMA table_info(used_parts)")
            columns = [row[1] for row in self.cursor.fetchall()]
            deleted_col = (
                "is_deleted"
                if "is_deleted" in columns
                else ("is_archived" if "is_archived" in columns else None)
            )

            query = """
                SELECT part_name, COUNT(*) as usage_count
                FROM used_parts
            """
            if deleted_col:
                query += f" WHERE ({deleted_col}=0 OR {deleted_col} IS NULL)"
            query += """
                GROUP BY part_name
                ORDER BY usage_count DESC
                LIMIT 10
            """
            self.cursor.execute(query)
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"get_popular_parts error: {e}")
            return []

    def check_critical_stock(self, limit=5):
        """Kritik stok seviyesindeki parçaları getir"""
        try:
            self.cursor.execute(
                """
                SELECT * FROM parts 
                WHERE stock <= min_stock 
                AND COALESCE(is_deleted, 0) = 0
                ORDER BY stock 
                LIMIT ?
            """,
                (limit,),
            )
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"check_critical_stock error: {e}")
            return []

    def get_critical_stock_items(self):
        """Kritik stok öğelerini getir (alias)"""
        return self.check_critical_stock(100)

    def update_part_min_stock(self, part_id, min_val):
        """Minimum stok seviyesini güncelle"""
        self.cursor.execute(
            "UPDATE parts SET min_stock=? WHERE id=?", (min_val, part_id)
        )
        self.conn.commit()

    def add_stock_movement(self, part_id, amount, current_stock, type_val, desc):
        """Record a stock movement and keep the main warehouse in sync."""
        try:
            self._ensure_stock_movements_schema()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            movement_key = str(type_val or "").strip().lower()
            is_inbound = movement_key in {"giris", "giri\u015f", "iade", "return"}
            signed_amount = float(amount or 0) if is_inbound else -float(amount or 0)
            new_stock = float(current_stock or 0) + signed_amount

            self.cursor.execute(
                """
                INSERT INTO stock_movements (part_id, movement_type, amount, new_stock, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (part_id, type_val, amount, new_stock, desc, created_at),
            )

            # Update part stock
            self.cursor.execute(
                "UPDATE parts SET stock=? WHERE id=?", (new_stock, part_id)
            )

            if hasattr(self, "apply_main_location_delta"):
                self.apply_main_location_delta(
                    part_id,
                    signed_amount,
                    commit=False,
                )

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Stock movement error: {e}")
            return False

    def ensure_stock_history_seeded(self):
        """Backfill opening stock movements for parts that have stock but no movement rows."""
        try:
            self._ensure_stock_movements_schema()
            self.cursor.execute("""
                SELECT p.id, p.name, COALESCE(p.stock, 0), COALESCE(p.created_at, datetime('now', 'localtime'))
                FROM parts p
                LEFT JOIN (
                    SELECT part_id, COUNT(*) AS move_count
                    FROM stock_movements
                    GROUP BY part_id
                ) sm ON sm.part_id = p.id
                WHERE (p.is_deleted = 0 OR p.is_deleted IS NULL)
                  AND COALESCE(p.stock, 0) > 0
                  AND COALESCE(sm.move_count, 0) = 0
            """)
            missing_rows = self.cursor.fetchall() or []
            for row in missing_rows:
                part_id = row[0]
                part_name = row[1] or "-"
                amount = float(row[2] or 0)
                created_at = row[3] or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cursor.execute(
                    """
                    INSERT INTO stock_movements (part_id, movement_type, amount, new_stock, description, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        part_id,
                        "Giriş",
                        amount,
                        amount,
                        f"Yeni stok kartı açılışı: {part_name}",
                        created_at,
                    ),
                )
            if missing_rows:
                self.conn.commit()
        except Exception as e:
            logger.error(f"ensure_stock_history_seeded error: {e}")

    def get_stock_history(
        self,
        part_id=None,
        limit=100,
        offset=0,
        with_total=False,
    ):
        """Stok geçmişini getir"""
        try:
            self._ensure_stock_movements_schema()
            limit = max(1, min(int(limit or 100), 500))
            offset = max(0, int(offset or 0))
            seed_row = self.cursor.execute(
                """
                SELECT 1
                FROM stock_movements
                WHERE is_deleted=0
                LIMIT 1
                """
            ).fetchone()
            if not seed_row:
                self.ensure_stock_history_seeded()

            # Use row_factory for dict-like access
            old_factory = self.conn.row_factory
            try:
                import sqlite3 as _sqlite3

                self.conn.row_factory = _sqlite3.Row
                cur = self.conn.cursor()
                if part_id:
                    total_row = cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM stock_movements
                        WHERE part_id=? AND is_deleted=0
                        """,
                        (part_id,),
                    ).fetchone()
                else:
                    total_row = cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM stock_movements
                        WHERE is_deleted=0
                        """
                    ).fetchone()
                total = int(total_row[0] or 0) if total_row else 0

                if part_id:
                    cur.execute(
                        """
                        SELECT sm.id, sm.part_id, sm.movement_type, sm.amount, sm.new_stock,
                               sm.description, sm.created_at,
                               COALESCE(p.name, p.part_name, 'Bilinmeyen Parça') AS part_name,
                               UPPER(COALESCE(p.currency, 'TRY')) AS currency,
                               COALESCE(p.purchase_price, 0) AS unit_cost
                        FROM stock_movements sm
                        LEFT JOIN parts p ON sm.part_id = p.id
                        WHERE sm.part_id=? AND sm.is_deleted=0
                        ORDER BY sm.created_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (part_id, limit, offset),
                    )
                else:
                    cur.execute(
                        """
                        SELECT sm.id, sm.part_id, sm.movement_type, sm.amount, sm.new_stock,
                               sm.description, sm.created_at,
                               COALESCE(p.name, p.part_name, 'Bilinmeyen Parça') AS part_name,
                               UPPER(COALESCE(p.currency, 'TRY')) AS currency,
                               COALESCE(p.purchase_price, 0) AS unit_cost
                        FROM stock_movements sm
                        LEFT JOIN parts p ON sm.part_id = p.id
                        WHERE sm.is_deleted=0
                        ORDER BY sm.created_at DESC
                        LIMIT ? OFFSET ?
                        """,
                        (limit, offset),
                    )

                rows = cur.fetchall()

                # Convert to plain dicts for reliability before restoring factory
                result = []
                for r in rows:
                    result.append(
                        {
                            "id": r["id"],
                            "part_id": r["part_id"],
                            "part_name": r["part_name"] or "-",
                            "movement_type": r["movement_type"] or "-",
                            "amount": r["amount"] or 0,
                            "new_stock": r["new_stock"] or 0,
                            "description": r["description"] or "",
                            "created_at": r["created_at"] or "",
                            "currency": (r["currency"] or "TRY"),
                            "unit_cost": float(r["unit_cost"] or 0),
                        }
                    )
            finally:
                self.conn.row_factory = old_factory

            # If stock_movements table is empty, generate virtual rows from current stock and used_parts
            if not result:
                old_factory = self.conn.row_factory
                try:
                    self.conn.row_factory = _sqlite3.Row
                    cur2 = self.conn.cursor()
                    try:
                        cur2.execute(
                            "SELECT id, name, stock, created_at FROM parts WHERE COALESCE(stock,0) > 0 ORDER BY id DESC LIMIT 200"
                        )
                        for r in cur2.fetchall():
                            result.append(
                                {
                                    "id": r["id"],
                                    "part_id": r["id"],
                                    "part_name": r["name"] or "-",
                                    "movement_type": "Giriş",
                                    "amount": r["stock"] or 0,
                                    "new_stock": r["stock"] or 0,
                                    "description": f"Yeni stok kartı açılışı: {r['name']}",
                                    "created_at": r["created_at"] or "",
                                    "currency": "TRY",
                                    "unit_cost": 0.0,
                                }
                            )
                    except Exception:
                        pass
                    try:
                        cur2.execute("""
                            SELECT up.id, up.part_id, up.part_name, up.price, up.quantity,
                                   up.tracking_no, up.created_at,
                                   COALESCE(p.name, p.part_name, up.part_name, 'Parça') AS pname
                            FROM used_parts up
                            LEFT JOIN parts p ON up.part_id = p.id
                            ORDER BY up.id DESC LIMIT 200
                        """)
                        up_rows = cur2.fetchall()
                        for r in up_rows:
                            result.append(
                                {
                                    "id": r["id"],
                                    "part_id": r["part_id"],
                                    "part_name": r["pname"] or r["part_name"] or "-",
                                    "movement_type": "Çıkış (Servis)",
                                    "amount": r["quantity"] or 1,
                                    "new_stock": "-",
                                    "description": f"Servis: {r['tracking_no']}",
                                    "created_at": r["created_at"] or "",
                                    "currency": "TRY",
                                    "unit_cost": 0.0,
                                }
                            )
                    except Exception:
                        pass
                finally:
                    self.conn.row_factory = old_factory

            if not total:
                total = len(result)
            return (result, total) if with_total else result
        except Exception as e:
            logger.error(f"get_stock_history error: {e}")
            return ([], 0) if with_total else []
