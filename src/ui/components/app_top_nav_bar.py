# -*- coding: utf-8 -*-
"""
AppTopNavBar — AYEC Pro üst navigasyon çubuğu.
Sayfa gruplarını yatay sekmelerde gösterir; hover/tıklamada floating dropdown açar.
Sol sidebar ile senkronize çalışır.
"""

import logging

from PyQt6.QtCore import QEvent, QPropertyAnimation, QEasingCurve, QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.utils.page_config import GROUP_ORDER, PAGE_NAMES, PAGE_PARENTS
from src.utils.theme_colors import theme_qss
from src.utils.sector_config import SECTOR_PAGES, SectorType
from src.utils.system_config import SystemConfig

logger = logging.getLogger(__name__)

# Grup adlarına karşılık emoji ikonlar
GROUP_ICONS = {
    "Servis Y\u00f6netimi": "\U0001f527",
    "Servis Y\u00f6netim Ayar\u0131": "\u2699",
    "Stok / Sipari\u015f": "\U0001f4e6",
    "Teklif Y\u00f6netimi": "\U0001f4c4",
    "Finans": "\U0001f4b0",
    "M\u00fc\u015fteri": "\U0001f465",
    "Personel": "\U0001f464",
    "Projeler": "\U0001f4c1",
    "Sistem": "\u2699",
}

# PAGE_PARENTS artık tam Türkçe — normalize haritası gerekmez
_NORMALIZE_MAP: dict[str, str] = {}


def _normalize_group(name: str) -> str:
    return _NORMALIZE_MAP.get(name, name)


def _get_sector_allowed_pages(db) -> set:
    """Aktif sektöre göre izin verilen sayfa ID'lerini döndürür."""
    try:
        sector_str = SystemConfig.get_current_sector(db)
        sector = SectorType(sector_str)
    except Exception:
        sector = SectorType.TEKNIK_SERVIS
    return SECTOR_PAGES.get(sector, SECTOR_PAGES[SectorType.TEKNIK_SERVIS])


def _pages_for_group(group_name: str, allowed_sector_pages: set | None = None) -> list[tuple[int, str]]:
    """Bir gruba ait (page_id, page_name) listesini döndürür — sektör filtresi uygulanır."""
    result = []
    seen = set()
    for pid, grp in PAGE_PARENTS.items():
        if _normalize_group(grp) != group_name:
            continue
        if pid in seen:
            continue
        # İsmi olmayan (fallback "Sayfa X") girdileri atla
        name = PAGE_NAMES.get(pid)
        if name is None:
            continue
        # Sektör filtresi
        if allowed_sector_pages is not None and pid not in allowed_sector_pages:
            continue
        result.append((pid, name))
        seen.add(pid)
    return result


def _menu_label(db, page_id: int, fallback: str) -> str:
    try:
        custom = db.get_internal_setting(f"menu_label_page_{int(page_id)}", "") if db else ""
        return (custom or "").strip() or fallback
    except Exception:
        return fallback


def _is_menu_visible(db, page_id: int) -> bool:
    try:
        if db and db.get_internal_setting(f"menu_visible_page_{int(page_id)}", "1") != "1":
            return False
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# FloatingDropdown
# ---------------------------------------------------------------------------

