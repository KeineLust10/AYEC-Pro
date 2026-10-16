# -*- coding: utf-8 -*-

import importlib
import inspect
import logging
import traceback
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from src.utils.page_config import PAGE_MAPPING, PAGE_NAMES
from src.utils.page_ids import PageIds
from src.utils.system_config import SystemConfig
from src.utils.sector_config import SECTOR_PAGES, SectorType
from src.utils.theme_colors import theme_qss
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.performance_monitor import perf_span, wrap_method_once

logger = logging.getLogger(__name__)

class MainWindowNavMixin:
    """Navigation, Page Loading, and Menu Management."""

    def _set_field_map_shell_mode(self, enabled):
        enabled = bool(enabled)
        nav_mode = getattr(self, "_active_nav_mode", "sol_menu")
        previous_mode = bool(getattr(self, "_field_map_shell_active", False))
        if enabled != previous_mode:
            self._set_field_map_reference_theme(enabled)
            self._field_map_shell_active = enabled
        if hasattr(self, "app_header"):
            self.app_header.setVisible(not enabled)
        if hasattr(self, "app_sidebar"):
            self.app_sidebar.setVisible(
                enabled or nav_mode in ("sol_menu", "her_ikisi")
            )
        if hasattr(self, "app_top_nav"):
            self.app_top_nav.setVisible(
                not enabled and nav_mode in ("ust_bar", "her_ikisi")
            )
        if hasattr(self, "shell_status_bar"):
            self.shell_status_bar.setVisible(not enabled)
        if hasattr(self, "assistant_fab"):
            self.assistant_fab.setVisible(
                not enabled and bool(getattr(self, "_assistant_fab_enabled", True))
            )

    def _set_field_map_reference_theme(self, enabled):
        from src.utils.theme_manager import ThemeManager
        try:
            sidebar = getattr(self, "app_sidebar", None)
            if sidebar is not None:
                ThemeManager.refresh_widget_tree(sidebar)
            pages = getattr(self, "pages", {})
            page = pages.get(int(PageIds.FIELD_MAP)) if pages else None
            if page is not None:
                ThemeManager.refresh_widget_tree(page)
        except Exception:
            logger.exception("Field map theme refresh failed")

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
        diagnostics = getattr(self, "_menu_window_diagnostics", None)
        if diagnostics is not None:
            diagnostics.record_menu_click(
                "Side menu",
                self.get_page_name_by_index(index),
                index,
            )
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
        previous_index = getattr(self, "_current_page_index", None)
        active_sidebar = getattr(getattr(self, "app_sidebar", None), "side_menu", None)
        previous_sidebar_page = getattr(active_sidebar, "_last_active_page_id", None)
        if active_sidebar is not None and int(index) == 130 and previous_index != 130:
            self._settings_sidebar_auto_previous_icon_only = bool(
                getattr(active_sidebar, "_icon_only", False)
            )
            self._settings_sidebar_user_override = False
            active_sidebar.set_menu_label_mode("icons", persist=False)
        elif active_sidebar is not None and previous_index == 130 and int(index) != 130:
            if not getattr(self, "_settings_sidebar_user_override", False):
                active_sidebar.set_menu_label_mode(
                    "icons"
                    if getattr(self, "_settings_sidebar_auto_previous_icon_only", False)
                    else "labels",
                    persist=False,
                )
            self.__dict__.pop("_settings_sidebar_auto_previous_icon_only", None)
            self.__dict__.pop("_settings_sidebar_user_override", None)
        if (
            previous_index is not None
            and int(previous_index) != int(index)
            and not getattr(self, "_navigation_back_active", False)
        ):
            history = getattr(self, "_navigation_history", [])
            history.append(int(previous_index))
            self._navigation_history = history[-30:]
        self._current_page_index = index
        if hasattr(self, "app_header") and hasattr(
            self.app_header, "set_customer_reference_mode"
        ):
            self.app_header.set_customer_reference_mode(
                int(index) == int(PageIds.CUSTOMER_LIST)
            )
            if int(index) == int(PageIds.CUSTOMER_LIST):
                self.app_header._sync_customer_reference_header(index)
        if hasattr(self, "set_customer_reference_shell_mode"):
            self.set_customer_reference_shell_mode(
                int(index) == int(PageIds.CUSTOMER_LIST)
            )
        self._set_field_map_shell_mode(int(index) == int(PageIds.FIELD_MAP))
        if active_sidebar is not None:
            if previous_sidebar_page != int(index) and (
                previous_sidebar_page in {146, 147} or int(index) in {146, 147}
            ):
                active_sidebar.on_page_changed_internal(int(index))
                active_sidebar.refresh_menu()
        if hasattr(self, "assistant_fab"):
            self.assistant_fab.setVisible(
                bool(getattr(self, "_assistant_fab_enabled", True))
                and int(index) not in {21, 146, 147, int(PageIds.FIELD_MAP)}
            )
            self.reposition_fab()
        self._sync_back_button()
        if hasattr(self, "app_top_nav"):
            self.app_top_nav.sync_active(index)
            self.app_top_nav.setVisible(
                int(index) != int(PageIds.NEW_SERVICE)
                and int(index) != int(PageIds.FIELD_MAP)
                and getattr(self, "_active_nav_mode", "sol_menu") in ("ust_bar", "her_ikisi")
            )
        requested_settings_tab = None
        if hasattr(self, "app_sidebar"):
            side_menu = getattr(self.app_sidebar, "side_menu", None)
            if (
                side_menu is not None
                and hasattr(side_menu, "on_page_changed_internal")
                and getattr(side_menu, "_last_active_page_id", None) != int(index)
            ):
                requested_settings_tab = getattr(side_menu, "_requested_settings_tab", None)
                if requested_settings_tab is not None:
                    side_menu._requested_settings_tab = None
                side_menu.on_page_changed_internal(index)
        
        with perf_span(f"navigation.page.{index}"):
            page = self.get_page(index)
            customer_page = (
                page if int(index) == int(PageIds.CUSTOMER_LIST)
                else getattr(self, "pages", {}).get(PageIds.CUSTOMER_LIST)
            )
            if customer_page is not None and hasattr(
                customer_page, "set_reference_shell_mode"
            ):
                customer_page.set_reference_shell_mode(
                    int(index) == int(PageIds.CUSTOMER_LIST)
                )
            if page:
                if (
                    requested_settings_tab is not None
                    and int(index) == 130
                    and hasattr(page, "change_page")
                ):
                    page.change_page(int(requested_settings_tab))
                if int(index) == int(PageIds.DASHBOARD) and hasattr(page, "show_shortcut_screen"):
                    page.show_shortcut_screen()
                # Avoid duplicate full dashboard queries during rapid navigation.
                if page.__class__.__name__ == "DashboardPage" and hasattr(page, "refresh_data"):
                    refresh = getattr(page, "refresh_data_if_stale", page.refresh_data)
                    QTimer.singleShot(0, refresh)
                self._switch_content_with_fade(page)
                if hasattr(self, "app_header") and hasattr(self.app_header, "breadcrumb"):
                    if int(index) == 140:
                        self.app_header.breadcrumb.update_path([
                            ("Servis Operasyon", 40),
                            ("Hizmet ve \u00dccret Y\u00f6netimi", None),
                        ])
                    elif int(index) == 146:
                        self.app_header.breadcrumb.update_path([
                            ("Servis Y\u00f6netimi", 140),
                            ("Servis Y\u00f6netim Ayar\u0131", 145),
                            ("\u00dcr\u00fcn Grubu Y\u00f6netimi", None),
                        ])
                    elif int(index) == 145:
                        self.app_header.breadcrumb.update_path([
                            ("Servis Y\u00f6netim Ayar\u0131", 146),
                            ("Cihaz Bilgisi & Markalar", None),
                        ])
                    elif int(index) == 115:
                        self.app_header.breadcrumb.update_path([
                            ("Finans", 101),
                            ("E-Fatura Olu\u015ftur Studio", None),
                        ])
                    elif int(index) == 106:
                        self.app_header.breadcrumb.update_path([
                            ("Finans Y\u00f6netimi", 101),
                            ("\u00c7ek & Senet Portf\u00f6y Takibi", None),
                        ])
                    elif int(index) == 21:
                        self.app_header.breadcrumb.update_path([
                            ("M\u00fc\u015fteri Hub", None),
                            ("M\u00fc\u015fteri Listesi", None),
                        ])
                    else:
                        self.app_header.breadcrumb.update_path([(self.get_page_name_by_index(index), index)])
                    self.app_header._apply_service_header_presentation()
                    if int(index) in {100, 101, 105, 106, 115}:
                        self.app_header.raise_()
                        QTimer.singleShot(250, self.app_header.raise_)
                    if hasattr(self, "_set_service_list_shell"):
                        self._set_service_list_shell(int(index) == 42)
                return
            logger.error(f"Page load failure: {index}")

    def navigate_back(self):
        history = getattr(self, "_navigation_history", [])
        current = getattr(self, "_current_page_index", None)
        while history and current is not None and int(history[-1]) == int(current):
            history.pop()
        if not history:
            self._sync_back_button()
            return
        target = int(history.pop())
        self._navigation_history = history
        self._navigation_back_active = True
        try:
            self.on_menu_click(target)
        finally:
            self._navigation_back_active = False
            self._sync_back_button()

    def _sync_back_button(self):
        header = getattr(self, "app_header", None)
        if header is not None and hasattr(header, "set_back_enabled"):
            header.set_back_enabled(bool(getattr(self, "_navigation_history", [])))

    def get_page(self, index):
        if index in self.pages:
            page = self.pages[index]
            if (
                page is not None
                and getattr(page, "_ayec_theme_revision", None)
                != getattr(self, "_theme_revision", 0)
                and hasattr(self, "_refresh_page_theme")
            ):
                try:
                    self._refresh_page_theme(page)
                except Exception as exc:
                    logger.warning("Cached page theme refresh failed for %s: %s", index, exc)
            return page
        
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
        # Page themes are applied once when a page is created. Reapplying them
        # on every navigation walks and repolishes the full widget tree, which
        # blocks the UI thread on large pages.
        self.content_area.setCurrentWidget(target_widget)

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
            if hasattr(page, "refresh_data"):
                page.refresh_data()
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
        field_map_mode = (
            int(getattr(self, "_current_page_index", -1)) == int(PageIds.FIELD_MAP)
        )
        self._set_field_map_shell_mode(field_map_mode)
        sidebar_visible = field_map_mode or nav_mode in ("sol_menu", "her_ikisi")
        topnav_visible = not field_map_mode and nav_mode in ("ust_bar", "her_ikisi")
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
