# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt, QSize, QByteArray
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

try:
    from PyQt6.QtSvg import QSvgRenderer
except ImportError:
    QSvgRenderer = None

from src.ui.dialogs.simple_confirm import SimpleConfirmDialog
from src.utils.theme_colors import tc, theme_qss
from src.utils.role_utils import is_admin_role


class SvgIconButton(QPushButton):
    """Button with colored background and white SVG icon"""
    def __init__(self, svg_content, bg_color, hover_color, tooltip, parent=None):
        super().__init__(parent)
        self._svg_content = svg_content
        self._bg_color = bg_color
        self._hover_color = hover_color
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)

        self.apply_theme_styles()

    def apply_theme_styles(self):
        icon_pixmap = self.render_svg(self._svg_content)
        self.setIcon(QIcon(icon_pixmap))
        self.setIconSize(QSize(18, 18))
        self.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: {self._bg_color};
                border: 1px solid transparent;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {self._hover_color};
                border: 1px solid rgba(255, 255, 255, 0.30);
            }}
            QPushButton:pressed {{
                background-color: {self._bg_color};
                margin-top: 1px;
            }}
        """))

    def render_svg(self, svg_content):
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        if QSvgRenderer is None:
            return pixmap

        renderer = QSvgRenderer(QByteArray(str(svg_content or '').encode()))
        if not renderer.isValid() or pixmap.isNull():
            return pixmap

        painter = QPainter(pixmap)
        if not painter.isActive():
            return pixmap
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), Qt.GlobalColor.white)
        painter.end()
        return pixmap

class ActionWidget(QWidget):
    """Tablo hücresi içindeki 9'lu işlem butonları grubu (SVG İkonlu)"""
    def __init__(self, tracking_no, parent_page):
        super().__init__()
        self.tracking_no = tracking_no
        self.parent_page = parent_page
        self._buttons = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6) # Better spacing for better touch/click targets
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # SVG Paths
        icon_info = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>"""
        icon_settings = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>"""
        icon_building = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><line x1="9" y1="22" x2="9" y2="22.01"></line><line x1="15" y1="22" x2="15" y2="22.01"></line><line x1="12" y1="22" x2="12" y2="22.01"></line><line x1="12" y1="2" x2="12" y2="22"></line><line x1="4" y1="10" x2="20" y2="10"></line><line x1="4" y1="16" x2="20" y2="16"></line></svg>"""
        icon_sms = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>"""
        icon_whatsapp = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>"""
        icon_barcode = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5v14"/><path d="M8 5v14"/><path d="M12 5v14"/><path d="M17 5v14"/><path d="M21 5v14"/></svg>"""
        icon_payment = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>"""
        icon_photo = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>"""
        icon_trash = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>"""

        # Definitions: Icon SVG, Color, HoverColor, Tooltip, Callback
        actions = [
            (icon_info,     tc("warning"), tc("warning"), "Detaylar", "on_info"),       # Orange (Info)
            (icon_settings, tc("text"), tc("text"), "Teknisyen Paneli", "on_edit"),# Dark Grey/Blue (Edit)
            (icon_building, tc("text"), tc("text"), "Müşteri / Bayi", "on_customer"),# Dark Blue (Customer)
            (icon_whatsapp, tc("success"), tc("success"), "WhatsApp", "on_whatsapp"),   # Light Green
            (icon_payment,  tc("accent"), tc("accent"), "Ödeme Al", "on_payment"),    # Teal (Payment)
            (icon_photo,    tc("warning"), tc("warning"), "Fotoğraflar", "on_photos"),  # Dark Orange (Photos)
            (icon_barcode,  tc("danger"), tc("danger"), "Barkod Yazdır", "on_barcode"), # Pink (Barcode)
            (icon_trash,    tc("danger"), tc("danger"), "Kaydı Sil", "on_archive")      # Red (Delete)
        ]

        role = "Personel"
        
        # Get user role - handle both dict and tuple formats
        if hasattr(self.parent_page.main_window, 'user_data') and self.parent_page.main_window.user_data:
            user_data = self.parent_page.main_window.user_data
            if isinstance(user_data, dict):
                role = user_data.get('role', 'Personel')
            else:
                try:
                    role = user_data['role']
                except Exception:
                    role = "Personel"
        
        # Check admin status
        is_admin = is_admin_role(role)

        for svg, color, h_color, tip, func_name in actions:
            # Filter logic
            if func_name == "on_archive" and not is_admin:
                continue # Only admin can delete typically
            
            # Show others
            btn = SvgIconButton(svg, color, h_color, tip)
            callback = getattr(self, func_name)
            btn.clicked.connect(callback)
            layout.addWidget(btn)
            self._buttons.append(btn)

    def apply_theme_styles(self):
        for btn in self._buttons:
            if hasattr(btn, "apply_theme_styles"):
                btn.apply_theme_styles()
        
    def on_info(self):
        self.parent_page.open_context_menu_action("info", self.tracking_no)

    def on_edit(self):
        self.parent_page.open_technician_panel(self.tracking_no)
        
    def on_customer(self):
        self.parent_page.open_context_menu_action("customer", self.tracking_no)

    def on_sms(self):
        self.parent_page.open_context_menu_action("sms", self.tracking_no)

    def on_whatsapp(self):
        self.parent_page.open_context_menu_action("whatsapp", self.tracking_no)

    def on_payment(self):
        self.parent_page.open_context_menu_action("payment", self.tracking_no)
        
    def on_photos(self):
        # Open Photo Manager
        try:
             from src.ui.dialogs.photo_gallery_dialog import PhotoGalleryDialog
             dlg = PhotoGalleryDialog(self.parent_page.db, self.tracking_no, self.parent_page)
             dlg.exec()
        except ImportError:
             self.parent_page.notify("Galeri modülü yüklenemedi.", "error")
        except Exception as e:
             self.parent_page.notify(f"Galeri hatası: {e}", "error")

    def on_barcode(self):
        self.parent_page.print_service(self.tracking_no)

    def on_archive(self):
        self.parent_page.delete_service(self.tracking_no)


class StatCard(QFrame):
    def __init__(self, title, value, icon_svg, color, callback=None, parent=None):
        super().__init__(parent)
        self.callback = callback
        self.value = value
        self.setObjectName("DashboardStatCard")
        self.setFixedHeight(95) # Optimized size
        
        if self.callback:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 10)) 
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)
        
        self.title = title
        self.icon_svg = icon_svg
        self.color = color
        
        self.apply_theme_styles()
        
    def apply_theme_styles(self):
        color = self.color
        tint = QColor(color)
        tint.setAlphaF(0.10)
        tint_hex = tint.name(QColor.NameFormat.HexArgb)
        self.setStyleSheet(theme_qss(f"""
            QFrame#DashboardStatCard {{
                background-color: @surface_alt;
                border-radius: 16px;
                border: 1px solid @border;
            }}
            QFrame#DashboardStatCard:hover {{
                border: 1px solid {color};
                background-color: @surface;
            }}
        """))
        
        # If we have content, we need to refresh it. 
        # Since init might not be finished, we check for existence of internal widgets
        if hasattr(self, "val_lbl"):
             self.val_lbl.setStyleSheet(theme_qss(f"color: @text; font-size: 26px; font-weight: 800; font-family: 'Inter', 'Segoe UI'; border:none; background:transparent;"))
        if hasattr(self, "title_lbl"):
             self.title_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border:none; background:transparent;"))
        if hasattr(self, "icon_container"):
             self.icon_container.setStyleSheet(theme_qss(f"background-color: {tint_hex}; border-radius: 23px;"))
             if self.icon_svg.startswith("<svg"):
                 icon_pixmap = self.render_colored_svg(self.icon_svg, color, size=24)
                 self.icon_container.setPixmap(icon_pixmap)
        if hasattr(self, "val_lbl") and hasattr(self, "title_lbl") and hasattr(self, "icon_container"):
             return
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # Left Side: Icon in Circle
        self.icon_container = QLabel()
        self.icon_container.setFixedSize(46, 46)
        # We use a semi-transparent background for the icon
        self.icon_container.setStyleSheet(theme_qss(f"""
            background-color: {tint_hex}; 
            border-radius: 23px; 
        """))
        self.icon_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Render Icon
        if self.icon_svg.startswith("<svg"):
            icon_pixmap = self.render_colored_svg(self.icon_svg, color, size=24)
            self.icon_container.setPixmap(icon_pixmap)
        else:
            # Assume Emoji or plain text
            self.icon_container.setText(self.icon_svg)
            self.icon_container.setStyleSheet(theme_qss(f"font-size: 24px; background-color: {tint_hex}; border-radius: 23px;"))
        
        layout.addWidget(self.icon_container)
        
        # Right Side: Text Info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        # Value (Big Number)
        self.val_lbl = QLabel(str(self.value))
        self.val_lbl.setStyleSheet(theme_qss(f"color: @text; font-size: 26px; font-weight: 800; font-family: 'Inter', 'Segoe UI'; border:none; background:transparent;"))
        text_layout.addWidget(self.val_lbl)
        
        # Title (Label)
        self.title_lbl = QLabel(self.title)
        self.title_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; border:none; background:transparent;"))
        text_layout.addWidget(self.title_lbl)
        
        layout.addLayout(text_layout)
        layout.addStretch() # Push everything to left

    def render_colored_svg(self, svg_content, color_hex, size=24):
        """Helper to render an SVG string into a QPixmap with a specific color"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        if QSvgRenderer is None or pixmap.isNull():
            return pixmap

        # Fixed str() call to encode()
        renderer = QSvgRenderer(QByteArray(str(svg_content or '').encode()))
        if not renderer.isValid():
            return pixmap

        painter = QPainter(pixmap)
        if not painter.isActive():
            return pixmap
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor(color_hex))
        painter.end()
        return pixmap

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.callback:
            self.callback()
        super().mousePressEvent(event)
# ActionWidget and ActionButton are already defined here, but if they were supposed to be imported:
# from src.ui.pages.dashboard_widgets.action_widget import ActionWidget
# from src.ui.pages.dashboard_widgets.action_button import ActionButton


class ActionButton(QPushButton):
    def apply_theme_styles(self):
        color = self.color
        hover_bg = QColor(color)
        hover_bg.setAlphaF(0.22)
        pressed_bg = QColor(color)
        pressed_bg.setAlphaF(0.30)
        self.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background-color: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 14px;
                text-align: center;
                padding: 0px;
                font-size: 22px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg.name(QColor.NameFormat.HexArgb)};
                border: 1px solid {color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg.name(QColor.NameFormat.HexArgb)};
                border: 1px solid {color};
            }}
            QPushButton:disabled {{
                background-color: @surface_alt;
                color: @text_muted;
                border: 1px solid @border;
            }}
        """))

    def __init__(self, text, icon, color, callback):
        super().__init__()
        self.setText(icon)          # Yalnızca ikon göster
        self.setToolTip(text)       # Metin tooltip'te görünsün
        self.color = color
        self.clicked.connect(callback)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(48, 48)   # Kare kompakt boyut
        self.setObjectName("DashboardActionButton")
        self.apply_theme_styles()


