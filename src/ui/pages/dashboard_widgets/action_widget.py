# -*- coding: utf-8 -*-

"""
Action Widget
Tablo hücresi içindeki işlem butonları grubu
"""
from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton, QFrame, 
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QAction
from src.utils.theme_colors import tc, theme_qss
from .svg_icon_button import SvgIconButton
from src.utils.role_utils import is_admin_role


class ActionWidget(QWidget):
    """Tablo hücresi içindeki işlem butonları grubu (SVG İkonlu)"""
    
    def __init__(self, tracking_no, parent_page):
        super().__init__()
        self.tracking_no = tracking_no
        self.parent_page = parent_page
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # SVG Paths
        icon_info = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>"""
        icon_settings = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>"""
        icon_building = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><line x1="9" y1="22" x2="9" y2="22.01"></line><line x1="15" y1="22" x2="15" y2="22.01"></line><line x1="12" y1="22" x2="12" y2="22.01"></line><line x1="12" y1="2" x2="12" y2="22"></line><line x1="4" y1="10" x2="20" y2="10"></line><line x1="4" y1="16" x2="20" y2="16"></line></svg>"""
        icon_whatsapp = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path></svg>"""
        icon_barcode = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 5v14"/><path d="M8 5v14"/><path d="M12 5v14"/><path d="M17 5v14"/><path d="M21 5v14"/></svg>"""
        icon_payment = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"></rect><line x1="1" y1="10" x2="23" y2="10"></line></svg>"""
        icon_photo = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>"""
        icon_trash = """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>"""

        # Definitions: Icon SVG, Color, HoverColor, Tooltip, Callback
        actions = [
            (icon_info,     tc("warning"), tc("warning"), "Detaylar", "on_info"),
            (icon_settings, tc("text_muted"), tc("text"), "İşlemler (Düzenle)", "on_edit"),
            (icon_building, tc("text"), tc("selection_text"), "Müşteri / Bayi", "on_customer"),
            (icon_whatsapp, tc("success"), tc("success"), "WhatsApp", "on_whatsapp"),
            (icon_payment,  tc("accent"), tc("accent_hover"), "Ödeme Al", "on_payment"),
            (icon_photo,    tc("warning"), tc("warning"), "Fotoğraflar", "on_photos"),
            (icon_barcode,  tc("accent_hover"), tc("accent_pressed"), "Barkod Yazdır", "on_barcode"),
            (icon_trash,    tc("danger"), tc("danger"), "Kaydı Sil", "on_archive")
        ]

        # Role check
        role = "Personel"
        if hasattr(self.parent_page.main_window, 'user_data') and self.parent_page.main_window.user_data:
            user_data = self.parent_page.main_window.user_data
            try:
                role = user_data["role"]
            except Exception:
                try:
                    role = user_data[3]
                except Exception:
                    role = "Personel"
        
        is_admin = is_admin_role(role)

        for svg, color, h_color, tip, func_name in actions:
            # Filter logic - Only admin can delete
            if func_name == "on_archive" and not is_admin:
                continue
            
            # Create button
            btn = SvgIconButton(svg, color, h_color, tip)
            callback = getattr(self, func_name)
            btn.clicked.connect(callback)
            layout.addWidget(btn)
        
    def on_info(self):
        self.parent_page.open_context_menu_action("info", self.tracking_no)

    def on_edit(self):
        self.parent_page.open_edit_dialog(self.tracking_no)
        
    def on_customer(self):
        self.parent_page.open_context_menu_action("customer", self.tracking_no)

    def on_sms(self):
        self.parent_page.open_context_menu_action("sms", self.tracking_no)

    def on_whatsapp(self):
        self.parent_page.open_context_menu_action("whatsapp", self.tracking_no)

    def on_payment(self):
        """Tahsilat / ödeme ekranını aç (ModernPaymentDialog ile)"""
        try:
            self.parent_page.open_context_menu_action("payment", self.tracking_no)
        except Exception as e:
            self.parent_page.notify(f"Ödeme ekranı hatası: {e}", "error")
        
    def on_photos(self):
        """Fotoğraf yöneticisi aç"""
        try:
            from src.ui.dialogs.photo_gallery_dialog import PhotoGalleryDialog
            dlg = PhotoGalleryDialog(self.parent_page.db, self.tracking_no, self.parent_page)
            dlg.exec()
        except ImportError:
            self.parent_page.notify("Fotoğraf modülü bulunamadı.", "error")

    def on_barcode(self):
        """Barkod yazdır"""
        self.parent_page.print_barcode(self.tracking_no)

    def on_archive(self):
        """Kaydı sil"""
        self.parent_page.delete_service(self.tracking_no)


