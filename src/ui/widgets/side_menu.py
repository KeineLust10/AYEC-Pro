# -*- coding: utf-8 -*-
# side_menu.py - Ana SideMenu sınıfı

import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy, QApplication, QLineEdit
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QCursor, QPixmap, QPalette, QPainter, QPen

from src.utils.theme_colors import theme_qss, tc
from src.utils.theme_manager import ThemeManager
from src.utils.design_system import DesignTokens as ReferenceDesignTokens
from src.utils.language_manager import LanguageManager
from src.utils.system_config import SystemConfig
from src.utils.role_utils import is_admin_role
from src.utils.page_config import PAGE_MAPPING
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.status_utils import is_active_device_status
from src.utils.toast_notification import show_info
from src.ui.widgets.navigation_glyph import NavigationGlyph, PAGE_KINDS, navigation_icon

from ._side_menu_constants import (
    _is_classic_appearance, PAGE_ICONS, DesignTokens
)
from ._side_menu_accordion import AccordionItem


class SideMenu(QWidget):
    page_changed = pyqtSignal(int)
    logout_requested = pyqtSignal()
    pin_changed = pyqtSignal(bool)
    navigation_layout_about_to_change = pyqtSignal()
    navigation_layout_changed = pyqtSignal()
    EXPANDED_WIDTH = 320
    COLLAPSED_WIDTH = 76
    ICON_ONLY_WIDTH = 76

    def __init__(self, parent=None, callback=None, db=None, sector_manager=None, current_user=None):
        # Handle parameter order confusion
        if parent is not None and not isinstance(parent, QWidget) and callable(parent) and callback is None:
            callback = parent
            parent = None

        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("SideMenu")
        self.db = db
        self.sector_manager = sector_manager
        self.current_user = dict(current_user or {})
        self.auto_collapse_enabled = False
        self._is_pinned = self._load_pin_state()
        self._icon_only = self._load_menu_label_mode()
        self._is_collapsed = False
        self.setMinimumWidth(self.COLLAPSED_WIDTH)
        self.setMaximumWidth(self.EXPANDED_WIDTH)
        self.resize(self.EXPANDED_WIDTH, self.height())
        self.setProperty("skipThemeTransform", False)

        # ULTRA PREMIUM: Gradient background
        self.setStyleSheet(theme_qss(f"""
            QWidget#SideMenu {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 @window,
                    stop:0.28 @window,
                    stop:0.72 @surface,
                    stop:1 @surface);
                border-right: 1px solid {DesignTokens.BORDER_COLOR};
            }}
        """))
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Header
        self.create_header()
        
        # Scroll Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("SideMenuScroll")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet(theme_qss("background-color: transparent; border: none;"))
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        try:
            self.scroll_area.viewport().setObjectName("SideMenuViewport")
        except Exception:
            pass
        
        # Custom Scrollbar Style
        self.scroll_area.setStyleSheet(theme_qss(f"""
            QScrollArea#SideMenuScroll {{ background-color: transparent; border: none; }}
            QScrollArea#SideMenuScroll::viewport {{ background-color: transparent; border: none; }}
            QScrollBar:vertical {{
                border: none;
                background: {DesignTokens.SIDEBAR_BG};
                width: 8px;
                margin: 0px; 
            }}
            QScrollBar::handle:vertical {{
                background: {DesignTokens.BORDER_COLOR};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {DesignTokens.HOVER_ACCENT};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
        """))
        
        self.menu_container = QWidget()
        self.menu_container.setObjectName("SideMenuContainer")
        self.menu_container.setStyleSheet(theme_qss("background-color: transparent;"))
        self.menu_layout = QVBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(0, 5, 4, 4)
        self.menu_layout.setSpacing(0)
        self.menu_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.menu_container)
        self.layout.addWidget(self.scroll_area)
        
        self._menu_initializing = True
        self._finance_navigation_mode = False
        self._einvoice_navigation_mode = False
        self.accordion_groups = []
        self.flat_buttons = []
        self._last_active_page_id = 40
        self.lang = LanguageManager(self.db)
        self.populate_menu()
        
        # Footer
        self.create_footer()
        
        self.page_changed.connect(self.on_page_changed_internal)
        if callback:
            self.page_changed.connect(callback)
        self.lang.labels_updated.connect(self.refresh_menu)

        # Badge sistemi: buton haritası oluştur ve periyodik yenile
        self._btn_map = {}       # {page_id: btn}
        self._badge_names = {}   # {page_id: orijinal_isim}
        self._build_btn_map()
        self.refresh_badges()
        self._badge_timer = QTimer(self)
        self._badge_timer.timeout.connect(self.refresh_badges)
        self._badge_timer.start(60_000)  # Her 60 saniyede bir yenile
        self.set_pinned(self._is_pinned, persist=False, animate=False)
        self.set_menu_label_mode("icons" if self._icon_only else "labels", persist=False)
        self._menu_initializing = False

    def expanded_width_for_window(self):
        window = self.window()
        viewport_width = window.width() if window is not None else 0
        if viewport_width:
            return min(self.EXPANDED_WIDTH, max(240, round(viewport_width * 0.20)))
        return self.EXPANDED_WIDTH

    def _load_pin_state(self):
        try:
            if self.db and hasattr(self.db, "get_setting"):
                return self.db.get_setting("side_menu_pinned", "1") == "1"
        except Exception:
            pass
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = self.width() <= 220 and self.width() > self.COLLAPSED_WIDTH
        if getattr(self, "_compact_density", None) == compact:
            return
        self._compact_density = compact
        einvoice_navigation = False
        reference_catalog = False
        reference_customers = False
        if hasattr(self, "header"):
            self.header.setFixedHeight(
                94 if reference_customers else (100 if reference_catalog else (
                    68 if einvoice_navigation else (64 if getattr(self, "_finance_navigation_mode", False) else 130)
                ))
            )
        if hasattr(self, "header_layout"):
            if einvoice_navigation:
                self.header_layout.setContentsMargins(10, 0, 10, 0)
            elif reference_catalog:
                self.header_layout.setContentsMargins(15, 11, 15, 0)
            elif reference_customers:
                self.header_layout.setContentsMargins(15, 15, 15, 2)
            elif getattr(self, "_finance_navigation_mode", False):
                self.header_layout.setContentsMargins(18, 15, 18, 11)
            elif reference_customers:
                self.brand_layout.setContentsMargins(8, 5, 8, 5)
            else:
                self.header_layout.setContentsMargins(15, 15, 15, 15)
        if hasattr(self, "brand_layout"):
            if einvoice_navigation:
                self.brand_layout.setContentsMargins(8, 4, 8, 4)
            else:
                self.brand_layout.setContentsMargins(6 if compact else 8, 13 if compact else 8,
                                                     6 if compact else 8, 3 if compact else 8)
            self.brand_layout.setSpacing(6 if compact else 8)
        if hasattr(self, "branding_logo"):
            logo_size = 50 if reference_customers else (36 if einvoice_navigation else (32 if compact else 44))
            self.branding_logo.setFixedSize(logo_size, logo_size)
        if hasattr(self, "brand_card"):
            if reference_customers:
                self.brand_card.setFixedHeight(77)
            elif compact:
                self.brand_card.setFixedHeight(88)
            elif einvoice_navigation:
                self.brand_card.setFixedHeight(67)
            else:
                self.brand_card.setFixedHeight(100)
        if hasattr(self, "branding_title"):
            self.branding_title.setStyleSheet(self._branding_text_qss(True, compact))
        if hasattr(self, "branding_subtitle"):
            self.branding_subtitle.setStyleSheet(self._branding_text_qss(False, compact))
        if hasattr(self, "branding_sector_badge"):
            self.branding_sector_badge.setVisible(not compact)
            self.branding_sector_badge.setFixedWidth(34 if not compact else 0)
        if hasattr(self, "pin_button"):
            self.pin_button.setFixedSize(22 if compact else 24, 22 if compact else 24)
        if hasattr(self, "footer"):
            self.footer.setFixedHeight(
                78 if compact else (
                    103 if reference_customers else (
                        84 if getattr(self, "_finance_navigation_mode", False) else 124
                    )
                )
            )
        if hasattr(self, "logout_btn"):
            self.logout_btn.setFixedHeight(26 if compact else 44)
        for label in self.findChildren(QLabel):
            if not label.property("menuSectionLabel"):
                continue
            label.setFixedHeight(18 if compact else 24)
            if einvoice_navigation and label.property("einvoiceActiveSectionHeading"):
                label.setStyleSheet(theme_qss(
                    "QLabel { color: @finance_breadcrumb_active; font-size: 10px; font-weight: 900; "
                    "padding: 0 4px; margin: 0; background: transparent; border: none; }"
                ))
            elif einvoice_navigation and label.property("einvoiceActiveBadge"):
                label.setFixedSize(49, 20)
                label.setStyleSheet(theme_qss(
                    "QLabel { color: @finance_breadcrumb_active; font-size: 9px; font-weight: 900; "
                    "padding: 0 5px; margin: 0; background: @finance_active_bg; "
                    "border: 1px solid @finance_breadcrumb_active; border-radius: 5px; }"
                ))
            elif einvoice_navigation and "AKTIF" in label.text():
                label.setStyleSheet(theme_qss(
                    "QLabel { color: @accent; font-size: 10px; font-weight: 900; padding: 0 14px; "
                    "margin: 6px 10px 2px 10px; background: transparent; border: none; }"
                ))
            else:
                label.setStyleSheet(theme_qss(
                    "color: @text_muted; font-size: 9px; font-weight: 900; padding: 0 10px; "
                    "margin: 4px 6px 1px 6px; background-color: transparent; border: none; letter-spacing: 0.5px;"
                    if compact else
                    "color: @text_muted; font-size: 10px; font-weight: 900; padding: 0 14px; "
                    "margin: 6px 10px 2px 10px; background-color: transparent; border: none; letter-spacing: 1px;"
                ))
        for group in getattr(self, "accordion_groups", []):
            group.set_compact_density(compact)
        if hasattr(self, "menu_layout"):
            self.menu_layout.invalidate()
        if hasattr(self, "_last_active_page_id"):
            self.on_page_changed_internal(self._last_active_page_id)

    def _load_menu_label_mode(self):
        try:
            if self.db and hasattr(self.db, "get_setting"):
                return self.db.get_setting("side_menu_label_mode", "labels") == "icons"
        except Exception:
            pass
        return False

    def refresh_menu(self):
        self.navigation_layout_about_to_change.emit()
        # Clear layout
        while self.menu_layout.count():
            child = self.menu_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.accordion_groups = []
        self.flat_buttons = []
        self._btn_map = {}
        self._badge_names = {}
        self.populate_menu()
        for group in self.accordion_groups:
            group.set_icon_only(self._icon_only)
        self._build_btn_map()
        self.refresh_sector_badge()
        self.refresh_badges()
        self.navigation_layout_changed.emit()

    def _current_sector(self):
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                sector_id = self.sector_manager.get_current_plugin().sector_id
                return SystemConfig.normalize_sector(sector_id)
            return SystemConfig.get_current_sector(self.db)
        except Exception:
            return "teknik_servis"

    def _sector_allowed_pages(self):
        sector = self._current_sector()
        if sector == "otomotiv":
            return {
                40, 41, 42, 43, 60, 62, 30, 150, 210,
                21, 25, 26, 90, 120,
                50, 51, 140, 145, 146, 147, 66, 313, 314,
                100, 101, 105, 106, 115,
                10, 160, 261, 130, 135, 180, 70,
            }
        technical_only = {
            40, 41, 42, 43, 62, 61, 30, 65, 201,
            21, 25, 26, 90, 120,
            50, 51, 66, 140, 145, 146, 147, 150, 250, 300,
            313, 314,
            100, 101, 105, 106, 115,
            10, 130, 135, 160, 180, 200, 202, 261, 70,
        }
        return technical_only

    def _is_page_visible_for_sector(self, page_id):
        allowed = self._sector_allowed_pages()
        if allowed is None:
            return True
        return int(page_id) in allowed

    def _classic_mode(self):
        if _is_classic_appearance():
            return True
        try:
            return AppearanceModeManager.is_classic(self.db)
        except Exception:
            return False

    def create_header(self):
        header = QFrame(self)
        self.header = header
        header.setObjectName("SideMenuHeader")
        header.setFixedHeight(104)
        header.setStyleSheet(theme_qss("""
            QFrame#SideMenuHeader {
                background-color: transparent;
                border: none;
                border-bottom: 1px solid @border;
            }
        """))
        hl = QHBoxLayout(header)
        self.header_layout = hl
        hl.setContentsMargins(15, 14, 15, 14)

        brand_card = QFrame()
        self.brand_card = brand_card
        brand_card.setObjectName("SideMenuBrandCard")
        brand_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        brand_card.setStyleSheet(theme_qss("""
            QFrame#SideMenuBrandCard {
                background: @finance_surface;
                border: 1px solid @finance_outline;
                border-radius: 14px;
            }
        """))
        brand_layout = QHBoxLayout(brand_card)
        self.brand_layout = brand_layout
        brand_layout.setContentsMargins(8, 8, 8, 8)
        brand_layout.setSpacing(8)
        
        self.branding_logo = QLabel()
        self.branding_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.branding_logo.setFixedSize(44, 44)
        self.branding_logo.setStyleSheet(theme_qss("""
            background: @finance_active_bg;
            border: 1px solid @finance_outline;
            border-radius: 14px;
        """))
        
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.branding_title = QLabel("AYEC Pro")
        self.branding_title.setWordWrap(True)
        self.branding_title.setStyleSheet(self._branding_text_qss(True))
        self.branding_subtitle = QLabel("Servis Y\u00f6netimi")
        self.branding_subtitle.setWordWrap(True)
        self.branding_subtitle.setStyleSheet(self._branding_text_qss(False))
        title_box.addWidget(self.branding_title)
        title_box.addWidget(self.branding_subtitle)
        self.branding_sector_badge = QLabel("")
        self.branding_sector_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.branding_sector_badge.setFixedHeight(18)
        self.branding_sector_badge.setStyleSheet(theme_qss(f"""
            background: {DesignTokens.HEADER_BADGE_BG};
            color: {DesignTokens.HEADER_BADGE_TEXT};
            border: 1px solid {DesignTokens.BORDER_COLOR};
            border-radius: 4px;
            padding: 0 4px;
            font-size: 8px;
            font-weight: 600;
        """))
        brand_layout.addWidget(self.branding_logo)
        brand_layout.addLayout(title_box, 1)
        self.branding_sector_badge.setFixedWidth(34)
        brand_layout.addWidget(self.branding_sector_badge, 0, Qt.AlignmentFlag.AlignVCenter)
        self.pin_button = QPushButton("")
        self.pin_button.setAccessibleName("Pin sidebar")
        self.pin_button.setObjectName("SideMenuPinButton")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(self._is_pinned)
        self.pin_button.setFixedSize(24, 24)
        self.pin_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_button.setToolTip("Sol men\u00fcy\u00fc sabitle")
        self.pin_button.toggled.connect(self.set_pinned)
        self.pin_button.setStyleSheet(self._pin_button_qss())
        pin_layout = QHBoxLayout(self.pin_button)
        pin_layout.setContentsMargins(0, 0, 0, 0)
        self.pin_glyph = NavigationGlyph("\U0001f4cc", title="Pin sidebar")
        self.pin_glyph.setFixedSize(18, 18)
        self.pin_glyph.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        pin_layout.addWidget(self.pin_glyph, 0, Qt.AlignmentFlag.AlignCenter)
        brand_layout.addWidget(self.pin_button, 0, Qt.AlignmentFlag.AlignTop)
        hl.addWidget(brand_card)
        self.nav_search_input = QLineEdit(header)
        self.nav_search_input.setPlaceholderText("Mod\u00fcl veya i\u015flem ara...")
        self.nav_search_input.setFixedHeight(38)
        self.nav_search_input.setStyleSheet(theme_qss(
            "QLineEdit { background: @finance_surface; color: @text; border: 1px solid @finance_outline; "
            "border-radius: 8px; padding: 0 12px; font-size: 12px; }"
        ))
        self.nav_search_input.textChanged.connect(self._filter_navigation)
        self.nav_search_input.hide()
        hl.addWidget(self.nav_search_input)
        
        self.layout.addWidget(header)
        self.refresh_sector_badge()
        try:
            if self.db and hasattr(self.db, "get_setting"):
                logo_path = self.db.get_setting("logo_path", "") or ""
                company_name = self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro"
                site_title = self.db.get_setting("site_title", "Servis Yönetimi") or "Servis Yönetimi"
                self.update_branding(logo_path, company_name, site_title)
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"Branding guncellenirken hata: {str(e)}")

    def _pin_button_qss(self):
        if _is_classic_appearance():
            return theme_qss("""
                QPushButton#SideMenuPinButton {
                    background-color: @surface;
                    color: @text;
                    border: 1px solid @border;
                    border-radius: 4px;
                    font-size: 14px;
                    font-weight: 800;
                }
                QPushButton#SideMenuPinButton:hover {
                    background-color: @surface_alt;
                    border-color: @accent;
                    color: @text;
                }
                QPushButton#SideMenuPinButton:checked {
                    background-color: @selection_bg;
                    border-color: @accent;
                    color: @selection_text;
                }
            """)
        return theme_qss("""
            QPushButton#SideMenuPinButton {
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton#SideMenuPinButton:hover {
                background-color: @surface;
                border-color: @accent;
            }
            QPushButton#SideMenuPinButton:checked {
                background-color: @accent;
                color: @selection_text;
                border-color: @accent;
            }
        """)

    def set_pinned(self, pinned: bool, persist: bool = True, animate: bool = False):
        self._is_pinned = bool(pinned)
        self.auto_collapse_enabled = not self._is_pinned and not self._icon_only
        if hasattr(self, "pin_button") and self.pin_button.isChecked() != self._is_pinned:
            self.pin_button.blockSignals(True)
            self.pin_button.setChecked(self._is_pinned)
            self.pin_button.blockSignals(False)
        if hasattr(self, "pin_button"):
            self.pin_button.setToolTip("Sol men\u00fc sabit" if self._is_pinned else "Sol men\u00fc hover ile a\u00e7\u0131l\u0131r")
            self.pin_button.setStyleSheet(self._pin_button_qss())
            if hasattr(self, "pin_glyph"):
                self.pin_glyph.set_navigation_state(self._is_pinned)
        if persist:
            try:
                if self.db and hasattr(self.db, "set_setting"):
                    self.db.set_setting("side_menu_pinned", "1" if self._is_pinned else "0")
            except Exception:
                pass
        if self._icon_only:
            self._apply_icon_only_visual_state()
        else:
            self.set_collapsed(False if self._is_pinned else True, animate=animate)
        self.pin_changed.emit(self._is_pinned)

    def set_menu_label_mode(self, mode: str, persist: bool = True):
        self._icon_only = str(mode or "labels").strip().lower() == "icons"
        if persist:
            try:
                if self.db and hasattr(self.db, "set_setting"):
                    self.db.set_setting(
                        "side_menu_label_mode",
                        "icons" if self._icon_only else "labels",
                    )
            except Exception:
                pass
        self.auto_collapse_enabled = not self._is_pinned and not self._icon_only
        if not getattr(self, "_menu_initializing", False):
            self.refresh_menu()
        self.on_page_changed_internal(self._last_active_page_id)
        if self._icon_only:
            self._apply_icon_only_visual_state()
        else:
            self.set_collapsed(False if self._is_pinned else True, animate=False)
        self.navigation_layout_changed.emit()

    def _apply_icon_only_visual_state(self):
        self._is_collapsed = False
        self.setMinimumWidth(self.ICON_ONLY_WIDTH)
        self.setMaximumWidth(self.ICON_ONLY_WIDTH)
        self.resize(self.ICON_ONLY_WIDTH, self.height())
        parent = self.parentWidget()
        if parent and hasattr(parent, "_sync_width"):
            parent._sync_width(self.ICON_ONLY_WIDTH)
        for widget_name in ("branding_title", "branding_subtitle", "branding_sector_badge", "footer"):
            widget = getattr(self, widget_name, None)
            if widget:
                widget.setVisible(False)
        if hasattr(self, "scroll_area") and self.scroll_area:
            self.scroll_area.setVisible(True)
        if hasattr(self, "header") and self.header:
            self.header.setFixedHeight(92)
        if hasattr(self, "brand_layout") and self.brand_layout:
            self.brand_layout.setContentsMargins(8, 10, 8, 10)
            self.brand_layout.setSpacing(4)
        if hasattr(self, "branding_logo") and self.branding_logo:
            self.branding_logo.setFixedSize(42, 42)
        if hasattr(self, "pin_button") and self.pin_button:
            self.pin_button.setFixedSize(26, 26)

    @staticmethod
    def _branding_text_qss(is_title, compact=False):
        return theme_qss(
            "background: transparent; border: none; padding: 0; color: @text; "
            f"font-size: {9 if compact else 13}px; font-weight: 600;" if is_title else
            "background: transparent; border: none; padding: 0; color: @text_muted; "
            f"font-size: {8 if compact else 10}px; font-weight: 400;"
        )

    def update_branding(self, logo_path="", company_name="", site_title=""):
        try:
            name = str(company_name or "").strip() or "AYEC Pro"
            subtitle = str(site_title or "").strip() or "Servis Yönetimi"
            if hasattr(self, "branding_title") and self.branding_title:
                self.branding_title.setText(name)
            if hasattr(self, "branding_subtitle") and self.branding_subtitle:
                self.branding_subtitle.setText(subtitle)

            path = str(logo_path or "").strip()
            if hasattr(self, "branding_logo") and self.branding_logo:
                if path and os.path.exists(path):
                    pm = QPixmap(path)
                    if not pm.isNull():
                        size = 46
                        ratio = self.branding_logo.devicePixelRatioF()
                        pixel_size = max(1, round(size * ratio))
                        logo = pm.scaled(
                            pixel_size, pixel_size, Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        logo.setDevicePixelRatio(ratio)
                        self.branding_logo.setText("")
                        self.branding_logo.setFixedSize(size, size)
                        self.branding_logo.setPixmap(logo)
                        self.branding_logo.setStyleSheet(theme_qss("background-color: transparent;"))
                        return
                fallback_path = os.path.join(os.getcwd(), "assets", "app_icon.png")
                fallback_pm = QPixmap(fallback_path)
                self.branding_logo.setPixmap(QPixmap())
                self.branding_logo.setFixedSize(46, 46)
                if not fallback_pm.isNull():
                    ratio = self.branding_logo.devicePixelRatioF()
                    pixel_size = max(1, round(46 * ratio))
                    logo = fallback_pm.scaled(
                        pixel_size, pixel_size, Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    logo.setDevicePixelRatio(ratio)
                    self.branding_logo.setText("")
                    self.branding_logo.setPixmap(logo)
                    self.branding_logo.setStyleSheet(theme_qss("""
                        background: @surface;
                        border: 1px solid @border;
                        border-radius: 14px;
                    """))
                else:
                    self.branding_logo.setText("AY")
                    self.branding_logo.setStyleSheet(theme_qss("""
                        color: @text;
                        font-size: 16px;
                        font-weight: 900;
                        background: @surface;
                        border: 1px solid @border;
                        border-radius: 14px;
                    """))
        except Exception as e:
            from src.utils.logger import logger
            logger.error(f"Marka guncellenirken hata: {str(e)}")

    def set_reference_module_branding(self, enabled):
        if enabled:
            self.branding_title.setText("Teknik Servis Modu")
            self.branding_subtitle.setText("Donan\u0131m & Onar\u0131m Hub")
            chip = QPixmap(28, 28)
            chip.fill(Qt.GlobalColor.transparent)
            painter = QPainter(chip)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor("#38bdf8"), 1.8))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(7, 7, 14, 14, 3, 3)
            for offset in (9, 14, 19):
                painter.drawLine(offset, 2, offset, 7)
                painter.drawLine(offset, 21, offset, 26)
                painter.drawLine(2, offset, 7, offset)
                painter.drawLine(21, offset, 26, offset)
            painter.end()
            self.branding_logo.setText("")
            self.branding_logo.setPixmap(chip)
            return
        logo_path = self.db.get_setting("company_logo", "") or ""
        company_name = self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro"
        site_title = self.db.get_setting("site_title", "Servis Y\u00f6netimi") or "Servis Y\u00f6netimi"
        self.update_branding(logo_path, company_name, site_title)

    def refresh_sector_badge(self):
        if not hasattr(self, "branding_sector_badge") or not self.branding_sector_badge:
            return
        sector = self._current_sector()
        self.branding_sector_badge.setText("OTOMOTIV MODU" if sector == "otomotiv" else "ERP")
        if hasattr(self, "footer_mode") and self.footer_mode:
            if getattr(self, "_finance_navigation_mode", False):
                self.footer_mode.setText("Lisans S\u00fcr\u00fcm\u00fc")
            else:
                self.footer_mode.setText("Otomotiv" if sector == "otomotiv" else "Teknik Servis")

    # Clean two-sector implementations. These later definitions intentionally override
    # the older multi-sector/fallback-heavy versions above.
    def _build_menu_from_plugin(self, allowed_pages):
        if self._current_sector() != "otomotiv":
            return None
        settings_items = [
            ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
            ("Marka Adlar\u0131 Y\u00f6netimi", 145),
            ("Rapor C\u00fcmle Kal\u0131plar\u0131", 147),
            ("\u0130\u015f\u00e7ilik & Fiyat Y\u00f6netimi", 140),
        ]
        return [
            ("SERVIS OPERASYON", [
                ("Servis Y\u00f6netimi", "\U0001f527", [
                    ("Genel Bak\u0131\u015f", 40),
                    ("Servis Listesi", 42),
                    ("Ara\u00e7 Bak\u0131m Takibi", 210),
                    ("Durum Paneli", 43),
                    ("Teknisyen Paneli", 62),
                    ("Randevular", 30),
                    ("Servis Y\u00f6netim Ayar\u0131", settings_items),
                ]),
            ]),
            ("MUSTERI", [
                ("M\u00fc\u015fteri Hub", "\U0001f465", [
                    ("M\u00fc\u015fteri Listesi", 21),
                    ("\u00c7al\u0131\u015fma Ortaklar\u0131", 26),
                    ("S\u00f6zle\u015fmeler", 25),
                    ("Hat\u0131rlat\u0131c\u0131lar", 90),
                    ("Duyurular", 120),
                ]),
            ]),
            ("TICARI", [
                ("Stok / Sipari\u015f", "\U0001f4e6", [
                    ("Yedek Par\u00e7a", 60),
                    ("Emanet (Konsinye) Cihazlar", 66),
                    ("Depo ve Ara\u00e7 Stoklar\u0131", 51),
                ]),
                ("Teklif Y\u00f6netimi", "\U0001f4c4", [
                    ("Teklif Olu\u015ftur", 150),
                    ("T\u00fcm Teklifler", 313),
                    ("Teklif Raporlar\u0131", 314),
                ]),
            ]),
            ("FINANS", [
                ("Finans", "\U0001f4b8", [
                    ("Finansal Dashboard", 100),
                    ("Gelir / Gider", 101),
                    ("Banka Hesaplar\u0131", 105),
                    ("\u00c7ek / Senet", 106),
                    ("E-Fatura", 115),
                ]),
            ]),
            ("IK VE PERSONEL", [
                ("Personel", "\U0001f464", [("Personel", 10)]),
            ]),
            ("SISTEM", [
                ("Sistem Yard\u0131mc\u0131lar\u0131", "\u2699", [
                    ("Sistem Ayarlar\u0131", 130),
                    ("Log Kay\u0131tlar\u0131", 135),
                    ("Bilgi Bankas\u0131", 160),
                    ("Yedekleme Merkezi", 180),
                    ("Kullan\u0131m K\u0131lavuzu", 261),
                    ("Destek Merkezi", 70),
                ]),
            ]),
        ]

    def _get_page_id_from_menu_item(self, item):
        if not isinstance(item, dict):
            return None

        direct_page_id = item.get("page_id")
        if isinstance(direct_page_id, int):
            return direct_page_id
        if isinstance(direct_page_id, str) and direct_page_id.strip().isdigit():
            return int(direct_page_id.strip())

        item_id = str(item.get("id", "")).strip().lower()
        if item_id == "stock":
            return 60 if self._current_sector() == "otomotiv" else 50

        page_mapping = {
            "dashboard": 40,
            "vehicles": 210,
            "service_board": 41,
            "service_list": 42,
            "customers": 21,
            "technician": 62,
            "appointments": 30,
            "field_service": 61,
            "logistics": 65,
            "job_service_tracking": 201,
            "ai_assistant": 170,
            "partners": 26,
            "contracts": 25,
            "reminders": 90,
            "announcements": 120,
            "services": 140,
            "product_groups": 146,
            "brands": 145,
            "report_templates": 147,
            "loaner_devices": 66,
            "sales_hub": 150,
            "sales": 150,
            "mobile_stock": 250,
            "pc_builder": 300,
            "projects": 200,
            "project_archive": 202,
            "finance": 101,
            "bank": 105,
            "check_note": 106,
            "invoice": 115,
            "personnel": 10,
            "knowledge_base": 160,
            "user_manual": 261,
            "settings": 130,
            "audit_log": 135,
            "backup": 180,
            "support": 70,
        }
        return page_mapping.get(str(item.get("id", "")).strip().lower())

    def _menu_label(self, pid, fallback):
        try:
            custom = self.db.get_internal_setting(f"menu_label_page_{int(pid)}", "") if self.db else ""
            return (custom or "").strip() or fallback
        except Exception:
            return fallback

    def _filter_sections_for_visibility(self, sections, allowed_pages):
        def filter_items(items):
            visible = []
            for name, target in items:
                if isinstance(target, (list, tuple)):
                    nested = filter_items(target)
                    if nested:
                        visible.append((name, nested))
                    continue
                pid = int(target)
                if allowed_pages is not None and pid not in allowed_pages:
                    continue
                if not self._is_page_visible_for_sector(pid):
                    continue
                if self.db and self.db.get_internal_setting(f"menu_visible_page_{pid}", "1") != "1":
                    continue
                visible.append((self._menu_label(pid, name), pid))
            return visible

        filtered_sections = []
        for section_title, groups in sections:
            filtered_groups = []
            for group in groups:
                group_title, group_icon, group_subs = group[:3]
                main_page_id = int(group[3]) if len(group) > 3 else None
                visible_subs = filter_items(group_subs)
                main_visible = (
                    main_page_id is not None
                    and (allowed_pages is None or main_page_id in allowed_pages)
                    and self._is_page_visible_for_sector(main_page_id)
                    and (not self.db or self.db.get_internal_setting(
                        f"menu_visible_page_{main_page_id}", "1"
                    ) == "1")
                )
                if visible_subs or main_visible:
                    filtered_groups.append((group_title, group_icon, visible_subs, main_page_id))
            if filtered_groups:
                filtered_sections.append((section_title, filtered_groups))
        return filtered_sections

    def _render_sections(self, sections, allowed_pages):
        first = True
        section_index = 0
        customer_tail_spacer_added = False
        for section_title, groups in sections:
            # Section header row with a subtle top spacing
            if not first:
                spacing = 15 if section_index == 1 else 17
                if self._last_active_page_id == 147:
                    spacing = 59 if section_index == 1 else (8 if section_index == 2 else spacing)
                self.menu_layout.addSpacing(spacing)
            first = False

            lbl = QLabel(section_title)
            lbl.setProperty("menuSectionLabel", True)
            lbl.setProperty("skipThemeTransform", False)
            lbl.setFixedHeight(24)
            lbl.setStyleSheet(theme_qss("""
                color: @text_muted;
                font-size: 10px;
                font-weight: 900;
                padding: 0 14px;
                margin: 6px 10px 2px 10px;
                background-color: transparent;
                border: none;
                letter-spacing: 1px;
            """))
            if self._einvoice_navigation_mode and section_title in {
                "FINANS & MUHASEBE", "F\u0130NANS & MUHASEBE"
            }:
                section_row = QWidget()
                section_row.setFixedHeight(24)
                section_row_layout = QHBoxLayout(section_row)
                section_row_layout.setContentsMargins(12, 6, 20, 2)
                section_row_layout.setSpacing(0)
                lbl.setText("FINANS & MUHASEBE")
                lbl.setProperty("einvoiceActiveSectionHeading", True)
                lbl.setStyleSheet(theme_qss(
                    "QLabel { color: @accent; font-size: 10px; font-weight: 900; "
                    "padding: 0 4px; margin: 0; background: transparent; border: none; }"
                ))
                section_row_layout.addWidget(lbl)
                section_row_layout.addStretch(1)
                active_badge = QLabel("AKTIF")
                active_badge.setProperty("einvoiceActiveBadge", True)
                active_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                active_badge.setFixedSize(49, 20)
                active_badge.setStyleSheet(theme_qss(
                    "QLabel { color: @accent; font-size: 9px; font-weight: 900; "
                    "padding: 0 5px; margin: 0; background: @finance_active_bg; "
                    "border: 1px solid @finance_breadcrumb_active; border-radius: 5px; }"
                ))
                section_row_layout.addWidget(active_badge)
                self.menu_layout.addWidget(section_row)
            else:
                self.menu_layout.addWidget(lbl)
            lbl.setVisible(not self._icon_only)
            if self._einvoice_navigation_mode and section_title in {
                "FINANS & MUHASEBE", "F\u0130NANS & MUHASEBE"
            }:
                section_row.setVisible(not self._icon_only)
            if section_title in {"FINANS", "F\u0130NANS & MUHASEBE"} and not self._einvoice_navigation_mode:
                finance_links = [
                    item
                    for _title, _icon, items, *_rest in groups
                    for item in items
                    if not isinstance(item[1], (list, tuple))
                ]
                finance_links = [
                    (label, int(page_id)) for label, page_id in finance_links
                    if allowed_pages is None or int(page_id) in allowed_pages
                ]
                lbl.hide()
                finance_group = AccordionItem(
                    section_title, "\U0001f4b8", finance_links, self,
                    allowed_pages=allowed_pages,
                )
                self.menu_layout.addWidget(finance_group)
                self.accordion_groups.append(finance_group)
                if any(page_id == self._last_active_page_id for _label, page_id in finance_links):
                    finance_group.expand()
                section_index += 1
                continue
            if self._einvoice_navigation_mode:
                for _title, _icon, links, *_rest in groups:
                    for label, page_id in links:
                        page_id = int(page_id)
                        if allowed_pages is not None and page_id not in allowed_pages:
                            continue
                        btn = QPushButton(label.replace("&", "&&"))
                        icon_kind = PAGE_KINDS.get(page_id)
                        btn._navigation_kind = icon_kind
                        btn.setIcon(navigation_icon(
                            icon_kind, 18,
                            "selection_text" if page_id == self._last_active_page_id else "text_muted"
                        ))
                        btn.setIconSize(QSize(18, 18))
                        btn.setAccessibleName(label)
                        btn.setCursor(Qt.CursorShape.PointingHandCursor)
                        btn.setFixedHeight(39)
                        btn.setProperty("skipThemeTransform", False)
                        btn.setStyleSheet(self._finance_navigation_button_style(page_id == self._last_active_page_id))
                        btn.clicked.connect(lambda checked=False, pid=page_id: self.page_changed.emit(pid))
                        self.menu_layout.addWidget(btn)
                        self.flat_buttons.append((btn, page_id))
                section_index += 1
                continue
            if self._finance_navigation_mode and section_index > 0:
                self.menu_layout.addSpacing(11 if section_index == 1 else 10)
            if self._finance_navigation_mode and section_title == "F\u0130NANS KONSOLU" and groups:
                self.flat_buttons = []
                finance_links = groups[0][2]
                for label, page_id in finance_links:
                    if allowed_pages is not None and int(page_id) not in allowed_pages:
                        continue
                    display_label = label.replace("&", "&&")
                    btn = QPushButton(display_label)
                    icon_kind = "card" if "Krediler" in label else PAGE_KINDS.get(int(page_id))
                    btn._navigation_kind = icon_kind
                    btn.setIcon(navigation_icon(icon_kind, 18, "selection_text" if int(page_id) == self._last_active_page_id else "text_muted"))
                    btn.setIconSize(QSize(18, 18))
                    btn.setAccessibleName(label)
                    btn.setCursor(Qt.CursorShape.PointingHandCursor)
                    btn.setFixedHeight(43)
                    btn.setProperty("skipThemeTransform", False)
                    btn.setStyleSheet(self._finance_navigation_button_style(int(page_id) == self._last_active_page_id))
                    btn.clicked.connect(lambda checked=False, pid=int(page_id): self.page_changed.emit(pid))
                    self.menu_layout.addWidget(btn)
                    self.flat_buttons.append((btn, int(page_id)))
                section_index += 1
                continue
            for group_index, group in enumerate(groups):
                title, icon, subs = group[:3]
                main_page_id = int(group[3]) if len(group) > 3 and group[3] is not None else None
                item = AccordionItem(
                    title, icon, subs, self, allowed_pages=allowed_pages,
                    main_page_id=main_page_id,
                )
                if title == "Servis Y\u00f6netimi":
                    item._keep_open_when_other_expands = True
                    item._reference_submenu_indent = 0 if self._last_active_page_id == 147 else 40
                if title in {"Servis Y\u00f6netim Ayar\u0131", "Servis Ayarlar\u0131"}:
                    if self._last_active_page_id == 147:
                        item._title_lbl.setText("SERVIS Y\u00d6NETIM AYARI")
                    item._reference_submenu_top_margin = 2
                    item._reference_child_row_height = 40 if self._last_active_page_id == 147 else 38
                    if self._last_active_page_id == 147 and item.sub_layout.count() >= 4:
                        item.sub_layout.insertSpacing(item.sub_layout.count() - 1, 14)
                if title == "Servis Y\u00f6netimi" and self._last_active_page_id == 147:
                    item._reference_child_row_height = 45
                self.menu_layout.addWidget(item)
                self.accordion_groups.append(item)
                if title == "Servis Y\u00f6netimi" and self._current_sector() != "otomotiv":
                    item.expand()
                    item._active_stays_expanded = False
                    item._toggle_row.show()
                if title in {"Servis Y\u00f6netim Ayar\u0131", "Servis Ayarlar\u0131"} and self._current_sector() != "otomotiv":
                    item._title_lbl.setText("Servis Ayarlar\u0131")
                    item._title_lbl.setStyleSheet(theme_qss(
                        "background: transparent; color: @text_muted; font-size: 12px; "
                        "font-weight: 800; letter-spacing: 0.6px; border: none; margin: 0px; padding: 0px;"
                    ))
                if self._finance_navigation_mode and section_index > 0:
                    item._toggle_row.setFixedHeight(50)
                    item._toggle_row.layout().setContentsMargins(22, 0, 34, 0)
                    if item._title == "WhatsApp API Masas\u0131":
                        self.menu_layout.addSpacing(2)
            section_index += 1
        self.menu_layout.addSpacing(6)

    def _flat_button_style(self, active=False, disabled=False):
        if self._classic_mode():
            if disabled:
                return theme_qss("""
                    QPushButton {
                        background-color: @surface_alt;
                        color: @text_muted;
                        font-size: 13px;
                        font-weight: 700;
                        text-align: left;
                        padding: 0 16px;
                        border: 1px solid @border;
                        border-radius: 14px;
                        margin: 2px 12px;
                    }
                """)
            if active:
                return theme_qss("""
                    QPushButton {
                        background-color: @selection_bg;
                        color: @selection_text;
                        font-size: 13px;
                        font-weight: 800;
                        text-align: left;
                        padding: 0 16px;
                        border: 1px solid @accent;
                        border-left: 5px solid @accent;
                        border-radius: 14px;
                        margin: 2px 12px;
                    }
                    QPushButton:hover {
                        background-color: @surface_alt;
                        color: @text;
                    }
                """)
            return theme_qss("""
                QPushButton {
                    background-color: @surface;
                    color: @text;
                    font-size: 13px;
                    font-weight: 800;
                    text-align: left;
                    padding: 0 16px;
                    border: 1px solid @border;
                    border-radius: 14px;
                    margin: 2px 12px;
                }
                QPushButton:hover {
                    background-color: @surface_alt;
                    color: @text;
                    border-color: @accent;
                }
                QPushButton:pressed {
                    background-color: @selection_bg;
                }
            """)
        if disabled:
            return theme_qss("""
                QPushButton {
                    background-color: @surface;
                    color: @text_muted;
                    font-size: 13px;
                    font-weight: 700;
                    text-align: left;
                    padding: 0 16px;
                    border: 1px solid @border;
                    border-radius: 16px;
                    margin: 2px 12px;
                }
            """)
        if active:
            return theme_qss("""
                QPushButton {
                    background-color: @selection_bg;
                    color: @selection_text;
                    font-size: 13px;
                    font-weight: 800;
                    text-align: left;
                    padding: 0 16px;
                    border: 1px solid @accent;
                    border-left: 5px solid @accent;
                    border-radius: 16px;
                    margin: 2px 12px;
                }
            """)
        return theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text;
                font-size: 13px;
                font-weight: 800;
                text-align: left;
                padding: 0 16px;
                border: 1px solid @border;
                border-radius: 16px;
                margin: 2px 12px;
            }
            QPushButton:hover {
                background-color: @surface;
                border-color: @accent;
            }
            QPushButton:pressed {
                background-color: @surface;
            }
        """)

    def _render_flat_menu(self, sections, allowed_pages):
        self.flat_buttons = []
        for _, groups in sections:
            for title, icon, subs in groups:
                if not subs:
                    continue
                name, page_id = subs[0]
                label_icon = icon or PAGE_ICONS.get(int(page_id), "")
                text = f"{label_icon}  {name}" if label_icon else name
                btn = QPushButton(text)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedHeight(44)
                btn.setProperty("skipThemeTransform", False)
                btn.setStyleSheet(self._flat_button_style(False))
                btn.clicked.connect(lambda checked=False, pid=page_id: self.page_changed.emit(pid))
                if allowed_pages is not None and int(page_id) not in allowed_pages:
                    btn.setEnabled(False)
                    btn.setCursor(Qt.CursorShape.ForbiddenCursor)
                    btn.setStyleSheet(self._flat_button_style(False, True))
                self.menu_layout.addWidget(btn)
                self.flat_buttons.append((btn, page_id))
        self.menu_layout.addSpacing(6)

    def populate_menu(self):
        allowed_pages = self._get_allowed_pages()
        current_sector = self._current_sector()
        self.dash_btn = None
        if current_sector == "otomotiv":
            sections = self._build_menu_from_plugin(allowed_pages) or []
        elif self._einvoice_navigation_mode:
            sections = [
                ("SERV\u0130S OPERASYON", [("", "", [("Servis Y\u00f6netimi", 40), ("M\u00fc\u015fteri Hub", 21)])]),
                (("T\u0130CAR\u0130 & SATI\u015e"), [("", "", [("Proje Y\u00f6netimi", 200), ("Stok / Sipari\u015f", 50), ("Teklif Y\u00f6netimi", 150)])]),
                ("F\u0130NANS & MUHASEBE", [("", "", [("Finansal Dashboard", 100), ("Gelir / Gider", 101), ("Banka Hesaplar\u0131", 105), ("\u00c7ek / Senet", 106), ("Fatura Kes (E-Fatura)", 115)])]),
                ("Y\u00d6NET\u0130M", [("", "", [("Personel & \u0130K", 10), ("Sistem Yard\u0131mc\u0131lar\u0131", 130)])]),
            ]
        else:
            sections = self._build_technical_sections()
            if self._last_active_page_id not in {146, 147}:
                sections.extend(self._build_system_sections())
            if getattr(self, "_finance_navigation_mode", False):
                finance_index = next((
                    i for i, section in enumerate(sections)
                    if "finans" in str(section[0]).casefold().replace("\u0307", "")
                ), None)
                if finance_index is not None:
                    _, finance_groups = sections.pop(finance_index)
                    finance_groups = list(finance_groups)
                    group_title, group_icon, group_pages = finance_groups[0]
                    labels = {
                        100: "Finansal Dashboard",
                        101: "Gelir / Gider",
                        105: "Banka Hesaplar\u0131",
                        106: "\u00c7ek & Senet Takibi",
                        115: "Fatura & E-D\u00f6n\u00fc\u015f\u00fcm",
                    }
                    finance_groups[0] = (
                        group_title, group_icon,
                        [(labels.get(page_id, label), page_id) for label, page_id in group_pages],
                    )
                    finance_groups[0][2].insert(2, ("Krediler & Taksitler", 105))
                    sections = [
                        ("F\u0130NANS KONSOLU", finance_groups),
                        ("M\u00dc\u015eTER\u0130 & SERV\u0130S", [
                            ("Teknik Servis Hub", "\U0001f527", [
                                ("Servis Panosu", 41),
                                ("Servis Listesi", 42),
                                ("Durum Paneli", 43),
                                ("Teknisyen Paneli", 62),
                                ("Saha Haritas\u0131", 61),
                                ("Randevular", 30),
                                ("Lojistik & Garanti Y\u00f6netimi", 65),
                                ("\u0130\u015f/Servis Takibi Raporlar\u0131", 201),
                            ], 40),
                            ("Cari M\u00fc\u015fteriler", "\U0001f465", [
                                ("\u00c7al\u0131\u015fma Ortaklar\u0131", 26),
                                ("S\u00f6zle\u015fmeler", 25),
                                ("Hat\u0131rlat\u0131c\u0131lar", 90),
                                ("Duyurular", 120),
                            ], 21),
                            ("Stok & Sipari\u015f", "\U0001f4e6", [
                                ("Stok Lokasyonlar\u0131", 51),
                                ("Hizmet Tan\u0131mlar\u0131", 140),
                                ("Cihaz Bilgisi & Markalar", 145),
                                ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
                                ("Rapor C\u00fcmle Kal\u0131plar\u0131", 147),
                                ("Emanet (Konsinye) Cihazlar", 66),
                                ("Mobil Stok", 250),
                                ("PC Yap\u0131land\u0131r\u0131c\u0131", 300),
                                ("Projeler", 200),
                                ("Proje Ar\u015fivi", 202),
                                ("Teklif Olu\u015ftur", 150),
                                ("T\u00fcm Teklifler & Ge\u00e7mi\u015f", 313),
                                ("Teklif Analiz Raporlar\u0131", 314),
                            ], 50),
                        ]),
                        ("S\u0130STEM & ENTEGRASYON", [
                            ("WhatsApp API Masas\u0131", "\U0001f4ac", [
                                ("WhatsApp Ayarlar\u0131", 130),
                            ], 130),
                            ("Sistem Parametreleri", "\u2699", [
                                ("Genel Ayarlar", 130),
                                ("Log Kay\u0131tlar\u0131", 135),
                                ("Bilgi Bankas\u0131", 160),
                                ("Yedekleme Merkezi", 180),
                                ("Kullan\u0131m K\u0131lavuzu", 261),
                                ("Destek Merkezi", 70),
                                ("Personel", 10),
                            ]),
                        ]),
                    ]
        self.layout_editor_sections = sections
        sections = self._filter_sections_for_visibility(sections, allowed_pages)
        self._render_sections(sections, allowed_pages)

    def _get_allowed_pages(self):
        if not self.db:
            return None
        try:
            current_user = dict(getattr(self, "current_user", None) or {})
            role = str(current_user.get("role") or "")
            perms = current_user.get("permissions") or ""
            if is_admin_role(role):
                return None

            username = str(current_user.get("username") or "").strip()
            if not username and hasattr(self.db, "get_setting"):
                username = self.db.get_setting("last_login_user", "") or ""
            if not username:
                return None

            if not role or not perms:
                self.db.cursor.execute("SELECT role, permissions FROM users WHERE username=?", (username,))
                row = self.db.cursor.fetchone()
                if not row:
                    return None
                role = role or row['role'] or ""
                perms = perms or row['permissions'] or ""
            if is_admin_role(role):
                return None
            if not perms:
                return None

            data = json.loads(perms)
            if isinstance(data, dict) and data.get("mode") == "all":
                return None
            if isinstance(data, dict) and isinstance(data.get("pages"), list):
                pages = {int(x) for x in data.get("pages", [])}
                if not pages:
                    return None
                if 60 in pages:
                    pages.add(62)
                return pages
            if isinstance(data, list):
                pages = {int(x) for x in data}
                if not pages:
                    return None
                if 60 in pages:
                    pages.add(62)
                return pages
            return None
        except Exception:
            return None

    def enterEvent(self, event):
        if self.auto_collapse_enabled:
            self.expand_menu()
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.auto_collapse_enabled:
            self.collapse_menu()
        super().leaveEvent(event)

    def expand_menu(self):
        self._is_collapsed = False
        target_width = self.expanded_width_for_window()
        self._apply_collapsed_visual_state(False)
        parent = self.parentWidget()
        if parent and hasattr(parent, "_sync_width"):
            parent._sync_width(target_width)
        self.setMinimumWidth(target_width)
        self.setMaximumWidth(target_width)
        self.resize(target_width, self.height())
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(target_width)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.anim2 = QPropertyAnimation(self, b"minimumWidth")
        self.anim2.setDuration(200)
        self.anim2.setStartValue(self.width())
        self.anim2.setEndValue(target_width)
        self.anim2.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.anim.start()
        self.anim2.start()

    def collapse_menu(self):
        self._is_collapsed = True
        self._apply_collapsed_visual_state(True)
        parent = self.parentWidget()
        if parent and hasattr(parent, "_sync_width"):
            parent._sync_width(self.COLLAPSED_WIDTH)
        self.setMinimumWidth(self.COLLAPSED_WIDTH)
        self.setMaximumWidth(self.COLLAPSED_WIDTH)
        self.resize(self.COLLAPSED_WIDTH, self.height())
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(self.COLLAPSED_WIDTH)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.anim2 = QPropertyAnimation(self, b"minimumWidth")
        self.anim2.setDuration(200)
        self.anim2.setStartValue(self.width())
        self.anim2.setEndValue(self.COLLAPSED_WIDTH)
        self.anim2.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.anim.start()
        self.anim2.start()

    def set_collapsed(self, collapsed: bool, animate: bool = False):
        self._is_collapsed = bool(collapsed)
        target_width = self.COLLAPSED_WIDTH if collapsed else self.expanded_width_for_window()
        if animate:
            if collapsed:
                self.collapse_menu()
            else:
                self.expand_menu()
            return

        self.setMinimumWidth(target_width)
        self.setMaximumWidth(target_width)
        self.resize(target_width, self.height())
        self._apply_collapsed_visual_state(collapsed)
        parent = self.parentWidget()
        if parent and hasattr(parent, "_sync_width"):
            parent._sync_width(target_width)

    def _apply_collapsed_visual_state(self, collapsed: bool):
        collapsed = bool(collapsed)
        for widget_name in ("branding_title", "branding_subtitle", "branding_sector_badge"):
            widget = getattr(self, widget_name, None)
            if widget:
                widget.setVisible(not collapsed)
        for widget_name in ("scroll_area", "footer"):
            widget = getattr(self, widget_name, None)
            if widget:
                widget.setVisible(not collapsed and not (
                    widget_name == "footer" and hasattr(self, "_service_list_reference_footer")
                ))
        if hasattr(self, "header") and self.header:
            self.header.setFixedHeight(60 if collapsed else 126)
        if hasattr(self, "brand_layout") and self.brand_layout:
            self.brand_layout.setContentsMargins(8 if collapsed else 12, 6 if collapsed else 8, 8 if collapsed else 12, 6 if collapsed else 8)
            self.brand_layout.setSpacing(4 if collapsed else 8)
        if hasattr(self, "branding_logo") and self.branding_logo:
            self.branding_logo.setFixedSize(42 if collapsed else 52, 42 if collapsed else 52)
        if hasattr(self, "pin_button") and self.pin_button:
            self.pin_button.setFixedSize(26 if collapsed else 30, 26 if collapsed else 30)
        self.navigation_layout_changed.emit()

    @staticmethod
    def _logout_button_qss():
        return theme_qss("""
            QPushButton#LogoutButton {
                background-color: @surface;
                color: @danger;
                font-weight: 600;
                font-size: 13px;
                border: 1px solid @danger;
                border-radius: 8px;
                text-align: center;
                padding: 0 14px;
            }
            QPushButton#LogoutButton:hover { background-color: @surface_alt; }
            QPushButton#LogoutButton:pressed { background-color: @surface; }
        """)

    def create_footer(self):
        footer = QFrame(self)
        self.footer = footer
        footer.setStyleSheet(theme_qss(f"background-color: transparent; border-top: 1px solid {DesignTokens.BORDER_COLOR};"))
        footer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        footer.setFixedHeight(124)
        fl = QVBoxLayout(footer)
        fl.setContentsMargins(12, 10, 12, 10)
        fl.setSpacing(6)

        utility_card = QFrame()
        utility_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        utility_card.setStyleSheet("background: transparent; border: none;")
        utility_layout = QHBoxLayout(utility_card)
        self.footer_utility_layout = utility_layout
        utility_layout.setContentsMargins(4, 8, 4, 8)
        utility_layout.setSpacing(8)

        try:
            _ver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "version.txt")
            with open(_ver_path, "r") as _f:
                _ver = _f.read().strip()
            _ver_text = f"v{_ver} Premium"
        except Exception:
            _ver_text = "v2.0.0 Premium"
        self.footer_mode = QLabel("")
        self.footer_mode.setStyleSheet(theme_qss("""
            color: @text;
            background: transparent;
            border: none;
            padding: 0;
            font-size: 10px;
            font-weight: 800;
        """))
        utility_layout.addWidget(self.footer_mode)
        utility_layout.addSpacing(22)
        self.version_label = QLabel(_ver_text)
        self.version_label.setFixedSize(122, 32)
        self.version_label.setFont(QFont(ReferenceDesignTokens.MONO_FONT_NAME, 10))
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setStyleSheet(theme_qss("""
            color: @accent;
            background: @finance_surface_alt;
            border: 1px solid @finance_outline;
            border-radius: 6px;
            padding: 0 6px;
            font-size: 10px;
            font-weight: 500;
        """))
        utility_layout.addWidget(self.version_label)
        fl.addWidget(utility_card)

        self.logout_btn = QPushButton("Oturumu Kapat")
        self.logout_btn.setObjectName("LogoutButton")
        self.logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_btn.setFixedHeight(44)
        self.logout_btn.setStyleSheet(self._logout_button_qss())
        self.logout_btn.clicked.connect(self.switch_user)
        fl.addWidget(self.logout_btn)
        self.refresh_sector_badge()
        
        self.layout.addWidget(footer)

    def ensure_item_visible(self, item_widget):
        try:
            if not item_widget:
                return
            bar = self.scroll_area.verticalScrollBar()
            viewport = self.scroll_area.viewport()
            if bar is None or viewport is None:
                return

            top = item_widget.mapTo(self.menu_container, item_widget.rect().topLeft()).y()
            bottom = top + item_widget.height()
            current = bar.value()
            view_top = current
            view_bottom = current + viewport.height()

            if top < view_top + 8:
                bar.setValue(max(0, top - 12))
            elif bottom > view_bottom - 8:
                bar.setValue(max(0, bottom - viewport.height() + 16))
        except Exception:
            pass

    # Badge Sistemi
    def _build_btn_map(self):
        """Tüm accordion alt-butonlarını page_id'ye göre bir sözlükte toplar."""
        self._btn_map = {}
        self._badge_names = {}
        for btn, page_id in getattr(self, "flat_buttons", []):
            self._btn_map[page_id] = btn
            self._badge_names[page_id] = btn.text()
        for group in self.accordion_groups:
            if getattr(group, "main_page_id", None) is not None:
                self._btn_map[group.main_page_id] = group.toggle_btn
                self._badge_names[group.main_page_id] = group._title
            for btn, page_id in group.sub_buttons:
                self._btn_map[page_id] = btn
                self._badge_names[page_id] = btn.text()

    def set_badge(self, page_id, count):
        """Belirtilen sayfa butonuna sayaç etiketi ekler/kaldırır."""
        btn = self._btn_map.get(page_id)
        if btn is None:
            return
        if hasattr(btn, "_row") and hasattr(btn._row, "layout"):
            badge = getattr(btn, "_count_badge", None)
            if badge is None:
                badge = QLabel(btn._row)
                badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                badge.setFixedSize(30, 24)
                badge.setStyleSheet(theme_qss(
                    "QLabel { color: @selection_text; background: @accent; border: none; "
                    "border-radius: 7px; font-size: 11px; font-weight: 800; }"
                ))
                btn._row.layout().insertWidget(2, badge)
                btn._count_badge = badge
            badge.setText(str(count) if count > 0 else "")
            badge.setVisible(count > 0)
            return
        base = self._badge_names.get(page_id, btn.text())
        btn.setText(f"{base}  ({count})" if count > 0 else base)

    def refresh_badges(self):
        """DB'den bekleyen servis ve randevu sayılarını çekip badge günceller."""
        if not self.db:
            return
        try:
            from datetime import date
            # Bekleyen/aktif servisler (Tamamlandı veya İptal olmayan)
            self.db.cursor.execute(
                "SELECT COUNT(*) FROM devices WHERE status NOT IN ('Tamamlandı','İptal')"
            )
            row = self.db.cursor.fetchone()
            pending_services = row[0] if row else 0
        except Exception:
            pending_services = 0

        try:
            today = date.today().strftime("%Y-%m-%d")
            self.db.cursor.execute(
                "SELECT COUNT(*) FROM appointments WHERE date=? AND status != 'Tamamlandı'",
                (today,)
            )
            row = self.db.cursor.fetchone()
            today_appointments = row[0] if row else 0
        except Exception:
            today_appointments = 0

        try:
            rows = self.db.cursor.execute(
                """
                SELECT status, COUNT(*)
                FROM devices
                WHERE COALESCE(is_deleted, 0)=0
                  AND COALESCE(is_archived, 0)=0
                GROUP BY status
                """
            ).fetchall()
            pending_services = sum(
                int(row[1] or 0)
                for row in rows
                if is_active_device_status(row[0])
            )
        except Exception:
            pending_services = 0

        try:
            today = date.today().strftime("%Y-%m-%d")
            row = self.db.cursor.execute(
                """
                SELECT COUNT(*)
                FROM appointments
                WHERE date=?
                  AND COALESCE(status, '') NOT IN (?, ?, ?)
                """,
                (today, "Tamamland\u0131", "Iptal", "\u0130ptal"),
            ).fetchone()
            today_appointments = row[0] if row else 0
        except Exception:
            today_appointments = 0

        self.set_badge(43, pending_services)   # Durum Paneli
        self.set_badge(41, pending_services)   # Servis Panosu compatibility badge
        self.set_badge(30, today_appointments)  # Randevular
        try:
            customer_count = self.db.cursor.execute(
                "SELECT COUNT(*) FROM customers WHERE COALESCE(is_deleted, 0)=0 AND COALESCE(is_partner, 0)=0"
            ).fetchone()[0]
        except Exception:
            customer_count = 0
        self.set_badge(21, int(customer_count or 0))
    # Badge Sistemi Sonu

    def trigger_assistant(self):
        top_level = self.window()
        if hasattr(top_level, "toggle_voice_assistant"):
            top_level.toggle_voice_assistant()
        elif hasattr(top_level, "jarvis_worker") and hasattr(top_level.jarvis_worker, "show_assistant"):
            top_level.jarvis_worker.show_assistant()
        else:
            show_info(self, "Asistan aktif değil veya yüklenemedi.")

    def update_voice_assistant_visibility(self):
        """Update Voice Assistant button visibility based on settings"""
        if hasattr(self, 'voice_assistant_btn') and self.db:
            is_active = self.db.get_setting("voice_assistant_active", "0") == "1"
            self.voice_assistant_btn.setVisible(is_active)

    def switch_user(self):
        try:
            self.logout_requested.emit()
        except Exception:
            QApplication.exit(0)

    def on_page_changed_internal(self, page_id):
        previous_page_id = getattr(self, "_last_active_page_id", None)
        was_finance_navigation = bool(getattr(self, "_finance_navigation_mode", False))
        is_finance_navigation = False
        was_einvoice_navigation = bool(getattr(self, "_einvoice_navigation_mode", False))
        is_einvoice_navigation = False
        self._last_active_page_id = int(page_id)
        compact_sidebar = self.width() <= 220 and self.width() > self.COLLAPSED_WIDTH
        self._set_service_list_navigation(False)
        if hasattr(self, "header"):
            self.header.setVisible(True)
        if hasattr(self, "menu_layout"):
            self.menu_layout.setContentsMargins(0, 5, 4, 4)
        if hasattr(self, "header"):
            self.header.setFixedHeight(130 if compact_sidebar else 104)
            self.header_layout.setContentsMargins(15, 15, 15, 15)
        if was_finance_navigation != is_finance_navigation or was_einvoice_navigation != is_einvoice_navigation:
            self._finance_navigation_mode = is_finance_navigation
            self._einvoice_navigation_mode = is_einvoice_navigation
            self._set_finance_navigation_chrome(is_finance_navigation)
            self._set_einvoice_navigation_chrome(is_einvoice_navigation)
            self.refresh_menu()
            if not getattr(self, "_is_collapsed", False):
                width = self.expanded_width_for_window()
                self.setMinimumWidth(width)
                self.setMaximumWidth(width)
                parent = self.parentWidget()
                if parent is not None and hasattr(parent, "_sync_width"):
                    parent._sync_width(width)

        compact_density = bool(getattr(self, "_compact_density", False))
        nav_font_size = 9 if compact_density else 12
        parent_font_size = 10 if compact_density else 13
        # Reset Dashboard Button
        if getattr(self, "dash_btn", None):
            self.dash_btn.setProperty("skipThemeTransform", False)
            if page_id == 40:
                self.dash_btn.setStyleSheet(
                    theme_qss("""
                    QPushButton {
                        background-color: @selection_bg;
                        color: @selection_text;
                        font-size: 13px;
                        font-weight: 800;
                        text-align: left;
                        padding: 0 16px;
                        border: 1px solid @accent;
                        border-left: 5px solid @accent;
                        border-radius: 14px;
                        margin: 2px 12px 8px 12px;
                    }
                    QPushButton:hover { background-color: @surface_alt; color: @text; }
                    """)
                    if self._classic_mode()
                    else theme_qss("""
                        QPushButton {
                            background-color: @selection_bg;
                            color: @selection_text;
                            font-size: 13px;
                            font-weight: 800;
                            text-align: left;
                            padding: 0 16px;
                            border: 1px solid @accent;
                            border-radius: 16px;
                            margin: 2px 12px 8px 12px;
                        }
                    """)
                )
            else:
                self.dash_btn.setStyleSheet(
                    theme_qss("""
                    QPushButton {
                        background-color: @surface;
                        color: @text;
                        font-size: 13px;
                        font-weight: 800;
                        text-align: left;
                        padding: 0 16px;
                        border: 1px solid @border;
                        border-radius: 14px;
                        margin: 2px 12px 8px 12px;
                    }
                    QPushButton:hover {
                        background-color: @surface_alt;
                        color: @text;
                        border-color: @accent;
                    }
                    QPushButton:disabled {
                        color: @text_muted;
                        background-color: @surface_alt;
                    }
                    """)
                    if self._classic_mode()
                    else theme_qss("""
                        QPushButton {
                            background-color: @surface_alt;
                            color: @text;
                            font-size: 13px;
                            font-weight: 800;
                            text-align: left;
                            padding: 0 16px;
                            border: 1px solid @border;
                            border-radius: 16px;
                            margin: 2px 12px 8px 12px;
                        }
                        QPushButton:hover {
                            background-color: @surface;
                            border-color: @accent;
                        }
                        QPushButton:disabled {
                            color: @text_muted;
                            background-color: @surface_alt;
                        }
                    """)
                )
        
        for btn, pid in getattr(self, "flat_buttons", []):
            btn.setProperty("skipThemeTransform", False)
            is_active = pid == page_id
            if getattr(self, "_finance_navigation_mode", False) and int(page_id) == 105 and "Krediler" in btn.text():
                is_active = False
            style = (
                self._finance_navigation_button_style(is_active)
                if getattr(self, "_finance_navigation_mode", False)
                else self._flat_button_style(is_active, not btn.isEnabled())
            )
            btn.setStyleSheet(style)
            icon_kind = getattr(btn, "_navigation_kind", None)
            if icon_kind:
                btn.setIcon(navigation_icon(icon_kind, 18, "selection_text" if is_active else "text_muted"))

        # Highlight sub items
        service_page_context = {40, 41, 42, 43, 61, 62, 140, 145, 146, 147}
        for group in self.accordion_groups:
            if not hasattr(group, "_reference_title_original"):
                group._reference_title_original = group._title_lbl.text()
            group._title_lbl.setText(group._reference_title_original)
            main_active = getattr(group, "main_page_id", None) == page_id
            has_active = main_active or (
                group._title == "Servis Y\u00f6netimi" and page_id in service_page_context
            )
            for btn, pid in group.sub_buttons:
                is_active = (pid == page_id)
                btn.setStyleSheet(group._child_button_style(is_active, not btn.isEnabled()))
                if hasattr(btn, "_active_dot"):
                    btn._active_dot.setVisible(is_active)
                if hasattr(btn, "_icon_lbl"):
                    btn._icon_lbl.set_navigation_state(is_active, not btn.isEnabled())
                # Update child row background wrapper styling
                if hasattr(btn, "_row") and hasattr(group, "_child_row_qss"):
                    btn._row.setStyleSheet(group._child_row_qss(is_active))
                # Update child text label color
                if hasattr(btn, "_txt_lbl"):
                    if is_active:
                        btn._txt_lbl.setStyleSheet(theme_qss(
                            "background: transparent; color: {}; font-size: {}px; font-weight: 700;".format(
                                "@finance_breadcrumb_active", nav_font_size
                            )
                        ))
                    else:
                        btn._txt_lbl.setStyleSheet(theme_qss(
                            "background: transparent; color: @text_muted; font-size: {}px; font-weight: 500;".format(nav_font_size)
                        ))
                if is_active:
                    has_active = True

            if (has_active or main_active) and not group.is_expanded:
                if hasattr(group, "reveal_page"):
                    group.reveal_page(page_id)
                group.expand()
            elif (has_active or main_active) and hasattr(group, "reveal_page"):
                group.reveal_page(page_id)
            elif group.is_expanded and not getattr(group, "_active_stays_expanded", False):
                group.collapse()

            # Highlight parent toggle if active
            if hasattr(group, "_icon_lbl"):
                group._icon_lbl.set_navigation_state(has_active, not group.toggle_btn.isEnabled())
            if main_active:
                group._toggle_row.setStyleSheet(theme_qss(
                    "QWidget#ToggleRowContainer { background-color: @accent; "
                    "border: none; border-radius: 8px; margin: 0px 8px; }"
                ))
                group._title_lbl.setStyleSheet(theme_qss(
                    "background: transparent; color: @selection_text; "
                    "font-size: {}px; font-weight: 700; border: none;".format(parent_font_size)
                ))
                group._icon_lbl.set_navigation_state(True, False)
            elif has_active:
                if compact_density:
                    group.setStyleSheet("")
                if hasattr(group, "_toggle_row") and hasattr(group, "_row_qss"):
                    group._toggle_row.setStyleSheet(
                        group._row_qss(not compact_density)
                    )
                    group._title_lbl.setStyleSheet(theme_qss(
                        "background: transparent; color: {}; font-size: {}px; "
                        "font-weight: 600; border: none;".format(
                            "@text", parent_font_size
                        )
                    ))
                else:
                    group.toggle_btn.setStyleSheet(group._parent_button_style(True))
            else:
                if hasattr(group, "_toggle_row") and hasattr(group, "_row_qss"):
                    group._toggle_row.setStyleSheet(group._row_qss(False))
                    group._title_lbl.setStyleSheet(theme_qss(
                        "background: transparent; color: @text; font-size: {}px; "
                        "font-weight: 600; border: none;".format(parent_font_size)
                    ))
                else:
                    group.toggle_btn.setStyleSheet(group._parent_button_style(False))

    def _set_service_list_navigation(self, enabled):
        if enabled and not hasattr(self, "_service_list_reference_widget"):
            self.scroll_area.setFixedHeight(686)
            self.footer.hide()
            reference_footer = QFrame(self)
            reference_footer.setFixedHeight(66)
            reference_footer.setStyleSheet(theme_qss(
                "QFrame { background: @surface; border: 0; border-top: 1px solid @border; }"
            ))
            footer_layout = QVBoxLayout(reference_footer)
            footer_layout.setContentsMargins(8, 5, 8, 5)
            footer_layout.setSpacing(3)
            status_row = QHBoxLayout()
            status_row.setContentsMargins(0, 0, 0, 0)
            status = QLabel("\u25cf  Bulut E\u015fitleme", reference_footer)
            status.setStyleSheet(theme_qss(
                "color: @text_muted; border: 0; font-size: 9px; font-family: 'JetBrains Mono';"
            ))
            status_row.addWidget(status)
            status_row.addStretch()
            version = QLabel("v4.2.1-TR", reference_footer)
            version.setStyleSheet(theme_qss(
                "color: @text_muted; border: 0; font-size: 9px; font-family: 'JetBrains Mono';"
            ))
            status_row.addWidget(version)
            footer_layout.addLayout(status_row)
            account_row = QHBoxLayout()
            account_row.setContentsMargins(0, 0, 0, 0)
            account_row.setSpacing(5)
            avatar = QLabel("\u263a", reference_footer)
            avatar.setFixedSize(26, 26)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet(theme_qss(
                "background: @electric_blue; color: @selection_text; border: 0; border-radius: 13px;"
            ))
            account_row.addWidget(avatar)
            username = str(self.current_user.get("username") or "Kullanici")
            account = QLabel(f"{username}\nKidemli Teknisyen", reference_footer)
            account.setStyleSheet(theme_qss(
                "color: @text; border: 0; font-size: 9px; line-height: 13px;"
            ))
            account_row.addWidget(account, 1)
            logout = QPushButton("\u21aa", reference_footer)
            logout.setToolTip("Oturumu Kapat")
            logout.setFixedSize(23, 23)
            logout.setStyleSheet(theme_qss(
                "QPushButton { color: @text_muted; background: transparent; border: 0; font-size: 16px; }"
            ))
            logout.clicked.connect(self.switch_user)
            account_row.addWidget(logout)
            footer_layout.addLayout(account_row)
            self.layout.addWidget(reference_footer)
            self._service_list_reference_footer = reference_footer
            self.layout.addStretch(1)
            original_widgets = []
            for index in range(self.menu_layout.count()):
                widget = self.menu_layout.itemAt(index).widget()
                if widget is not None:
                    original_widgets.append((widget, not widget.isHidden()))
                    widget.hide()
            self._service_list_original_menu = original_widgets
            panel = QWidget(self)
            panel.setObjectName("ServiceListReferenceNavigation")
            layout = QVBoxLayout(panel)
            layout.setContentsMargins(8, 2, 8, 0)
            layout.setSpacing(3)
            section = QLabel("\u0130\u015eLEMLER", panel)
            section.setStyleSheet(theme_qss(
                "color: @text_muted; font-size: 9px; font-weight: 800; "
                "letter-spacing: 1px; padding: 0 5px;"
            ))
            layout.addWidget(section)
            entries = (
                ("Servis Listesi", 42),
                ("Cihaz Y\u00f6netimi", 43),
                ("M\u00fc\u015fteri Rehberi", 21),
                ("Yedek Par\u00e7a & Stok", 50),
                ("Kargo & Lojistik", 65),
                ("Muhasebe & Faturalar", 101),
                ("Raporlar", 201),
                ("Sistem Ayarlar\u0131", 130),
            )
            self._service_list_reference_buttons = {}
            for label, page_id in entries:
                button = QPushButton(label.replace("&", "&&"), panel)
                button.setCursor(Qt.CursorShape.PointingHandCursor)
                button.setFixedHeight(30)
                icon_kind = PAGE_KINDS.get(page_id)
                if icon_kind:
                    button.setIcon(navigation_icon(
                        icon_kind, 16,
                        "selection_text" if page_id == 42 else "text_muted",
                    ))
                button.setStyleSheet(theme_qss(
                    "QPushButton { text-align: left; color: @text; background: transparent; "
                    "border: 0; border-radius: 6px; padding: 0 8px; font-size: 11px; font-weight: 500; } "
                    "QPushButton:hover { background: @surface_high; }"
                ))
                button.clicked.connect(lambda checked=False, target=page_id: self.page_changed.emit(target))
                layout.addWidget(button)
                self._service_list_reference_buttons[page_id] = button
            self.menu_layout.insertWidget(0, panel)
            self._service_list_reference_widget = panel
        elif not enabled and hasattr(self, "_service_list_reference_widget"):
            stretch = self.layout.takeAt(self.layout.count() - 1)
            del stretch
            reference_footer = self._service_list_reference_footer
            self.layout.removeWidget(reference_footer)
            reference_footer.deleteLater()
            del self._service_list_reference_footer
            self.scroll_area.setMinimumHeight(0)
            self.scroll_area.setMaximumHeight(16777215)
            self.footer.show()
            panel = self._service_list_reference_widget
            self.menu_layout.removeWidget(panel)
            panel.deleteLater()
            del self._service_list_reference_widget
            for widget, was_visible in getattr(self, "_service_list_original_menu", []):
                widget.setVisible(was_visible)
            self._service_list_original_menu = []
            self._service_list_reference_buttons = {}
        if enabled:
            for page_id, button in self._service_list_reference_buttons.items():
                active = page_id == self._last_active_page_id
                button.setIcon(navigation_icon(
                    PAGE_KINDS.get(page_id, "settings"), 16,
                    "selection_text" if active else "text_muted",
                ))
                button.setStyleSheet(theme_qss(
                    "QPushButton { text-align: left; color: @selection_text; background: @accent; "
                    "border: 0; border-radius: 6px; padding: 0 8px; font-size: 11px; font-weight: 700; }"
                    if active else
                    "QPushButton { text-align: left; color: @text; background: transparent; "
                    "border: 0; border-radius: 6px; padding: 0 8px; font-size: 11px; font-weight: 500; } "
                    "QPushButton:hover { background: @surface_high; }"
                ))
    def _apply_product_group_reference_items(self, page_id):
        service_group = next(
            (
                group for group in self.accordion_groups
                if any(int(target) == 40 for _button, target in group.sub_buttons)
            ),
            None,
        )
        if service_group is None:
            return
        reference_items = (
            ("Randevular", 30),
            ("Lojistik & Garanti Y\u00f6netimi", 65),
            ("\u0130\u015f/Servis Takibi Raporlar\u0131", 201),
        )
        existing = {int(target) for _button, target in service_group.sub_buttons}
        for label, target in reference_items:
            if target in existing:
                continue
            service_group._add_page_row(label, target, service_group.sub_layout)
            button, _page_id = service_group.sub_buttons[-1]
            button._reference_product_group_item = True
            if hasattr(button, "_row"):
                button._row.setVisible(page_id == 146)
            if page_id == 146 and getattr(self, "_compact_density", False):
                button._row.setFixedHeight(23)
        for button, target in service_group.sub_buttons:
            if not getattr(button, "_reference_product_group_item", False):
                continue
            visible = page_id == 146
            if hasattr(button, "_row"):
                button._row.setVisible(visible)
            if visible and getattr(self, "_compact_density", False):
                button._row.setFixedHeight(23)
        service_group.sub_layout.invalidate()
        service_group.updateGeometry()

    def refresh_theme(self):
        """Refresh colors without rebuilding menu widgets."""
        ThemeManager.refresh_widget_tree(self)
        if self._icon_only:
            self._apply_icon_only_visual_state()
            try:
                self.on_page_changed_internal(self._last_active_page_id)
            except Exception:
                pass
            return
        parent = self.parentWidget()
        current_width = int(parent.width() if parent else self.width() or self.EXPANDED_WIDTH)
        target_width = self.COLLAPSED_WIDTH if self._is_collapsed or current_width <= 100 else self.EXPANDED_WIDTH

        try:
            if hasattr(self, "_last_active_page_id"):
                self.on_page_changed_internal(self._last_active_page_id)
        except Exception:
            pass
        try:
            self.set_collapsed(target_width == self.COLLAPSED_WIDTH, animate=False)
        except Exception:
            pass

        try:
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        except Exception:
            pass

        if _is_classic_appearance():
            try:
                self.setStyleSheet(theme_qss("""
                    QWidget#SideMenu {
                        background: @window;
                        border-right: 1px solid @border;
                        color: @text;
                    }
                """))
                if hasattr(self, "header") and self.header:
                    self.header.setStyleSheet(theme_qss("background: @window; border-bottom: 1px solid @border;"))
                if hasattr(self, "footer") and self.footer:
                    self.footer.setStyleSheet(theme_qss("background: @window; border-top: 1px solid @border;"))
                if hasattr(self, "scroll_area") and self.scroll_area:
                    self.scroll_area.setStyleSheet(theme_qss("""
                        QScrollArea#SideMenuScroll { background-color: transparent; border: none; }
                        QScrollArea#SideMenuScroll::viewport { background-color: transparent; border: none; }
                        QWidget#SideMenuViewport { background-color: transparent; border: none; }
                        QScrollBar:vertical {
                            border: none;
                            background: @surface_alt;
                            width: 8px;
                            margin: 0px;
                        }
                        QScrollBar::handle:vertical {
                            background: @border;
                            min-height: 20px;
                            border-radius: 3px;
                        }
                        QScrollBar::handle:vertical:hover { background: @accent; }
                        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
                        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background-color: transparent; }
                    """))
                if hasattr(self, "menu_container") and self.menu_container:
                    self.menu_container.setStyleSheet(theme_qss("background-color: transparent; color: @text;"))
                if hasattr(self, "logout_btn") and self.logout_btn:
                    self.logout_btn.setStyleSheet(self._logout_button_qss())
            except Exception:
                pass
            self.repaint()
            return

        # Then re-apply base shells
        try:
            self.setStyleSheet(theme_qss(f"""
                QWidget#SideMenu {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 @window,
                        stop:0.28 @window,
                        stop:0.72 @surface,
                        stop:1 @surface);
                    border-right: 1px solid {DesignTokens.BORDER_COLOR};
                }}
            """))
        except Exception:
            pass
        try:
            if hasattr(self, "header") and self.header:
                self.header.setStyleSheet(theme_qss(f"background-color: {DesignTokens.HEADER_BG}; border-bottom: 1px solid {DesignTokens.BORDER_COLOR};"))
        except Exception:
            pass
        try:
            if hasattr(self, "footer") and self.footer:
                self.footer.setStyleSheet(theme_qss(f"background-color: {DesignTokens.HEADER_BG}; border-top: 1px solid {DesignTokens.BORDER_COLOR};"))
        except Exception:
            pass
        try:
            if hasattr(self, "branding_logo") and self.branding_logo:
                self.branding_logo.setStyleSheet(theme_qss("""
                    color: @text;
                    font-size: 15px;
                    font-weight: 900;
                    background-color: @surface;
                    border: 1px solid @border;
                    border-radius: 14px;
                """))
            if hasattr(self, "branding_title") and self.branding_title:
                self.branding_title.setStyleSheet(self._branding_text_qss(True))
            if hasattr(self, "branding_subtitle") and self.branding_subtitle:
                self.branding_subtitle.setStyleSheet(self._branding_text_qss(False))
            self.refresh_sector_badge()
        except Exception:
            pass
        try:
            if hasattr(self, "scroll_area") and self.scroll_area:
                self.scroll_area.setStyleSheet(theme_qss(f"""
                    QScrollArea#SideMenuScroll {{ background-color: transparent; border: none; }}
                    QScrollArea#SideMenuScroll::viewport {{ background-color: transparent; border: none; }}
                    QWidget#SideMenuViewport {{ background-color: transparent; border: none; }}
                    QScrollBar:vertical {{
                        border: none;
                        background: {DesignTokens.SIDEBAR_BG};
                        width: 8px;
                        margin: 0px;
                    }}
                    QScrollBar::handle:vertical {{
                        background: {DesignTokens.BORDER_COLOR};
                        min-height: 20px;
                        border-radius: 4px;
                    }}
                    QScrollBar::handle:vertical:hover {{
                        background: {DesignTokens.SUBTEXT_COLOR};
                    }}
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background-color: transparent; }}
                """))
        except Exception:
            pass
        try:
            if hasattr(self, "menu_container") and self.menu_container:
                self.menu_container.setStyleSheet(theme_qss("background-color: transparent;"))
        except Exception:
            pass
        try:
            if hasattr(self, "logout_btn") and self.logout_btn:
                self.logout_btn.setStyleSheet(self._logout_button_qss())
        except Exception:
            pass
        self.repaint()

    def _build_system_sections(self):
        return [(
            "SİSTEM",
            [(
                "Sistem Yardımcıları",
                "⚙️",
                [
                    ("Ayarlar", 130),
                    ("Yedekleme", 180),
                    ("Log Kayıtları", 135),
                    ("Bilgi Bankası", 160),
                    ("Kullanım Kılavuzu", 261),
                    ("Destek", 70),
                ],
            )],
        )]

    def _build_technical_sections(self):
        if getattr(self, "_last_active_page_id", None) == 147:
            return [
                ("SERVIS OPERASYON", [
                    ("Servis Y\u00f6netimi", "\\U0001f527", [
                        ("Genel Bak\u0131\u015f", 40), ("Servis Panosu", 41),
                        ("Servis Listesi", 42), ("Teknisyen Paneli", 62),
                    ]),
                ]),
                ("SERVIS Y\u00d6NETIM AYARI", [
                    ("Servis Y\u00f6netim Ayar\u0131", "\\u2699", [
                        ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
                        ("Marka Adlar\u0131 Y\u00f6netimi", 145),
                        ("Rapor C\u00fcmle Kal\u0131plar\u0131", 147),
                        ("\u0130\u015f\u00e7ilik & Fiyat Kalemleri", 140),
                    ]),
                ]),
                ("MOD\u00dcLLER", [
                    ("M\u00fc\u015fteri Hub", "\U0001f465", [("M\u00fc\u015fteri Listesi", 21), ("\u00c7al\u0131\u015fma Ortaklar\u0131", 26)]),
                    ("Stok & Yedek Par\u00e7a", "\U0001f4e6", [("Stok / Sipari\u015f", 50), ("Yedek Par\u00e7a", 60), ("Emanet Cihazlar", 66)]),
                ]),
            ]
        if getattr(self, "_legacy_product_group_reference_navigation", False):
            return [
                ("SERVIS OPERASYON", [
                    ("Servis Y\u00f6netimi", "\U0001f527", [
                        ("Genel Bak\u0131\u015f", 40),
                        ("Servis Panosu", 41),
                        ("Servis Listesi", 42),
                        ("Durum Paneli", 43),
                        ("Teknisyen Paneli", 62),
                        ("Saha Haritas\u0131", 61),
                        ("Di\u011fer Servis \u0130\u015flemleri", [
                            ("Randevular", 30),
                            ("Lojistik & Garanti", 65),
                            ("\u0130\u015f / Servis Raporlar\u0131", 201),
                        ]),
                    ]),
                    ("Servis Y\u00f6netim Ayar\u0131", "\u2699", [
                        ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
                        ("Marka Adlar\u0131 Y\u00f6netimi", 145),
                        ("Rapor C\u00fcmle Kal\u0131plar\u0131", 147),
                    ]),
                ]),
                ("T\u0130CAR\u0130 & M\u00dc\u015eTER\u0130", [
                    ("M\u00fc\u015fteri Hub", "\U0001f465", [("\u00c7al\u0131\u015fma Ortaklar\u0131", 26), ("M\u00fc\u015fteri Listesi", 21)]),
                    ("Proje Y\u00f6netimi", "\U0001f4ca", [("Projeler", 200), ("Proje Ar\u015fivi", 202)]),
                    ("Stok / Sipari\u015f", "\U0001f4e6", [("Stok Y\u00f6netimi", 50), ("Yedek Par\u00e7a", 60)]),
                    ("Teklif Olu\u015ftur", "\U0001f4c4", [("Teklif Olu\u015ftur", 150), ("T\u00fcm Teklifler", 313)]),
                ]),
            ]
        return [
            ("SERVIS OPERASYON", [
                ("Servis Y\u00f6netimi", "\U0001f527", [
                    ("Genel Bak\u0131\u015f", 40),
                    ("Servis Panosu", 41),
                    ("Servis Listesi", 42),
                    ("Durum Paneli", 43),
                    ("Teknisyen Paneli", 62),
                    ("Saha Haritas\u0131", 61),
                    ("Di\u011fer Servis \u0130\u015flemleri", [
                        ("Randevular", 30),
                        ("Lojistik & Garanti Y\u00f6netimi", 65),
                        ("\u0130\u015f/Servis Takibi Raporlar\u0131", 201),
                        ("AI Asistan", 170),
                    ]),
                ]),
                (
                    "Servis Y\u00f6netim Ayar\u0131",
                    "\u2699",
                    [
                        ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
                        ("Marka Adlar\u0131 Y\u00f6netimi", 145),
                        ("Rapor C\u00fcmle Kal\u0131plar\u0131", 147),
                        ("\u0130\u015f\u00e7ilik & Fiyat Y\u00f6netimi", 140),
                    ],
                ),
            ]),
            ("MÜŞTERİ", [
                ("Müşteri Hub", "👥", [
                    ("Çalışma Ortakları", 26),
                    ("Müşteri Listesi", 21),
                    ("Sözleşmeler", 25),
                    ("Hatırlatıcılar", 90),
                    ("Duyurular", 120),
                ]),
            ]),
            ("TİCARİ", [
                ("Proje Yönetimi", "📊", [
                    ("Projeler", 200),
                    ("Proje Arşivi", 202),
                ]),
                ("Stok ve Satış", "📦", [
                    ("Stok Yönetimi", 50),
                    ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
                    ("Cihaz Bilgisi & Markaları", 145),
                    ("Emanet (Konsinye) Cihazlar", 66),
                    ("Depo ve Ara\u00e7 Stoklar\u0131", 51),
                    ("Mobil Stok", 250),
                    ("PC Builder", 300),
                ]),
            ]),
            ("FİNANS", [
                ("Finans", "💸", [
                    ("Finansal Dashboard", 100),
                    ("Gelir / Gider", 101),
                    ("Banka Hesapları", 105),
                    ("Çek / Senet", 106),
                    ("Fatura Kes (E-Fatura)", 115),
                ]),
            ]),
            ("İK VE PERSONEL", [
                ("Personel", "👤", [
                    ("Personel", 10),
                ]),
            ]),
        ]

    _build_technical_sections_base = _build_technical_sections

    def _set_finance_navigation_chrome(self, enabled):
        enabled = bool(enabled)
        self.brand_card.setVisible(not enabled)
        self.nav_search_input.setVisible(enabled)
        self.header.setFixedHeight(64 if enabled else 104)
        self.header_layout.setContentsMargins(18, 15, 18, 11) if enabled else self.header_layout.setContentsMargins(15, 14, 15, 14)
        self.menu_layout.setContentsMargins(0, 6 if enabled else 15, 0, 4)
        if hasattr(self, "footer"):
            self.footer.setFixedHeight(84 if enabled else 124)
        if hasattr(self, "logout_btn"):
            self.logout_btn.setFixedHeight(44)
        if hasattr(self, "footer_mode"):
            self.footer_mode.setText("Lisans S\u00fcr\u00fcm\u00fc" if enabled else self._current_sector().title())
            self.footer_mode.setStyleSheet(theme_qss(
                "QLabel { color: @text_muted; background: transparent; border: none; padding: 0; "
                "font-size: 12px; font-weight: 400; }"
            ) if enabled else theme_qss(
                "QLabel { color: @text; background: transparent; border: none; padding: 0; "
                "font-size: 10px; font-weight: 800; }"
            ))
        if hasattr(self, "version_label"):
            self.version_label.setStyleSheet(theme_qss(
                "QLabel { color: @accent; background: @finance_surface_alt; border: 1px solid @finance_outline; "
                "border-radius: 6px; padding: 0 6px; font-size: 10px; font-weight: 500; }"
            ))

    def _set_einvoice_navigation_chrome(self, enabled):
        if not hasattr(self, "brand_card"):
            return
        if enabled:
            if not hasattr(self, "_einvoice_brand_original"):
                self._einvoice_brand_original = (
                    self.branding_title.text(), self.branding_subtitle.text(),
                    self.branding_logo.pixmap(), self.branding_logo.text(),
                )
            company_name = "Aslan Computer"
            try:
                company_name = str(self.db.get_setting("company_name", company_name) or company_name)
            except Exception:
                pass
            self.brand_card.show()
            self.brand_card.setFixedHeight(67)
            self.brand_card.setStyleSheet(theme_qss(
                "QFrame#SideMenuBrandCard { background: @finance_surface; "
                "border: 1px solid @finance_outline; border-radius: 12px; }"
            ))
            self.nav_search_input.hide()
            self.header.setFixedHeight(68)
            self.header_layout.setContentsMargins(10, 0, 10, 0)
            self.brand_layout.setContentsMargins(8, 4, 8, 4)
            self.brand_layout.setSpacing(8)
            self.branding_logo.setPixmap(QPixmap())
            self.branding_logo.setText("\u25c8")
            self.branding_logo.setFixedSize(36, 36)
            self.branding_logo.setStyleSheet(theme_qss(
                "color: @accent; background: @finance_active_bg; border: 1px solid @finance_outline; "
                "border-radius: 10px; font-size: 18px; font-weight: 800;"
            ))
            self.branding_title.setText(company_name)
            self.branding_title.setStyleSheet(theme_qss(
                "color: @text; font-size: 12px; font-weight: 700;"
            ))
            self.branding_subtitle.setText("Online Hub")
            self.branding_subtitle.setStyleSheet(theme_qss(
                "color: @text_muted; font-size: 10px; font-weight: 400;"
            ))
            self.branding_sector_badge.hide()
            self.pin_button.hide()
            self.footer.setFixedHeight(112)
        else:
            self.brand_card.setFixedHeight(0 if self._finance_navigation_mode else 100)
            self.brand_card.setVisible(not self._finance_navigation_mode)
            self.nav_search_input.setVisible(self._finance_navigation_mode)
            self.header.setFixedHeight(64 if self._finance_navigation_mode else 104)
            self.header_layout.setContentsMargins(*(
                (18, 15, 18, 11) if self._finance_navigation_mode else (15, 14, 15, 14)
            ))
            self.brand_layout.setContentsMargins(8, 8, 8, 8)
            self.brand_layout.setSpacing(8)
            if hasattr(self, "_einvoice_brand_original"):
                title, subtitle, logo, logo_text = self._einvoice_brand_original
                self.branding_title.setText(title)
                self.branding_subtitle.setText(subtitle)
                self.branding_logo.setPixmap(logo)
                self.branding_logo.setText(logo_text)
                self.branding_logo.setFixedSize(44, 44)
                self.branding_sector_badge.setVisible(not self._finance_navigation_mode)
                self.pin_button.setVisible(not self._finance_navigation_mode)
            self.footer.setFixedHeight(84 if self._finance_navigation_mode else 124)

    def _finance_navigation_button_style(self, active=False):
        if active:
            return theme_qss(
                "QPushButton { background: @accent; color: @selection_text; border: 1px solid @accent; "
                "border-radius: 8px; text-align: left; padding: 0 16px; "
                "margin: 1px 10px; font-size: 13px; font-weight: 700; }"
            )
        return theme_qss(
            "QPushButton { background: transparent; color: @text_muted; border: 1px solid transparent; "
            "border-radius: 7px; text-align: left; padding: 0 16px; margin: 1px 10px; font-size: 13px; } "
            "QPushButton:hover { background: @surface_alt; color: @text; border-color: @border; }"
        )

    def _filter_navigation(self, query):
        value = str(query or "").strip().casefold()
        for group in self.accordion_groups:
            parent_match = value in group._title.casefold()
            visible_children = 0
            for button, _page_id in group.sub_buttons:
                visible = not value or parent_match or value in button.text().casefold()
                button.setVisible(visible)
                visible_children += int(visible)
            group.setVisible(not value or parent_match or visible_children > 0)
        for button, _page_id in self.flat_buttons:
            button.setVisible(not value or value in button.text().casefold())
        self.menu_layout.invalidate()

    def _build_technical_sections(self):
        if getattr(self, "_legacy_product_group_reference_navigation", False):
            return [
                ("SERVIS OPERASYON", [
                    ("Servis Y\u00f6netimi", "\U0001f527", [
                        ("Genel Bak\u0131\u015f", 40), ("Servis Panosu", 41),
                        ("Servis Listesi", 42), ("Durum Paneli", 43),
                        ("Teknisyen Paneli", 62), ("Saha Haritas\u0131", 61),
                    ]),
                    ("Servis Y\u00f6netim Ayar\u0131", "\u2699", [
                        ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
                        ("Marka Adlar\u0131 Y\u00f6netimi", 145),
                        ("Rapor C\u00fcmle Kal\u0131plar\u0131", 147),
                    ]),
                ]),
                ("T\u0130CAR\u0130 & M\u00dc\u015eTER\u0130", [
                    ("M\u00fc\u015fteri Hub", "\U0001f465", [("\u00c7al\u0131\u015fma Ortaklar\u0131", 26), ("M\u00fc\u015fteri Listesi", 21)]),
                    ("Proje Y\u00f6netimi", "\U0001f4ca", [("Projeler", 200), ("Proje Ar\u015fivi", 202)]),
                    ("Stok / Sipari\u015f", "\U0001f4e6", [("Stok Y\u00f6netimi", 50), ("Yedek Par\u00e7a", 60)]),
                    ("Teklif Olu\u015ftur", "\U0001f4c4", [("Teklif Olu\u015ftur", 150), ("T\u00fcm Teklifler", 313)]),
                ]),
            ]
        sections = self._build_technical_sections_base()
        managed_page_ids = {140, 145, 146, 147}
        labor_price_item = ("\u0130\u015f\u00e7ilik & Fiyat Y\u00f6netimi", 140)
        offers_group = (
            "Teklif Olu\u015ftur",
            "\U0001f4c4",
            [
                ("T\u00fcm Teklifler & Ge\u00e7mi\u015f", 313),
                ("Teklif Analiz Raporlar\u0131", 314),
            ],
            150,
        )
        additional_service_items = None
        normalized_sections = []
        for section_name, groups in sections:
            normalized_groups = []
            for group_title, icon, items in groups:
                if group_title == "Servis Y\u00f6netimi":
                    expanded_items = []
                    for item in items:
                        if isinstance(item[1], (list, tuple)) and item[0] == "Di\u011fer Servis \u0130\u015flemleri":
                            expanded_items.extend(
                                ("Kargo & Lojistik" if int(target) == 65 else label, target)
                                for label, target in item[1]
                            )
                        else:
                            expanded_items.append(item)
                    items = expanded_items
                page_ids = {
                    int(item[1]) for item in items
                    if not isinstance(item[1], (list, tuple))
                }
                if {140, 145, 146}.issubset(page_ids) and 50 not in page_ids:
                    items = [
                        item for item in items
                        if isinstance(item[1], (list, tuple)) or int(item[1]) in {145, 146, 147}
                    ]
                items = [
                    item for item in items
                    if isinstance(item[1], (list, tuple)) or int(item[1]) != 170
                ]
                retained_items = []
                for item in items:
                    if isinstance(item[1], (list, tuple)) and item[0] == "Di\u011fer Servis \u0130\u015flemleri":
                        additional_service_items = item
                    else:
                        retained_items.append(item)
                items = retained_items
                has_service_management = 40 in page_ids
                if has_service_management:
                    group_title = "Servis Y\u00f6netimi"
                if 50 in page_ids:
                    items = [
                        item for item in items
                        if isinstance(item[1], (list, tuple))
                        or int(item[1]) not in managed_page_ids | {150}
                    ]
                    items.append(labor_price_item)
                    group_title = "Stok / Sipari\u015f"
                if section_name == "SISTEM" and group_title == "Sistem Yard\u0131mc\u0131lar\u0131" and additional_service_items:
                    items.append(additional_service_items)
                normalized_groups.append((group_title, icon, items))
                if 50 in page_ids:
                    normalized_groups.append(offers_group)
            normalized_sections.append((section_name, normalized_groups))
        customer_groups = []
        for section_name, groups in normalized_sections:
            if section_name == "M\u00dc\u015eTER\u0130":
                customer_groups = groups
        result = []
        for section_name, groups in normalized_sections:
            if section_name == "M\u00dc\u015eTER\u0130":
                continue
            if section_name == "SERVIS OPERASYON":
                groups.extend(customer_groups)
            elif section_name == "T\u0130CAR\u0130":
                section_name = "T\u0130CAR\u0130 & SATI\u015e"
            elif section_name == "F\u0130NANS":
                section_name = "F\u0130NANS & MUHASEBE"
            elif section_name == "\u0130K VE PERSONEL":
                section_name = "Y\u00d6NET\u0130M"
            result.append((section_name, groups))
        return result

