# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QHBoxLayout, 
                             QPushButton, QFrame, QGraphicsDropShadowEffect, QTableWidget, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QBrush

class ZoneNode(QFrame):
    def __init__(self, title, count, color, icon):
        super().__init__()
        self.setFixedSize(180, 120)
        self.color = QColor(color)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        
        self.lbl_icon = QLabel(icon)
        self.lbl_icon.setFont(QFont("Segoe UI Emoji", 24))
        self.lbl_icon.setStyleSheet("background: transparent;")
        
        self.lbl_count = QLabel(str(count))
        self.lbl_count.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        self.lbl_count.setStyleSheet(f"color: {color}; background: transparent;")
        
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("letter-spacing: 1px;")
        
        layout.addWidget(self.lbl_icon, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_count, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_title, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.setObjectName("ZoneNode")
        self.setStyleSheet(f"border-bottom: 3px solid {color};")

class WorkshopMapWidget(QWidget):
    """Modern Atölye Operasyon Haritası (Bağlantılı Şema)"""
    def __init__(self, stats=None):
        super().__init__()
        self.setMinimumHeight(250)
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(0)
        
        self.stats = stats or {}
        self.init_map()

    def init_map(self):
        # 1. Giriş / Kayıt
        self.add_zone("Giriş Paneli", self.stats.get("Beklemede", 0), "#3498db", "📥")
        self.add_connector()
        
        # 2. Teknik Laboratuvar
        self.add_zone("Atölye / Tamir", self.stats.get("Tamirde", 0), "#f39c12", "🔬")
        self.add_connector()
        
        # 3. Kalite Kontrol
        self.add_zone("Test & QC", self.stats.get("Test", 0), "#9b59b6", "🧪")
        self.add_connector()
        
        # 4. Teslimat Kasası
        self.add_zone("Hazır Deposu", self.stats.get("Tamamlandı", 0), "#27ae60", "📦")

    def add_zone(self, title, count, color, icon):
        node = ZoneNode(title, count, color, icon)
        self.main_layout.addWidget(node)

    def add_connector(self):
        connector = QFrame()
        connector.setFixedWidth(60)
        connector.setStyleSheet("background: transparent;")
        # Arrow
        inner_layout = QVBoxLayout(connector)
        lbl_arrow = QLabel("➔")
        lbl_arrow.setStyleSheet("opacity: 0.3; font-size: 18px;")
        inner_layout.addWidget(lbl_arrow, 0, Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(connector)

    def update_stats(self, stats):
        self.stats = stats
        # Re-draw
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.init_map()
