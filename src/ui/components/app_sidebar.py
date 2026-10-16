# -*- coding: utf-8 -*-

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QEvent, QPropertyAnimation, QEasingCurve

from src.ui.widgets.side_menu import SideMenu
from src.utils.appearance_mode import AppearanceModeManager

logger = logging.getLogger(__name__)


class AppSidebar(QWidget):
    """
    Uygulamanın yan menü bileşeni.
    Daralma ve genişleme animasyonlarını yönetir.
    """

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.db = main_window.db
        self.sector_manager = getattr(main_window, "sector_manager", None)
        self._is_collapsed = False
        self._nav_hidden = False

        self.setMinimumWidth(SideMenu.COLLAPSED_WIDTH)
        self.setMaximumWidth(SideMenu.EXPANDED_WIDTH)
        self.init_ui()

    def init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.side_menu = SideMenu(
            db=self.db,
            callback=self.main_window.on_menu_click,
            sector_manager=self.sector_manager,
            current_user=getattr(self.main_window, "current_user", None),
        )
        self.side_menu.logout_requested.connect(self.main_window.handle_logout_requested)
        self.side_menu.installEventFilter(self)
        self.layout.addWidget(self.side_menu)

        if hasattr(self.side_menu, "set_collapsed"):
            pinned = bool(getattr(self.side_menu, "_is_pinned", True))
            self.side_menu.set_collapsed(not pinned, animate=False)
            expanded_width = self.side_menu.expanded_width_for_window()
            self._sync_width(expanded_width if pinned else SideMenu.COLLAPSED_WIDTH)
        else:
            self._sync_width(SideMenu.EXPANDED_WIDTH)

    def toggle_menu(self):
        """Menüyü daraltır veya genişletir."""
        main_window = self.window()
        if (
            getattr(main_window, "_current_page_index", None) == 130
            and hasattr(main_window, "_settings_sidebar_auto_previous_icon_only")
        ):
            main_window._settings_sidebar_user_override = True
            if self.side_menu._icon_only:
                self.side_menu.set_pinned(True, persist=False, animate=False)
                self.side_menu.set_menu_label_mode("labels", persist=False)
            else:
                self.side_menu.set_menu_label_mode("icons", persist=False)
            return
        self._is_collapsed = not self._is_collapsed
        width = self.width()
        expanded_width = self.side_menu.expanded_width_for_window()
        new_width = SideMenu.COLLAPSED_WIDTH if self._is_collapsed else expanded_width

        if AppearanceModeManager.is_classic(self.db):
            self._sync_width(new_width)
            if hasattr(self.side_menu, "set_collapsed"):
                self.side_menu.set_collapsed(self._is_collapsed, animate=False)
            return

        self.anim = QPropertyAnimation(self, b"minimumWidth")
        self.anim.setDuration(300)
        self.anim.setStartValue(width)
        self.anim.setEndValue(new_width)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuart)

        self.anim2 = QPropertyAnimation(self, b"maximumWidth")
        self.anim2.setDuration(300)
        self.anim2.setStartValue(width)
        self.anim2.setEndValue(new_width)

        self.anim.start()
        self.anim2.start()

        if hasattr(self.side_menu, "set_collapsed"):
            self.side_menu.set_collapsed(self._is_collapsed)

    def eventFilter(self, obj, event):
        if obj is getattr(self, "side_menu", None) and event.type() == QEvent.Type.Resize:
            self._sync_width(self.side_menu.width())
        return super().eventFilter(obj, event)

    def set_nav_hidden(self, hidden: bool):
        self._nav_hidden = bool(hidden)
        if self._nav_hidden:
            if hasattr(self, "side_menu"):
                self.side_menu.setVisible(False)
            self.setMinimumWidth(0)
            self.setMaximumWidth(0)
            self.resize(0, self.height())
            self.setVisible(False)
            return

        self.setVisible(True)
        if hasattr(self, "side_menu"):
            self.side_menu.setVisible(True)
        expanded_width = self.side_menu.expanded_width_for_window()
        width = SideMenu.COLLAPSED_WIDTH if self._is_collapsed else expanded_width
        self._sync_width(width)

    def apply_responsive_width(self):
        if self._is_collapsed or self._nav_hidden or not hasattr(self, "side_menu"):
            return
        target_width = self.side_menu.expanded_width_for_window()
        if self.width() != target_width:
            self.side_menu.set_collapsed(False, animate=False)
            self._sync_width(target_width)

    def _sync_width(self, width):
        if getattr(self, "_nav_hidden", False):
            self.setMinimumWidth(0)
            self.setMaximumWidth(0)
            return
        width = max(SideMenu.COLLAPSED_WIDTH, min(SideMenu.EXPANDED_WIDTH, int(width)))
        self._is_collapsed = width <= SideMenu.COLLAPSED_WIDTH
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)
