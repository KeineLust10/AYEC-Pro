# -*- coding: utf-8 -*-

"""
Snoozeable Toast - Ertelenebilir Bildirim Widget'ı
Tamam + 15 Dakika Ertele butonları ile
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QEasingCurve
from src.utils.theme_colors import theme_qss
from src.utils.logger import logger
from PyQt6.QtGui import QFont


class SnoozeableToast(QWidget):
    """
    Ertelenebilir toast bildirimi
    - Tamam butonu (kapat)
    - 15 Dakika Ertele butonu
    """
    
    snoozed = pyqtSignal(dict)  # alert_data
    dismissed = pyqtSignal()
    
    def __init__(self, message, alert_data, parent=None, duration=10000):
        super().__init__(parent)
        self.alert_data = alert_data
        self.duration = duration
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._build_ui(message)
        self._setup_auto_close()
    
    def _build_ui(self, message):
        """UI oluştur"""
        # Ana layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # İçerik container
        container = QWidget()
        container.setObjectName("SnoozeableToastContainer")
        container.setStyleSheet(theme_qss("""
            QWidget#SnoozeableToastContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 @accent_pressed, stop:1 @accent);
                border-radius: 12px;
                border: 2px solid @accent;
            }
        """))
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(20, 15, 20, 15)
        container_layout.setSpacing(12)
        
        # Icon + Mesaj
        msg_layout = QHBoxLayout()
        
        icon_label = QLabel("⏰")
        icon_label.setStyleSheet(theme_qss("font-size: 32px;"))
        msg_layout.addWidget(icon_label)
        
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(theme_qss("""
            color: @selection_text;
            font-size: 14px;
            font-weight: 600;
            padding-left: 10px;
        """))
        msg_layout.addWidget(msg_label, 1)
        
        container_layout.addLayout(msg_layout)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_dismiss = QPushButton("✅ Tamam")
        self.btn_dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_dismiss.setFixedHeight(36)
        self.btn_dismiss.setStyleSheet(theme_qss("""
            QPushButton {
                background: @success;
                color: @selection_text;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: @success;
            }
            QPushButton:pressed {
                background: @success;
            }
        """))
        self.btn_dismiss.clicked.connect(self._on_dismiss)
        
        self.btn_snooze = QPushButton("⏰ 15 Dakika Ertele")
        self.btn_snooze.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_snooze.setFixedHeight(36)
        self.btn_snooze.setStyleSheet(theme_qss("""
            QPushButton {
                background: @warning;
                color: @selection_text;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background: @warning;
            }
            QPushButton:pressed {
                background: @warning;
            }
        """))
        self.btn_snooze.clicked.connect(self._on_snooze)
        
        btn_layout.addWidget(self.btn_dismiss)
        btn_layout.addWidget(self.btn_snooze)
        
        container_layout.addLayout(btn_layout)
        
        layout.addWidget(container)
        
        # Boyut
        self.setFixedWidth(400)
        self.adjustSize()
    
    def _setup_auto_close(self):
        """Otomatik kapanma timer"""
        if self.duration > 0:
            QTimer.singleShot(self.duration, self._on_dismiss)
    
    def _on_dismiss(self):
        """Tamam - Kapat"""
        self.dismissed.emit()
        self._fade_out()
    
    def _on_snooze(self):
        """Ertele"""
        self.snoozed.emit(self.alert_data)
        self._fade_out()
    
    def _fade_out(self):
        """Fade out animation"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(300)
        self.animation.setStartValue(1.0)
        self.animation.setEndValue(0.0)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self.close)
        self.animation.start()
    
    def show_at_position(self, x, y):
        """Belirli konumda göster"""
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()


def show_snoozeable_toast(parent, message, alert_data):
    """
    Ertelenebilir toast göster
    Returns: SnoozeableToast instance
    """
    toast = SnoozeableToast(message, alert_data, parent=parent)
    
    # Sağ alt köşe
    if parent:
        parent_geo = parent.geometry()
        x = parent_geo.right() - toast.width() - 20
        y = parent_geo.bottom() - toast.height() - 60
    else:
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().geometry()
        x = screen.right() - toast.width() - 20
        y = screen.bottom() - toast.height() - 60
    
    toast.show_at_position(x, y)
    return toast


# Test
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    
    alert_data = {'type': 'loan_reminder', 'time': '11:00'}
    toast = show_snoozeable_toast(None, "💳 Kredi Taksit Hatırlatması\nBugün 2 ödeme var!", alert_data)
    
    toast.snoozed.connect(lambda data: logger.debug(f"SNOOZED: {data}"))
    toast.dismissed.connect(lambda: logger.debug("DISMISSED"))
    
    sys.exit(app.exec())

