# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPainter, QPen

class FlowNode(QFrame):
    def __init__(self, title, count, color, active=False):
        super().__init__()
        self.setFixedSize(140, 80)
        self.active = active
        self.color = QColor(color)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_count = QLabel(str(count))
        self.lbl_count.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_count.setStyleSheet(f"color: {color}; background: transparent;")
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont("Segoe UI", 9))
        self.lbl_title.setStyleSheet("color: #7f8c8d; background: transparent;")
        
        layout.addWidget(self.lbl_count, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_title, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {"#ddd" if not active else color};
                border-radius: 15px;
            }}
        """)

class ServiceFlowWidget(QWidget):
    """Görsel Hizmet Akış Şeması (Bağlantılı Şema)"""
    def __init__(self, stats=None):
        super().__init__()
        self.setFixedHeight(120)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(40) # Space for lines
        
        self.nodes = []
        self.stats = stats or {}
        self.setup_ui()

    def setup_ui(self):
        # Akış adımları
        steps = [
            ("Kayıt / Yeni", "Beklemede", "#3498db"),
            ("Tamir Süreci", "Tamirde", "#f39c12"),
            ("Test Kontrol", "Test", "#9b59b6"),
            ("Teslime Hazır", "Tamamlandı", "#27ae60"),
            ("Teslim Edildi", "Teslim Edildi", "#95a5a6")
        ]
        
        for i, (title, key, color) in enumerate(steps):
            count = self.stats.get(key, 0)
            node = FlowNode(title, count, color, active=(count > 0))
            self.layout.addWidget(node)
            self.nodes.append(node)
            
            # Ara bağlantı çizgisi (Painter ile çizilecek veya basit bir label)
            if i < len(steps) - 1:
                arrow = QLabel("➜")
                arrow.setStyleSheet("color: #bdc3c7; font-size: 20px;")
                self.layout.addWidget(arrow)

    def update_stats(self, stats):
        self.stats = stats
        # Re-setup
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.nodes = []
        self.setup_ui()
