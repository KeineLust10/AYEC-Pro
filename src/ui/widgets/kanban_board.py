# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QScrollArea, QPushButton, QGraphicsDropShadowEffect,
                             QMenu, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QSize, QEvent
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.theme_colors import theme_qss, tc
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_manager import ThemeManager
from src.utils.appearance_mode import AppearanceModeManager
from src.utils.status_utils import is_active_device_status, normalize_device_status
from PyQt6.QtGui import QFont, QColor, QDrag, QPixmap, QPainter, QAction
import logging

logger = logging.getLogger("AYECProLogger")

def get_kanban_colors():
    return {
        "Bekliyor": "#F59E0B",
        "Tamirde": "#2563EB",
        "Parça Bekliyor": "#D97706",
        "Test Sürecinde": "#0EA5E9",
        "Teslim Edildi": "#10B981",
        "İptal": "#EF4444",
    }


def _status_surface(color_hex):
    color = QColor(color_hex)
    if not color.isValid():
        return tc("surface_alt", default="#E9EEF6")
    base = QColor(tc("surface_alt", default="#E9EEF6"))
    ratio = 0.34 if ThemeManager.is_dark_theme(ThemeManager._current_theme) else 0.22
    red = round(base.red() * (1 - ratio) + color.red() * ratio)
    green = round(base.green() * (1 - ratio) + color.green() * ratio)
    blue = round(base.blue() * (1 - ratio) + color.blue() * ratio)
    return QColor(red, green, blue).name()


def _status_outline(color_hex):
    color = QColor(color_hex)
    if not color.isValid():
        return tc("border", default="#D7DFEA")
    ratio = 0.82 if ThemeManager.is_dark_theme(ThemeManager._current_theme) else 0.72
    red = round(color.red() * ratio)
    green = round(color.green() * ratio)
    blue = round(color.blue() * ratio)
    return QColor(red, green, blue).name()


def _status_ring(color_hex):
    color = QColor(color_hex)
    if not color.isValid():
        return tc("border", default="#D7DFEA")
    ratio = 0.9 if ThemeManager.is_dark_theme(ThemeManager._current_theme) else 0.8
    red = round(color.red() * ratio)
    green = round(color.green() * ratio)
    blue = round(color.blue() * ratio)
    return QColor(red, green, blue).name()


def _status_text(color_hex):
    color = QColor(color_hex)
    if not color.isValid():
        return tc("text", default="#172033")
    luminance = (0.299 * color.red()) + (0.587 * color.green()) + (0.114 * color.blue())
    return "#0F172A" if luminance > 170 else "#FFFFFF"

def _is_classic_appearance():
    app = QApplication.instance()
    return bool(app and app.property("appearanceMode") == AppearanceModeManager.CLASSIC)

