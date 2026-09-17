# -*- coding: utf-8 -*-

"""
Service Repository

Hizmet yönetimi için veritabanı işlemleri.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .base_repository import BaseRepository


class ServiceRepository(BaseRepository):
    """Hizmet yönetimi için repository."""

    def _get_table_name(self) -> str:
        return 'services'

    def create_service(self, service_data: Dict[str, Any]) -> int:
        """
        Yeni hizmet oluştur.

        Args:
            service_data: Hizmet bilgileri

        Returns:
            Oluşturulan hizmet ID'si
        """
        defaults = {
            'price': 0.0,
            'created_at': datetime.now().isoformat(),
            'is_deleted': 0,
        }

        for key, value in defaults.items():
            if key not in service_data:
                service_data[key] = value

        return self.insert(service_data)

    def get_service_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        İsme göre hizmet bul.

        Args:
            name: Hizmet adı

        Returns:
            Hizmet kaydı veya None
        """
        query = """
            SELECT * FROM services
            WHERE name = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            LIMIT 1
        """
        return self.fetch_one(query, (name,))

    def get_service_by_barcode(self, barcode: str) -> Optional[Dict[str, Any]]:
        """
        Barkod ile hizmet bul.

        Args:
            barcode: Barkod

        Returns:
            Hizmet kaydı veya None
        """
        query = """
            SELECT * FROM services
            WHERE barcode = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            LIMIT 1
        """
        return self.fetch_one(query, (barcode,))

    def search_services(
        self,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Hizmet ara (isim, barkod, açıklama).

        Args:
            search_term: Arama terimi
            limit: Maksimum sonuç

        Returns:
            Hizmet listesi
        """
        query = """
            SELECT * FROM services
            WHERE (
                name LIKE ? OR
                barcode LIKE ? OR
                description LIKE ?
            )
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY name ASC
            LIMIT ?
        """
        pattern = f"%{search_term}%"
        return self.fetch_many(query, (pattern, pattern, pattern, limit))

    def get_services_by_price_range(
        self,
        min_price: float = 0,
        max_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Fiyat aralığına göre hizmetleri getir.

        Args:
            min_price: Minimum fiyat
            max_price: Maksimum fiyat (None = sınırsız)

        Returns:
            Hizmet listesi
        """
        if max_price is not None:
            query = """
                SELECT * FROM services
                WHERE price BETWEEN ? AND ?
                AND (is_deleted = 0 OR is_deleted IS NULL)
                ORDER BY price ASC
            """
            return self.fetch_many(query, (min_price, max_price))
        else:
            query = """
                SELECT * FROM services
                WHERE price >= ?
                AND (is_deleted = 0 OR is_deleted IS NULL)
                ORDER BY price ASC
            """
            return self.fetch_many(query, (min_price,))

    def update_price(self, service_id: int, new_price: float) -> bool:
        """
        Hizmet fiyatını güncelle.

        Args:
            service_id: Hizmet ID
            new_price: Yeni fiyat

        Returns:
            Başarılı ise True
        """
        return self.update(service_id, {'price': new_price})

    def update_barcode(self, service_id: int, barcode: str) -> bool:
        """
        Hizmet barkodunu güncelle.

        Args:
            service_id: Hizmet ID
            barcode: Yeni barkod

        Returns:
            Başarılı ise True
        """
        return self.update(service_id, {'barcode': barcode})

    def get_service_statistics(self) -> Dict[str, Any]:
        """
        Hizmet istatistiklerini getir.

        Returns:
            İstatistik sözlüğü
        """
        stats = {}

        # Toplam hizmet
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM services
            WHERE is_deleted = 0 OR is_deleted IS NULL
        """)
        stats['total_services'] = result['count'] if result else 0

        # Ortalama fiyat
        result = self.fetch_one("""
            SELECT AVG(price) as avg_price FROM services
            WHERE is_deleted = 0 OR is_deleted IS NULL
        """)
        stats['average_price'] = result['avg_price'] if result and result['avg_price'] else 0.0

        # En yüksek fiyat
        result = self.fetch_one("""
            SELECT MAX(price) as max_price FROM services
            WHERE is_deleted = 0 OR is_deleted IS NULL
        """)
        stats['max_price'] = result['max_price'] if result and result['max_price'] else 0.0

        # En düşük fiyat
        result = self.fetch_one("""
            SELECT MIN(price) as min_price FROM services
            WHERE is_deleted = 0 OR is_deleted IS NULL
        """)
        stats['min_price'] = result['min_price'] if result and result['min_price'] else 0.0

        # Barkodlu hizmet sayısı
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM services
            WHERE barcode IS NOT NULL AND barcode != ''
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """)
        stats['barcoded_services'] = result['count'] if result else 0

        return stats

    def get_recent_services(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Son eklenen hizmetleri getir.

        Args:
            limit: Maksimum sonuç sayısı

        Returns:
            Hizmet listesi
        """
        query = """
            SELECT * FROM services
            WHERE is_deleted = 0 OR is_deleted IS NULL
            ORDER BY created_at DESC
            LIMIT ?
        """
        return self.fetch_many(query, (limit,))

    def has_barcode(self, service_id: int) -> bool:
        """
        Hizmetin barkodu var mı kontrol et.

        Args:
            service_id: Hizmet ID

        Returns:
            Barkod varsa True
        """
        query = """
            SELECT 1 FROM services
            WHERE id = ? AND barcode IS NOT NULL AND barcode != ''
            AND (is_deleted = 0 OR is_deleted IS NULL)
            LIMIT 1
        """
        result = self.fetch_one(query, (service_id,))
        return result is not None
