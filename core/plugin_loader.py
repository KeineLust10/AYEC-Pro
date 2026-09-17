# -*- coding: utf-8 -*-
"""
PluginLoader - Sektor pluginlerini dinamik olarak yukler.
"""

import importlib
import pkgutil
import sys
from pathlib import Path
from typing import Dict, Optional, Type

from interfaces import BaseSector
from plugins.otomotiv import SectorPlugin as AutomotiveSectorPlugin
from plugins.teknik_servis import SectorPlugin as TechnicalServiceSectorPlugin

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

BUILTIN_PLUGINS = (
    TechnicalServiceSectorPlugin,
    AutomotiveSectorPlugin,
)


class PluginLoader:
    """
    Sektor pluginlerini kesfeder, yukler ve yonetir.
    Lazy loading kullanir; sadece aktif sektor bellekte tutulur.
    """

    _plugins: Dict[str, BaseSector] = {}
    _plugin_classes: Dict[str, Type[BaseSector]] = {}
    _current_sector_id: Optional[str] = None

    @classmethod
    def discover_plugins(cls) -> Dict[str, Type[BaseSector]]:
        if cls._plugin_classes:
            return cls._plugin_classes

        plugins_dir = project_root / "plugins"
        discovered = {}
        for plugin_class in BUILTIN_PLUGINS:
            plugin = plugin_class()
            discovered[plugin.sector_id] = plugin_class

        if not plugins_dir.exists():
            print(f"[PluginLoader] Uyari: Plugins dizini bulunamadi: {plugins_dir}")
            cls._plugin_classes = discovered
            return discovered

        for module_info in pkgutil.iter_modules([str(plugins_dir)]):
            module_name = module_info.name
            if module_name.startswith("_"):
                continue

            try:
                module_path = f"plugins.{module_name}"
                module = importlib.import_module(module_path)

                if hasattr(module, "SectorPlugin"):
                    plugin_class = module.SectorPlugin
                    if issubclass(plugin_class, BaseSector):
                        temp_instance = plugin_class()
                        sector_id = temp_instance.sector_id
                        discovered[sector_id] = plugin_class
                        print(f"[PluginLoader] Plugin kesfedildi: {sector_id} ({module_name})")
                    else:
                        print(
                            f"[PluginLoader] Uyari: {module_name}.SectorPlugin BaseSector'dan turemiyor"
                        )

            except ImportError as exc:
                print(f"[PluginLoader] Hata: {module_name} yuklenemedi: {exc}")
            except Exception as exc:
                print(f"[PluginLoader] Hata: {module_name} islenirken hata: {exc}")

        cls._plugin_classes = discovered
        return discovered

    @classmethod
    def get_available_sectors(cls) -> Dict[str, str]:
        discovered = cls.discover_plugins()
        return {
            sector_id: plugin_class().sector_name
            for sector_id, plugin_class in discovered.items()
        }

    @classmethod
    def activate_sector(cls, sector_id: str) -> BaseSector:
        if sector_id in cls._plugins:
            cls._current_sector_id = sector_id
            return cls._plugins[sector_id]

        discovered = cls.discover_plugins()
        if sector_id not in discovered:
            available = list(discovered.keys())
            raise ValueError(
                f"Sektor bulunamadi: '{sector_id}'. Mevcut sektorler: {available}"
            )

        plugin_class = discovered[sector_id]
        plugin_instance = plugin_class()
        cls._plugins[sector_id] = plugin_instance
        cls._current_sector_id = sector_id
        print(f"[PluginLoader] Sektor aktif edildi: {sector_id} ({plugin_instance.sector_name})")
        return plugin_instance

    @classmethod
    def get_current_sector(cls) -> Optional[BaseSector]:
        if cls._current_sector_id and cls._current_sector_id in cls._plugins:
            return cls._plugins[cls._current_sector_id]
        return None

    @classmethod
    def get_current_sector_id(cls) -> Optional[str]:
        return cls._current_sector_id

    @classmethod
    def clear_cache(cls):
        cls._plugins.clear()
        cls._plugin_classes.clear()
        cls._current_sector_id = None
        print("[PluginLoader] Onbellek temizlendi")

    @classmethod
    def reload_sector(cls, sector_id: str) -> BaseSector:
        if sector_id in cls._plugins:
            del cls._plugins[sector_id]

        module_path = f"plugins.{sector_id}"
        if module_path in sys.modules:
            importlib.reload(sys.modules[module_path])

        if sector_id in cls._plugin_classes:
            del cls._plugin_classes[sector_id]

        return cls.activate_sector(sector_id)
