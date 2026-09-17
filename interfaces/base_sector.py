# -*- coding: utf-8 -*-

from __future__ import annotations

from abc import ABC
from typing import Any, Dict, List, Optional


class BaseSector(ABC):
    """
    AYEC Pro sektör pluginleri için temel sözleşme.

    Çoğu metod varsayılan no-op/fallback davranışla gelir; pluginler ihtiyaca göre override eder.
    """

    @property
    def sector_id(self) -> str:
        raise NotImplementedError("sector_id must be implemented")

    @property
    def sector_name(self) -> str:
        raise NotImplementedError("sector_name must be implemented")

    @property
    def sector_icon(self) -> str:
        return ""

    def initialize_database(self, db) -> None:
        return None

    def get_menu_items(self) -> List[Dict[str, Any]]:
        return []

    def get_dashboard_widget(self, parent=None, db=None):
        return None

    def get_stock_columns(self) -> List[Dict[str, Any]]:
        return []

    def get_customer_form_fields(self) -> List[Dict[str, Any]]:
        return []

    def get_service_form_fields(self) -> List[Dict[str, Any]]:
        return []

    def get_quick_categories(self) -> Dict[str, Any]:
        return {}

    def get_page_overrides(self) -> Dict[str, str]:
        return {}

    def get_extension_schema(self) -> Dict[str, List[Dict[str, Any]]]:
        return {}

    def get_form_descriptors(self, entity: str) -> List[Dict[str, Any]]:
        return []

    def get_checklist_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        return {}

    def get_maintenance_card_sections(self) -> List[Dict[str, Any]]:
        return []

    def get_automotive_modules(self) -> List[Dict[str, Any]]:
        return []

    def get_checkup_templates(self) -> Dict[str, List[Dict[str, Any]]]:
        return {}

    def get_quote_form_descriptors(self) -> List[Dict[str, Any]]:
        return []

    def get_delivery_form_descriptors(self) -> List[Dict[str, Any]]:
        return []

    def get_history_sections(self) -> List[Dict[str, Any]]:
        return []

    def get_template_override_entities(self) -> List[str]:
        return []

    def map_core_to_extension_payload(self, entity: str, form_data: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def hydrate_form_defaults(
        self,
        entity: str,
        core_row: Optional[Dict[str, Any]],
        extension_row: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        if core_row:
            merged.update(dict(core_row))
        if extension_row:
            merged.update(dict(extension_row))
        return merged

    def is_feature_available(self, feature_name: str) -> bool:
        return False

    def get_sectoral_stats(self, db) -> Dict[str, Any]:
        return {}
