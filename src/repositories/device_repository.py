# -*- coding: utf-8 -*-

"""
Device Repository

Cihaz ve servis takibi için veritabanı işlemleri.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .base_repository import BaseRepository


class DeviceRepository(BaseRepository):
    """Cihaz ve servis yönetimi için repository."""

    def _get_table_name(self) -> str:
        return 'devices'

    def create_device(self, device_data: Dict[str, Any]) -> int:
        """
        Yeni cihaz kaydı oluştur.

        Args:
            device_data: Cihaz bilgileri

        Returns:
            Oluşturulan cihaz ID'si
        """
        # Varsayılan değerler
        defaults = {
            'entry_date': datetime.now().isoformat(),
            'status': 'Beklemede',
            'approval_status': 'Beklemede',
            'is_deleted': 0,
            'price': 0.0,
        }

        for key, value in defaults.items():
            if key not in device_data:
                device_data[key] = value

        return self.insert(device_data)

    def get_device_by_tracking_no(self, tracking_no: str) -> Optional[Dict[str, Any]]:
        """
        Takip numarasına göre cihaz bul.

        Args:
            tracking_no: Takip numarası

        Returns:
            Cihaz kaydı veya None
        """
        query = """
            SELECT * FROM devices
            WHERE tracking_no = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            LIMIT 1
        """
        return self.fetch_one(query, (tracking_no,))

    def get_devices_by_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """
        Müşteriye ait cihazları getir.

        Args:
            customer_id: Müşteri ID

        Returns:
            Cihaz listesi
        """
        query = """
            SELECT * FROM devices
            WHERE customer_id = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY entry_date DESC
        """
        return self.fetch_many(query, (customer_id,))

    def get_devices_by_status(self, status: str) -> List[Dict[str, Any]]:
        """
        Duruma göre cihazları getir.

        Args:
            status: Cihaz durumu (örn: 'Beklemede', 'Tamamlandı')

        Returns:
            Cihaz listesi
        """
        query = """
            SELECT * FROM devices
            WHERE status = ?
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY entry_date DESC
        """
        return self.fetch_many(query, (status,))

    def update_status(self, device_id: int, status: str) -> bool:
        """
        Cihaz durumunu güncelle.

        Args:
            device_id: Cihaz ID
            status: Yeni durum

        Returns:
            Başarılı ise True
        """
        return self.update(device_id, {'status': status})

    def update_approval_status(self, device_id: int, approval_status: str) -> bool:
        """
        Onay durumunu güncelle.

        Args:
            device_id: Cihaz ID
            approval_status: Yeni onay durumu

        Returns:
            Başarılı ise True
        """
        return self.update(device_id, {'approval_status': approval_status})

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """
        Onay bekleyen cihazları getir.

        Returns:
            Onay bekleyen cihaz listesi
        """
        query = """
            SELECT * FROM devices
            WHERE approval_status = 'Beklemede'
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY entry_date ASC
        """
        return self.fetch_many(query)

    def get_overdue_devices(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Gecikmiş cihazları getir.

        Args:
            days: Kaç günden eski cihazlar

        Returns:
            Gecikmiş cihaz listesi
        """
        query = """
            SELECT * FROM devices
            WHERE estimated_date < date('now', '-{} days')
            AND status NOT IN ('Tamamlandı', 'İptal Edildi')
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY estimated_date ASC
        """.format(days)
        return self.fetch_many(query)

    def search_devices(
        self,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Cihaz ara (takip no, müşteri adı, model).

        Args:
            search_term: Arama terimi
            limit: Maksimum sonuç sayısı

        Returns:
            Bulunan cihazlar
        """
        query = """
            SELECT * FROM devices
            WHERE (
                tracking_no LIKE ? OR
                customer_name LIKE ? OR
                device_model LIKE ? OR
                serial_no LIKE ?
            )
            AND (is_deleted = 0 OR is_deleted IS NULL)
            ORDER BY entry_date DESC
            LIMIT ?
        """
        pattern = f"%{search_term}%"
        return self.fetch_many(query, (pattern, pattern, pattern, pattern, limit))

    def get_device_statistics(self) -> Dict[str, Any]:
        """
        Cihaz istatistiklerini getir.

        Returns:
            İstatistik sözlüğü
        """
        stats = {}

        # Toplam cihaz
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM devices
            WHERE is_deleted = 0 OR is_deleted IS NULL
        """)
        stats['total_devices'] = result['count'] if result else 0

        # Duruma göre dağılım
        result = self.fetch_many("""
            SELECT status, COUNT(*) as count
            FROM devices
            WHERE is_deleted = 0 OR is_deleted IS NULL
            GROUP BY status
        """)
        stats['status_distribution'] = {
            row['status']: row['count'] for row in result
        }

        # Onay bekleyen
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM devices
            WHERE approval_status = 'Beklemede'
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """)
        stats['pending_approvals'] = result['count'] if result else 0

        # Bu ay gelen
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM devices
            WHERE entry_date >= date('now', 'start of month')
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """)
        stats['new_this_month'] = result['count'] if result else 0

        # Gecikmiş
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM devices
            WHERE estimated_date < date('now')
            AND status NOT IN ('Tamamlandı', 'İptal Edildi')
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """)
        stats['overdue'] = result['count'] if result else 0

        return stats

    def get_revenue_by_period(self, start_date: str, end_date: str) -> float:
        """
        Belirli dönemdeki toplam geliri hesapla.

        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD)
            end_date: Bitiş tarihi (YYYY-MM-DD)

        Returns:
            Toplam gelir
        """
        query = """
            SELECT COALESCE(SUM(price), 0) as total
            FROM devices
            WHERE entry_date BETWEEN ? AND ?
            AND status = 'Tamamlandı'
            AND (is_deleted = 0 OR is_deleted IS NULL)
        """
        result = self.fetch_one(query, (start_date, end_date))
        return result['total'] if result else 0.0
