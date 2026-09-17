from PyQt6.QtWidgets import (QDialog as QtDialog, QVBoxLayout, QWidget, QFrame, QLabel, 
                             QPushButton, QHBoxLayout, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QFont
from src.utils.theme_colors import theme_qss

class PremiumDialog(QtDialog):
    """
    Premium, Frameless, Rounded Dialog base class.
    Includes custom title bar and shadow effects.
    """
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Shadow Effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 60))
        
        # Container
        self.container = QFrame(self)
        self.container.setObjectName("MainContainer")
        self.container.setGraphicsEffect(shadow)
        self.container.setStyleSheet(theme_qss("""
            #MainContainer {
                background-color: @surface;
                border-radius: 20px;
                border: 2px solid @border;
            }
        """))
        
        # Main Layout
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(15, 15, 15, 15)
        self.root_layout.addWidget(self.container)
        
        # Content Layout
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # --- TITLE BAR ---
        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(65)
        self.title_bar.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface_alt;
                border-top-left-radius: 20px;
                border-top-right-radius: 20px;
                border-bottom: 1px solid @border;
            }
        """))
        tbl = QHBoxLayout(self.title_bar)
        tbl.setContentsMargins(25, 0, 15, 0)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(theme_qss("font-size: 18px; font-weight: 800; color: @text; border: none;"))
        
        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(36, 36)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet(theme_qss("""
            QPushButton { 
                border-radius: 18px; font-size: 16px; color: @text_muted; background: transparent; border: none;
            }
            QPushButton:hover { background-color: @danger; color: @selection_text; }
        """))
        self.btn_close.clicked.connect(self.reject)
        
        tbl.addWidget(self.title_lbl)
        tbl.addStretch()
        tbl.addWidget(self.btn_close)
        self.layout.addWidget(self.title_bar)
        
        # Body Area
        self.body = QWidget()
        self.body.setStyleSheet(theme_qss("background: @surface; color: @text;"))
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(30, 25, 30, 30)
        self.body_layout.setSpacing(20)
        self.layout.addWidget(self.body)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.old_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if hasattr(self, "old_pos"):
            delta = event.globalPosition().toPoint() - self.old_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.old_pos = event.globalPosition().toPoint()
            
    def set_body_layout(self, layout):
        """Replaces body layout"""
        # Note: In PyQt, it's easier to add to existing layout
        pass
