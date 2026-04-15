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

    def update_parts_schema(self):
        """Guarantee automotive-friendly stock columns exist."""
        try:
            self.cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    brand TEXT,
                    stock INTEGER,
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
                ("min_stock", "INTEGER DEFAULT 5"),
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
            ):
                if col_name.lower() not in columns:
                    safe_col = self._safe_identifier(col_name)
                    self.cursor.execute(
                        "ALTER TABLE parts ADD COLUMN {column} {ddl}".format(
                            column=safe_col,
                            ddl=col_type,
                        )
                    )
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
            except Exception:
                pass

            self.conn.commit()
            return affected > 0
        except Exception as e:
            logger.error(f"apply_stock_price_increase error: {e}")
            return False

    def _ensure_stock_movements_schema(self):
        """Guarantee required stock movement columns exist on older installations."""
        try:
            # Ayrı cursor kullan — self.cursor başka thread tarafından kullanılıyor olabilir
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
                except Exception:
                    pass

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

            self.conn.commit()
            cur.close()
            return True
        except Exception as e:
            logger.error(f"_ensure_stock_movements_schema error: {e}")
            return False

    def get_parts_paginated(
        self, limit=50, offset=0, search_query="", category="Tümü", critical_only=False
    ):
        """Sayfalı parça listesi döndürür: (rows, total_count)."""
        try:
            cur = self.conn.cursor()
            where = ["COALESCE(is_deleted, 0) = 0"]
            aliased_where = ["COALESCE(p.is_deleted, 0) = 0"]
            params = []

            if search_query:
                where.append("(name LIKE ? OR code LIKE ?)")
                aliased_where.append("(p.name LIKE ? OR p.code LIKE ?)")
                like = f"%{search_query.strip()}%"
                params.extend([like, like])

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
                    "CAST(COALESCE(stock,0) AS REAL) <= CAST(COALESCE(min_stock,0) AS REAL)"
                )
                aliased_where.append(
                    "CAST(COALESCE(p.stock,0) AS REAL) <= CAST(COALESCE(p.min_stock,0) AS REAL)"
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
                ORDER BY COALESCE(p.name, '') COLLATE NOCASE ASC
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
                    COALESCE(stock,0) AS stock,
                    COALESCE(price,0) AS price,
                    COALESCE(purchase_price,0) AS purchase_price,
                    UPPER(COALESCE(currency,'TRY')) AS currency,
                    COALESCE(min_stock,0) AS min_stock
                FROM parts
                WHERE (is_deleted=0 OR is_deleted IS NULL)
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

            for row in rows:
                stock = float(_val(row, "stock", 0) or 0)
                sale_price = float(_val(row, "price", 1) or 0)
                purchase_price = float(_val(row, "purchase_price", 2) or 0)
                currency = str(_val(row, "currency", 3) or "TRY").upper()
                min_stock = float(_val(row, "min_stock", 4) or 0)

                total_items += 1
                total_stock += stock
                total_sale_try += CurrencyHelper.convert_amount(
                    self, stock * sale_price, currency, "TRY"
                )
                total_purchase_try += CurrencyHelper.convert_amount(
                    self, stock * purchase_price, currency, "TRY"
                )
                if min_stock > 0 and stock <= min_stock:
                    critical_items += 1

            display_currency = CurrencyHelper.get_code(self)
            display_value = CurrencyHelper.convert_amount(
                self, total_purchase_try, "TRY", display_currency
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
            }

    def record_stock_movement(
        self, part_id, delta, current_stock=0, type_val=None, desc=""
    ):
        """Stok hareketi kaydı + parts.stock güncellemesi."""
        try:
            self._ensure_stock_movements_schema()
            delta_i = int(delta or 0)
            old_stock = int(current_stock or 0)
            new_stock = old_stock + delta_i
            movement_type = type_val or ("Giriş" if delta_i >= 0 else "Çıkış")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.cursor.execute(
                """
                INSERT INTO stock_movements (part_id, movement_type, amount, new_stock, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    part_id,
                    movement_type,
                    abs(delta_i),
                    new_stock,
                    desc or "",
                    created_at,
                ),
            )
            self.cursor.execute(
                "UPDATE parts SET stock=? WHERE id=?", (new_stock, part_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"record_stock_movement error: {e}")
            return False

    def adjust_stock(self, part_id, delta, description="", type_val=None):
        """Stok düzeltme metodu (Database.add_part/update_part çağrıları için)."""
        try:
            self.cursor.execute("SELECT stock FROM parts WHERE id=?", (part_id,))
            row = self.cursor.fetchone()
            if not row:
                return False
            current_stock = int(
                (
                    row["stock"]
                    if hasattr(row, "keys") and "stock" in row.keys()
                    else row[0]
                )
                or 0
            )
            return self.record_stock_movement(
                part_id, delta, current_stock, type_val, description
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
    ):
        """Yeni parça ekle ve ilk stok girişini stock_movements'a kaydet."""
        try:
            self.update_parts_schema()
            self._ensure_stock_movements_schema()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                """
                INSERT INTO parts (
                    name, brand, category, stock, price, purchase_price, currency,
                    description, min_stock, code, shelf_number, created_at, photo_path,
                    oem_code, equivalent_code, compatible_models
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    name,
                    brand,
                    category,
                    stock,
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
                ),
            )
            part_id = self.cursor.lastrowid
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
            if hasattr(self, "upsert_sector_extension"):
                self.upsert_sector_extension(
                    "stock",
                    part_id,
                    {
                        "oem_code": oem_code,
                        "equivalent_code": equivalent_code,
                        "compatible_models": compatible_models,
                    },
                    sector_id="otomotiv",
                )
            self.conn.commit()
            return part_id
        except Exception as e:
            logger.error(f"Part add error: {e}")
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
    ):
        """Parça bilgilerini güncelle"""
        try:
            self.update_parts_schema()
            self.cursor.execute(
                "SELECT stock, purchase_price, currency, name, photo_path FROM parts WHERE id=?",
                (part_id,),
            )
            row = self.cursor.fetchone()
            if row:
                if hasattr(row, "keys"):
                    old_stock = int(row["stock"] or 0)
                    old_purchase_price = float(row["purchase_price"] or 0)
                    old_currency = str(row["currency"] or "TRY").upper()
                    old_name = str(row["name"] or "")
                    existing_photo = row["photo_path"]
                else:
                    old_stock = int(row[0] or 0)
                    old_purchase_price = float(row[1] or 0)
                    old_currency = str(row[2] or "TRY").upper()
                    old_name = str(row[3] or "")
                    existing_photo = row[4]

                if photo_path is None:
                    photo_path = existing_photo
            else:
                old_stock = 0
                old_purchase_price = 0
                old_currency = "TRY"
                old_name = ""

            new_stock = old_stock if stock in (None, "") else int(stock)
            delta = new_stock - old_stock

            new_purchase_price = float(purchase_price or 0)
            new_currency = str(currency or "TRY").upper()
            price_changed = (abs(new_purchase_price - old_purchase_price) > 0.001) or (
                new_currency != old_currency
            )

            self.cursor.execute(
                """
                UPDATE parts
                SET name=?, brand=?, category=?, price=?, purchase_price=?, currency=?, description=?, min_stock=?, code=?, shelf_number=?, photo_path=?, oem_code=?, equivalent_code=?, compatible_models=?
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
                    part_id,
                ),
            )
            if hasattr(self, "upsert_sector_extension"):
                self.upsert_sector_extension(
                    "stock",
                    part_id,
                    {
                        "oem_code": oem_code,
                        "equivalent_code": equivalent_code,
                        "compatible_models": compatible_models,
                    },
                    sector_id="otomotiv",
                )

            # 1. Stok Hareketi Kaydı (Miktar veya Fiyat değiştiyse)
            if delta != 0 or price_changed:
                move_type = (
                    "Giriş" if delta > 0 else ("Çıkış" if delta < 0 else "Güncelleme")
                )
                move_desc = f"Bilgi Güncelleme - {name}"
                if price_changed and delta == 0:
                    move_desc = f"Fiyat Güncelleme ({old_purchase_price} -> {new_purchase_price} {new_currency}) - {name}"

                self.record_stock_movement(
                    part_id=part_id,
                    delta=delta,
                    current_stock=old_stock,
                    type_val=move_type,
                    desc=move_desc,
                )

            # 2. Finansal Kayıt / Düzeltme
            if delta != 0:
                try:
                    unit_cost = new_purchase_price
                    qty = abs(delta)
                    if delta > 0:
                        self.add_transaction(
                            t_type="Gider",
                            category="Stok Alımı",
                            amount=unit_cost * qty,
                            description=f"Stok Artışı (Güncelleme): {qty} x {name}",
                            payment_method="Nakit",
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
                        )
                    else:
                        self.add_transaction(
                            t_type="Gider",
                            category="Stok Düşüm / Fire",
                            amount=unit_cost * qty,
                            description=f"Stok Azalışı (Güncelleme): {qty} x {name}",
                            payment_method="Nakit",
                            currency=new_currency,
                            original_amount=unit_cost * qty,
                        )
                except Exception as e:
                    logger.error(f"Stock qty update accounting error: {e}")

            elif price_changed and old_stock > 0:
                try:
                    price_difference = new_purchase_price - old_purchase_price
                    total_adj = price_difference * old_stock

                    if abs(total_adj) > 0.001:
                        # Her iki durumda da "Gider" olarak kaydet:
                        # Fiyat artışı = ek maliyet gideri, Fiyat düşüşü = negatif maliyet düzeltmesi
                        # Asla "Gelir" olarak kaydetme — stok düzeltmesi ciro değildir.
                        t_type = "Gider"
                        if total_adj > 0:
                            adj_category = "Stok Değer Düzeltme - Artış"
                        else:
                            adj_category = "Stok Değer Düzeltme - Düşüş"
                        adj_desc = f"Fiyat Düzeltme ({old_purchase_price} -> {new_purchase_price}): {old_stock} adet {name}"

                        self.add_transaction(
                            t_type=t_type,
                            category=adj_category,
                            amount=abs(total_adj),
                            description=adj_desc,
                            payment_method="Nakit",
                            currency=new_currency,
                            original_amount=abs(total_adj),
                        )
                except Exception as e:
                    logger.error(f"Stock price adjustment accounting error: {e}")

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Part update error: {e}")
            return False

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

    def use_part(self, part_id, quantity=1, tracking_no=None, **kwargs):
        """Parça kullan — stok düşer, used_parts'a kayıt eklenir.
        Not: Parça maliyeti zaten 'Stok Alımı' Gider kaydı ile muhasebeleştirilmiştir.
        Gelir kaydı, cihaz teslim edildiğinde oluşturulur."""
        try:
            # Mevcut stoku kontrol et (currency da çekilir)
            self.cursor.execute(
                "SELECT name, stock, price, purchase_price, COALESCE(currency, 'TRY') FROM parts WHERE id=?",
                (part_id,),
            )
            result = self.cursor.fetchone()
            if not result:
                return False

            part_name = result[0] or f"Parça #{part_id}"
            current_stock = int(result[1] or 0)
            sell_price = float(result[2] or 0)
            purchase_price = float(result[3] or 0)
            part_currency = str(result[4] or "TRY").upper()

            if current_stock < quantity:
                logger.warning(f"Insufficient stock for part {part_id}")
                return False

            # Stok düş
            new_stock = current_stock - quantity
            self.cursor.execute(
                "UPDATE parts SET stock=? WHERE id=?", (new_stock, part_id)
            )

            # Kullanım kaydı — currency da saklanır
            if tracking_no:
                self.cursor.execute(
                    """
                    INSERT INTO used_parts (tracking_no, part_id, part_name, price, quantity, purchase_price_snapshot, currency, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                """,
                    (
                        tracking_no,
                        part_id,
                        part_name,
                        sell_price,
                        quantity,
                        purchase_price,
                        part_currency,
                    ),
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
                        "Service debt sync skipped after use_part (%s): %s",
                        tracking_no,
                        sync_err,
                    )
            return True
        except Exception as e:
            logger.error(f"Use part error: {e}")
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

            query = "SELECT id, tracking_no, part_id, part_name, COALESCE(quantity, 1) FROM used_parts WHERE id=?"
            if deleted_col:
                query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
            self.cursor.execute(query, (used_part_id,))
            row = self.cursor.fetchone()
            if not row:
                return False

            tracking_no = row[1]
            stock_part_id = row[2]
            part_name = row[3] or "-"
            quantity = int(row[4] or 1)

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
                self.add_stock_movement(
                    part_id=stock_part_id,
                    amount=quantity,
                    current_stock=current_stock,
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
        """Stok hareketi kaydet"""
        try:
            self._ensure_stock_movements_schema()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_stock = current_stock + (amount if type_val == "Giriş" else -amount)

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

    def get_stock_history(self, part_id=None):
        """Stok geçmişini getir"""
        try:
            self._ensure_stock_movements_schema()
            self.ensure_stock_history_seeded()

            # Use row_factory for dict-like access
            old_factory = self.conn.row_factory
            try:
                import sqlite3 as _sqlite3

                self.conn.row_factory = _sqlite3.Row
                cur = self.conn.cursor()

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
                        WHERE sm.part_id=? AND COALESCE(sm.is_deleted, 0) = 0
                        ORDER BY sm.created_at DESC
                    """,
                        (part_id,),
                    )
                else:
                    cur.execute("""
                        SELECT sm.id, sm.part_id, sm.movement_type, sm.amount, sm.new_stock,
                               sm.description, sm.created_at,
                               COALESCE(p.name, p.part_name, 'Bilinmeyen Parça') AS part_name,
                               UPPER(COALESCE(p.currency, 'TRY')) AS currency,
                               COALESCE(p.purchase_price, 0) AS unit_cost
                        FROM stock_movements sm
                        LEFT JOIN parts p ON sm.part_id = p.id
                        WHERE COALESCE(sm.is_deleted, 0) = 0
                        ORDER BY sm.created_at DESC LIMIT 200
                    """)

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

            return result
        except Exception as e:
            logger.error(f"get_stock_history error: {e}")
            return []
