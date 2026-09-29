# -*- coding: utf-8 -*-

from PyQt6.QtCore import QTimer
from src.utils.system_config import SystemConfig
from src.utils.logger import logger

class DashboardBaseMixin:
    def _resolve_technician_panel_class(self):
        cache_name = "_technician_panel_class_cache"
        cache = getattr(self, cache_name, {})
        key = "automotive" if self._is_automotive() else "technical"
        if key in cache:
            return cache[key]
        if key == "automotive":
            from src.ui.dialogs.automotive_technician_panel import (
                AutomotiveTechnicianPanel as panel_cls,
            )
        else:
            from src.ui.dialogs.technical_service_technician_panel import (
                TechnicalServiceTechnicianPanel as panel_cls,
            )
        cache[key] = panel_cls
        setattr(self, cache_name, cache)
        return panel_cls

    def _update_recent_empty_state(self):
        if hasattr(self, "recent_empty_state") and hasattr(self, "table"):
            has_rows = self.table.rowCount() > 0
            self.table.setVisible(has_rows)
            self.recent_empty_state.setVisible(not has_rows)

    def _is_automotive(self):
        """🆕 Otomotiv sektöründe olup olmadığını kontrol et (Plugin aware)"""
        try:
            if hasattr(self, "sector_manager") and self.sector_manager:
                if hasattr(self.sector_manager, "get_current_plugin"):
                    return self.sector_manager.get_current_plugin().sector_id == "otomotiv"
                if hasattr(self.sector_manager, "get_current_sector"):
                    sector = self.sector_manager.get_current_sector()
                    return getattr(sector, "value", sector) == "otomotiv"
            return SystemConfig.get_current_sector(self.db) == "otomotiv"
        except Exception:
            return False

    def refresh_data(self):
        from src.utils.ayec_accelerator import fast_render_context
        try:
            if hasattr(self, "sync_dashboard_sector_texts"):
                self.sync_dashboard_sector_texts()
            if hasattr(self, "lbl_table_title"):
                if hasattr(self, "_table_title"):
                    category = getattr(self, "current_filter_category", "all")
                    self.lbl_table_title.setText(self._table_title(category))
                else:
                    self.lbl_table_title.setText("Servis Listesi")

            if hasattr(self, "apply_theme_styles"):
                self.apply_theme_styles()
            if hasattr(self, "update_dashboard_status_tiles"):
                self.update_dashboard_status_tiles()
            if hasattr(self, "update_filter_buttons_style"):
                self.update_filter_buttons_style()

            # Refresh breakdown panel counts
            if hasattr(self, "_breakdown_labels") and hasattr(self, "_status_tiles"):
                for key, lbl in self._breakdown_labels.items():
                    tile = self._status_tiles.get(key)
                    if tile and tile.get("count"):
                        count_text = tile["count"].text()
                        try:
                            count_val = int(count_text.replace("ADET", "").strip())
                            lbl.setText(str(count_val))
                        except (ValueError, AttributeError):
                            lbl.setText("0")

            # Refresh recent activity panel
            if hasattr(self, "_refresh_recent_activity"):
                self._refresh_recent_activity()
            if hasattr(self, "_refresh_dashboard_chart_widgets"):
                self._refresh_dashboard_chart_widgets()
            
            # Utilize fast_render_context if table exists
            table_widget = getattr(self, "table", None)
            if table_widget:
                with fast_render_context(table_widget):
                    self.populate_table()
            else:
                self.populate_table()

            if hasattr(self, "_apply_dashboard_quick_filters"):
                self._apply_dashboard_quick_filters()

            if hasattr(self, "_refresh_today_appointments"):
                self._refresh_today_appointments()
            
        except Exception as e:
            logger.error(f"Dashboard refresh error: {e}")
            if "has been deleted" in str(e).lower():
                return
            if hasattr(self, "notify"):
                self.notify(
                    "Genel bak\u0131\u015f ekran\u0131 yenilenemedi. Sayfay\u0131 yeniden a\u00e7may\u0131 deneyin.",
                    "error",
                )
