from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGraphicsDropShadowEffect
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt

class StatusCard(QFrame):
    def __init__(self, title, count, total, color, status_key, parent_callback):
        super().__init__()
        self.status_key = status_key
        self.parent_callback = parent_callback
        
        # Style
        self.setObjectName("StatusCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0,0,0,15))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(1)
        
        self.lbl_title = QLabel(title.upper())
        self.lbl_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet("letter-spacing: 0.5px;")
        
        self.lbl_count = QLabel(str(count))
        self.lbl_count.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        self.lbl_count.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        percent = (count / total * 100) if total > 0 else 0
        self.lbl_percent = QLabel(f"%{percent:.1f} Pay")
        self.lbl_percent.setFont(QFont("Segoe UI", 7))
        self.lbl_percent.setStyleSheet("opacity: 0.7;")
        
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_count)
        layout.addWidget(self.lbl_percent)

    def mousePressEvent(self, event):
        self.parent_callback(self.status_key)
