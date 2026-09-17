
# -*- coding: utf-8 -*-
import logging
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QApplication, QWidget

from src.utils.theme_manager import ThemeManager
from src.utils.theme_colors import theme_qss
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.logger import logger
from src.utils.performance_monitor import perf_span


class MainWindowThemeMixin:
    """Theme and appearance-related functionality for MainWindow."""

    def _apply_shell_theme_styles(self):
        """Apply theme styles to central widget, container, and content area."""
        try:
            self.central_widget.setStyleSheet(theme_qss("QWidget#CentralWidget { background-color: @window; }"))
        except Exception:
            pass
        try:
            self.right_container.setStyleSheet(theme_qss("QWidget#RightContainer { background-color: @window; }"))
        except Exception:
            pass
        try:
            self.content_area.setStyleSheet(theme_qss("""
                QStackedWidget#ContentArea {
                    background-color: @window;
                    border: none;
                }
                QStackedWidget#ContentArea > QWidget {
                    background-color: @window;
                    color: @text;
                }
            """))
        except Exception:
            pass
        try:
            if hasattr(self, "_startup_placeholder") and self._startup_placeholder:
                self._startup_placeholder.setStyleSheet(theme_qss("QWidget#StartupPlaceholder { background-color: @window; }"))
        except Exception:
            pass

    def _apply_theme_early(self):
        """Set current theme BEFORE widget creation for correct theme_qss() calls."""
        app = QApplication.instance()
        if not app:
            return
        try:
            ThemeManager.load_custom_colors(self.db)
            ThemeManager.apply_interface_scale(app, refresh=False)
        except Exception as e:
            logger.warning("Custom theme colors could not be loaded (early): %s", e)
        try:
            theme_name = self.db.get_setting("color_theme_full", "AYEC")
        except Exception as e:
            logger.warning("Theme setting could not be read (early): %s", e)
            theme_name = "AYEC"
        normalized = ThemeManager.normalize_theme_name(theme_name)
        self._current_theme_name = normalized
        ThemeManager._current_theme = normalized
        try:
            app.setPalette(ThemeManager._build_palette(normalized))
            app.setStyleSheet(ThemeManager.get_stylesheet(normalized))
            AppearanceModeManager.apply(app, self.db, self, mode=AppearanceModeManager.current(self.db))
        except Exception as e:
            logger.warning("Early theme apply failed: %s", e)

    def apply_theme_on_startup(self):
        """Apply saved theme on application startup."""
        app = QApplication.instance()
        if not app:
            return
        try:
            ThemeManager.load_custom_colors(self.db)
            ThemeManager.apply_interface_scale(app, refresh=False)
        except Exception as e:
            logger.warning("Custom theme colors could not be loaded: %s", e)
        try:
            theme_name = self.db.get_setting("color_theme_full", "AYEC")
        except Exception as e:
            logger.warning("Theme setting could not be read: %s", e)
            theme_name = "AYEC"
        normalized = ThemeManager.normalize_theme_name(theme_name)
        self._current_theme_name = normalized
        ThemeManager.apply_theme(app, normalized, window=self, animate=False)
        self.apply_appearance_mode(force_tree=True)
        self._apply_shell_theme_styles()

        if hasattr(self.app_header, "apply_theme_styles"):
            self.app_header.apply_theme_styles()
        if hasattr(self, "app_top_nav"):
            self.app_top_nav.apply_theme_styles()

        if hasattr(self.app_sidebar, "side_menu") and hasattr(self.app_sidebar.side_menu, "refresh_theme"):
            try:
                self.app_sidebar.side_menu.refresh_theme()
            except Exception as e:
                logger.debug("Sidebar theme refresh skipped: %s", e)
        self.sync_theme_toggle_button()

    def apply_theme(self, theme_name):
        """Apply a new theme to the entire application."""
        app = QApplication.instance()
        if not app or self._theme_applying:
            return

        self._theme_applying = True
        try:
            normalized = ThemeManager.normalize_theme_name(theme_name)
            with perf_span(f"theme.apply.{normalized}"):
                appearance_mode = AppearanceModeManager.current(self.db)
                ThemeManager.apply_theme(
                    app,
                    normalized,
                    window=self,
                    animate=appearance_mode != AppearanceModeManager.CLASSIC,
                    duration_ms=0 if appearance_mode == AppearanceModeManager.CLASSIC else 320,
                )
                self._current_theme_name = normalized
                self.apply_appearance_mode(appearance_mode, force_tree=True)
                self._apply_shell_theme_styles()

            try:
                self.db.set_setting("color_theme_full", normalized)
                if ThemeManager.is_dark_theme(normalized):
                    self.db.set_setting("preferred_dark_theme", normalized)
                else:
                    self.db.set_setting("preferred_light_theme", normalized)
            except Exception as e:
                logger.warning("Theme preference could not be persisted: %s", e)

            active_page = None
            try:
                active_page = self.content_area.currentWidget()
            except Exception:
                active_page = None
            if active_page is not None:
                try:
                    self._refresh_page_theme(active_page)
                except Exception as e:
                    logger.debug("Page theme refresh skipped: %s", e)
            self._refresh_visible_top_level_themes(appearance_mode)

            self.sync_theme_toggle_button()

            self.schedule_ui_task("soon", self._refresh_theme_chrome, f"theme.chrome.{normalized}")
            self._theme_refresh_generation = getattr(self, "_theme_refresh_generation", 0) + 1

            def _rebuild_sidebar():
                try:
                    if hasattr(self, "app_sidebar") and hasattr(self.app_sidebar, "side_menu") and hasattr(self.app_sidebar.side_menu, "refresh_theme"):
                        self.app_sidebar.side_menu.refresh_theme()
                except Exception as ex:
                    logger.debug("Deferred sidebar refresh_theme skipped: %s", ex)
                try:
                    self._reapply_nav_mode()
                except Exception as ex:
                    logger.debug("Deferred nav_mode reapply skipped: %s", ex)
            QTimer.singleShot(50, _rebuild_sidebar)
        finally:
            self._theme_applying = False

    def _refresh_theme_chrome(self):
        """Refresh theme-related UI components (header, topnav, sidebar)."""
        if hasattr(self.app_header, "apply_theme_styles"):
            self.app_header.apply_theme_styles()
        if hasattr(self, "app_top_nav"):
            self.app_top_nav.apply_theme_styles()
        try:
            if hasattr(self, "app_sidebar") and hasattr(self.app_sidebar, "side_menu") and hasattr(self.app_sidebar.side_menu, "refresh_theme"):
                self.app_sidebar.side_menu.refresh_theme()
        except Exception as e:
            logger.debug("Sidebar theme refresh skipped: %s", e)
        self.apply_appearance_mode(force_tree=False)

    def _refresh_visible_top_level_themes(self, appearance_mode):
        """Refresh visible top-level widgets' themes."""
        app = QApplication.instance()
        if not app:
            return
        for widget in app.topLevelWidgets():
            if widget is self or not isinstance(widget, QWidget) or not widget.isVisible():
                continue
            try:
                if hasattr(widget, "apply_theme_styles"):
                    widget.apply_theme_styles()
                elif hasattr(widget, "refresh_theme"):
                    widget.refresh_theme()
                ThemeManager.refresh_widget_tree(widget)
                AppearanceModeManager.apply_to_widget_tree(widget, appearance_mode)
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
            except Exception as e:
                logger.debug("Top-level theme refresh skipped for %s: %s", type(widget).__name__, e)

    def _refresh_page_theme(self, page):
        """Refresh a single page's theme."""
        if not page:
            return
        handled = False
        if hasattr(page, "apply_theme_styles"):
            try:
                page.apply_theme_styles()
                handled = True
            except Exception as e:
                logger.debug("Page apply_theme_styles failed: %s", e)
        elif hasattr(page, "refresh_theme"):
            try:
                page.refresh_theme()
                handled = True
            except Exception as e:
                logger.debug("Page refresh_theme failed: %s", e)
        ThemeManager.refresh_widget_tree(page, include_root=not handled)
        AppearanceModeManager.apply_to_widget_tree(
            page,
            getattr(self, "_appearance_mode", AppearanceModeManager.current(self.db)),
        )
        page.update()

    def apply_appearance_mode(self, mode=None, force_tree=True):
        """Apply Modern/Classic visual density and effect preferences."""
        try:
            app = QApplication.instance()
            resolved = AppearanceModeManager.normalize(
                mode if mode is not None else AppearanceModeManager.current(self.db)
            )
            root = self if force_tree or getattr(self, "_appearance_mode", None) != resolved else None
            resolved = AppearanceModeManager.apply(app, self.db, root, mode=resolved)
            self._appearance_mode = resolved
            return resolved
        except Exception as e:
            logger.debug("Appearance mode apply skipped: %s", e)
            return AppearanceModeManager.MODERN

    def sync_theme_toggle_button(self):
        """Sync header theme toggle button with current theme."""
        if hasattr(self.app_header, "sync_theme_controls"):
            self.app_header.sync_theme_controls(getattr(self, "_current_theme_name", "AYEC"))

    def toggle_theme_from_header(self):
        """Cycle through available themes from header button."""
        themes = ThemeManager.get_available_themes(self.db)
        if not themes:
            return
        current = ThemeManager.normalize_theme_name(getattr(self, "_current_theme_name", "AYEC"))
        try:
            idx = themes.index(current)
        except ValueError:
            idx = -1
        self.apply_theme(themes[(idx + 1) % len(themes)])

    def on_header_theme_changed(self, theme_name):
        self.apply_theme(theme_name)
