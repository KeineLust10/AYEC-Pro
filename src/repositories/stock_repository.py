# -*- coding: utf-8 -*-

"""
Stock Repository

Stok ve envanter yönetimi için veritabanı işlemleri.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .base_repository import BaseRepository


class StockRepository(BaseRepository):
    """Stok yönetimi için repository."""

    def _get_table_name(self) -> str:
        return 'parts'

    def create_part(self, part_data: Dict[str, Any]) -> int:
        """
        Yeni parça/ürün oluştur.

        Args:
            part_data: Parça bilgileri

        Returns:
            Oluşturulan parça ID'si
        """
        defaults = {
            'stock': 0,
            'price': 0.0,
            'category': 'Genel',
        }

        for key, value in defaults.items():
            if key not in part_data:
                part_data[key] = value

        return self.insert(part_data)

    def get_part_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Parça koduna göre parça bul.

        Args:
            code: Parça kodu

        Returns:
            Parça kaydı veya None
        """
        query = """
            SELECT * FROM parts
            WHERE code = ?
            LIMIT 1
        """
        return self.fetch_one(query, (code,))

    def get_part_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Barkod ile parça bul.

        Args:
            barcode: Barkod

        Returns:
            Parça kaydı veya None
        """
        query = """
            SELECT * FROM parts
            WHERE barcode = ?
            LIMIT 1
        """
        return self.fetch_one(query, (barcode,))

    def search_parts(
        self,
        search_term: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Parça ara (isim, kod, barkod).

        Args:
            search_term: Arama terimi
            category: Kategori filtresi (opsiyonel)
            limit: Maksimum sonuç

        Returns:
            Parça listesi
        """
        if category:
            query = """
                SELECT * FROM parts
                WHERE (name LIKE ? OR code LIKE ? OR barcode LIKE ?)
                AND category = ?
                ORDER BY name ASC
                LIMIT ?
            """
            pattern = f"%{search_term}%"
            return self.fetch_many(query, (pattern, pattern, pattern, category, limit))
        else:
            query = """
                SELECT * FROM parts
                WHERE (name LIKE ? OR code LIKE ? OR barcode LIKE ?)
                ORDER BY name ASC
                LIMIT ?
            """
            pattern = f"%{search_term}%"
            return self.fetch_many(query, (pattern, pattern, pattern, limit))

    def get_parts_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Kategoriye göre parçaları getir.

        Args:
            category: Kategori adı

        Returns:
            Parça listesi
        """
        query = """
            SELECT * FROM parts
            WHERE category = ?
            ORDER BY name ASC
        """
        return self.fetch_many(query, (category,))

    def update_stock(self, part_id: int, quantity_change: int) -> bool:
        """
        Stok miktarını güncelle.

        Args:
            part_id: Parça ID
            quantity_change: Değişim miktarı (+/-)

        Returns:
            Başarılı ise True
        """
        query = """
            UPDATE parts
            SET stock = stock + ?
            WHERE id = ?
        """
        cursor = self.execute(query, (quantity_change, part_id))
        self._conn.commit()
        return cursor.rowcount > 0

    def get_low_stock_parts(self, threshold: int = 5) -> List[Dict[str, Any]]:
        """
        Düşük stoklu parçaları getir.

        Args:
            threshold: Stok eşik değeri

        Returns:
            Düşük stoklu parça listesi
        """
        query = """
            SELECT * FROM parts
            WHERE stock <= ?
            ORDER BY stock ASC
        """
        return self.fetch_many(query, (threshold,))

    def get_out_of_stock_parts(self) -> List[Dict[str, Any]]:
        """
        Tükenmiş stokları getir.

        Returns:
            Stoğu bitmiş parça listesi
        """
        query = """
            SELECT * FROM parts
            WHERE stock = 0
            ORDER BY name ASC
        """
        return self.fetch_many(query)

    def get_stock_value(self) -> Dict[str, Any]:
        """
        Stok değerlerini hesapla.

        Returns:
            Stok değeri özeti
        """
        summary = {}

        # Toplam parça çeşidi
        result = self.fetch_one("SELECT COUNT(*) as count FROM parts")
        summary['total_parts'] = result['count'] if result else 0

        # Toplam stok adedi
        result = self.fetch_one("SELECT COALESCE(SUM(stock), 0) as total FROM parts")
        summary['total_stock'] = result['total'] if result else 0

        # Toplam stok değeri
        result = self.fetch_one("""
            SELECT COALESCE(SUM(stock * price), 0) as value
            FROM parts
        """)
        summary['total_value'] = result['value'] if result else 0.0

        # Düşük stoklu çeşit sayısı
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM parts
            WHERE stock <= 5
        """)
        summary['low_stock_count'] = result['count'] if result else 0

        # Tükenmiş çeşit sayısı
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM parts
            WHERE stock = 0
        """)
        summary['out_of_stock_count'] = result['count'] if result else 0

        return summary

    def get_categories(self) -> List[str]:
        """
        Tüm kategorileri getir.

        Returns:
            Kategori listesi
        """
        query = """
            SELECT DISTINCT category FROM parts
            ORDER BY category ASC
        """
        results = self.fetch_many(query)
        return [row['category'] for row in results if row['category']]

    def get_category_summary(self) -> List[Dict[str, Any]]:
        """
        Kategori bazlı stok özeti.

        Returns:
            Kategori özet listesi
        """
        query = """
            SELECT
                category,
                COUNT(*) as part_count,
                COALESCE(SUM(stock), 0) as total_stock,
                COALESCE(SUM(stock * price), 0) as total_value
            FROM parts
            GROUP BY category
            ORDER BY total_value DESC
        """
        return self.fetch_many(query)

    def update_price(self, part_id: int, new_price: float) -> bool:
        """
        Parça fiyatını güncelle.

        Args:
            part_id: Parça ID
            new_price: Yeni fiyat

        Returns:
            Başarılı ise True
        """
        return self.update(part_id, {'price': new_price})

    def get_part_movements(self, part_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Parça hareketlerini getir.

        Args:
            part_id: Parça ID
            limit: Maksimum kayıt sayısı

        Returns:
            Hareket listesi
        """
        query = """
            SELECT * FROM stock_movements
            WHERE part_id = ? AND COALESCE(is_deleted, 0) = 0
            ORDER BY created_at DESC
            LIMIT ?
        """
        return self.fetch_many(query, (part_id, limit))

    def record_stock_movement(
        self,
        part_id: int,
        movement_type: str,
        quantity: int,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> int:
        """
        Stok hareketi kaydet.

        Args:
            part_id: Parça ID
            movement_type: 'in' (giriş) veya 'out' (çıkış)
            quantity: Miktar
            reference_type: Referans tipi (örn: 'service', 'purchase')
            reference_id: Referans ID
            notes: Notlar

        Returns:
            Hareket kaydı ID'si
        """
        # Get current stock for new_stock calculation
        part = self.get_by_id(part_id)
        current_stock = part.get('stock', 0) if part else 0

        # Calculate new stock based on movement type
        delta = int(quantity or 0)
        if movement_type.lower() in ('out', 'çıkış', 'cikis', 'sale', 'satış'):
            new_stock = current_stock - delta
            m_type = 'Çıkış'
        else:
            new_stock = current_stock + delta
            m_type = 'Giriş'

        # Build description from notes and reference info
        desc_parts = []
        if notes:
            desc_parts.append(notes)
        if reference_type:
            desc_parts.append(f"Ref: {reference_type}")
        if reference_id:
            desc_parts.append(f"ID: {reference_id}")
        description = " | ".join(desc_parts) if desc_parts else "Stok hareketi"

        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor = self.execute("""
            INSERT INTO stock_movements
            (part_id, movement_type, amount, new_stock, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (part_id, m_type, abs(delta), new_stock, description, created_at))

        # Update part stock
        self.execute("UPDATE parts SET stock = ? WHERE id = ?", (new_stock, part_id))

        self._conn.commit()
        return cursor.lastrowid
