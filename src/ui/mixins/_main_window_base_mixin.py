# -*- coding: utf-8 -*-

import logging
from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QPoint
from src.utils.theme_manager import ThemeManager
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.toast_notification import show_toast
from src.utils.performance_monitor import perf_span

logger = logging.getLogger(__name__)

class MainWindowBaseMixin:
    """Theme management, Frameless Window controls and Notifications."""

    def _apply_theme_early(self):
        app = QApplication.instance()
        if not app: return
        try: ThemeManager.load_custom_colors(self.db)
        except Exception: pass
        try: theme_name = self.db.get_setting("color_theme_full", "AYEC")
        except Exception: theme_name = "AYEC"
        normalized = ThemeManager.normalize_theme_name(theme_name)
        self._current_theme_name = normalized
        ThemeManager._current_theme = normalized
        try:
            # First, install the patch to catch any subsequent widget setStyleSheet calls
            ThemeManager._install_stylesheet_patch()
            app.setPalette(ThemeManager._build_palette(normalized))
            # get_stylesheet now returns a transformed and sanitized string internally
            app.setStyleSheet(ThemeManager.get_stylesheet(normalized))
            AppearanceModeManager.apply(app, self.db, self, mode=AppearanceModeManager.current(self.db))
            self._theme_applied_early = True
        except Exception as e:
            logger.warning(f"Early theme apply failed: {e}")

    def apply_theme_on_startup(self):
        app = QApplication.instance()
        if not app: return
        try: ThemeManager.load_custom_colors(self.db)
        except Exception: pass
        try: theme_name = self.db.get_setting("color_theme_full", "AYEC")
        except Exception: theme_name = "AYEC"
        normalized = ThemeManager.normalize_theme_name(theme_name)
        self._current_theme_name = normalized
        if not getattr(self, "_theme_applied_early", False):
            ThemeManager.apply_theme(app, normalized, window=self, animate=False)
        self.apply_appearance_mode(force_tree=True)
        if hasattr(self, "_apply_shell_theme_styles"): self._apply_shell_theme_styles()
        if hasattr(self, "app_header") and hasattr(self.app_header, "apply_theme_styles"):
            self.app_header.apply_theme_styles()
        if hasattr(self, "app_top_nav"): self.app_top_nav.apply_theme_styles()
        self.sync_theme_toggle_button()

    def apply_theme(self, theme_name):
        app = QApplication.instance()
        if not app or getattr(self, "_theme_applying", False): return
        self._theme_applying = True
        try:
            normalized = ThemeManager.normalize_theme_name(theme_name)
            with perf_span(f"theme.apply.{normalized}"):
                appearance_mode = AppearanceModeManager.current(self.db)
                ThemeManager.apply_theme(app, normalized, window=self, animate=appearance_mode != AppearanceModeManager.CLASSIC)
                self._current_theme_name = normalized
                self.apply_appearance_mode(appearance_mode, force_tree=True)
                if hasattr(self, "_apply_shell_theme_styles"): self._apply_shell_theme_styles()
            
            try: self.db.set_setting("color_theme_full", normalized)
            except Exception: pass
            
            if hasattr(self, "content_area"):
                page = self.content_area.currentWidget()
                if page: self._refresh_page_theme(page)

            self._refresh_theme_chrome(refresh_appearance=False)
            self._refresh_visible_top_level_themes(appearance_mode)
            self.sync_theme_toggle_button()
        finally:
            self._theme_applying = False

    def _deferred_theme_refresh(self):
        try:
            if hasattr(self, "app_sidebar") and hasattr(self.app_sidebar, "side_menu"):
                self.app_sidebar.side_menu.refresh_theme()
        except Exception: pass

    def _refresh_theme_chrome(self, refresh_appearance=True):
        if hasattr(self, "app_header") and hasattr(self.app_header, "apply_theme_styles"):
            self.app_header.apply_theme_styles()
        if hasattr(self, "app_top_nav"): self.app_top_nav.apply_theme_styles()
        if hasattr(self, "app_sidebar") and hasattr(self.app_sidebar, "side_menu"):
            self.app_sidebar.side_menu.refresh_theme()
        if refresh_appearance:
            self.apply_appearance_mode(force_tree=True)

    def _refresh_visible_top_level_themes(self, appearance_mode):
        app = QApplication.instance()
        if not app: return
        for widget in app.topLevelWidgets():
            if widget is self or not isinstance(widget, QWidget) or not widget.isVisible(): continue
            try:
                if hasattr(widget, "apply_theme_styles"): widget.apply_theme_styles()
                elif hasattr(widget, "refresh_theme"): widget.refresh_theme()
                AppearanceModeManager.apply_to_widget_tree(widget, appearance_mode)
                widget.style().unpolish(widget)
                widget.style().polish(widget)
                widget.update()
            except Exception: pass

    def _refresh_page_theme(self, page):
        if not page: return
        handled = False
        if hasattr(page, "apply_theme_styles"):
            page.apply_theme_styles()
            handled = True
        elif hasattr(page, "refresh_theme"):
            page.refresh_theme()
            handled = True
        if not handled:
            ThemeManager.refresh_widget_tree(page)
        AppearanceModeManager.apply_to_widget_tree(
            page,
            getattr(self, "_appearance_mode", AppearanceModeManager.current(self.db)),
        )
        page.update()

    def apply_appearance_mode(self, mode=None, force_tree=True):
        try:
            app = QApplication.instance()
            resolved = AppearanceModeManager.normalize(mode or AppearanceModeManager.current(self.db))
            root = self if force_tree or getattr(self, "_appearance_mode", None) != resolved else None
            resolved = AppearanceModeManager.apply(app, self.db, root, mode=resolved)
            self._appearance_mode = resolved
            return resolved
        except Exception:
            return AppearanceModeManager.MODERN

    def sync_theme_toggle_button(self):
        if hasattr(self, "app_header") and hasattr(self.app_header, "sync_theme_controls"):
            self.app_header.sync_theme_controls(getattr(self, "_current_theme_name", "AYEC"))

    def toggle_theme_from_header(self):
        """Header'daki butondan temaları sırayla değiştir."""
        themes = ThemeManager.get_available_themes(self.db)
        if not themes: return
        current = ThemeManager.normalize_theme_name(getattr(self, "_current_theme_name", "AYEC"))
        try: idx = themes.index(current)
        except ValueError: idx = -1
        self.apply_theme(themes[(idx + 1) % len(themes)])

    def on_header_theme_changed(self, theme_name):
        self.apply_theme(theme_name)

    def on_language_changed(self, lang_code):
        logger.info(f"Language changed to: {lang_code}")

    def show_notification(self, message, n_type="info"):
        """Publish a notification to the toast queue and notification center."""
        try:
            category_map = {
                "success": "System",
                "info": "Technical",
                "warning": "Stock",
                "error": "Technical",
            }
            priority_map = {"error": "critical", "warning": "high"}
            category = category_map.get(str(n_type), "System")
            if hasattr(self.db, "add_notification"):
                self.db.add_notification(
                    category,
                    "AYEC Pro",
                    str(message),
                    priority=priority_map.get(str(n_type), "normal"),
                )
            if hasattr(self, "toast"):
                duration = 5000 if n_type in ("error", "warning") else 3500
                self.toast.show_toast(str(message), str(n_type), duration)
            else:
                show_toast(self, message, n_type, 3200)
            if hasattr(self, "refresh_notification_bell"):
                self.refresh_notification_bell()
        except Exception as exc:
            logger.debug("Central notification publish failed: %s", exc)

    def window_minimize(self): self.showMinimized()
    def window_maximize_restore(self):
        if self.isMaximized(): self.showNormal()
        else: self.showMaximized()
    def window_close(self): self.close()

    def start_window_drag(self, global_pos: QPoint):
        if not self.isMaximized():
            self._drag_active = True
            self._drag_pos = global_pos - self.frameGeometry().topLeft()

    def update_window_drag(self, global_pos: QPoint):
        if getattr(self, "_drag_active", False) and not self.isMaximized():
            self.move(global_pos - getattr(self, "_drag_pos", QPoint()))

    def stop_window_drag(self): self._drag_active = False
