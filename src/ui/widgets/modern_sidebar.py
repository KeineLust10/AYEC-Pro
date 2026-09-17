# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QScrollArea, 
                             QFrame, QLabel, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QColor, QCursor
from src.utils.theme_colors import theme_qss
from src.utils.logger import logger

class SidebarItem(QWidget):
    """
    Menü Elemanı. Tıklanabilir bir widget.
    Alt menüsü varsa ok işareti gösterir ve açılır/kapanır.
    """
    clicked = pyqtSignal(object) # page_id

    def __init__(self, title, icon_text, page_id=None, level=0):
        super().__init__()
        self.page_id = page_id
        self.title = title
        self.level = level
        self.is_expanded = False
        
        # Ana Layout (Dikey: Buton Satırı + Alt Menü Container)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # --- 1. Satır (Görünür Kısım) ---
        self.row_frame = QFrame()
        self.row_frame.setFixedHeight(50) # Sabit Yükseklik (Daha geniş)
        self.row_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.row_frame.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # The following lines are added based on the "Code Edit" in the instruction.
        # Note: These methods are typically called on QScrollArea, not QFrame.
        # Assuming the user intends to add these to the QFrame for some reason,
        # or there's a misunderstanding in the instruction's context.
        # Also, the original instruction had a syntax error, which is corrected here.
        # If these lines are meant for a QScrollArea, they should be moved.
        # For now, faithfully applying the edit as shown in the instruction's context.
        # If this QFrame is later wrapped in a QScrollArea, these calls might be redundant or incorrect.
        # However, the instruction explicitly places them here.
        # Correcting the syntax error from the instruction's "Code Edit"
        # Scroll Policy removed (invalid on QFrame)
        self.row_frame.setStyleSheet(theme_qss(self.get_row_style(False)))
        
        row_layout = QHBoxLayout(self.row_frame)
        row_layout.setContentsMargins(20 + (level * 20), 0, 15, 0) # Girinti
        row_layout.setSpacing(15)
        
        # İkon (Varsayılan nokta, eğer icon_text yoksa)
        display_icon = icon_text if icon_text else ("●" if level > 0 else "■")
        self.lbl_icon = QLabel(display_icon)
        self.lbl_icon.setFixedSize(24, 24)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_icon.setStyleSheet(theme_qss("color: @text_muted; font-size: 16px;"))
        
        # Başlık
        self.lbl_text = QLabel(title)
        self.lbl_text.setFont(QFont("Segoe UI", 11 if level == 0 else 10))
        self.lbl_text.setStyleSheet(theme_qss("color: @text;"))
        
        # Ok İkonu (Alt menü varsa gösterilecek)
        self.lbl_arrow = QLabel("▼")
        self.lbl_arrow.setFixedSize(20, 20)
        self.lbl_arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_arrow.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
        self.lbl_arrow.hide()
        
        row_layout.addWidget(self.lbl_icon)
        row_layout.addWidget(self.lbl_text)
        row_layout.addStretch()
        row_layout.addWidget(self.lbl_arrow)
        
        self.main_layout.addWidget(self.row_frame)
        
        # --- 2. Alt Menü Container (Başlangıçta Gizli) ---
        self.children_container = QWidget()
        self.children_layout = QVBoxLayout(self.children_container)
        self.children_layout.setContentsMargins(0, 0, 0, 0)
        self.children_layout.setSpacing(1) # Alt öğeler arası boşluk
        self.children_container.hide()
        self.children_container.setMaximumHeight(0)
        
        self.main_layout.addWidget(self.children_container)
        
        # Animations
        self.anim = QPropertyAnimation(self.children_container, b"maximumHeight")
        self.anim.setDuration(300)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        # Event Filter kullanmak yerine MousePressEvent override edilebilir ama 
        # QFrame üzerinde MousePress yakalamak daha temiz.
        self.row_frame.mousePressEvent = self.on_row_clicked
        self.row_frame.keyPressEvent = self.on_row_key_press

    def add_children(self, children_data):
        self.lbl_arrow.show()
        for data in children_data:
            child_item = SidebarItem(data['title'], data.get('icon', ''), data.get('id'), level=self.level + 1)
            child_item.clicked.connect(self.propagate_click)
            self.children_layout.addWidget(child_item)

    def on_row_clicked(self, event):
        if self.lbl_arrow.isVisible():
            # Alt menüsü var, genişlet/daralt
            self.toggle_expand()
        else:
            # Alt menü yok, sayfa aç
            self.clicked.emit(self.page_id)

    def on_row_key_press(self, event):
        if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space]:
            self.on_row_clicked(None)
        else:
            # Fix: Super call
            QFrame.keyPressEvent(self.row_frame, event)

    def toggle_expand(self):
        self.is_expanded = not self.is_expanded
        
        if self.is_expanded:
            self.children_container.show()
            # Calculate full height based on children count
            row_height = 51 # 50px + 1px spacing
            full_height = self.children_layout.count() * row_height
            self.anim.stop()
            self.anim.setStartValue(self.children_container.height())
            self.anim.setEndValue(full_height)
        else:
            self.anim.stop()
            self.anim.setStartValue(self.children_container.height())
            self.anim.setEndValue(0)
            # Need a way to hide after finish without multiple connections
            try:
                self.anim.finished.disconnect()
            except Exception as e:
                logger.debug(f"ModernSidebar finished.disconnect skipped: {e}")
            self.anim.finished.connect(lambda: self.children_container.hide() if not self.is_expanded else None)

        self.anim.start()
        self.lbl_arrow.setText("▲" if self.is_expanded else "▼")
        self.row_frame.setStyleSheet(theme_qss(self.get_row_style(self.is_expanded)))

    def get_row_style(self, active):
        base_color = "transparent"
        if active:
            base_color = "@surface_alt"
        
        return f"""
            QFrame {{
                background-color: {base_color};
                border-radius: 4px;
                outline: none;
            }}
            QFrame:hover {{
                background-color: @surface_alt;
            }}
            QFrame:focus {{
                border: 1px solid @accent;
                background-color: @selection_bg;
            }}
        """

    def propagate_click(self, page_id):
        self.clicked.emit(page_id)


