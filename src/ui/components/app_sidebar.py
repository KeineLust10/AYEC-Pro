# -*- coding: utf-8 -*-

import logging
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import QEvent, QPropertyAnimation, QEasingCurve

from src.ui.widgets.side_menu import SideMenu

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
            self._sync_width(SideMenu.EXPANDED_WIDTH if pinned else SideMenu.COLLAPSED_WIDTH)
        else:
            self._sync_width(SideMenu.EXPANDED_WIDTH)

    def toggle_menu(self):
        """Menüyü daraltır veya genişletir."""
        self._is_collapsed = not self._is_collapsed
        width = self.width()
        new_width = SideMenu.COLLAPSED_WIDTH if self._is_collapsed else SideMenu.EXPANDED_WIDTH

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
        width = SideMenu.COLLAPSED_WIDTH if self._is_collapsed else SideMenu.EXPANDED_WIDTH
        self._sync_width(width)

    def _sync_width(self, width):
        if getattr(self, "_nav_hidden", False):
            self.setMinimumWidth(0)
            self.setMaximumWidth(0)
            return
        width = max(SideMenu.COLLAPSED_WIDTH, min(SideMenu.EXPANDED_WIDTH, int(width)))
        self._is_collapsed = width <= SideMenu.COLLAPSED_WIDTH
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)
