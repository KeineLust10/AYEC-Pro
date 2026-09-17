# -*- coding: utf-8 -*-
"""
Legacy compatibility layer for sector selection.
Only two sectors are supported: teknik_servis and otomotiv.
"""

from enum import Enum
from typing import Dict, List, Optional, Set

from src.utils.system_config import DEFAULT_SECTOR, SystemConfig


class SectorType(Enum):
    OTOMOTIV = "otomotiv"
    TEKNIK_SERVIS = "teknik_servis"


SECTOR_INFO = {
    SectorType.OTOMOTIV: {
        "name": "Otomotiv Servis",
        "description": "Araç bakım, onarım ve servis yönetimi",
        "icon": "OS",
        "color": "#2563eb",
    },
    SectorType.TEKNIK_SERVIS: {
        "name": "Teknik Servis",
        "description": "Genel teknik servis ve bakım yönetimi",
        "icon": "TS",
        "color": "#059669",
    },
}


SECTOR_PAGES: Dict[SectorType, Set[int]] = {
    SectorType.OTOMOTIV: {
        40, 41, 42, 60, 62, 30, 150, 210,
        21, 25, 26, 90, 120,
        140, 145, 146, 147, 51, 66,
        313, 314,
        101, 105, 106, 115,
        10, 130, 135, 160, 180, 261, 70,
    },
    SectorType.TEKNIK_SERVIS: {
        40, 41, 42, 62, 61, 30, 65, 201,
        21, 25, 26, 90, 120,
        50, 51, 66, 140, 145, 146, 147, 150, 250, 300,
        313, 314,
        101, 105, 106, 115,
        10, 130, 135, 160, 180, 200, 202, 261, 70,
    },
}


SECTOR_MENU_GROUPS: Dict[SectorType, Dict[str, List[int]]] = {
    SectorType.OTOMOTIV: {
        "Ana Sayfa": [40],
        "Servis Y\u00f6netimi": [41, 60, 62, 30, 170],
        "Müşteri": [21, 25, 26, 90, 120],
        "Ticari": [66, 140, 145, 150],
        "Finans": [101, 105, 106, 115],
        "Sistem": [10, 130, 135, 160, 180, 261, 70],
    },
    SectorType.TEKNIK_SERVIS: {
        "Ana Sayfa": [40],
        "Servis Y\u00f6netimi": [41, 62, 61, 30, 65, 170, 201],
        "Müşteri": [21, 25, 26, 90, 120],
        "Ticari": [50, 66, 140, 145, 150, 250, 300],
        "Projeler": [200, 202],
        "Finans": [101, 105, 106, 115],
        "Sistem": [10, 130, 135, 160, 180, 261, 70],
    },
}

# Keep the automotive menu aligned with the allowed page set.
SECTOR_MENU_GROUPS[SectorType.OTOMOTIV] = {
    "Ana Sayfa": [40],
    "Servis Y\u00f6netimi": [41, 42, 62, 210, 30],
    "Servis Y\u00f6netim Ayar\u0131": [146, 145, 147, 140],
    "M\u00fc\u015fteri": [21, 25, 26, 90, 120],
    "Stok / Sipari\u015f": [60, 51, 66],
    "Teklif Y\u00f6netimi": [150, 313, 314],
    "Finans": [101, 105, 106, 115],
    "Sistem": [10, 130, 135, 160, 180, 261, 70],
}

SECTOR_MENU_GROUPS[SectorType.TEKNIK_SERVIS] = {
    "Ana Sayfa": [40],
    "Servis Y\u00f6netimi": [41, 42, 62, 61, 30, 65, 201],
    "Servis Y\u00f6netim Ayar\u0131": [146, 145, 147, 140],
    "M\u00fc\u015fteri": [21, 25, 26, 90, 120],
    "Stok / Sipari\u015f": [50, 51, 66, 250, 300],
    "Teklif Y\u00f6netimi": [150, 313, 314],
    "Projeler": [200, 202],
    "Finans": [101, 105, 106, 115],
    "Sistem": [10, 130, 135, 160, 180, 261, 70],
}


SECTOR_FEATURES: Dict[SectorType, Dict[str, bool]] = {
    SectorType.OTOMOTIV: {
        "vehicle_maintenance": True,
        "workshop_map": False,
        "field_service": False,
        "pc_builder": False,
        "project_management": False,
    },
    SectorType.TEKNIK_SERVIS: {
        "vehicle_maintenance": False,
        "workshop_map": True,
        "field_service": True,
        "pc_builder": True,
        "project_management": True,
    },
}


class SectorManager:
    def __init__(self, db=None):
        self.db = db
        self._current_sector: Optional[SectorType] = None

    def get_current_sector(self) -> Optional[SectorType]:
        if self._current_sector is None:
            sector_str = DEFAULT_SECTOR
            if self.db:
                sector_str = SystemConfig.get_current_sector(self.db)
            self._current_sector = SectorType(SystemConfig.normalize_sector(sector_str))
        return self._current_sector

    def set_sector(self, sector: SectorType):
        self._current_sector = sector
        if self.db:
            try:
                self.db.set_internal_setting("current_sector", sector.value)
            except Exception:
                pass

    def get_available_pages(self) -> Set[int]:
        sector = self.get_current_sector() or SectorType.TEKNIK_SERVIS
        return SECTOR_PAGES.get(sector, SECTOR_PAGES[SectorType.TEKNIK_SERVIS])

    def get_menu_groups(self) -> Dict[str, List[int]]:
        sector = self.get_current_sector() or SectorType.TEKNIK_SERVIS
        return SECTOR_MENU_GROUPS.get(sector, SECTOR_MENU_GROUPS[SectorType.TEKNIK_SERVIS])

    def is_page_available(self, page_id: int) -> bool:
        return page_id in self.get_available_pages()

    def has_feature(self, feature_name: str) -> bool:
        sector = self.get_current_sector() or SectorType.TEKNIK_SERVIS
        features = SECTOR_FEATURES.get(sector, {})
        return features.get(feature_name, False)

    @staticmethod
    def get_sector_list() -> List[Dict]:
        return [
            {
                "id": sector.value,
                "type": sector,
                "name": info["name"],
                "description": info["description"],
                "icon": info["icon"],
                "color": info["color"],
            }
            for sector, info in SECTOR_INFO.items()
        ]

    @staticmethod
    def get_sector_info(sector: SectorType) -> Dict:
        return SECTOR_INFO.get(sector, SECTOR_INFO[SectorType.TEKNIK_SERVIS])


_sector_manager: Optional[SectorManager] = None


def get_sector_manager(db=None) -> SectorManager:
    global _sector_manager
    if _sector_manager is None:
        _sector_manager = SectorManager(db)
    elif db is not None:
        _sector_manager.db = db
        _sector_manager._current_sector = None
    return _sector_manager
