from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame, QGraphicsDropShadowEffect, QProgressBar
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from src.utils.theme_colors import theme_qss
from PyQt6.QtGui import QColor, QFont

class AssistantToast(QFrame):
    clicked = pyqtSignal()
    
    def __init__(self, parent, title, message, duration=5000):
        super().__init__(parent)
        self.duration = duration
        self.setFixedSize(320, 100)
        self.setObjectName("AssistantToast")
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
        
        self.setStyleSheet(theme_qss("""
            #AssistantToast {
                background-color: @surface;
                border-left: 5px solid @warning;
                border-radius: 8px;
            }
        """))
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        # Icon / Avatar
        self.icon_lbl = QLabel("🤖")
        self.icon_lbl.setFont(QFont("Segoe UI", 24))
        self.icon_lbl.setStyleSheet(theme_qss("background: transparent;"))
        layout.addWidget(self.icon_lbl)
        
        # Content
        content_layout = QVBoxLayout()
        content_layout.setSpacing(2)
        
        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(theme_qss("color: @warning; font-weight: bold; font-size: 14px; background: transparent;"))
        
        self.msg_lbl = QLabel(message)
        self.msg_lbl.setWordWrap(True)
        self.msg_lbl.setStyleSheet(theme_qss("color: @text; font-size: 12px; background: transparent;"))
        
        content_layout.addWidget(self.title_lbl)
        content_layout.addWidget(self.msg_lbl)
        layout.addLayout(content_layout)
        
        # Progress Bar for timer
        self.progress = QProgressBar(self)
        self.progress.setFixedHeight(3)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(theme_qss("""
            QProgressBar {
                background: rgba(255,255,255,0.1);
                border: none;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QProgressBar::chunk {
                background-color: @warning;
            }
        """))
        self.progress.setGeometry(0, 97, 320, 3)
        self.progress.setValue(100)
        
        # Animations
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(500)
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.start_time = 0
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    def update_progress(self):
        val = self.progress.value() - 2
        if val <= 0:
            self.timer.stop()
            self.hide_toast()
        else:
            self.progress.setValue(val)
            
    def mousePressEvent(self, event):
        self.clicked.emit()
        self.timer.stop()
        self.hide_toast()
        super().mousePressEvent(event)
        
    def show_toast(self):
        parent_rect = self.parent().rect()
        target_x = parent_rect.width() - self.width() - 30
        target_y = parent_rect.height() - self.height() - 30
        
        # Start from the right side, sliding in
        self.move(parent_rect.width(), target_y)
        self.show()
        
        self.slide_anim.setStartValue(QPoint(parent_rect.width(), target_y))
        self.slide_anim.setEndValue(QPoint(target_x, target_y))
        self.slide_anim.start()
        
        self.timer.start(int(self.duration / 50)) # 50 steps
        
    def hide_toast(self):
        parent_rect = self.parent().rect()
        current_pos = self.pos()
        self.slide_anim.setStartValue(current_pos)
        self.slide_anim.setEndValue(QPoint(parent_rect.width(), current_pos.y()))
        self.slide_anim.finished.connect(self.deleteLater)
        self.slide_anim.start()


