# -*- coding: utf-8 -*-

import importlib
import inspect
import logging
import traceback
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from src.utils.page_config import PAGE_MAPPING, PAGE_NAMES
from src.utils.system_config import SystemConfig
from src.utils.sector_config import SECTOR_PAGES, SectorType
from src.utils.theme_colors import theme_qss
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.performance_monitor import perf_span, wrap_method_once

logger = logging.getLogger(__name__)

class MainWindowNavMixin:
    """Navigation, Page Loading, and Menu Management."""

    def _active_sector_id(self):
        try:
            manager = getattr(self, "sector_manager", None)
            plugin = manager.get_current_plugin() if manager else None
            if plugin:
                return SystemConfig.normalize_sector(plugin.sector_id)
            return SystemConfig.get_current_sector(self.db)
        except Exception:
            return "teknik_servis"

    def _is_page_allowed_for_active_sector(self, index):
        try:
            sector = SectorType(self._active_sector_id())
        except Exception:
            sector = SectorType.TEKNIK_SERVIS
        allowed_pages = SECTOR_PAGES.get(
            sector,
            SECTOR_PAGES[SectorType.TEKNIK_SERVIS],
        )
        return int(index) in allowed_pages

    def on_menu_click(self, index):
        if index == 999: index = 50
        if index == 107: index = 105
        if index == 62 or (
            index == 60 and self._active_sector_id() != "otomotiv"
        ):
            if hasattr(self, "open_technician_panel"):
                self.open_technician_panel()
                return
        if not self._is_page_allowed_for_active_sector(index):
            logger.warning(
                "Blocked page %s for sector %s",
                index,
                self._active_sector_id(),
            )
            if hasattr(self, "show_notification"):
                self.show_notification(
                    "Bu sayfa aktif sekt\u00f6rde kullan\u0131lamaz.",
                    "warning",
                )
            return
        self._current_page_index = index
        if hasattr(self, "app_top_nav"): self.app_top_nav.sync_active(index)
        
        with perf_span(f"navigation.page.{index}"):
            page = self.get_page(index)
            if page:
                self._switch_content_with_fade(page)
                if hasattr(self, "app_header") and hasattr(self.app_header, "breadcrumb"):
                    self.app_header.breadcrumb.update_path([(self.get_page_name_by_index(index), index)])
                return
            logger.error(f"Page load failure: {index}")

    def get_page(self, index):
        if index in self.pages:
            return self.pages[index]
        
        if index not in self.page_mapping:
            return None
        module_path, class_name, attr, args = self.page_mapping[index]
        cls = self._load_class(module_path, class_name)
        if not cls:
            return None
            
        try:
            page_args = self._resolve_page_args(cls, args)
            with perf_span(f"page_create.{index}"):
                page = cls(*page_args)
            self.pages[index] = page
            setattr(self, attr, page)
            self.content_area.addWidget(page)
            if hasattr(self, "_refresh_page_theme"): self._refresh_page_theme(page)
            self._instrument_page(page, index)
            if hasattr(page, 'refresh_data') and class_name in ["AccountingPage", "DashboardPage"]:
                self.stock_updated.connect(page.refresh_data)
            return page
        except Exception as e:
            logger.error(f"Error initializing page {class_name}: {e}\n{traceback.format_exc()}")
            return None

    def _load_class(self, module_path, class_name):
        try:
            mod = importlib.import_module(module_path)
            return getattr(mod, class_name)
        except Exception as e:
            logger.error(f"Module load error [{module_path}]: {e}")
            return None

    def _resolve_page_args(self, cls, explicit_args):
        if explicit_args: return explicit_args
        try:
            sig = inspect.signature(cls.__init__)
            params = [p for n, p in sig.parameters.items() if n != "self" and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        except Exception: return (self.db, self)
        
        if not params: return ()
        res = []
        for p in params:
            if p.name == "db": res.append(self.db)
            elif p.name in ("parent", "main_window", "window"): res.append(self)
            elif p.name == "sector_manager": res.append(getattr(self, "sector_manager", None))
            elif p.default is not inspect.Parameter.empty: break
            else: break
        return tuple(res)

    def _switch_content_with_fade(self, target_widget):
        if not target_widget or self.content_area.currentWidget() == target_widget: return
        
        # Read disable_tab_animations setting from database
        disable_anim = False
        try:
            if self.db and hasattr(self.db, "get_setting"):
                disable_anim = (self.db.get_setting("disable_tab_animations", "1") == "1")
        except Exception:
            pass
            
        if disable_anim:
            # Instant transition (0ms)
            if target_widget.graphicsEffect():
                try:
                    target_widget.setGraphicsEffect(None)
                except Exception:
                    pass
            self.content_area.setCurrentWidget(target_widget)
            QTimer.singleShot(0, lambda page=target_widget: self._apply_active_page_appearance(page))
            return

        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
        
        # Clear any leftover graphics effect
        if target_widget.graphicsEffect():
            try:
                target_widget.setGraphicsEffect(None)
            except Exception:
                pass
                
        effect = QGraphicsOpacityEffect(target_widget)
        target_widget.setGraphicsEffect(effect)
        
        self.content_area.setCurrentWidget(target_widget)
        QTimer.singleShot(0, lambda page=target_widget: self._apply_active_page_appearance(page))
        
        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(40)  # Ultra-fast (40ms) transition
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: target_widget.setGraphicsEffect(None))
        
        self._page_transition_anim = anim
        anim.start()

    def _apply_active_page_appearance(self, page):
        """Apply the active visual mode after a page finishes its show hooks."""
        if page is None:
            return
        try:
            mode = getattr(self, "_appearance_mode", AppearanceModeManager.current(self.db))
            AppearanceModeManager.apply_to_widget_tree(page, mode)
        except Exception as exc:
            logger.debug("Active page appearance refresh skipped: %s", exc)


    def toggle_menu(self):
        if hasattr(self, "app_sidebar"): self.app_sidebar.toggle_menu()

    def switch_page(self, index):
        """Alias for on_menu_click - used by page modules to navigate programmatically."""
        self.on_menu_click(index)

    def open_service_list(self, category="all"):
        self.on_menu_click(PageIds.SERVICE_LIST)
        page = self.pages.get(PageIds.SERVICE_LIST)
        if page is not None and hasattr(page, "show_service_list"):
            page.show_service_list(category)

    def refresh_side_menu(self):
        try:
            if hasattr(self, "app_sidebar") and hasattr(self.app_sidebar, "side_menu"):
                self.app_sidebar.side_menu.refresh_menu()
                self.app_sidebar.side_menu.on_page_changed_internal(self._current_page_index)
            if hasattr(self, "app_top_nav"): self.app_top_nav.refresh_visibility()
        except Exception as e:
            logger.warning(f"Refresh side menu failed: {e}")
        finally:
            if hasattr(self, "_reapply_nav_mode"): self._reapply_nav_mode()
            self.apply_appearance_mode(force_tree=True)

    def apply_nav_mode(self, nav_mode=None):
        if nav_mode is None:
            try: nav_mode = self.db.get_setting("nav_mode", "sol_menu")
            except Exception as e:
                logger.warning(f"Navigation mode lookup failed: {e}")
                nav_mode = "sol_menu"
        self._active_nav_mode = nav_mode
        sidebar_visible = nav_mode in ("sol_menu", "her_ikisi")
        topnav_visible  = nav_mode in ("ust_bar",  "her_ikisi")
        if hasattr(self, "app_sidebar"):
            self.app_sidebar.setVisible(sidebar_visible)
            # Adjust sidebar widths based on visibility
        if hasattr(self, "app_top_nav"): self.app_top_nav.setVisible(topnav_visible)

    def _reapply_nav_mode(self):
        self.apply_nav_mode(getattr(self, "_active_nav_mode", None))

    def get_page_name_by_index(self, index):
        sector = self._active_sector_id()
        if sector == "otomotiv":
            ovr = {
                41: "Servis Panosu",
                60: "Ara\u00e7 Par\u00e7a Sto\u011fu",
                62: "Teknisyen Paneli",
                210: "Ara\u00e7 Bak\u0131m Takibi",
            }
            if index in ovr: return ovr[index]
        return PAGE_NAMES.get(index, "Sayfa")

    def _load_initial_page(self):
        if getattr(self, "_initial_page_loaded", False): return
        try:
            self.on_menu_click(40)
            side_menu = getattr(
                getattr(self, "app_sidebar", None),
                "side_menu",
                None,
            )
            if side_menu and hasattr(side_menu, "on_page_changed_internal"):
                side_menu.on_page_changed_internal(40)
            self._initial_page_loaded = True
        except Exception as e:
            logger.error(f"Initial page load failed: {e}")

    def _install_startup_placeholder(self):
        p = QWidget(); p.setObjectName("StartupPlaceholder"); p.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        l = QVBoxLayout(p); l.setContentsMargins(48, 48, 48, 48); l.addStretch()
        t = QLabel("AYEC Pro yükleniyor..."); t.setObjectName("StartupPlaceholderTitle"); t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(theme_qss("QLabel#StartupPlaceholderTitle { color: @text; font-size: 28px; font-weight: 700; }"))
        l.addWidget(t); l.addStretch()
        self.content_area.addWidget(p); self.content_area.setCurrentWidget(p)

    def _instrument_page(self, page, index):
        if not page or getattr(page, "_perf_instrumented", False): return
        pname = self.get_page_name_by_index(index)
        for m in ["refresh_data", "request_reload", "populate_table", "load_data"]:
            if hasattr(page, m): wrap_method_once(page, m, f"page_{m}.{index}.{pname}")
        try: setattr(page, "_perf_instrumented", True)
        except Exception as e:
            logger.debug(f"Page instrumentation flag failed: {e}")
