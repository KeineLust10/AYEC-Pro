# -*- coding: utf-8 -*-

"""
Personnel Repository

Personel yönetimi için veritabanı işlemleri.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from .base_repository import BaseRepository


class PersonnelRepository(BaseRepository):
    """Personel yönetimi için repository."""

    def _get_table_name(self) -> str:
        return 'personnel'

    def create_personnel(self, personnel_data: Dict[str, Any]) -> int:
        """
        Yeni personel oluştur.

        Args:
            personnel_data: Personel bilgileri

        Returns:
            Oluşturulan personel ID'si
        """
        defaults = {
            'salary': 0.0,
            'commission': 0.0,
            'created_at': datetime.now().isoformat(),
            'active': 1,
        }

        for key, value in defaults.items():
            if key not in personnel_data:
                personnel_data[key] = value

        return self.insert(personnel_data)

    def get_personnel_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """
        Kullanıcı adına göre personel bul.

        Args:
            username: Kullanıcı adı

        Returns:
            Personel kaydı veya None
        """
        query = """
            SELECT * FROM personnel
            WHERE username = ?
            LIMIT 1
        """
        return self.fetch_one(query, (username,))

    def get_personnel_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        E-posta adresine göre personel bul.

        Args:
            email: E-posta adresi

        Returns:
            Personel kaydı veya None
        """
        query = """
            SELECT * FROM personnel
            WHERE email = ?
            LIMIT 1
        """
        return self.fetch_one(query, (email,))

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Personel kimlik doğrulama.

        Args:
            username: Kullanıcı adı
            password: Şifre (hash'lenmiş olmalı)

        Returns:
            Personel kaydı veya None
        """
        query = """
            SELECT * FROM personnel
            WHERE username = ? AND password = ? AND active = 1
            LIMIT 1
        """
        return self.fetch_one(query, (username, password))

    def get_active_personnel(self) -> List[Dict[str, Any]]:
        """
        Aktif personelleri getir.

        Returns:
            Aktif personel listesi
        """
        query = """
            SELECT * FROM personnel
            WHERE active = 1
            ORDER BY name ASC
        """
        return self.fetch_many(query)

    def get_personnel_by_role(self, role: str) -> List[Dict[str, Any]]:
        """
        Role göre personelleri getir.

        Args:
            role: Personel rolü

        Returns:
            Personel listesi
        """
        query = """
            SELECT * FROM personnel
            WHERE role = ?
            ORDER BY name ASC
        """
        return self.fetch_many(query, (role,))

    def search_personnel(
        self,
        search_term: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Personel ara (isim, kullanıcı adı, telefon, e-posta).

        Args:
            search_term: Arama terimi
            limit: Maksimum sonuç

        Returns:
            Personel listesi
        """
        query = """
            SELECT * FROM personnel
            WHERE (
                name LIKE ? OR
                username LIKE ? OR
                phone LIKE ? OR
                email LIKE ?
            )
            ORDER BY name ASC
            LIMIT ?
        """
        pattern = f"%{search_term}%"
        return self.fetch_many(query, (pattern, pattern, pattern, pattern, limit))

    def update_salary(self, personnel_id: int, new_salary: float) -> bool:
        """
        Personel maaşını güncelle.

        Args:
            personnel_id: Personel ID
            new_salary: Yeni maaş

        Returns:
            Başarılı ise True
        """
        return self.update(personnel_id, {'salary': new_salary})

    def update_commission(self, personnel_id: int, new_commission: float) -> bool:
        """
        Personel prim oranını güncelle.

        Args:
            personnel_id: Personel ID
            new_commission: Yeni prim oranı (%)

        Returns:
            Başarılı ise True
        """
        return self.update(personnel_id, {'commission': new_commission})

    def activate(self, personnel_id: int) -> bool:
        """
        Personeli aktifleştir.

        Args:
            personnel_id: Personel ID

        Returns:
            Başarılı ise True
        """
        return self.update(personnel_id, {'active': 1})

    def deactivate(self, personnel_id: int) -> bool:
        """
        Personeli pasifleştir.

        Args:
            personnel_id: Personel ID

        Returns:
            Başarılı ise True
        """
        return self.update(personnel_id, {'active': 0})

    def update_password(self, personnel_id: int, new_password: str) -> bool:
        """
        Personel şifresini güncelle.

        Args:
            personnel_id: Personel ID
            new_password: Yeni şifre (hash'lenmiş olmalı)

        Returns:
            Başarılı ise True
        """
        return self.update(personnel_id, {'password': new_password})

    def get_personnel_statistics(self) -> Dict[str, Any]:
        """
        Personel istatistiklerini getir.

        Returns:
            İstatistik sözlüğü
        """
        stats = {}

        # Toplam personel
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM personnel
        """)
        stats['total_personnel'] = result['count'] if result else 0

        # Aktif personel
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM personnel
            WHERE active = 1
        """)
        stats['active_personnel'] = result['count'] if result else 0

        # Pasif personel
        result = self.fetch_one("""
            SELECT COUNT(*) as count FROM personnel
            WHERE active = 0
        """)
        stats['inactive_personnel'] = result['count'] if result else 0

        # Role göre dağılım
        result = self.fetch_many("""
            SELECT role, COUNT(*) as count
            FROM personnel
            GROUP BY role
            ORDER BY count DESC
        """)
        stats['role_distribution'] = {
            row['role'] or 'Belirtilmemiş': row['count'] for row in result
        }

        # Toplam maaş bütçesi
        result = self.fetch_one("""
            SELECT COALESCE(SUM(salary), 0) as total FROM personnel
            WHERE active = 1
        """)
        stats['total_salary_budget'] = result['total'] if result else 0.0

        # Ortalama maaş
        result = self.fetch_one("""
            SELECT AVG(salary) as avg_salary FROM personnel
            WHERE active = 1
        """)
        stats['average_salary'] = result['avg_salary'] if result and result['avg_salary'] else 0.0

        return stats

    def get_roles(self) -> List[str]:
        """
        Tüm rolleri getir.

        Returns:
            Rol listesi
        """
        query = """
            SELECT DISTINCT role FROM personnel
            WHERE role IS NOT NULL AND role != ''
            ORDER BY role ASC
        """
        results = self.fetch_many(query)
        return [row['role'] for row in results]

    def calculate_commission(self, personnel_id: int, sale_amount: float) -> float:
        """
        Belirli bir satış tutarı için prim hesapla.

        Args:
            personnel_id: Personel ID
            sale_amount: Satış tutarı

        Returns:
            Prim tutarı
        """
        personnel = self.get_by_id(personnel_id)
        if not personnel:
            return 0.0

        commission_rate = personnel.get('commission', 0) or 0
        return sale_amount * (commission_rate / 100)