class FloatingDropdown(QFrame):
    """Grup sekmesinin altında açılan sayfa listesi paneli."""

    page_clicked = pyqtSignal(int)

    def __init__(self, parent_window: QWidget):
        # Tool window + FramelessWindowHint: bağımsız pencere — tıklama her zaman çalışır
        super().__init__(
            parent_window,
            Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint,
        )
        self.setObjectName("TopNavDropdown")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowFlag(Qt.WindowType.NoDropShadowWindowHint, False)
        self._active_page_id: int = -1
        self._close_timer = QTimer(self)
        self._close_timer.setSingleShot(True)
        self._close_timer.setInterval(200)
        self._close_timer.timeout.connect(self.hide)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(2)
        self._layout = layout
        self.hide()

    # ------------------------------------------------------------------
    def populate(self, group_name: str, active_page_id: int, allowed_sector_pages: set | None = None):
        """Dropdown içeriğini verilen gruba göre doldurur."""
        self._active_page_id = active_page_id
        # Önceki butonları temizle
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        pages = [
            (pid, name)
            for pid, name in _pages_for_group(group_name, allowed_sector_pages)
            if _is_menu_visible(getattr(self.parent(), "db", None), pid)
        ]
        if not pages:
            self.hide()
            return

        for pid, pname in pages:
            pname = _menu_label(getattr(self.parent(), "db", None), pid, pname)
            btn = QPushButton(f"  ▸  {pname}")
            btn.setObjectName("DropdownPageBtn")
            btn.setProperty("active", pid == active_page_id)
            btn.setFixedHeight(36)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(self._page_btn_qss(pid == active_page_id))
            btn.clicked.connect(lambda checked=False, p=pid: self._on_page_clicked(p))
            self._layout.addWidget(btn)

        self.setMinimumWidth(200)
        self.adjustSize()

    def enterEvent(self, event):
        self._cancel_close()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._schedule_close()
        super().leaveEvent(event)

    def _on_page_clicked(self, page_id: int):
        self.hide()
        self.page_clicked.emit(page_id)

    def _page_btn_qss(self, is_active: bool) -> str:
        if is_active:
            return theme_qss(
                """
                QPushButton {
                    background: @selection_bg;
                    color: @selection_text;
                    border: none;
                    border-left: 3px solid @accent;
                    border-radius: 6px;
                    font-weight: 700;
                    font-size: 12px;
                    text-align: left;
                    padding-left: 10px;
                }
                """
            )
        return theme_qss(
            """
            QPushButton {
                background-color: transparent;
                color: @text;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                text-align: left;
                padding-left: 13px;
            }
            QPushButton:hover {
                background-color: @surface_alt;
                color: @text;
            }
            """
        )

    def apply_theme_styles(self):
        self.setStyleSheet(
            theme_qss(
                """
                QFrame#TopNavDropdown {
                    background: @surface;
                    border: 1px solid @border;
                    border-radius: 12px;
                }
                """
            )
        )
        # Butonları da yeniden renklendir
        for i in range(self._layout.count()):
            w = self._layout.itemAt(i).widget()
            if isinstance(w, QPushButton):
                is_active = w.property("active") or False
                w.setStyleSheet(self._page_btn_qss(is_active))

    def show_at(self, global_pos: QPoint):
        self.raise_()
        # ToolTip tipi için doğrudan global koordinat kullanılır
        self.move(global_pos)
        self.show()
        # Fade-in animasyonu
        anim = QPropertyAnimation(self, b"maximumHeight", self)
        anim.setDuration(140)
        anim.setStartValue(0)
        anim.setEndValue(self.sizeHint().height())
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # Zamanlayıcı bazlı kapat/iptal
    def _schedule_close(self):
        self._close_timer.start()

    def _cancel_close(self):
        self._close_timer.stop()

    def schedule_close(self):
        self._schedule_close()

    def cancel_close(self):
        self._cancel_close()


# ---------------------------------------------------------------------------
# AppTopNavBar
# ---------------------------------------------------------------------------

