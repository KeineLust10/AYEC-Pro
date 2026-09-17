# -*- coding: utf-8 -*-
"""
BaseService - Servis işlemleri için temel sınıf
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseService(ABC):
    """
    Servis kayıtları için sektöre özel işlemler
    """

    @abstractmethod
    def get_service_types(self) -> List[Dict[str, str]]:
        """
        Servis türleri listesi
        
        Returns:
            List[Dict]: [{'id': 'tamir', 'name': 'Tamir', 'color': '#FF0000'}, ...]
        """
        pass

    @abstractmethod
    def get_status_flow(self) -> List[str]:
        """
        Servis durum akışı (sıralı)
        
        Returns:
            List[str]: Durum adları
        """
        pass

    @abstractmethod
    def validate_service_data(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Servis verilerini doğrula
        
        Args:
            data: Servis verileri
            
        Returns:
            tuple: (geçerli_mi, hata_mesajı)
        """
        pass

    @abstractmethod
    def format_service_summary(self, service_data: Dict[str, Any]) -> str:
        """
        Servis özetini formatla
        
        Args:
            service_data: Servis verileri
            
        Returns:
            str: Formatlanmış özet
        """
        pass
