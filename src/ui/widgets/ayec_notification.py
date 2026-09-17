# -*- coding: utf-8 -*-

"""
AYEC Pro - Premium Notification Widget
Modern bildirim penceresi: Ertele + Kapat butonlar, animasyon, otomatik kapanma
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from src.utils.theme_colors import theme_qss
from PyQt6.QtWidgets import QGraphicsDropShadowEffect
from src.utils.logger import logger


class AyecNotification(QWidget):
    """
    Premium bildirim penceresi
    - Modern dark theme
    - Snooze (15 dk ertele) butonu
    - Otomatik kapanma (30 saniye)
    - Slide-up animation
    """
    
    snoozed = pyqtSignal(dict)  # alert_data
    dismissed = pyqtSignal()
    
    def __init__(self, title, message, alert_data=None, parent=None, auto_close=30000):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.alert_data = alert_data or {}
        self.auto_close_duration = auto_close
        
        self._build_ui(title, message)
        self._setup_auto_close()
    
    def _build_ui(self, title, message):
        """UI oluştur"""
        # Ana container
        self.container = QWidget(self)
        self.container.setObjectName("AyecNotificationContainer")
        self.container.setStyleSheet(theme_qss("""
            QWidget#AyecNotificationContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 @text, stop:1 @text);
                border: 2px solid @text_muted;
                border-radius: 12px;
            }
        """))
        
        # Glge efekti
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 180))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)
        
        # Container layout
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 15, 20, 15)
        container_layout.setSpacing(12)
        
        # Icon + Balk
        header_layout = QHBoxLayout()
        
        icon_label = QLabel("")
        icon_label.setStyleSheet(theme_qss("font-size: 28px; border: none; background: transparent;"))
        header_layout.addWidget(icon_label)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(theme_qss("""
            color: @warning;
            font-weight: bold;
            font-size: 14px;
            border: none;
            background: transparent;
        """))
        header_layout.addWidget(self.lbl_title, 1)
        
        container_layout.addLayout(header_layout)
        
        # Mesaj
        self.lbl_msg = QLabel(message)
        self.lbl_msg.setWordWrap(True)
        self.lbl_msg.setStyleSheet(theme_qss("""
            color: @text_muted;
            font-size: 12px;
            border: none;
            background: transparent;
            padding: 5px 0;
        """))
        container_layout.addWidget(self.lbl_msg)
        
        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.btn_snooze = QPushButton(" 15 Dk Ertele")
        self.btn_snooze.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_snooze.setFixedHeight(36)
        self.btn_snooze.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
            QPushButton:pressed {
                background-color: @accent_pressed;
            }
        """))
        self.btn_snooze.clicked.connect(self._on_snooze)
        
        self.btn_close = QPushButton(" Kapat")
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setFixedHeight(36)
        self.btn_close.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @success;
                color: @selection_text;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: @success;
            }
            QPushButton:pressed {
                background-color: @success;
            }
        """))
        self.btn_close.clicked.connect(self._on_close)
        
        btn_layout.addWidget(self.btn_snooze)
        btn_layout.addWidget(self.btn_close)
        
        container_layout.addLayout(btn_layout)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        
        # Boyut
        self.setFixedSize(350, 170)
    
    def _setup_auto_close(self):
        """Otomatik kapanma timer (30 saniye)"""
        if self.auto_close_duration > 0:
            QTimer.singleShot(self.auto_close_duration, self._on_close)
    
    def _on_snooze(self):
        """Ertele butonuna tkland"""
        self.snoozed.emit(self.alert_data)
        self._fade_out()
    
    def _on_close(self):
        """Kapat butonuna tkland"""
        self.dismissed.emit()
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
    
    def show_animated(self, x, y):
        """
        Pencereyi belirtilen konumda aadan yukar szlerek gster
        """
        # Balang konumu (ekran d, aada)
        start_y = y + 100
        
        self.move(x, start_y)
        self.show()
        
        # Slide-up animation
        self.slide_animation = QPropertyAnimation(self, b"pos")
        self.slide_animation.setDuration(400)
        self.slide_animation.setStartValue(self.pos())
        self.slide_animation.setEndValue(QRect(x, y, self.width(), self.height()).topLeft())
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide_animation.start()


class NotificationManager:
    """
    Birden fazla bildirimi ynetir
    - Stack layout (merdiven gibi dizme)
    - akma nleme
    """
    
    def __init__(self, parent=None):
        self.parent = parent
        self.active_notifications = []
        self.stack_offset_y = 10  # Her bildirim aras boluk
    
    def show_notification(self, title, message, alert_data=None):
        """
        Yeni bildirim gster
        Returns: AyecNotification instance
        """
        notification = AyecNotification(title, message, alert_data, parent=self.parent)
        
        # Konum hesapla (sa alt ke, stack layout)
        x, y = self._calculate_position(notification)
        
        # Gster
        notification.show_animated(x, y)
        
        # Listede tut
        self.active_notifications.append(notification)
        
        # Kapandnda listeden kar
        notification.dismissed.connect(lambda: self._remove_notification(notification))
        notification.snoozed.connect(lambda data: self._remove_notification(notification))
        
        return notification
    
    def _calculate_position(self, notification):
        """Stack layout iin konum hesapla"""
        # Ekran boyutu
        if self.parent:
            parent_geo = self.parent.geometry()
            screen_width = parent_geo.width()
            screen_height = parent_geo.height()
            screen_x = parent_geo.x()
            screen_y = parent_geo.y()
        else:
            from PyQt6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            screen_width = screen.width()
            screen_height = screen.height()
            screen_x = screen.x()
            screen_y = screen.y()
        
        # Sağ alt köşe
        x = screen_x + screen_width - notification.width() - 20
        
        # Y pozisyonu: Mevcut bildirimlerin altına ekle
        base_y = screen_y + screen_height - notification.height() - 60
        
        offset = len(self.active_notifications) * (notification.height() + self.stack_offset_y)
        y = base_y - offset
        
        return x, y
    
    def _remove_notification(self, notification):
        """Bildirimi listeden kaldır."""
        if notification in self.active_notifications:
            self.active_notifications.remove(notification)
    
    def clear_all(self):
        """Tüm bildirimleri kapat."""
        for notif in list(self.active_notifications):
            notif.close()
        self.active_notifications.clear()


# Test
if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    
    manager = NotificationManager()
    
    # Test 1: Tek bildirim
    alert_data = {'type': 'loan_reminder', 'time': '11:00'}
    notif1 = manager.show_notification(
        "Kredi Taksit Hatırlatması",
        "Engin Bey, vadesi gelen banka demenizi hatırlatmak için belirlediçiniz saat geldi. Bugün 2 taksit var.",
        alert_data
    )
    
    notif1.snoozed.connect(lambda data: logger.debug(f"SNOOZED: {data}"))
    notif1.dismissed.connect(lambda: logger.debug("DISMISSED"))
    
    # Test 2: Stack test (3 saniye sonra ikinci bildirim)
    def show_second():
        manager.show_notification(
            "Çek/Senet Hatırlatması",
            "Önümüzdeki 7 gün içinde 3 adet vade var.",
            {'type': 'check_reminder'}
        )
    
    QTimer.singleShot(3000, show_second)
    
    sys.exit(app.exec())


