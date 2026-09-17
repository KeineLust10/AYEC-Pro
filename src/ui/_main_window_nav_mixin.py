
# -*- coding: utf-8 -*-
import logging
from PyQt6.QtWidgets import QApplication
from src.utils.logger import logger
from src.utils.system_config import SystemConfig


class MainWindowNavMixin:
    """Navigation and display profile functionality for MainWindow."""

    def toggle_menu(self):
        """Toggle sidebar expansion/collapse."""
        if hasattr(self, "app_sidebar"):
            self.app_sidebar.toggle_menu()

    def refresh_side_menu(self):
        """Refresh sidebar menu items and appearance."""
        try:
            if hasattr(self, "app_sidebar") and hasattr(self.app_sidebar, "side_menu"):
                self.app_sidebar.side_menu.refresh_menu()
                self.app_sidebar.side_menu.on_page_changed_internal(self._current_page_index)
            if hasattr(self, "app_top_nav") and hasattr(self.app_top_nav, "refresh_visibility"):
                self.app_top_nav.refresh_visibility()
        except Exception as e:
            logger.warning("refresh_side_menu error: %s", e)
        finally:
            self._reapply_nav_mode()
            self.apply_appearance_mode(force_tree=False)

    def apply_nav_mode(self, nav_mode: str | None = None):
        """Apply navigation mode (sol_menu, ust_bar, her_ikisi)."""
        if nav_mode is None:
            try:
                nav_mode = self.db.get_setting("nav_mode", "sol_menu")
            except Exception:
                nav_mode = "sol_menu"

        self._active_nav_mode = nav_mode

        sidebar_visible = nav_mode in ("sol_menu", "her_ikisi")
        topnav_visible = nav_mode in ("ust_bar", "her_ikisi")

        if hasattr(self, "app_sidebar"):
            if hasattr(self.app_sidebar, "set_nav_hidden"):
                self.app_sidebar.set_nav_hidden(not sidebar_visible)
            else:
                self.app_sidebar.setVisible(sidebar_visible)
            if not sidebar_visible:
                self.app_sidebar.setMinimumWidth(0)
                self.app_sidebar.setMaximumWidth(0)
            else:
                if nav_mode == "her_ikisi":
                    target_width = getattr(getattr(self.app_sidebar, "side_menu", None), "EXPANDED_WIDTH", 300)
                    if hasattr(self.app_sidebar, "side_menu") and hasattr(self.app_sidebar.side_menu, "set_collapsed"):
                        self.app_sidebar.side_menu.set_collapsed(False, animate=False)
                    if hasattr(self.app_sidebar, "_sync_width"):
                        self.app_sidebar._sync_width(target_width)
                    else:
                        self.app_sidebar.setMinimumWidth(target_width)
                        self.app_sidebar.setMaximumWidth(target_width)
                else:
                    self.app_sidebar.setMaximumWidth(320)
            if sidebar_visible and hasattr(self.app_sidebar, "side_menu") and hasattr(self.app_sidebar.side_menu, "set_collapsed"):
                is_collapsed = False if nav_mode == "her_ikisi" else getattr(self.app_sidebar, "_is_collapsed", False)
                self.app_sidebar.side_menu.set_collapsed(is_collapsed, animate=False)
        if hasattr(self, "app_top_nav"):
            self.app_top_nav.setVisible(topnav_visible)

        logger.debug("apply_nav_mode: %s (sidebar=%s top_nav=%s)", nav_mode, sidebar_visible, topnav_visible)

    def apply_display_profile(self):
        """Apply display profile for laptop/large screens."""
        try:
            profile = self.db.get_setting("display_profile", "auto")
        except Exception:
            profile = "auto"

        try:
            screen = QApplication.primaryScreen()
            width = screen.availableGeometry().width() if screen else self.width()
        except Exception:
            width = self.width()

        compact = profile == "laptop" or (profile == "auto" and width <= 1500)
        if compact:
            self.setMinimumSize(1080, 700)
        else:
            self.setMinimumSize(1280, 800)

        if hasattr(self, "app_sidebar") and hasattr(self.app_sidebar, "side_menu"):
            try:
                mode = getattr(self, "_active_nav_mode", None) or self.db.get_setting("nav_mode", "sol_menu")
            except Exception:
                mode = "sol_menu"

            if mode == "sol_menu":
                pinned = bool(getattr(self.app_sidebar.side_menu, "_is_pinned", True))
                self.app_sidebar.side_menu.set_collapsed(not pinned, animate=False)
                if hasattr(self.app_sidebar, "_sync_width"):
                    target = (
                        getattr(self.app_sidebar.side_menu, "EXPANDED_WIDTH", 300)
                        if pinned
                        else getattr(self.app_sidebar.side_menu, "COLLAPSED_WIDTH", 92)
                    )
                    self.app_sidebar._sync_width(target)

    def _reapply_nav_mode(self):
        """Reapply active navigation mode (called after refresh_side_menu)."""
        mode = getattr(self, "_active_nav_mode", None)
        if mode is None:
            try:
                mode = self.db.get_setting("nav_mode", "sol_menu")
            except Exception:
                mode = "sol_menu"
        sidebar_visible = mode in ("sol_menu", "her_ikisi")
        topnav_visible = mode in ("ust_bar", "her_ikisi")
        if hasattr(self, "app_sidebar"):
            if hasattr(self.app_sidebar, "set_nav_hidden"):
                self.app_sidebar.set_nav_hidden(not sidebar_visible)
            else:
                self.app_sidebar.setVisible(sidebar_visible)
            if not sidebar_visible:
                self.app_sidebar.setMinimumWidth(0)
                self.app_sidebar.setMaximumWidth(0)
            else:
                if mode == "her_ikisi":
                    target_width = getattr(getattr(self.app_sidebar, "side_menu", None), "EXPANDED_WIDTH", 300)
                    if hasattr(self.app_sidebar, "side_menu") and hasattr(self.app_sidebar.side_menu, "set_collapsed"):
                        self.app_sidebar.side_menu.set_collapsed(False, animate=False)
                    if hasattr(self.app_sidebar, "_sync_width"):
                        self.app_sidebar._sync_width(target_width)
                    else:
                        self.app_sidebar.setMinimumWidth(target_width)
                        self.app_sidebar.setMaximumWidth(target_width)
                else:
                    self.app_sidebar.setMaximumWidth(320)
            if sidebar_visible and hasattr(self.app_sidebar, "side_menu") and hasattr(self.app_sidebar.side_menu, "set_collapsed"):
                is_collapsed = False if mode == "her_ikisi" else getattr(self.app_sidebar, "_is_collapsed", False)
                self.app_sidebar.side_menu.set_collapsed(is_collapsed, animate=False)
        if hasattr(self, "app_top_nav"):
            self.app_top_nav.setVisible(topnav_visible)

    def get_page_name_by_index(self, index):
        """Get page name by index, considering sector-specific overrides."""
        sector = "teknik_servis"
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                sector = self.sector_manager.get_current_plugin().sector_id
            else:
                sector = self.db.get_internal_setting("current_sector", "teknik_servis")
        except Exception:
            pass
        if sector == "otomotiv":
            overrides = {
                41: "Servis Panosu",
                60: "Teknisyen Paneli",
                61: "Saha Servis Haritasi",
                145: "Marka & Arac Bilgileri",
                201: "Servis / Bakim Raporlari",
                210: "Arac Bakim Takibi",
            }
            if index in overrides:
                return overrides[index]
        from src.utils.page_config import PAGE_NAMES
        return PAGE_NAMES.get(index, "Sayfa")

    def apply_sector_change(self, sector_id, target_index=40):
        """Change active sector and reload UI components."""
        sector_id = SystemConfig.normalize_sector(sector_id)
        try:
            self.db.set_internal_setting("current_sector", sector_id)
        except Exception as e:
            logger.warning("current_sector persistence warning: %s", e)

        try:
            if self.sector_manager:
                if hasattr(self.sector_manager, "load_sector"):
                    self.sector_manager.load_sector(sector_id)
                elif hasattr(self.sector_manager, "set_sector"):
                    from src.utils.sector_config import SectorType
                    self.sector_manager.set_sector(SectorType(SystemConfig.normalize_sector(sector_id)))
                else:
                    self.sector_manager._current_sector = None
        except Exception as e:
            logger.error("sector_manager reload failed: %s", e)

        try:
            if hasattr(self, "app_sidebar") and self.app_sidebar:
                self.app_sidebar.db = self.db
                self.app_sidebar.sector_manager = self.sector_manager
                if hasattr(self.app_sidebar, "side_menu") and self.app_sidebar.side_menu:
                    self.app_sidebar.side_menu.db = self.db
                    self.app_sidebar.side_menu.sector_manager = self.sector_manager
        except Exception as e:
            logger.warning("sidebar sector sync warning: %s", e)

        if sector_id == "otomotiv":
            visible_targets = {41, 60, 21, 30, 101, 170, 210}
            if target_index not in visible_targets:
                target_index = 41
        else:
            hidden_targets = {210}
            if target_index in hidden_targets:
                target_index = 40

        self._reload_all_pages()
        self.refresh_side_menu()
        self._refresh_active_page(target_index)