class AppTopNavBar(QWidget):
    """
    Ana pencerede AppHeader ile content_area arasında yer alan
    yatay grup sekme navigasyon çubuğu.
    """

    def __init__(self, main_window):
        super().__init__(main_window)
        self.main_window = main_window
        self.db = getattr(main_window, "db", None)
        self.setObjectName("AppTopNavBar")
        self.setFixedHeight(48)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._active_page_id: int = -1
        self._active_group: str = ""
        self._group_btns: dict[str, QPushButton] = {}

        # Tek bir floating dropdown tüm gruplar için paylaşılır
        self._dropdown = FloatingDropdown(main_window)
        self._dropdown.page_clicked.connect(self._on_page_selected)

        self._init_ui()
        self.apply_theme_styles()
        self.refresh_visibility()

    # ------------------------------------------------------------------
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(0)

        for group in GROUP_ORDER:
            icon = GROUP_ICONS.get(group, "▸")
            btn = QPushButton(f"{icon}  {group}")
            btn.setObjectName("TopNavGroupBtn")
            btn.setProperty("group", group)
            btn.setProperty("navActive", False)
            btn.setFixedHeight(48)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

            # Hover + tıklama: dropdown aç
            btn.enterEvent = lambda e, g=group, b=btn: self._on_tab_hover(g, b)
            btn.leaveEvent = lambda e, g=group: self._on_tab_leave(g)
            btn.clicked.connect(lambda checked=False, g=group, b=btn: self._on_tab_click(g, b))

            self._group_btns[group] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # İnce separator + aktif sayfa etiketi (sağda)
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setObjectName("TopNavSep")
        layout.addWidget(sep)

        self._lbl_active = QLabel("")
        self._lbl_active.setObjectName("TopNavActiveLabel")
        self._lbl_active.setContentsMargins(10, 0, 8, 0)
        self._lbl_active.setMaximumWidth(200)
        layout.addWidget(self._lbl_active)

    # ------------------------------------------------------------------
    def _on_tab_hover(self, group: str, btn: QPushButton):
        self._dropdown.cancel_close()
        self._open_dropdown(group, btn)

    def _on_tab_leave(self, group: str):
        self._dropdown.schedule_close()

    def _on_tab_click(self, group: str, btn: QPushButton):
        self._dropdown.cancel_close()
        self._open_dropdown(group, btn)

    def _open_dropdown(self, group: str, btn: QPushButton):
        allowed = _get_sector_allowed_pages(self.db)
        self._dropdown.populate(group, self._active_page_id, allowed)
        if self._dropdown._layout.count() == 0:
            return
        # Sekmenin sol-alt köşesini bul
        btn_global_bottom_left = btn.mapToGlobal(QPoint(0, btn.height()))
        self._dropdown.show_at(btn_global_bottom_left)
        self._dropdown.apply_theme_styles()

    def _on_page_selected(self, page_id: int):
        if hasattr(self.main_window, "on_menu_click"):
            self.main_window.on_menu_click(page_id)

    # ------------------------------------------------------------------
    def sync_active(self, page_index: int):
        """MainWindow.on_menu_click tarafından çağrılır; aktif sekmeyi günceller."""
        self.refresh_visibility()
        self._active_page_id = page_index
        raw_group = PAGE_PARENTS.get(page_index, "")
        new_group = _normalize_group(raw_group)
        self._active_group = new_group

        for group, btn in self._group_btns.items():
            is_active = group == new_group
            btn.setProperty("navActive", is_active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.setStyleSheet(self._tab_btn_qss(is_active))

        # Sağdaki aktif sayfa etiketi — uzun adlarda elide uygula
        page_name = PAGE_NAMES.get(page_index, "")
        page_name = _menu_label(self.db, page_index, page_name)
        fm = self._lbl_active.fontMetrics()
        elided = fm.elidedText(page_name, Qt.TextElideMode.ElideRight, self._lbl_active.maximumWidth() - 4)
        self._lbl_active.setText(elided)
        self._lbl_active.setToolTip(page_name)

    def refresh_visibility(self):
        allowed = _get_sector_allowed_pages(self.db)
        for group, btn in self._group_btns.items():
            pages = [
                pid for pid, _ in _pages_for_group(group, allowed)
                if _is_menu_visible(self.db, pid)
            ]
            btn.setVisible(bool(pages))

    # ------------------------------------------------------------------
    def apply_theme_styles(self):
        self.refresh_visibility()
        self.setStyleSheet(
            theme_qss(
                """
                QWidget#AppTopNavBar {
                    background-color: @surface;
                    border-bottom: 1px solid @border;
                }
                QFrame#TopNavSep {
                    color: @border;
                    max-height: 20px;
                    margin-top: 14px;
                }
                QLabel#TopNavActiveLabel {
                    color: @accent;
                    font-size: 11px;
                    font-weight: 700;
                }
                """
            )
        )
        for group, btn in self._group_btns.items():
            btn.setStyleSheet(self._tab_btn_qss(group == self._active_group))
        self._dropdown.apply_theme_styles()

    def _tab_btn_qss(self, is_active: bool) -> str:
        if is_active:
            return theme_qss(
                """
                QPushButton {
                    background-color: transparent;
                    color: @accent;
                    border: 1px solid @accent;
                    border-radius: 0px;
                    font-size: 12px;
                    font-weight: 700;
                    padding-left: 16px;
                    padding-right: 16px;
                }
                QPushButton:hover {
                    background-color: @surface_alt;
                    color: @accent;
                    border: 1px solid @accent;
                }
                """
            )
        return theme_qss(
            """
            QPushButton {
                background-color: transparent;
                color: @text_muted;
                border: 1px solid transparent;
                border-radius: 0px;
                font-size: 12px;
                font-weight: 500;
                padding-left: 16px;
                padding-right: 16px;
            }
            QPushButton:hover {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
            }
            """
        )
