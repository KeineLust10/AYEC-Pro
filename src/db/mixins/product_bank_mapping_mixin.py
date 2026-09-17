# -*- coding: utf-8 -*-

"""
Stok/Hizmet - Banka Hesabı Eşleştirme Mixin
Her stok veya hizmet için varsayılan banka hesabı, KDV oranı ve kategori tanımlar.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ProductBankMappingMixin:

    def create_product_bank_mappings_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_bank_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    item_id INTEGER NOT NULL,
                    bank_account_id INTEGER,
                    default_kdv_rate REAL DEFAULT 20,
                    default_category TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT,
                    UNIQUE(item_type, item_id)
                )
            """)
            self.conn.commit()
        except Exception as e:
            logger.error(f"product_bank_mappings table creation error: {e}")

    def get_product_bank_mapping(self, item_type, item_id):
        """Belirli bir stok veya hizmetin banka eşleştirmesini getir."""
        try:
            self.cursor.execute(
                "SELECT bank_account_id, default_kdv_rate, default_category "
                "FROM product_bank_mappings WHERE item_type=? AND item_id=?",
                (item_type, item_id),
            )
            row = self.cursor.fetchone()
            if not row:
                if item_id != 0:
                    fallback_types = []
                    if item_type == "product":
                        fallback_types = [
                            "product_stock",
                            "product_loaner",
                            "product_mobile",
                            "product",
                        ]
                    elif item_type == "service":
                        fallback_types = [
                            "service_definitions",
                            "service",
                        ]
                    else:
                        fallback_types = [item_type]
                    for fallback_type in fallback_types:
                        self.cursor.execute(
                            "SELECT bank_account_id, default_kdv_rate, default_category "
                            "FROM product_bank_mappings WHERE item_type=? AND item_id=0",
                            (fallback_type,),
                        )
                        row = self.cursor.fetchone()
                        if row:
                            break
                if not row:
                    return None
            if hasattr(row, "keys"):
                return dict(row)
            return {
                "bank_account_id": row[0],
                "default_kdv_rate": row[1],
                "default_category": row[2],
            }
        except Exception as e:
            logger.error(f"get_product_bank_mapping error: {e}")
            return None

    def get_all_product_bank_mappings(self):
        """Tüm stok ve hizmetleri eşleştirme bilgileriyle birlikte getir."""
        results = []
        try:
            # Ürünler (parts)
            self.cursor.execute("""
                SELECT p.id, p.name, p.price, p.category,
                       m.bank_account_id, m.default_kdv_rate, m.default_category
                FROM parts p
                LEFT JOIN product_bank_mappings m
                    ON m.item_type='product' AND m.item_id=p.id
                WHERE p.is_deleted IS NULL OR p.is_deleted=0
                ORDER BY p.name
            """)
            for row in self.cursor.fetchall():
                if hasattr(row, "keys"):
                    r = dict(row)
                else:
                    r = {
                        "id": row[0], "name": row[1], "price": row[2],
                        "category": row[3], "bank_account_id": row[4],
                        "default_kdv_rate": row[5], "default_category": row[6],
                    }
                r["item_type"] = "product"
                results.append(r)
        except Exception as e:
            logger.warning(f"get_all_product_bank_mappings (products): {e}")
            # parts tablosu is_deleted sütunu olmayabilir
            try:
                self.cursor.execute("""
                    SELECT p.id, p.name, p.price, p.category,
                           m.bank_account_id, m.default_kdv_rate, m.default_category
                    FROM parts p
                    LEFT JOIN product_bank_mappings m
                        ON m.item_type='product' AND m.item_id=p.id
                    ORDER BY p.name
                """)
                for row in self.cursor.fetchall():
                    if hasattr(row, "keys"):
                        r = dict(row)
                    else:
                        r = {
                            "id": row[0], "name": row[1], "price": row[2],
                            "category": row[3], "bank_account_id": row[4],
                            "default_kdv_rate": row[5], "default_category": row[6],
                        }
                    r["item_type"] = "product"
                    results.append(r)
            except Exception as e2:
                logger.error(f"get_all_product_bank_mappings (products fallback): {e2}")

        try:
            # Hizmetler (services)
            self.cursor.execute("""
                SELECT s.id, s.name, s.price, 'Hizmet' as category,
                       m.bank_account_id, m.default_kdv_rate, m.default_category
                FROM services s
                LEFT JOIN product_bank_mappings m
                    ON m.item_type='service' AND m.item_id=s.id
                ORDER BY s.name
            """)
            for row in self.cursor.fetchall():
                if hasattr(row, "keys"):
                    r = dict(row)
                else:
                    r = {
                        "id": row[0], "name": row[1], "price": row[2],
                        "category": row[3], "bank_account_id": row[4],
                        "default_kdv_rate": row[5], "default_category": row[6],
                    }
                r["item_type"] = "service"
                results.append(r)
        except Exception as e:
            logger.warning(f"get_all_product_bank_mappings (services): {e}")

        return results

    def set_product_bank_mapping(self, item_type, item_id, bank_account_id,
                                  default_kdv_rate=None, default_category=None):
        """Stok/hizmet için banka eşleştirmesi ekle veya güncelle (upsert)."""
        try:
            if default_kdv_rate is None:
                from src.utils.tax_settings import TaxSettings
                default_kdv_rate = TaxSettings.get_percent(self)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO product_bank_mappings
                    (item_type, item_id, bank_account_id, default_kdv_rate, default_category, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_type, item_id) DO UPDATE SET
                    bank_account_id=excluded.bank_account_id,
                    default_kdv_rate=excluded.default_kdv_rate,
                    default_category=excluded.default_category,
                    updated_at=excluded.updated_at
            """, (item_type, item_id, bank_account_id, default_kdv_rate, default_category, now))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"set_product_bank_mapping error: {e}")
            return False

    def delete_product_bank_mapping(self, item_type, item_id):
        """Eşleştirmeyi sil."""
        try:
            self.cursor.execute(
                "DELETE FROM product_bank_mappings WHERE item_type=? AND item_id=?",
                (item_type, item_id),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"delete_product_bank_mapping error: {e}")
            return False

    def bulk_set_bank_for_category(self, category, bank_account_id, default_kdv_rate=None):
        """Belirli bir kategorideki tüm ürünlere toplu banka ataması yap."""
        count = 0
        try:
            if default_kdv_rate is None:
                from src.utils.tax_settings import TaxSettings
                default_kdv_rate = TaxSettings.get_percent(self)
            self.cursor.execute(
                "SELECT id FROM parts WHERE category=?", (category,)
            )
            part_ids = [row[0] for row in self.cursor.fetchall()]
            for pid in part_ids:
                if self.set_product_bank_mapping("product", pid, bank_account_id,
                                                  default_kdv_rate, category):
                    count += 1
            return count
        except Exception as e:
            logger.error(f"bulk_set_bank_for_category error: {e}")
            return count
