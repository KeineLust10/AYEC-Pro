# -*- coding: utf-8 -*-

"""
Modern Side Menu - PyQt5
Gradient tasarım, animasyonlar ve düzgün menü yapısı
"""
from PyQt6.QtWidgets import (QFrame, QVBoxLayout, QLabel, QPushButton, 
                             QWidget, QScrollArea, QHBoxLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, Qt, QVariantAnimation
from PyQt6.QtGui import QFont, QColor, QLinearGradient, QPainter, QAction


class SideMenu(QFrame):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
        self.setFixedWidth(250)
        self.active_button = None
        
        self.setObjectName("SideMenu")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # --- Header with Logo ---
        self.create_header()
        
        # --- Scroll Area for Menu ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        # ScrollBar'ı otomatik yap (İhtiyaç duyulursa görünsün)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setObjectName("SideMenuScroll")
        
        self.menu_container = QWidget()
        self.menu_container.setObjectName("SideMenuContent")
        self.menu_layout = QVBoxLayout(self.menu_container)
        self.menu_layout.setContentsMargins(12, 10, 12, 10)
        self.menu_layout.setSpacing(4)
        
        # --- MENÜ ÖĞELERİ ---
        self.create_menu_items()
        
        self.menu_layout.addStretch()
        self.scroll_area.setWidget(self.menu_container)
        self.layout.addWidget(self.scroll_area)
        
        # --- Footer ---
        self.create_footer()
    
    def create_header(self):
        """Başlık alanı - Kurumsal Marka"""
        header_frame = QFrame()
        header_frame.setObjectName("SideMenuHeader")
        header_frame.setFixedHeight(110)
        
        main_layout = QHBoxLayout(header_frame)
        main_layout.setContentsMargins(20, 20, 10, 20)
        main_layout.setSpacing(15)
        
        # 1. Logo (Basitleştirilmiş Bulut İkonu)
        lbl_icon = QLabel("🌩️") # Modern fırtına/güç bulutu
        lbl_icon.setObjectName("SideMenuLogo")
        lbl_icon.setFixedSize(50, 50)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_icon.setStyleSheet("""
            QLabel {
                font-size: 32px;
                color: #2980b9; 
                background: white;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }
        """)
        
        # 2. Marka İsim
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        
        lbl_title = QLabel("bulutteknoloji")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        # Kurumsal Mavi-Sarı Geçiş (Gradient taklidi text shadow ile)
        lbl_title.setStyleSheet("""
            color: #2c3e50; 
            letter-spacing: -0.5px;
        """) 
        
        lbl_subtitle = QLabel("Bilişim ve Güvenlik")
        lbl_subtitle.setFont(QFont("Segoe UI", 8))
        lbl_subtitle.setStyleSheet("color: #7f8c8d;")
        
        text_layout.addWidget(lbl_title)
        text_layout.addWidget(lbl_subtitle)
        
        main_layout.addWidget(lbl_icon)
        main_layout.addLayout(text_layout)
        main_layout.addStretch()
        
        self.layout.addWidget(header_frame)
    
    def create_menu_items(self):
        """Menü öğelerini oluştur - Hiyerarşik ve Eksiksiz Yapı"""
        
        # 1. Dashboard
        self.add_menu_item("Genel Bakış", 40, "📊")
        self.add_menu_item("Yönetici Özeti", 45, "📈")
        
        self.add_separator()
        
        # 2. Operasyon
        self.add_section_label("OPERASYON")
        self.add_menu_item("Teknisyen Paneli", 60, "🛠️")
        self.add_menu_item("İş Emirleri (Pano)", 41, "📋")
        self.add_menu_item("Durum Ekranı", 42, "🖥️")
        self.add_menu_item("Hızlı Kayıt", 150, "➕")
        
        # 3. Müşteri
        self.add_section_label("MÜŞTERİ")
        self.add_menu_item("Müşteri Hub", 21, "👥")
        self.add_menu_item("Randevular", 30, "📅")
        self.add_menu_item("Hatırlatıcılar", 90, "🔔")
        # self.add_menu_item("Sözleşmeler", 25, "📝") # Sayfası henüz yok
        
        with_separator = True
        if with_separator: self.add_separator()

        # 4. Ticari
        self.add_section_label("TİCARİ")
        self.add_menu_item("Stok Yönetimi", 50, "📦") # ID Düzeltildi: 999 -> 50
        # self.add_menu_item("Hızlı Satış (POS)", 220, "💰") # Sayfası henüz yok
        self.add_menu_item("Hizmet & Fiyatlar", 140, "🏷️")
        
        # 5. Finans & Rapor
        self.add_section_label("FİNANS & RAPOR")
        self.add_menu_item("Gelir / Gider", 101, "💵")
        self.add_menu_item("Raporlar", 111, "📊")

        self.add_separator()

        # 6. Sistem
        self.add_section_label("SİSTEM")
        self.add_menu_item("AI Asistan", 170, "🤖")
        self.add_menu_item("Yedekleme Merkezi", 180, "💾") # Eklendi
        self.add_menu_item("Bilgi Bankası", 160, "📚")
        self.add_menu_item("Personel", 10, "👔")
        self.add_menu_item("Ayarlar", 130, "⚙️")
        self.add_menu_item("Destek & Yardım", 70, "❓")

    def add_separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #34495e; margin-top: 5px; margin-bottom: 5px;")
        line.setFixedHeight(1)
        self.menu_layout.addWidget(line)

    def contextMenuEvent(self, event):
        pass

    def add_section_label(self, text):
        """Bölüm başlığı ekle"""
        lbl = QLabel(text)
        lbl.setObjectName("SideMenuSection")
        lbl.setStyleSheet("""
            color: #94a3b8; 
            font-weight: 700; 
            font-size: 11px; 
            letter-spacing: 0.5px;
            margin-top: 15px; 
            margin-bottom: 8px; 
            padding-left: 12px;
            font-family: 'Segoe UI';
        """)
        self.menu_layout.addWidget(lbl)
    
    def add_menu_item(self, text, index, icon_text):
        """Menü öğesi ekle - Premium Buton"""
        btn = QPushButton()
        btn.setFixedHeight(42)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("index", index)
        # Context Menu Policy
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda pos, b=btn, t=text: self.show_context_menu(pos, b, t))
        
        # Premium Stil
        btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #e2e8f0;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 12px;
                font-size: 13px;
                font-family: 'Segoe UI';
                margin-bottom: 2px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: white;
            }
            QPushButton[active="true"] {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1d4ed8);
                color: white;
                font-weight: 600;
                border-left: 3px solid #60a5fa;
            }
        """)

        layout = QHBoxLayout(btn)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(12)
        
        # İkon
        lbl_icon = QLabel(icon_text)
        lbl_icon.setFixedSize(20, 20)
        lbl_icon.setStyleSheet("background: transparent; color: inherit;")
        
        # Metin
        lbl_text = QLabel(text)
        lbl_text.setStyleSheet("background: transparent; border: none; color: inherit;")
        
        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_text)
        layout.addStretch()
        
        btn.clicked.connect(lambda ch, idx=index: self.on_menu_click(btn, idx))
        btn.setToolTip(text)
        btn.setStatusTip(f"{text} sayfasını aç")
        self.menu_layout.addWidget(btn)
        return btn
    
    def add_group_item(self, title, sub_items, icon_text):
        """Alt menülü grup öğesi ekle"""
        # Ana buton
        btn_group = QPushButton()
        btn_group.setFixedHeight(44)
        btn_group.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(btn_group)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(12)
        
        lbl_icon = QLabel(icon_text)
        lbl_icon.setObjectName("MenuItemIcon")
        lbl_icon.setFixedSize(22, 22)
        lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_text = QLabel(title)
        lbl_text.setObjectName("MenuItemText")
        
        lbl_arrow = QLabel("▸")
        lbl_arrow.setObjectName("MenuArrow")
        
        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_text)
        layout.addStretch()
        layout.addWidget(lbl_arrow)
        
        btn_group.setToolTip(f"{title} alt menüsünü aç/kapat")
        btn_group.setStatusTip(f"{title} kategorisindeki işlemleri göster")
        btn_group.setObjectName("MenuGroupButton")
        
        # Alt menü container
        sub_widget = QWidget()
        sub_layout = QVBoxLayout(sub_widget)
        sub_layout.setContentsMargins(0, 4, 0, 4)
        sub_layout.setSpacing(2)
        sub_widget.setStyleSheet("background: transparent;")
        
        for text, idx in sub_items:
            sub_btn = QPushButton()
            sub_btn.setFixedHeight(36)
            sub_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            sub_btn_layout = QHBoxLayout(sub_btn)
            sub_btn_layout.setContentsMargins(50, 0, 16, 0)
            
            lbl_dot = QLabel("○")
            lbl_dot.setObjectName("MenuSubDot")
            
            lbl_sub_text = QLabel(text)
            lbl_sub_text.setObjectName("MenuSubText")
            
            sub_btn_layout.addWidget(lbl_dot)
            sub_btn_layout.addSpacing(8)
            sub_btn_layout.addWidget(lbl_sub_text)
            sub_btn_layout.addStretch()
            
            sub_btn.setObjectName("MenuSubButton")
            sub_btn.setToolTip(text)
            sub_btn.setStatusTip(f"{text} işlemini başlat")
            sub_btn.clicked.connect(lambda checked, i=idx: self.callback(i))
            
            # Sağ Tık Menüsü Ekle
            sub_btn.setContextMenuPolicy(Qt.CustomContextMenu)
            sub_btn.customContextMenuRequested.connect(lambda pos, b=sub_btn, t=text: self.show_context_menu(pos, b, t))
            
            sub_layout.addWidget(sub_btn)
        
        # Başlangıçta kapalı
        total_height = len(sub_items) * 40
        sub_widget.setFixedHeight(0)
        
        btn_group.clicked.connect(lambda: self.toggle_group(sub_widget, total_height, lbl_arrow))
        
        self.menu_layout.addWidget(btn_group)
        self.menu_layout.addWidget(sub_widget)
    
    def on_menu_click(self, button, index):
        """Menü tıklama işlemi"""
        if self.active_button:
            self.active_button.setProperty("active", "false")
            self.active_button.style().unpolish(self.active_button)
            self.active_button.style().polish(self.active_button)
        
        self.active_button = button
        button.setProperty("active", "true")
        button.style().unpolish(button)
        button.style().polish(button)
        
        self.callback(index)
    
    def toggle_group(self, widget, target_height, arrow_label):
        """Alt menü aç/kapa animasyonu"""
        current_height = widget.height()
        
        if current_height == 0:
            start = 0
            end = target_height
            arrow_label.setText("▾")
        else:
            start = target_height
            end = 0
            arrow_label.setText("▸")
        
        def on_value_changed(val):
            widget.setFixedHeight(int(val))
        
        self.anim = QVariantAnimation()
        self.anim.setDuration(200)
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.valueChanged.connect(on_value_changed)
        self.anim.start()
    
    
    def show_context_menu(self, pos, button, text):
        """Sağ tık menüsü - Arama Entegrasyonu"""
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QDesktopServices, QAction
        from PyQt6.QtCore import QUrl
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2c3e50;
                color: white;
                border: 1px solid #34495e;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
        """)
        
        action_search = QAction(f"🔍 '{text}' Hakkında Ara", self)
        action_help = QAction("❓ Yardım / Dokümantasyon", self)
        
        action_search.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(f"https://www.google.com/search?q=Bulut+Teknik+Servis+{text.replace(' ', '+')}")))
        
        menu.addAction(action_search)
        menu.addAction(action_help)
        
        menu.exec(button.mapToGlobal(pos))
        
    def create_footer(self):
        """Alt bilgi alanı"""
        footer = QFrame()
        footer.setObjectName("SideMenuFooter")
        footer.setFixedHeight(50)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        lbl_version = QLabel("v68.0.0 Premium © 2026")
        lbl_version.setObjectName("FooterVersionLabel")
        footer_layout.addWidget(lbl_version)
        
        self.layout.addWidget(footer)