class ModernSidebar(QWidget):
    page_selected = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(260)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("ModernSidebar")
        self.setStyleSheet(theme_qss("""
            QWidget#ModernSidebar {
                background-color: @surface;
            }
            QLabel {
                color: @text;
            }
        """))
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Header (Logo) ---
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet(theme_qss("background-color: @surface_alt; border-bottom: 1px solid @border;"))
        hl = QHBoxLayout(header)
        
        lbl_logo = QLabel("🔧")
        lbl_logo.setFont(QFont("Segoe UI Emoji", 26))
        lbl_logo.setStyleSheet(theme_qss("color: @accent; background: transparent;"))
        
        lbl_title = QLabel("BULUT TECH\nServis Sistemi")
        lbl_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        lbl_title.setStyleSheet(theme_qss("color: @text; background: transparent;"))
        
        hl.addWidget(lbl_logo)
        hl.addWidget(lbl_title)
        hl.addStretch()
        layout.addWidget(header)
        
        # --- Menü Listesi (Scroll) ---
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(theme_qss("""
            QScrollArea { border: none; background-color: @surface; }
            QScrollBar:vertical { width: 5px; background: transparent; }
            QScrollBar::handle:vertical { background: @border; border-radius: 2px; }
            QScrollBar::handle:vertical:hover { background: @text_muted; }
        """))
        
        container = QWidget()
        container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        container.setStyleSheet(theme_qss("background-color: @surface;"))
        self.menu_layout = QVBoxLayout(container)
        self.menu_layout.setContentsMargins(10, 20, 10, 20) # Kenar boşlukları
        self.menu_layout.setSpacing(5) # Elemanlar arası boşluk
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # --- Footer ---
        footer = QFrame()
        footer.setFixedHeight(50)
        footer.setStyleSheet(theme_qss("background-color: @surface_alt; border-top: 1px solid @border;"))
        fl = QHBoxLayout(footer)
        fl.addStretch()
        lbl_ver = QLabel("v2.1.0")
        lbl_ver.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
        fl.addWidget(lbl_ver)
        fl.addSpacing(10)
        layout.addWidget(footer)
        
        self.init_menu_items()

    def init_menu_items(self):
        # Menü Yapısı
        structure = [
            {"title": "Ana Sayfa", "icon": "🏠", "id": 40},
            
            {"title": "Operasyon", "icon": "⚡", "children": [
                 {"title": "Yeni Servis Kaydı", "id": 150},
                 {"title": "Servis Listesi", "id": 41},
                 {"title": "Teknisyen Paneli", "id": 60},
                 {"title": "AI Operasyon Asistanı", "id": 170}, # YENİ
                 {"title": "Randevu & Takvim", "id": 30},
                 {"title": "Stok Yönetimi", "id": 50}
            ]},
            
            {"title": "Müşteri & Finans", "icon": "👥", "children": [
                 {"title": "Müşteri Listesi", "id": 21},
                 {"title": "Müşteri&Bayi Ekle", "id": 22},
                 {"title": "Gelir/Gider", "id": 101}
            ]},

            {"title": "Yönetim Paneli", "icon": "📊", "children": [
                 {"title": "Yönetici Özeti", "id": 45},
                 {"title": "Personel Yönetimi", "id": 10}, 
                 {"title": "Raporlar", "id": 111},
                 {"title": "Hizmet Ayarları", "id": 140}
            ]},

            {"title": "Sistem", "icon": "⚙️", "children": [
                 {"title": "Yedekleme Merkezi", "id": 180}, # YENİ
                 {"title": "Bilgi Bankası", "id": 160},
                 {"title": "Teknik Destek", "id": 70}, 
                 {"title": "Genel Ayarlar", "id": 130},
                 {"title": "Güvenli Çıkış", "id": -1}
            ]}
        ]
        
        for item_data in structure:
            self.add_item(item_data)
            
        self.menu_layout.addStretch()

    def add_item(self, data):
        item = SidebarItem(data['title'], data.get('icon'), data.get('id'))
        item.clicked.connect(self.page_selected.emit)
        if 'children' in data:
            item.add_children(data['children'])
        self.menu_layout.addWidget(item)
