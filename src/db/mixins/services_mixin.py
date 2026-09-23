# -*- coding: utf-8 -*-

"""
Services Mixin
Hizmet yönetimi ile ilgili database metodları
"""

from datetime import datetime
from src.utils.logger import logger


class ServicesMixin:
    def _ensure_services_management_schema(self):
        """Add extended labor columns without losing legacy service data."""
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                price REAL DEFAULT 0,
                currency TEXT DEFAULT 'TRY',
                description TEXT,
                barcode TEXT,
                created_at TEXT,
                is_deleted INTEGER DEFAULT 0,
                deleted_at TEXT,
                price_try REAL DEFAULT 0,
                price_usd REAL DEFAULT 0,
                price_eur REAL DEFAULT 0,
                is_active INTEGER DEFAULT 1
            )
            """
        )
        self.cursor.execute("PRAGMA table_info(services)")
        columns = {row[1] for row in self.cursor.fetchall()}
        additions = (
            ("price_try", "REAL DEFAULT 0"),
            ("price_usd", "REAL DEFAULT 0"),
            ("price_eur", "REAL DEFAULT 0"),
            ("is_active", "INTEGER DEFAULT 1"),
        )
        for column, declaration in additions:
            if column not in columns:
                self.cursor.execute(
                    f"ALTER TABLE services ADD COLUMN {column} {declaration}"
                )
        self.cursor.execute(
            """
            UPDATE services
            SET price_try = CASE
                    WHEN COALESCE(price_try, 0) = 0
                     AND UPPER(COALESCE(currency, 'TRY')) = 'TRY'
                    THEN COALESCE(price, 0) ELSE COALESCE(price_try, 0) END,
                price_usd = CASE
                    WHEN COALESCE(price_usd, 0) = 0
                     AND UPPER(COALESCE(currency, 'TRY')) = 'USD'
                    THEN COALESCE(price, 0) ELSE COALESCE(price_usd, 0) END,
                price_eur = CASE
                    WHEN COALESCE(price_eur, 0) = 0
                     AND UPPER(COALESCE(currency, 'TRY')) = 'EUR'
                    THEN COALESCE(price, 0) ELSE COALESCE(price_eur, 0) END,
                is_active = COALESCE(is_active, 1)
            """
        )
        self.conn.commit()

    """Hizmetler için database metodları"""
    
    def get_services_list(self):
        """Tüm hizmetleri getir"""
        try:
            self._ensure_services_management_schema()
            self.cursor.execute(
                """
                SELECT id, name, price, currency, description, barcode, created_at,
                       COALESCE(price_try, 0) AS price_try,
                       COALESCE(price_usd, 0) AS price_usd,
                       COALESCE(price_eur, 0) AS price_eur,
                       COALESCE(is_active, 1) AS is_active
                FROM services
                WHERE COALESCE(is_deleted, 0) = 0
                ORDER BY name
                """
            )
            columns = [item[0] for item in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except Exception as e:
            logger.error("Get services list error: %s", e)
            return []
    
    def get_service_by_barcode(self, barcode):
        """Barkod ile hizmet ara"""
        try:
            self.cursor.execute("SELECT * FROM services WHERE barcode=? AND COALESCE(is_deleted, 0) = 0", (barcode,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Service barcode search error: {e}")
            return None
    
    def add_service(
        self,
        name,
        price,
        description="",
        barcode="",
        currency="TRY",
        price_try=None,
        price_usd=None,
        price_eur=None,
        is_active=1,
    ):
        """Add or restore an extended labor definition."""
        try:
            self._ensure_services_management_schema()
            selected_currency = (currency or "TRY").upper()
            prices = self._normalize_service_prices(
                price,
                selected_currency,
                price_try,
                price_usd,
                price_eur,
            )
            legacy_price = prices[selected_currency]
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("SELECT id FROM services WHERE name=?", (name,))
            existing = self.cursor.fetchone()
            if existing:
                service_id = existing[0]
                self.cursor.execute(
                    """
                    UPDATE services
                    SET price=?, description=?, barcode=?, currency=?,
                        price_try=?, price_usd=?, price_eur=?, is_active=?,
                        is_deleted=0, deleted_at=NULL
                    WHERE id=?
                    """,
                    (
                        legacy_price,
                        description,
                        barcode,
                        selected_currency,
                        prices["TRY"],
                        prices["USD"],
                        prices["EUR"],
                        int(bool(is_active)),
                        service_id,
                    ),
                )
            else:
                self.cursor.execute(
                    """
                    INSERT INTO services (
                        name, price, description, barcode, currency, created_at,
                        price_try, price_usd, price_eur, is_active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        legacy_price,
                        description,
                        barcode,
                        selected_currency,
                        created_at,
                        prices["TRY"],
                        prices["USD"],
                        prices["EUR"],
                        int(bool(is_active)),
                    ),
                )
                service_id = self.cursor.lastrowid
            self.conn.commit()
            return service_id
        except Exception as exc:
            logger.error("Service add error: %s", exc)
            return None

    def update_service(
        self,
        service_id,
        name,
        price,
        description="",
        barcode="",
        currency="TRY",
        price_try=None,
        price_usd=None,
        price_eur=None,
        is_active=1,
    ):
        """Update an extended labor definition."""
        try:
            self._ensure_services_management_schema()
            selected_currency = (currency or "TRY").upper()
            prices = self._normalize_service_prices(
                price,
                selected_currency,
                price_try,
                price_usd,
                price_eur,
            )
            self.cursor.execute(
                """
                UPDATE services
                SET name=?, price=?, description=?, barcode=?, currency=?,
                    price_try=?, price_usd=?, price_eur=?, is_active=?
                WHERE id=?
                """,
                (
                    name,
                    prices[selected_currency],
                    description,
                    barcode,
                    selected_currency,
                    prices["TRY"],
                    prices["USD"],
                    prices["EUR"],
                    int(bool(is_active)),
                    service_id,
                ),
            )
            self.conn.commit()
            return True
        except Exception as exc:
            logger.error("Service update error: %s", exc)
            return False

    @staticmethod
    def _normalize_service_prices(
        price,
        currency,
        price_try,
        price_usd,
        price_eur,
    ):
        selected = currency if currency in {"TRY", "USD", "EUR"} else "TRY"
        values = {
            "TRY": price_try,
            "USD": price_usd,
            "EUR": price_eur,
        }
        for code in values:
            if values[code] is None:
                values[code] = price if code == selected else 0
            values[code] = float(values[code] or 0)
        return values

    def delete_service(self, service_id):
        """Hizmet soft delete"""
        try:
            if hasattr(self, "soft_delete_record"):
                return self.soft_delete_record("services", "id", service_id)
            deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                "UPDATE services SET is_deleted=1, deleted_at=? WHERE id=?",
                (deleted_at, service_id)
            )
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Service delete error: {e}")
            return False
    
    def load_ato_2025_services(self):
        """ATO 2025 Resmi Fiyat Listesini yükle (eğer boşsa)"""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM services")
            if self.cursor.fetchone()[0] > 0:
                return  # Zaten hizmetler var
            
            # ATO 2025 default hizmetler listesi...
            default_services = [
                ("Ekran Değişimi", 350.00, "Ekran camı değişimi", "SRV001"),
                ("Batarya Değişimi", 200.00, "Batarya değişimi", "SRV002"),
                ("Şarj Soketi Tamiri", 150.00, "Şarj soketi onarımı", "SRV003"),
                # ... (daha fazla hizmet eklenebilir)
            ]
            
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for name, price, desc, barcode in default_services:
                self.cursor.execute("""
                    INSERT INTO services (name, price, description, barcode, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, price, desc, barcode, created_at))
            
            self.conn.commit()
            logger.info("ATO 2025 hizmetleri yüklendi")

        except Exception as e:
            logger.error(f"ATO services load error: {e}")

    def add_customer_service_record(self, customer_id, name, qty, unit_price, total, notes, date):
        """Müşteri hizmet geçmişine kayıt ekle (Sihirbaz/Hızlı İşlem)"""
        try:
            self.cursor.execute("""
                INSERT INTO customer_services 
                (customer_id, service_name, quantity, unit_price, total_amount, notes, date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (customer_id, name, qty, unit_price, total, notes, date))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add customer service record error: {e}")
            return False
