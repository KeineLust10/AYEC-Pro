# -*- coding: utf-8 -*-

class SectorScopedManager:
    """Read-only sector manager facade used by sector-specific public dialogs."""

    def __init__(self, sector_id, db=None, wrapped=None):
        self.sector_id = sector_id
        self._db = db
        self._wrapped = wrapped
        self._plugin = self._load_plugin(sector_id)
        if self._plugin and db:
            try:
                self._plugin.initialize_database(db)
            except Exception:
                pass

    def _load_plugin(self, sector_id):
        try:
            from core.plugin_loader import PluginLoader

            discovered = PluginLoader.discover_plugins()
            plugin_cls = discovered.get(sector_id)
            return plugin_cls() if plugin_cls else None
        except Exception:
            return None

    def __getattr__(self, name):
        if self._wrapped is not None:
            return getattr(self._wrapped, name)
        raise AttributeError(name)

    def get_current_plugin(self):
        return self._plugin

    def get_current_sector(self):
        return self.sector_id

    def get_customer_fields(self):
        return self._plugin.get_customer_form_fields() if self._plugin else []

    def get_service_fields(self):
        return self._plugin.get_service_form_fields() if self._plugin else []

    def get_stock_columns(self):
        return self._plugin.get_stock_columns() if self._plugin else []

    def get_quick_categories(self):
        return self._plugin.get_quick_categories() if self._plugin else {}

    def get_form_descriptors(self, entity):
        return self._plugin.get_form_descriptors(entity) if self._plugin else []

    def get_checklist_templates(self):
        return self._plugin.get_checklist_templates() if self._plugin else {}

    def get_maintenance_card_sections(self):
        return self._plugin.get_maintenance_card_sections() if self._plugin else []

    def map_core_to_extension_payload(self, entity, form_data):
        if self._plugin:
            return self._plugin.map_core_to_extension_payload(entity, form_data)
        if self._wrapped and hasattr(self._wrapped, "map_core_to_extension_payload"):
            return self._wrapped.map_core_to_extension_payload(entity, form_data)
        return {}

    def hydrate_form_defaults(self, entity, core_row, extension_row):
        if self._plugin:
            return self._plugin.hydrate_form_defaults(entity, core_row, extension_row)
        merged = {}
        if core_row:
            merged.update(dict(core_row))
        if extension_row:
            merged.update(dict(extension_row))
        return merged

    def is_feature_available(self, feature_name):
        return self._plugin.is_feature_available(feature_name) if self._plugin else False


def scoped_sector_manager(sector_id, db=None, sector_manager=None):
    return SectorScopedManager(sector_id, db=db, wrapped=sector_manager)
