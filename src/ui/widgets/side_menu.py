# -*- coding: utf-8 -*-
# side_menu.py - Ana SideMenu sınıfı

import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QScrollArea, QSizePolicy, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtGui import QIcon, QFont, QColor, QCursor, QPixmap

from src.utils.theme_colors import theme_qss, tc
from src.utils.theme_manager import ThemeManager
from src.utils.language_manager import LanguageManager
from src.utils.system_config import SystemConfig
from src.utils.role_utils import is_admin_role
from src.utils.page_config import PAGE_MAPPING
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.status_utils import is_active_device_status
from src.utils.toast_notification import show_info

from ._side_menu_constants import (
    _is_classic_appearance, PAGE_ICONS, DesignTokens
)
from ._side_menu_accordion import AccordionItem


class SideMenu(QWidget):
    page_changed = pyqtSignal(int)
    logout_requested = pyqtSignal()
    pin_changed = pyqtSignal(bool)
    EXPANDED_WIDTH = 272
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
        
        if callback:
            self.page_changed.connect(callback)
            
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
        self.menu_layout.setContentsMargins(0, 6, 0, 4)
        self.menu_layout.setSpacing(0)
        self.menu_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.menu_container)
        self.layout.addWidget(self.scroll_area)
        
        self.accordion_groups = []
        self.flat_buttons = []
        self._last_active_page_id = 40
        self.lang = LanguageManager(self.db)
        self.populate_menu()
        
        # Footer
        self.create_footer()
        
        self.page_changed.connect(self.on_page_changed_internal)
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

    def _load_pin_state(self):
        try:
            if self.db and hasattr(self.db, "get_setting"):
                return self.db.get_setting("side_menu_pinned", "1") == "1"
        except Exception:
            pass
        return True

    def _load_menu_label_mode(self):
        try:
            if self.db and hasattr(self.db, "get_setting"):
                return self.db.get_setting("side_menu_label_mode", "labels") == "icons"
        except Exception:
            pass
        return False

    def refresh_menu(self):
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
                101, 105, 106, 115,
                10, 160, 261, 130, 135, 180, 70,
            }
        technical_only = {
            40, 41, 42, 43, 62, 61, 30, 65, 201,
            21, 25, 26, 90, 120,
            50, 51, 66, 140, 145, 146, 147, 150, 250, 300,
            313, 314,
            101, 105, 106, 115,
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
        header.setFixedHeight(132)
        header.setStyleSheet(theme_qss("""
            background-color: transparent;
            border-bottom: 1px solid @border;
        """))
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 14, 12, 12)

        brand_card = QFrame()
        self.brand_card = brand_card
        brand_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        brand_card.setStyleSheet(theme_qss("""
            background: @surface;
            border: 1px solid @border;
            border-radius: 18px;
        """))
        brand_layout = QHBoxLayout(brand_card)
        self.brand_layout = brand_layout
        brand_layout.setContentsMargins(14, 12, 14, 12)
        brand_layout.setSpacing(10)
        
        self.branding_logo = QLabel()
        self.branding_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.branding_logo.setFixedSize(46, 46)
        self.branding_logo.setStyleSheet(theme_qss("""
            background: @surface;
            border: 1px solid @border;
            border-radius: 14px;
        """))
        
        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        title_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.branding_title = QLabel("AYEC Pro")
        self.branding_title.setWordWrap(True)
        self.branding_title.setStyleSheet(theme_qss(f"color: {DesignTokens.TEXT_COLOR}; font-size: 17px; font-weight: 900;"))
        self.branding_subtitle = QLabel("Servis Yönetimi")
        self.branding_subtitle.setWordWrap(True)
        self.branding_subtitle.setStyleSheet(theme_qss(f"color: {DesignTokens.SUBTEXT_COLOR}; font-size: 10px; font-weight: 700;"))
        title_box.addWidget(self.branding_title)
        title_box.addWidget(self.branding_subtitle)
        self.branding_sector_badge = QLabel("")
        self.branding_sector_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.branding_sector_badge.setFixedHeight(22)
        self.branding_sector_badge.setStyleSheet(theme_qss(f"""
            background: {DesignTokens.HEADER_BADGE_BG};
            color: {DesignTokens.HEADER_BADGE_TEXT};
            border: 1px solid {DesignTokens.BORDER_COLOR};
            border-radius: 11px;
            padding: 0 8px;
            font-size: 10px;
            font-weight: 800;
        """))
        title_box.addWidget(self.branding_sector_badge, 0, Qt.AlignmentFlag.AlignLeft)
        
        brand_layout.addWidget(self.branding_logo)
        brand_layout.addLayout(title_box, 1)
        self.pin_button = QPushButton("📎")
        self.pin_button.setObjectName("SideMenuPinButton")
        self.pin_button.setCheckable(True)
        self.pin_button.setChecked(self._is_pinned)
        self.pin_button.setFixedSize(30, 30)
        self.pin_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_button.setToolTip("Sol menüyü sabitle")
        self.pin_button.toggled.connect(self.set_pinned)
        self.pin_button.setStyleSheet(self._pin_button_qss())
        brand_layout.addWidget(self.pin_button, 0, Qt.AlignmentFlag.AlignTop)
        hl.addWidget(brand_card)
        
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
            self.pin_button.setToolTip("Sol menü sabit" if self._is_pinned else "Sol menü hover ile açılır")
            self.pin_button.setStyleSheet(self._pin_button_qss())
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
        self.refresh_menu()
        self.on_page_changed_internal(self._last_active_page_id)
        if self._icon_only:
            self._apply_icon_only_visual_state()
        else:
            self.set_collapsed(False if self._is_pinned else True, animate=False)

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
                        self.branding_logo.setText("")
                        self.branding_logo.setFixedSize(size, size)
                        self.branding_logo.setPixmap(
                            pm.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        )
                        self.branding_logo.setStyleSheet(theme_qss("background-color: transparent;"))
                        return
                fallback_path = os.path.join(os.getcwd(), "assets", "app_icon.png")
                fallback_pm = QPixmap(fallback_path)
                self.branding_logo.setPixmap(QPixmap())
                self.branding_logo.setFixedSize(46, 46)
                if not fallback_pm.isNull():
                    self.branding_logo.setText("")
                    self.branding_logo.setPixmap(
                        fallback_pm.scaled(46, 46, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    )
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

    def refresh_sector_badge(self):
        if not hasattr(self, "branding_sector_badge") or not self.branding_sector_badge:
            return
        sector = self._current_sector()
        self.branding_sector_badge.setText("OTOMOTIV MODU" if sector == "otomotiv" else "TEKNIK SERVIS MODU")
        if hasattr(self, "footer_mode") and self.footer_mode:
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
            ("\u0130\u015f\u00e7ilik Ekle", 140),
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
            for group_title, group_icon, group_subs in groups:
                visible_subs = filter_items(group_subs)
                if visible_subs:
                    filtered_groups.append((group_title, group_icon, visible_subs))
            if filtered_groups:
                filtered_sections.append((section_title, filtered_groups))
        return filtered_sections

    def _render_sections(self, sections, allowed_pages):
        first = True
        for section_title, groups in sections:
            # Section header row with a subtle top spacing
            if not first:
                self.menu_layout.addSpacing(4)
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
            self.menu_layout.addWidget(lbl)
            lbl.setVisible(not self._icon_only)
            for title, icon, subs in groups:
                item = AccordionItem(title, icon, subs, self, allowed_pages=allowed_pages)
                self.menu_layout.addWidget(item)
                self.accordion_groups.append(item)
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
        else:
            sections = self._build_technical_sections()
            sections.extend(self._build_system_sections())
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
        self._apply_collapsed_visual_state(False)
        parent = self.parentWidget()
        if parent and hasattr(parent, "_sync_width"):
            parent._sync_width(self.EXPANDED_WIDTH)
        self.setMinimumWidth(self.EXPANDED_WIDTH)
        self.setMaximumWidth(self.EXPANDED_WIDTH)
        self.resize(self.EXPANDED_WIDTH, self.height())
        self.anim = QPropertyAnimation(self, b"maximumWidth")
        self.anim.setDuration(200)
        self.anim.setStartValue(self.width())
        self.anim.setEndValue(self.EXPANDED_WIDTH)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        self.anim2 = QPropertyAnimation(self, b"minimumWidth")
        self.anim2.setDuration(200)
        self.anim2.setStartValue(self.width())
        self.anim2.setEndValue(self.EXPANDED_WIDTH)
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
        target_width = self.COLLAPSED_WIDTH if collapsed else self.EXPANDED_WIDTH
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
                widget.setVisible(not collapsed)
        if hasattr(self, "header") and self.header:
            self.header.setFixedHeight(92 if collapsed else 132)
        if hasattr(self, "brand_layout") and self.brand_layout:
            self.brand_layout.setContentsMargins(8 if collapsed else 14, 10 if collapsed else 12, 8 if collapsed else 14, 10 if collapsed else 12)
            self.brand_layout.setSpacing(4 if collapsed else 10)
        if hasattr(self, "branding_logo") and self.branding_logo:
            self.branding_logo.setFixedSize(42 if collapsed else 46, 42 if collapsed else 46)
        if hasattr(self, "pin_button") and self.pin_button:
            self.pin_button.setFixedSize(26 if collapsed else 30, 26 if collapsed else 30)

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
        utility_card.setStyleSheet(theme_qss("""
            background: @surface;
            border: 1px solid @border;
            border-radius: 14px;
        """))
        utility_layout = QHBoxLayout(utility_card)
        utility_layout.setContentsMargins(12, 8, 12, 8)
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
            background: @surface_alt;
            border: 1px solid @border;
            border-radius: 10px;
            padding: 4px 8px;
            font-size: 10px;
            font-weight: 800;
        """))
        utility_layout.addWidget(self.footer_mode)
        utility_layout.addStretch()
        self.version_label = QLabel(_ver_text)
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.version_label.setStyleSheet(theme_qss("""
            color: @text_muted;
            background: @surface_alt;
            border: 1px solid @border;
            border-radius: 10px;
            padding: 4px 8px;
            font-size: 10px;
            font-weight: 700;
        """))
        utility_layout.addWidget(self.version_label)
        fl.addWidget(utility_card)

        self.logout_btn = QPushButton("Oturumu Kapat")
        self.logout_btn.setObjectName("LogoutButton")
        self.logout_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_btn.setFixedHeight(40)
        self.logout_btn.setStyleSheet(theme_qss("""
            QPushButton#LogoutButton {
                background-color: @danger;
                color: @selection_text;
                font-weight: 800;
                font-size: 13px;
                border: 1px solid @danger;
                border-radius: 14px;
                text-align: center;
                padding: 0 14px;
            }
            QPushButton#LogoutButton:hover {
                background-color: @danger;
                color: @selection_text;
                border-color: @danger;
            }
            QPushButton#LogoutButton:pressed {
                background-color: @danger;
                color: @selection_text;
                border-color: @danger;
            }
        """))
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
            for btn, page_id in group.sub_buttons:
                self._btn_map[page_id] = btn
                self._badge_names[page_id] = btn.text()

    def set_badge(self, page_id, count):
        """Belirtilen sayfa butonuna sayaç etiketi ekler/kaldırır."""
        btn = self._btn_map.get(page_id)
        if btn is None:
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
        self.set_badge(30, today_appointments)  # Randevular
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
            is_active = self.db.get_setting("voice_assistant_active", "1") == "1"
            self.voice_assistant_btn.setVisible(is_active)

    def switch_user(self):
        try:
            self.logout_requested.emit()
        except Exception:
            QApplication.exit(0)

    def on_page_changed_internal(self, page_id):
        self._last_active_page_id = int(page_id)
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
            btn.setStyleSheet(self._flat_button_style(pid == page_id, not btn.isEnabled()))

        # Highlight sub items
        for group in self.accordion_groups:
            has_active = False
            for btn, pid in group.sub_buttons:
                is_active = (pid == page_id)
                btn.setStyleSheet(group._child_button_style(is_active, not btn.isEnabled()))
                # Update child row background wrapper styling
                if hasattr(btn, "_row") and hasattr(group, "_child_row_qss"):
                    btn._row.setStyleSheet(group._child_row_qss(is_active))
                # Update child text label color
                if hasattr(btn, "_txt_lbl"):
                    if is_active:
                        btn._txt_lbl.setStyleSheet(theme_qss(
                            "background: transparent; color: @text; font-size: 12px; font-weight: 700;"
                        ))
                    else:
                        btn._txt_lbl.setStyleSheet(theme_qss(
                            "background: transparent; color: @text_muted; font-size: 12px; font-weight: 500;"
                        ))
                if is_active:
                    has_active = True

            if has_active and not group.is_expanded:
                if hasattr(group, "reveal_page"):
                    group.reveal_page(page_id)
                group.expand()
            elif has_active and hasattr(group, "reveal_page"):
                group.reveal_page(page_id)

            # Highlight parent toggle if active
            if has_active:
                if hasattr(group, "_toggle_row") and hasattr(group, "_row_qss"):
                    group._toggle_row.setStyleSheet(group._row_qss(True))
                else:
                    group.toggle_btn.setStyleSheet(group._parent_button_style(True))
            else:
                if hasattr(group, "_toggle_row") and hasattr(group, "_row_qss"):
                    group._toggle_row.setStyleSheet(group._row_qss(False))
                else:
                    group.toggle_btn.setStyleSheet(group._parent_button_style(False))

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
                    self.logout_btn.setStyleSheet(theme_qss("""
                        QPushButton#LogoutButton {
                            background-color: @danger;
                            color: @selection_text;
                            font-weight: 800;
                            font-size: 13px;
                            border: 1px solid @danger;
                            border-radius: 10px;
                            text-align: left;
                            padding: 0 14px;
                        }
                        QPushButton#LogoutButton:hover { background-color: @danger_bg; color: @text; }
                        QPushButton#LogoutButton:pressed { background-color: @danger_bg; }
                    """))
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
                self.branding_title.setStyleSheet(theme_qss(f"color: {DesignTokens.TEXT_COLOR}; font-size: 17px; font-weight: 900;"))
            if hasattr(self, "branding_subtitle") and self.branding_subtitle:
                self.branding_subtitle.setStyleSheet(theme_qss(f"color: {DesignTokens.SUBTEXT_COLOR}; font-size: 10px; font-weight: 700;"))
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
                self.logout_btn.setStyleSheet(theme_qss("""
                    QPushButton#LogoutButton {
                        background-color: @danger;
                        color: @selection_text;
                        font-weight: 800;
                        font-size: 13px;
                        border: 1px solid @border;
                        border-radius: 10px;
                        text-align: left;
                        padding: 0 14px;
                    }
                    QPushButton#LogoutButton:hover { background-color: @danger; }
                    QPushButton#LogoutButton:pressed { background-color: @danger; }
                """))
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
        return [
            ("SERVIS OPERASYON", [
                ("Servis Y\u00f6netimi", "\U0001f527", [
                    ("Genel Bak\u0131\u015f", 40),
                    ("Servis Panosu", 41),
                    ("Servis Listesi", 42),
                    ("Durum Paneli", 43),
                    ("Teknisyen Paneli", 62),
                    ("Saha Haritas\u0131", 61),
                    ("Randevular", 30),
                    ("Lojistik & Garanti Y\u00f6netimi", 65),
                    ("\u0130\u015f/Servis Takibi Raporlar\u0131", 201),
                    ("AI Asistan", 170),
                ]),
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
                    ("Hizmet Tanımları", 140),
                    ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
                    ("Cihaz Bilgisi & Markaları", 145),
                    ("Emanet (Konsinye) Cihazlar", 66),
                    ("Depo ve Ara\u00e7 Stoklar\u0131", 51),
                    ("Mobil Stok", 250),
                    ("PC Builder", 300),
                ]),
                (
                    "Servis Y\u00f6netim Ayar\u0131",
                    "\u2699",
                    [
                        ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
                        ("Marka Adlar\u0131 Y\u00f6netimi", 145),
                        ("Rapor C\u00fcmle Kal\u0131plar\u0131", 147),
                        ("\u0130\u015f\u00e7ilik Ekle", 140),
                    ],
                ),
            ]),
            ("FİNANS", [
                ("Finans", "💸", [
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

    def _build_technical_sections(self):
        sections = self._build_technical_sections_base()
        managed_page_ids = {140, 145, 146}
        settings_items = [
            ("\u00dcr\u00fcn Grubu Y\u00f6netimi", 146),
            ("Marka Adlar\u0131 Y\u00f6netimi", 145),
            ("Rapor C\u00fcmle Kal\u0131plar\u0131", 147),
            ("\u0130\u015f\u00e7ilik Ekle", 140),
        ]
        offers_group = (
            "Teklif Y\u00f6netimi",
            "\U0001f4c4",
            [
                ("Teklif Olu\u015ftur", 150),
                ("T\u00fcm Teklifler", 313),
                ("Teklif Raporlar\u0131", 314),
            ],
        )
        normalized_sections = []
        for section_name, groups in sections:
            normalized_groups = []
            for group_title, icon, items in groups:
                page_ids = {
                    int(item[1]) for item in items
                    if not isinstance(item[1], (list, tuple))
                }
                if {140, 145, 146}.issubset(page_ids) and 50 not in page_ids:
                    continue
                items = [
                    item for item in items
                    if isinstance(item[1], (list, tuple)) or int(item[1]) != 170
                ]
                if 40 in page_ids:
                    items.append(("Servis Y\u00f6netim Ayar\u0131", settings_items))
                    group_title = "Servis Y\u00f6netimi"
                if 50 in page_ids:
                    items = [
                        item for item in items
                        if isinstance(item[1], (list, tuple))
                        or int(item[1]) not in managed_page_ids | {150}
                    ]
                    group_title = "Stok / Sipari\u015f"
                normalized_groups.append((group_title, icon, items))
                if 50 in page_ids:
                    normalized_groups.append(offers_group)
            normalized_sections.append((section_name, normalized_groups))
        return normalized_sections

