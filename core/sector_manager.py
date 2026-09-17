# -*- coding: utf-8 -*-
"""
SectorManager - Aktif sektörün yönetimi ve UI entegrasyonu
"""

from typing import Optional, Dict, Any, List
from PyQt6.QtWidgets import QWidget

from .plugin_loader import PluginLoader
from interfaces import BaseSector


class SectorManager:
    """
    Aktif sektörün yönetiminden sorumludur.
    UI bileşenleri ile sektör eklentisi arasında köprü görevi görür.
    """

    def __init__(self, db=None):
        self._db = db
        self._current_plugin: Optional[BaseSector] = None

    def load_sector(self, sector_id: str) -> BaseSector:
        """
        Sektörü yükle ve hazırla.

        Args:
            sector_id: Yüklenecek sektör kimliği

        Returns:
            BaseSector: Yüklenen sektör eklentisi
        """
        self._current_plugin = PluginLoader.activate_sector(sector_id)

        if self._db:
            self._current_plugin.initialize_database(self._db)

        return self._current_plugin

    def get_current_plugin(self) -> Optional[BaseSector]:
        """Şu anki aktif eklentiyi döndürür."""
        return self._current_plugin

    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Aktif sektörün menü öğelerini alır."""
        if not self._current_plugin:
            return []
        return self._current_plugin.get_menu_items()

    def get_dashboard(self, parent=None) -> Optional[QWidget]:
        """Aktif sektörün dashboard widget'ını alır."""
        if not self._current_plugin:
            return None
        return self._current_plugin.get_dashboard_widget(parent, self._db)

    def get_stock_columns(self) -> List[Dict[str, Any]]:
        """Aktif sektörün stok kolonlarını alır."""
        if not self._current_plugin:
            return []
        return self._current_plugin.get_stock_columns()

    def get_customer_fields(self) -> List[Dict[str, Any]]:
        """Aktif sektörün müşteri form alanlarını alır."""
        if not self._current_plugin:
            return []
        return self._current_plugin.get_customer_form_fields()

    def get_service_fields(self) -> List[Dict[str, Any]]:
        """Aktif sektörün servis form alanlarını alır."""
        if not self._current_plugin:
            return []
        return self._current_plugin.get_service_form_fields()

    def get_quick_categories(self) -> Dict[str, Any]:
        """Aktif sektörün hızlı kategori tanımlarını alır."""
        if not self._current_plugin:
            return {}
        return self._current_plugin.get_quick_categories()

    def get_page_overrides(self) -> Dict[str, str]:
        """Aktif sektörün sayfa ve diyalog override eşlemelerini alır."""
        if not self._current_plugin:
            return {}
        return self._current_plugin.get_page_overrides()

    def get_extension_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        """Aktif sektörün extension şemasını alır."""
        if not self._current_plugin:
            return {}
        return self._current_plugin.get_extension_schema()

    def get_extension_fields(self, entity: str) -> List[Dict[str, Any]]:
        """Belirli entity için extension alanlarını alır."""
        return self.get_extension_schema().get(entity, [])

    def get_form_descriptors(self, entity: str) -> List[Dict[str, Any]]:
        """Aktif sektörün section bazlı form descriptor listesini alır."""
        if not self._current_plugin:
            return []
        return self._current_plugin.get_form_descriptors(entity)

    def get_checklist_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        """Aktif sektörün hazır checklist şablonlarını alır."""
        if not self._current_plugin:
            return {}
        return self._current_plugin.get_checklist_templates()

    def get_maintenance_card_sections(self) -> List[Dict[str, Any]]:
        """Aktif sektörün bakım kartı section tanımlarını alır."""
        if not self._current_plugin:
            return []
        return self._current_plugin.get_maintenance_card_sections()

    def get_automotive_modules(self) -> List[Dict[str, Any]]:
        if not self._current_plugin:
            return []
        return self._current_plugin.get_automotive_modules()

    def get_checkup_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        if not self._current_plugin:
            return {}
        return self._current_plugin.get_checkup_templates()

    def get_quote_form_descriptors(self) -> List[Dict[str, Any]]:
        if not self._current_plugin:
            return []
        return self._current_plugin.get_quote_form_descriptors()

    def get_delivery_form_descriptors(self) -> List[Dict[str, Any]]:
        if not self._current_plugin:
            return []
        return self._current_plugin.get_delivery_form_descriptors()

    def get_history_sections(self) -> List[Dict[str, Any]]:
        if not self._current_plugin:
            return []
        return self._current_plugin.get_history_sections()

    def get_template_override_entities(self) -> List[str]:
        if not self._current_plugin:
            return []
        return self._current_plugin.get_template_override_entities()

    def map_core_to_extension_payload(self, entity: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Form verisini aktif sektör extension payload'una dönüştürür."""
        if not self._current_plugin:
            return {}
        return self._current_plugin.map_core_to_extension_payload(entity, form_data)

    def hydrate_form_defaults(
        self,
        entity: str,
        core_row: Optional[Dict[str, Any]],
        extension_row: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Form için core ve extension verisini birleştirir."""
        if not self._current_plugin:
            merged = {}
            if core_row:
                merged.update(dict(core_row))
            if extension_row:
                merged.update(dict(extension_row))
            return merged
        return self._current_plugin.hydrate_form_defaults(entity, core_row, extension_row)

    def is_feature_available(self, feature_name: str) -> bool:
        """Belirli bir özellik aktif sektörde var mı?"""
        if not self._current_plugin:
            return False
        return self._current_plugin.is_feature_available(feature_name)

    def get_sectoral_stats(self) -> Dict[str, Any]:
        """Aktif sektörün istatistiklerini alır."""
        if not self._current_plugin or not self._db:
            return {}
        return self._current_plugin.get_sectoral_stats(self._db)

    @staticmethod
    def get_available_sectors() -> Dict[str, str]:
        """Tüm mevcut sektörleri alır."""
        return PluginLoader.get_available_sectors()