class KanbanCard(QFrame):
    clicked = pyqtSignal(str) # tracking_no
    action_triggered = pyqtSignal(str, str) # action_type, tracking_no

    def __init__(self, device_data, db=None):
        super().__init__()
        self.device_data = device_data
        self.db = db
        
        self.tracking_no = str(self._get("tracking_no", ""))
        self.customer = str(self._get("customer_name", "")) if self._get("customer_name") else "Bilinmiyor"
        self.brand = str(self._get("device_brand", "") or "")
        self.model = str(self._get("device_model", "") or "")
        self.brand_model = f"{self.brand} {self.model}".strip() or "Cihaz"
        self.fault_category = str(self._get("fault_category", "") or "")
        self.urgency = str(self._get("urgency", "") or "")
        self.status = str(self._get("status", "") or "")
        self.entry_date = str(self._get("entry_date", "") or "")
        self.price = self._to_float(self._get("price", 0))
        self.device_type = str(self._get("device_type", "") or "")
        self.fault_desc = str(self._get("fault_description", "") or "") or self.brand_model
        
        self.setFrameShape(QFrame.Shape.NoFrame)
        # self.setFixedWidth(280) # Responsive
        self.setObjectName("KanbanCard")
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setMinimumHeight(220)
        
        self._accent = None
        self._bar = None
        self._status_pill = None
        accent = self._status_color(self.status)
        self._apply_accent_styles(accent)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 12, 14, 12)

        bar = QFrame()
        self._bar = bar
        bar.setFixedHeight(4)
        bar.setStyleSheet(theme_qss(f"background-color: {accent}; border-radius: 2px;"))
        layout.addWidget(bar)
        
        top = QHBoxLayout()
        top.setSpacing(10)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        lbl_title = QLabel(self._ellipsize(self.fault_desc, 60))
        lbl_title.setObjectName("KanbanTitle")
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(theme_qss("color: @text; font-size: 13px; font-weight: 800;"))
        title_box.addWidget(lbl_title)

        lbl_sub = QLabel(self._ellipsize(self.customer, 42))
        lbl_sub.setObjectName("KanbanCustomer")
        lbl_sub.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; font-weight: 600;"))
        title_box.addWidget(lbl_sub)

        top.addLayout(title_box, 1)

        status_pill = QLabel(self._status_label(self.status))
        status_pill.setObjectName("KanbanStatusPill")
        self._status_pill = status_pill
        status_pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_pill.setStyleSheet(theme_qss(f"background: {_status_surface(accent)}; color: {accent}; border: 1px solid {_status_outline(accent)}; border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 900;"))
        top.addWidget(status_pill, 0, Qt.AlignmentFlag.AlignTop)

        layout.addLayout(top)
        
        # 2. Tags Row (Vibrant Badges)
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(6)
        
        # Urgency Tag (Rose/Emerald)
        if self.urgency in ["Kritik", "Yüksek", "Acil"]:
            tag_style = "background-color: @surface_alt; color: @danger; border: 1px solid @danger;"
            tag_text = "Acil"
        else:
            tag_style = "background-color: @surface_alt; color: @success; border: 1px solid @success;"
            tag_text = "Normal"

        lbl_tag = QLabel(tag_text)
        lbl_tag.setObjectName("KanbanUrgencyBadge")
        lbl_tag.setStyleSheet(theme_qss(f"border-radius: 10px; padding: 3px 10px; font-size: 10px; font-weight: 900; {tag_style}"))
        tags_layout.addWidget(lbl_tag)
        
        if self.device_type:
            lbl_type = QLabel(self._ellipsize(self.device_type, 14))
            lbl_type.setObjectName("KanbanTypeBadge")
            lbl_type.setStyleSheet(theme_qss("border-radius: 10px; padding: 3px 10px; font-size: 10px; font-weight: 900; background-color: @surface_alt; color: @accent; border: 1px solid @accent;"))
            tags_layout.addWidget(lbl_type)
        if self.fault_category:
            lbl_cat = QLabel(self._ellipsize(self.fault_category, 14))
            lbl_cat.setObjectName("KanbanCategoryBadge")
            lbl_cat.setStyleSheet(theme_qss("border-radius: 10px; padding: 3px 10px; font-size: 10px; font-weight: 900; background-color: @surface_alt; color: @warning; border: 1px solid rgba(180, 83, 9, 0.22);"))
            tags_layout.addWidget(lbl_cat)
        
        tags_layout.addStretch()
        layout.addLayout(tags_layout)
        
        mid = QHBoxLayout()
        mid.setSpacing(10)
        lbl_device = QLabel(self._ellipsize(self.brand_model, 34))
        lbl_device.setObjectName("KanbanDevice")
        lbl_device.setStyleSheet(theme_qss("color: @text; font-size: 12px; font-weight: 700;"))
        mid.addWidget(lbl_device)
        mid.addStretch()
        layout.addLayout(mid)

        if self.price and self.price > 0:
            price_row = QHBoxLayout()
            price_row.setContentsMargins(0, 0, 0, 0)
            price_row.addStretch()
            lbl_price = QLabel(
                CurrencyHelper.format_try_for_display(
                    self.price,
                    db=self.db,
                    include_try_reference=False,
                )
            )
            lbl_price.setObjectName("KanbanPrice")
            lbl_price.setMinimumWidth(92)
            lbl_price.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_price.setStyleSheet(theme_qss("color: @selection_text; font-size: 12px; font-weight: 900; background: @surface_alt; border: 1px solid @border; border-radius: 10px; padding: 3px 10px;"))
            price_row.addWidget(lbl_price)
            layout.addLayout(price_row)

        info = self._load_quick_info()
        if info:
            info_frame = QFrame()
            info_frame.setObjectName("KanbanInfo")
            info_frame.setStyleSheet(theme_qss(f"background: @surface_alt; border: 1px solid @border; border-radius: 12px;"))
            info_l = QVBoxLayout(info_frame)
            info_l.setContentsMargins(10, 8, 10, 8)
            info_l.setSpacing(4)

            for line in info:
                lbl_i = QLabel(line)
                lbl_i.setObjectName("KanbanInfoText")
                lbl_i.setWordWrap(True)
                lbl_i.setStyleSheet(theme_qss("color: @text; font-size: 11px; font-weight: 700;"))
                info_l.addWidget(lbl_i)

            layout.addWidget(info_frame)

        # 3. Bottom Row: Tracking + Date + Avatar
        bottom_layout = QHBoxLayout()
        
        lbl_track = QLabel(f"#{self.tracking_no}")
        lbl_track.setObjectName("KanbanTrack")
        lbl_track.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; font-weight: 800;"))
        bottom_layout.addWidget(lbl_track)

        if self.entry_date:
            lbl_when = QLabel(self._short_date(self.entry_date))
            lbl_when.setObjectName("KanbanDate")
            lbl_when.setStyleSheet(theme_qss("color: @disabled_text; font-size: 11px; font-weight: 700;"))
            bottom_layout.addWidget(lbl_when)
        
        bottom_layout.addStretch()
        
        # Avatar (Soft Blue)
        initials = "".join([n[0] for n in self.customer.split()[:2]]).upper()
        lbl_avatar = QLabel(initials)
        lbl_avatar.setObjectName("KanbanAvatar")
        lbl_avatar.setFixedSize(28, 28)
        lbl_avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_avatar.setStyleSheet(theme_qss("""
            background-color: @selection_bg; 
            color: @accent; 
            border-radius: 14px; 
            font-size: 11px; 
            font-weight: 700;
        """))
        bottom_layout.addWidget(lbl_avatar)
        
        layout.addLayout(bottom_layout)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setColor(QColor(15, 23, 42, 22))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)
        self._apply_accent_styles(accent)

    def _get(self, key, default=None):
        try:
            if self.device_data is None:
                return default
            
            # named access (sqlite3.Row or dict)
            try:
                v = self.device_data[key]
                return default if v is None else v
            except (KeyError, IndexError, TypeError):
                # Fallback to old numeric indexing if absolutely necessary, 
                # but we prefer named access.
                return default
        except Exception:
            return default

    def _to_float(self, value, default=0.0):
        try:
            return float(value)
        except Exception:
            return default

    def _ellipsize(self, text, max_len):
        s = "" if text is None else str(text)
        s = " ".join(s.split())
        if len(s) <= max_len:
            return s
        return s[:max_len - 1] + "…"

    def _status_color(self, status):
        s = (status or "").strip().lower()
        colors = get_kanban_colors()
        if "bek" in s:
            return colors["Bekliyor"]
        if "tamir" in s or "servis" in s or "işlem" in s:
            return colors["Tamirde"]
        if "parça" in s or "sipariş" in s:
            return colors["Parça Bekliyor"]
        if "test" in s or "onay" in s or "hazır" in s or "bitti" in s or "tamam" in s:
            return colors["Test Sürecinde"]
        if "teslim" in s:
            return colors["Teslim Edildi"]
        if "iptal" in s:
            return colors["İptal"]
        return colors["Tamirde"]

    def _status_label(self, status):
        s = (status or "").strip()
        return s if s else "Durum"

    def _short_date(self, date_str):
        s = (date_str or "").strip()
        if not s:
            return ""
        if len(s) >= 10:
            return s[:10]
        return s

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.tracking_no)
            drag.setMimeData(mime)
            
            # Pixmap for drag visual - Ghost Effect
            original = self.grab()
            pixmap = QPixmap(original.size())
            pixmap.fill(Qt.GlobalColor.transparent)
            
            painter = QPainter(pixmap)
            painter.setOpacity(0.8)
            painter.drawPixmap(0, 0, original)
            painter.end()
            
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
            
            drag.exec(Qt.DropAction.MoveAction)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        return super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        return super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tracking_no)
        return super().mouseDoubleClickEvent(event)

    def _apply_accent_styles(self, accent):
        self._accent = accent
        if _is_classic_appearance():
            self.setMinimumHeight(196)
            self.setStyleSheet("""
                #KanbanCard {
                    background-color: #FFFFFF;
                    border-radius: 12px;
                    border: 1px solid #D5DDE8;
                }
                #KanbanCard:hover {
                    border: 1px solid #8FA3BD;
                    background-color: #FFFFFF;
                }
            """)
            if self._bar is not None:
                self._bar.setStyleSheet(f"background-color: {accent}; border-radius: 2px;")
            if self._status_pill is not None:
                self._status_pill.setStyleSheet(
                    f"background: {_status_surface(accent)}; color: {accent}; border: 1px solid {_status_outline(accent)}; border-radius: 10px; padding: 2px 9px; font-size: 10px; font-weight: 900;"
                )
            effect = self.graphicsEffect()
            if effect is not None:
                effect.setEnabled(True)
                effect.setBlurRadius(18)
                effect.setColor(QColor(15, 23, 42, 18))
                effect.setOffset(0, 4)
            self._apply_classic_modern_child_styles(accent)
            return
        self.setStyleSheet(theme_qss(f"""
            #KanbanCard {{
                background-color: @surface;
                border-radius: 14px;
                border: 1px solid @border;
            }}
            #KanbanCard:hover {{
                border: 1px solid {accent};
                background-color: @surface_alt;
            }}
        """))
        if self._bar is not None:
            self._bar.setStyleSheet(theme_qss(f"background-color: {accent}; border-radius: 2px;"))
        if self._status_pill is not None:
            self._status_pill.setStyleSheet(theme_qss(
                f"background: {_status_surface(accent)}; color: {accent}; border: 1px solid {_status_outline(accent)}; border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 900;"
            ))
        self._apply_modern_child_styles()

    def _apply_classic_modern_child_styles(self, accent):
        styles = {
            "KanbanTitle": "color: #111827; font-size: 13px; font-weight: 800; background: transparent; border: none;",
            "KanbanCustomer": "color: #5B677A; font-size: 12px; font-weight: 600; background: transparent; border: none;",
            "KanbanDevice": "color: #111827; font-size: 12px; font-weight: 700; background: transparent; border: none;",
            "KanbanTrack": "color: #41536B; font-size: 12px; font-weight: 800; background: transparent; border: none;",
            "KanbanDate": "color: #64748B; font-size: 11px; font-weight: 700; background: transparent; border: none;",
            "KanbanInfoText": "color: #111827; font-size: 11px; font-weight: 700; background: transparent; border: none;",
        }
        for label in self.findChildren(QLabel):
            name = label.objectName()
            if name in styles:
                label.setStyleSheet(styles[name])
        for badge_name in ("KanbanTypeBadge", "KanbanCategoryBadge"):
            for badge in self.findChildren(QLabel, badge_name):
                badge.setStyleSheet("background: #F4F7FB; color: #2563EB; border: 1px solid #C7D7F5; border-radius: 10px; padding: 3px 9px; font-size: 10px; font-weight: 900;")
        for badge in self.findChildren(QLabel, "KanbanUrgencyBadge"):
            if self.urgency in ["Kritik", "Yüksek", "Yüksek", "Acil"]:
                badge.setStyleSheet("background: #FFF1F2; color: #DC2626; border: 1px solid #FDA4AF; border-radius: 10px; padding: 3px 9px; font-size: 10px; font-weight: 900;")
            else:
                badge.setStyleSheet("background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; border-radius: 10px; padding: 3px 9px; font-size: 10px; font-weight: 900;")
        for price in self.findChildren(QLabel, "KanbanPrice"):
            price.setStyleSheet("background: #EDF3FA; color: #111827; border: 1px solid #D5DDE8; border-radius: 10px; padding: 3px 9px; font-size: 12px; font-weight: 900;")
        for avatar in self.findChildren(QLabel, "KanbanAvatar"):
            avatar.setStyleSheet(f"background: {_status_surface(accent)}; color: {accent}; border: 1px solid {_status_outline(accent)}; border-radius: 14px; font-size: 11px; font-weight: 800;")
        for frame in self.findChildren(QFrame, "KanbanInfo"):
            frame.setStyleSheet("background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px;")

    def _apply_modern_child_styles(self):
        styles = {
            "KanbanTitle": theme_qss("color: @text; font-size: 13px; font-weight: 800;"),
            "KanbanCustomer": theme_qss("color: @text_muted; font-size: 12px; font-weight: 600;"),
            "KanbanDevice": theme_qss("color: @text; font-size: 12px; font-weight: 700;"),
            "KanbanTrack": theme_qss("color: @text_muted; font-size: 12px; font-weight: 800;"),
            "KanbanDate": theme_qss("color: @disabled_text; font-size: 11px; font-weight: 700;"),
            "KanbanInfoText": theme_qss("color: @text; font-size: 11px; font-weight: 700;"),
        }
        for label in self.findChildren(QLabel):
            style = styles.get(label.objectName())
            if style:
                label.setStyleSheet(style)
        for badge in self.findChildren(QLabel, "KanbanUrgencyBadge"):
            if self.urgency in ["Kritik", "Yüksek", "Yüksek", "Acil"]:
                badge.setStyleSheet(theme_qss("border-radius: 10px; padding: 3px 10px; font-size: 10px; font-weight: 900; background-color: @surface_alt; color: @danger; border: 1px solid @danger;"))
            else:
                badge.setStyleSheet(theme_qss("border-radius: 10px; padding: 3px 10px; font-size: 10px; font-weight: 900; background-color: @surface_alt; color: @success; border: 1px solid @success;"))
        for badge in self.findChildren(QLabel, "KanbanTypeBadge"):
            badge.setStyleSheet(theme_qss("border-radius: 10px; padding: 3px 10px; font-size: 10px; font-weight: 900; background-color: @surface_alt; color: @accent; border: 1px solid @accent;"))
        for badge in self.findChildren(QLabel, "KanbanCategoryBadge"):
            badge.setStyleSheet(theme_qss("border-radius: 10px; padding: 3px 10px; font-size: 10px; font-weight: 900; background-color: @surface_alt; color: @warning; border: 1px solid rgba(180, 83, 9, 0.22);"))
        for price in self.findChildren(QLabel, "KanbanPrice"):
            price.setStyleSheet(theme_qss("color: @selection_text; font-size: 12px; font-weight: 900; background: @surface_alt; border: 1px solid @border; border-radius: 10px; padding: 3px 10px;"))
        for avatar in self.findChildren(QLabel, "KanbanAvatar"):
            avatar.setStyleSheet(theme_qss("background-color: @selection_bg; color: @accent; border-radius: 14px; font-size: 11px; font-weight: 700;"))
        for frame in self.findChildren(QFrame, "KanbanInfo"):
            frame.setStyleSheet(theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 12px;"))

    def apply_theme_styles(self):
        self._apply_accent_styles(self._status_color(self.status))

    def _load_quick_info(self):
        cached = self._get("_kanban_quick_info")
        if isinstance(cached, (list, tuple)):
            return [str(line) for line in cached if line]
        if not self.db:
            return []
        lines = []

        parts = []
        try:
            rows = self.db.cursor.execute(
                "SELECT part_name, price FROM used_parts WHERE tracking_no=? ORDER BY created_at DESC LIMIT 2",
                (self.tracking_no,)
            ).fetchall()
            for r in rows:
                parts.append(str(r[0]))
        except Exception:
            try:
                rows = self.db.cursor.execute(
                    """
                    SELECT p.name, up.quantity
                    FROM used_parts up
                    LEFT JOIN parts p ON p.id = up.part_id
                    WHERE up.tracking_no=?
                    ORDER BY up.used_at DESC
                    LIMIT 2
                    """,
                    (self.tracking_no,)
                ).fetchall()
                for r in rows:
                    name = str(r[0] or "")
                    qty = r[1]
                    if name:
                        parts.append(f"{name} x{qty}")
            except Exception:
                parts = []

        if parts:
            lines.append("Parçalar: " + ", ".join(parts))

        last_log = None
        try:
            row = self.db.cursor.execute(
                "SELECT message FROM service_logs WHERE device_tracking_no=? ORDER BY created_at DESC LIMIT 1",
                (self.tracking_no,)
            ).fetchone()
            if row:
                last_log = row[0]
        except Exception:
            last_log = None

        if last_log:
            lines.append("Son işlem: " + self._ellipsize(last_log, 60))

        return lines

    def contextMenuEvent(self, event):
        self.show_context_menu(event.globalPos())

    def show_context_menu(self, position):
        if not is_context_menu_enabled(self.db):
            return
        menu = QMenu()
        
        # Style the menu
        menu_style = """
            QMenu {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                color: @text;
                padding: 8px 20px;
                font-size: 13px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: @surface_alt;
                color: @text;
            }
            QMenu::separator {
                height: 1px;
                background: @surface_alt;
                margin: 4px 10px;
            }
        """
        menu.setStyleSheet(theme_qss(menu_style))
        
        action_view = QAction("👁️ Detayları Görüntüle", self)
        action_view.triggered.connect(lambda: self.clicked.emit(self.tracking_no))
        menu.addAction(action_view)
        
        action_status = QMenu("✏️ Durumu Güncelle", self)
        action_status.setStyleSheet(theme_qss(menu_style)) # Apply style to sub-menu too
        for s in ["Bekliyor", "Tamirde", "Parça Bekliyor", "Test Sürecinde", "Hazır", "Teslim Edildi", "İptal"]:
            a = QAction(s, self)
            a.triggered.connect(lambda ch, st=s: self.action_triggered.emit(f"update_status:{st}", self.tracking_no))
            action_status.addAction(a)
        menu.addMenu(action_status)
        
        menu.addSeparator()
        
        action_print = QAction("🖨️ Barkod Yazdır", self)
        action_print.triggered.connect(lambda: self.action_triggered.emit("print_barcode", self.tracking_no))
        menu.addAction(action_print)
        
        action_wp = QAction("📱 WhatsApp", self)
        action_wp.triggered.connect(lambda: self.action_triggered.emit("whatsapp", self.tracking_no))
        menu.addAction(action_wp)
        
        action_external = QAction("📦 Dış Servise Gönder", self)
        action_external.triggered.connect(lambda: self.action_triggered.emit("external_send", self.tracking_no))
        menu.addAction(action_external)
        
        menu.addSeparator()
        
        action_cancel = QAction("🗑️ Servisi İptal Et", self)
        action_cancel.triggered.connect(lambda: self.action_triggered.emit("cancel", self.tracking_no))
        menu.addAction(action_cancel)
        
        menu.exec(position)

class KanbanColumn(QWidget):
    card_dropped = pyqtSignal(str, str) # tracking_no, new_status_key

    def __init__(self, title, status_key, color, db=None):
        super().__init__()
        self.title = title
        self.status_key = status_key
        self.color = color
        from PyQt6.QtWidgets import QSizePolicy
        self.db = db
        # self.setFixedWidth(320) # REMOVED: Fixed width causes scroll
        self.setMinimumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAcceptDrops(True)
        
        self.all_devices = []
        self.loaded_count = 0
        self.CHUNK_SIZE = 5
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        from src.utils.design_system import DesignTokens
        # Header
        self.header = QFrame()
        self.header.setObjectName("KanbanColumnHeader")
        self.header.setFixedHeight(54)
        self.header.setStyleSheet(theme_qss(f"""
            QFrame {{
                background-color: {_status_surface(color)};
                border-radius: 16px;
                border: 1px solid {color};
            }}
        """))
        h_layout = QHBoxLayout(self.header)
        h_layout.setContentsMargins(16, 0, 16, 0)
        
        icon = QLabel(self._icon_for_key(status_key))
        icon.setObjectName("KanbanColumnIcon")
        self.lbl_icon = icon
        icon.setStyleSheet(theme_qss(f"color: {color}; font-size: 16px; border:none;"))
        h_layout.addWidget(icon)

        lbl = QLabel(title)
        lbl.setObjectName("KanbanColumnTitle")
        self.lbl_title = lbl
        lbl.setFont(QFont(DesignTokens.FONT_FAMILY, 10, QFont.Weight.Bold))
        lbl.setStyleSheet(theme_qss(f"color: {tc('text')}; letter-spacing: 0.6px; border: none;"))
        h_layout.addWidget(lbl)
        
        h_layout.addStretch()

        self.lbl_count = QLabel("0")
        self.lbl_count.setObjectName("KanbanColumnCount")
        self.lbl_count.setStyleSheet(theme_qss(f"background-color: {color}; color: {_status_text(color)}; border-radius: 10px; padding: 4px 12px; font-weight: 900; border: 1px solid {color};"))
        h_layout.addWidget(self.lbl_count)
        
        layout.addWidget(self.header)

        header_shadow = QGraphicsDropShadowEffect(self.header)
        header_shadow.setBlurRadius(18)
        header_shadow.setColor(QColor(15, 23, 42, 26))
        header_shadow.setOffset(0, 6)
        self.header.setGraphicsEffect(header_shadow)
        
        # Content Area
        self.scroll = QScrollArea()
        self.scroll.setObjectName("KanbanColumnScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.scroll.setStyleSheet(theme_qss("""
            QScrollArea {
                background-color: @surface_alt;
                border-radius: 16px;
                border: 1px solid @border;
            }
            QScrollArea::viewport {
                background-color: transparent;
                border-radius: 16px;
            }
            QScrollBar:vertical {
                border: none;
                background-color: transparent;
                width: 8px;
                margin: 12px 6px 12px 0px;
            }
            QScrollBar::handle:vertical {
                background-color: rgba(100, 116, 139, 0.45);
                min-height: 24px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: rgba(100, 116, 139, 0.70);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
        """))
        
        self.content = QWidget()
        self.content.setObjectName("ColumnContent")
        self.content.setStyleSheet(theme_qss("#ColumnContent { background-color: transparent; border-radius: 16px; }"))
        self.content.setAcceptDrops(True)
        self.cards_layout = QVBoxLayout(self.content)
        self.cards_layout.setContentsMargins(12, 12, 12, 12)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()
        
        self.scroll.setWidget(self.content)
        layout.addWidget(self.scroll)
        try:
            self.scroll.setAcceptDrops(True)
            self.scroll.viewport().setAcceptDrops(True)
            self.scroll.viewport().installEventFilter(self)
            self.content.installEventFilter(self)
        except Exception:
            pass

    def update_color(self, color):
        self.color = color
        if hasattr(self, "header") and self.header:
            if _is_classic_appearance():
                self.header.setStyleSheet(f"""
                    QFrame#KanbanColumnHeader {{
                        background-color: {_status_surface(color)};
                        border-radius: 12px;
                        border: 1px solid {_status_outline(color)};
                    }}
                """)
                effect = self.header.graphicsEffect()
                if effect is not None:
                    effect.setEnabled(True)
                    effect.setBlurRadius(12)
                    effect.setColor(QColor(15, 23, 42, 14))
                    effect.setOffset(0, 3)
            else:
                self.header.setStyleSheet(theme_qss(f"""
                    QFrame {{
                        background-color: {_status_surface(color)};
                        border-radius: 16px;
                        border: 1px solid {_status_outline(color)};
                    }}
                """))
        if hasattr(self, "lbl_count") and self.lbl_count:
            if _is_classic_appearance():
                self.lbl_count.setStyleSheet(
                    f"background-color: #FFFFFF; color: {color}; border-radius: 10px; padding: 4px 11px; font-weight: 900; border: 1px solid {_status_outline(color)};"
                )
            else:
                self.lbl_count.setStyleSheet(theme_qss(
                    f"background-color: {color}; color: {_status_text(color)}; border-radius: 10px; padding: 4px 12px; font-weight: 900; border: 1px solid {_status_outline(color)};"
                ))
        if hasattr(self, "lbl_icon") and self.lbl_icon:
            self.lbl_icon.setStyleSheet(f"color: {color}; font-size: 16px; border: none; background: transparent;" if _is_classic_appearance() else theme_qss(f"color: {color}; font-size: 16px; border:none;"))
        if hasattr(self, "lbl_title") and self.lbl_title:
            self.lbl_title.setStyleSheet("color: #111827; letter-spacing: 0px; border: none; background: transparent; font-weight: 800;" if _is_classic_appearance() else theme_qss(f"color: {tc('text')}; letter-spacing: 0.6px; border: none;"))
        if hasattr(self, "scroll") and self.scroll and _is_classic_appearance():
            self.scroll.setStyleSheet("""
                QScrollArea#KanbanColumnScroll {
                    background-color: #F7FAFE;
                    border-radius: 12px;
                    border: 1px solid #D5DDE8;
                }
                QScrollArea#KanbanColumnScroll::viewport {
                    background-color: #F7FAFE;
                    border-radius: 12px;
                }
                QScrollBar:vertical {
                    background-color: transparent;
                    width: 8px;
                    margin: 10px 5px 10px 0px;
                    border: none;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(100, 116, 139, 0.42);
                    min-height: 24px;
                    border-radius: 4px;
                }
            """)
        if hasattr(self, "content") and self.content and _is_classic_appearance():
            self.content.setStyleSheet("#ColumnContent { background: transparent; border: none; }")
        elif hasattr(self, "scroll") and self.scroll:
            self.scroll.setStyleSheet(theme_qss("""
                QScrollArea {
                    background-color: @surface_alt;
                    border-radius: 16px;
                    border: 1px solid @border;
                }
                QScrollArea::viewport {
                    background-color: transparent;
                    border-radius: 16px;
                }
                QScrollBar:vertical {
                    border: none;
                    background-color: transparent;
                    width: 8px;
                    margin: 12px 6px 12px 0px;
                }
                QScrollBar::handle:vertical {
                    background-color: rgba(100, 116, 139, 0.45);
                    min-height: 24px;
                    border-radius: 4px;
                }
                QScrollBar::handle:vertical:hover {
                    background-color: rgba(100, 116, 139, 0.70);
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            """))
            if hasattr(self, "content") and self.content:
                self.content.setStyleSheet(theme_qss("#ColumnContent { background-color: transparent; border-radius: 16px; }"))

    def apply_theme_styles(self):
        for i in range(self.cards_layout.count()):
            item = self.cards_layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if hasattr(w, "apply_theme_styles"):
                w.apply_theme_styles()

    def set_devices(self, devices, board_signals=None):
        from src.utils.ayec_accelerator import fast_render_context
        with fast_render_context(self.content):
            self.clear()
            self.all_devices = devices
            self.board_signals = board_signals
            self.loaded_count = 0
            self._set_empty_state_visible(len(devices) == 0)
            self.load_next_chunk()
            self.update_count()


    def load_next_chunk(self):
        if self.loaded_count >= len(self.all_devices):
            return
            
        next_chunk = self.all_devices[self.loaded_count : self.loaded_count + self.CHUNK_SIZE]
        for dev in next_chunk:
            card = KanbanCard(dev, db=self.db)
            if self.board_signals:
                card.clicked.connect(self.board_signals['clicked'])
                card.action_triggered.connect(self.board_signals['action'])
            self.cards_layout.insertWidget(self.cards_layout.count()-1, card)
            
        self.loaded_count += len(next_chunk)

    def on_scroll(self, value):
        # Trigger load more when near bottom
        scroll_bar = self.scroll.verticalScrollBar()
        if value > scroll_bar.maximum() * 0.8:
            self.load_next_chunk()

    def clear(self):
        self.all_devices = []
        self.loaded_count = 0
        for i in range(self.cards_layout.count() - 1, -1, -1):
            item = self.cards_layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if not w:
                continue
            if hasattr(self, "empty_label") and w is self.empty_label:
                continue
            self.cards_layout.takeAt(i)
            w.setParent(None)
            w.deleteLater()
        self._set_empty_state_visible(True)
        self.update_count()
        
    def update_count(self):
        self.lbl_count.setText(str(len(self.all_devices)))

    def dragEnterEvent(self, event):

        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.scroll.setStyleSheet(theme_qss(f"""
                QScrollArea {{
                    background-color: {_status_surface(self.color)};
                    border-radius: 16px;
                    border: 2px solid {_status_ring(self.color)};
                }}
                QScrollArea::viewport {{
                    background-color: transparent;
                }}
            """))
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.scroll.setStyleSheet(theme_qss("""
            QScrollArea {
                background-color: @surface_alt;
                border-radius: 16px;
                border: 1px solid @border;
            }
            QScrollArea::viewport {
                background-color: transparent;
            }
        """))
        event.accept()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()
            
    def dropEvent(self, event):
        self.scroll.setStyleSheet(theme_qss("""
            QScrollArea {
                background-color: @surface_alt;
                border-radius: 16px;
                border: 1px solid @border;
            }
            QScrollArea::viewport {
                background-color: transparent;
            }
        """))
        tracking_no = event.mimeData().text()
        self.card_dropped.emit(tracking_no, self.status_key)
        event.acceptProposedAction()

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.DragEnter:
            if event.mimeData().hasText():
                event.acceptProposedAction()
                self.scroll.setStyleSheet(theme_qss(f"""
                    QScrollArea {{
                        background-color: {_status_surface(self.color)};
                        border-radius: 16px;
                        border: 2px solid {_status_ring(self.color)};
                    }}
                    QScrollArea::viewport {{
                        background-color: transparent;
                    }}
                """))
                return True
            event.ignore()
            return True
        if event.type() == QEvent.Type.DragMove:
            if event.mimeData().hasText():
                event.acceptProposedAction()
                return True
            event.ignore()
            return True
        if event.type() == QEvent.Type.DragLeave:
            self.scroll.setStyleSheet(theme_qss("""
                QScrollArea {
                    background-color: @surface_alt;
                    border-radius: 16px;
                    border: 1px solid @border;
                }
                QScrollArea::viewport {
                    background-color: transparent;
                }
            """))
            event.accept()
            return True
        if event.type() == QEvent.Type.Drop:
            self.scroll.setStyleSheet(theme_qss("""
                QScrollArea {
                    background-color: @surface_alt;
                    border-radius: 16px;
                    border: 1px solid @border;
                }
                QScrollArea::viewport {
                    background-color: transparent;
                }
            """))
            if event.mimeData().hasText():
                tracking_no = event.mimeData().text()
                self.card_dropped.emit(tracking_no, self.status_key)
                event.acceptProposedAction()
            else:
                event.ignore()
            return True
        return super().eventFilter(watched, event)

    def _icon_for_key(self, status_key):
        k = (status_key or "").lower()
        if "bek" in k:
            return "⏳"
        if "tamir" in k:
            return "🛠️"
        if "parça" in k:
            return "📦"
        if "test" in k or "onay" in k:
            return "✅"
        if "teslim" in k:
            return "🚚"
        return "📌"

    def _set_empty_state_visible(self, visible):
        if not hasattr(self, "empty_label"):
            self.empty_label = QLabel("Bu sütun boş")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet(theme_qss("""
                color: @text_muted;
                font-size: 12px;
                font-weight: 700;
                padding: 22px 18px;
                border: 1px dashed @border;
                border-radius: 14px;
                background: @surface;
            """))
            self.cards_layout.insertWidget(0, self.empty_label)
        self.empty_label.setVisible(bool(visible))


class KanbanBoard(QScrollArea):
    card_clicked = pyqtSignal(str)
    action_triggered = pyqtSignal(str, str) # action, tracking_no
    status_changed = pyqtSignal(str, str) # tracking_no, new_status

    def __init__(self, db=None):
        super().__init__()
        self.setObjectName("KanbanBoard")
        self.db = db
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(theme_qss("""
            QScrollArea { background-color: transparent; border: none; }
            QScrollArea::viewport { background-color: transparent; }
        """))
        # Prevent horizontal scrolling if possible, let columns shrink
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.container = QWidget()
        self.container.setObjectName("KanbanBoardContainer")
        self.container.setStyleSheet(theme_qss("background: transparent;"))
        self.layout = QHBoxLayout(self.container)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(12, 10, 12, 10)
        self.layout.setSpacing(12)
        self.setWidget(self.container)
        self.viewport().setAcceptDrops(True)
        self.viewport().installEventFilter(self)
        
        self.columns = {}
        # We need a mapping from DB Status -> Column Key
        self.status_map = {
            "Bekliyor": "Bekliyor", "Beklemede": "Bekliyor", "İşleme Alınacak": "Bekliyor", "Isleme Alinacak": "Bekliyor",
            "NONE": "Bekliyor", "None": "Bekliyor", "Bilinmiyor": "Bekliyor", None: "Bekliyor",
            "Tamirde": "Tamirde", "Serviste": "Tamirde", "İşlemde": "Tamirde", "Islemde": "Tamirde", "Onarımda": "Tamirde", "Onarimda": "Tamirde",
            "Parça Bekliyor": "Parça Bekliyor", "Parca Bekliyor": "Parça Bekliyor", "Sipariş Geçildi": "Parça Bekliyor", "Siparis Gecildi": "Parça Bekliyor", "Parça": "Parça Bekliyor", "Parca": "Parça Bekliyor",
            "Test Sürecinde": "Test Sürecinde", "Test Surecinde": "Test Sürecinde", "Test Aşaması": "Test Sürecinde", "Test Asamasi": "Test Sürecinde", "Kontrol Ediliyor": "Test Sürecinde",
            "Onay Bekleyen": "Test Sürecinde", "Onay Bekliyor": "Test Sürecinde",
            "Hazır": "Test Sürecinde", "Bitti": "Test Sürecinde", "Tamamlandı": "Test Sürecinde", "Tamir Edildi": "Test Sürecinde",
            "Kabul Edildi": "Bekliyor",
            "Teslim Edildi": "Teslim Edildi", "Teslim": "Teslim Edildi",
            "İptal": "İptal", "Iptal": "İptal", "İptal Edildi": "İptal", "Iptal Edildi": "İptal"
        }
        
        self.setup_columns()

    def apply_theme_styles(self):
        if _is_classic_appearance():
            self.setStyleSheet("""
                QScrollArea#KanbanBoard {
                    background-color: #F3F6FA;
                    border: none;
                }
                QScrollArea#KanbanBoard::viewport {
                    background-color: #F3F6FA;
                    border: none;
                }
                QScrollBar:horizontal {
                    background: #E7ECF3;
                    height: 10px;
                    border: none;
                }
                QScrollBar::handle:horizontal {
                    background: #AEB8C7;
                    min-width: 32px;
                    border-radius: 4px;
                }
            """)
            self.container.setStyleSheet("#KanbanBoardContainer { background: #F3F6FA; border: none; }")
        else:
            self.setStyleSheet(theme_qss("""
                QScrollArea { background-color: transparent; border: none; }
                QScrollArea::viewport { background-color: transparent; }
            """))
            self.container.setStyleSheet(theme_qss("background: transparent;"))
        colors = get_kanban_colors()
        for key, col in self.columns.items():
            col.update_color(colors.get(key, tc("accent")))
            col.apply_theme_styles()
        
    def setup_columns(self):
        from src.utils.design_system import DesignTokens
        # Title, ColumnKey (Main Status), Color
        colors = get_kanban_colors()
        cols = [
            ("BEKLİYOR", "Bekliyor", colors["Bekliyor"]),
            ("TAMİRDE", "Tamirde", colors["Tamirde"]),
            ("PARÇA BEKLİYOR", "Parça Bekliyor", colors["Parça Bekliyor"]),
            ("TEST / ONAY", "Test Sürecinde", colors["Test Sürecinde"]),
            ("TESLİM", "Teslim Edildi", colors["Teslim Edildi"]),
            ("İPTAL", "İptal", colors["İptal"])
        ]
        
        for title, key, color in cols:
            col = KanbanColumn(title, key, color, db=self.db)
            col.card_dropped.connect(self.on_drop)
            self.layout.addWidget(col)
            self.columns[key] = col
            
    def on_drop(self, tracking_no, new_status):
        self.action_triggered.emit(f"update_status:{new_status}", tracking_no)

    def eventFilter(self, watched, event):
        if watched is self.viewport():
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasText():
                    event.acceptProposedAction()
                else:
                    event.ignore()
                return True
            if event.type() == QEvent.Type.DragMove:
                if event.mimeData().hasText():
                    event.acceptProposedAction()
                else:
                    event.ignore()
                return True
            if event.type() == QEvent.Type.Drop:
                if not event.mimeData().hasText():
                    event.ignore()
                    return True

                tracking_no = event.mimeData().text()
                try:
                    pos = event.position().toPoint()
                except Exception:
                    try:
                        pos = event.pos()
                    except Exception:
                        pos = None

                if pos is None:
                    event.ignore()
                    return True

                container_pos = self.container.mapFrom(self.viewport(), pos)
                target_key = None
                for key, col in self.columns.items():
                    if col.geometry().contains(container_pos):
                        target_key = key
                        break

                if target_key:
                    self.on_drop(tracking_no, target_key)
                    event.acceptProposedAction()
                else:
                    event.ignore()
                return True

        return super().eventFilter(watched, event)

    def refresh(self, devices):
        if not getattr(self, "_theme_initialized", False):
            self.apply_theme_styles()
            self._theme_initialized = True
        # Group devices by status
        grouped = {k: [] for k in self.columns.keys()}
        unmapped_statuses = {}
        
        for dev in devices:
            try:
                raw_status = dev["status"]
            except (IndexError, KeyError, TypeError):
                # Fallback if row is not indexed by name
                raw_status = dev[8] if len(dev) > 8 else "Bekliyor"

            normalized_status = normalize_device_status(raw_status)
            if not is_active_device_status(normalized_status):
                continue

            target_col_key = self.status_map.get(normalized_status) or self.status_map.get(raw_status)
            
            if target_col_key and target_col_key in self.columns:
                grouped[target_col_key].append(dev)
            else:
                try:
                    tracking_no = dev["tracking_no"]
                except Exception:
                    tracking_no = dev[1] if len(dev) > 1 else "Unknown"
                    
                if raw_status not in unmapped_statuses: unmapped_statuses[raw_status] = []
                unmapped_statuses[raw_status].append(tracking_no)

        # Set devices to columns (Lazy load starts inside)
        signals = {
            'clicked': self.card_clicked.emit,
            'action': self.action_triggered.emit
        }
        
        for key, col_devices in grouped.items():
            self.columns[key].set_devices(col_devices, signals)
        
        # Summary report of unmapped statuses
        if unmapped_statuses:
            logger.warning("[KANBAN] Eşlenmemiş durumlar bulundu")
            logger.warning(
                "Toplam %s cihaz mapping eksikliği nedeniyle gösterilemiyor",
                sum(len(v) for v in unmapped_statuses.values())
            )
            for status, devices in unmapped_statuses.items():
                logger.warning(
                    "  - '%s' durumu: %s cihaz (#%s)",
                    status,
                    len(devices),
                    ", #".join(devices)
                )
            logger.warning("Lütfen kanban_board.py içindeki status_map'e bu durumları ekleyin.")

