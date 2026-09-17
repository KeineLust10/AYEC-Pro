# -*- coding: utf-8 -*-

"""
ModernToast - Premium sağ alt köşeden çıkan bildirimler
Küçük, zarif ve otomatik kapanan toast mesajları
"""

from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint, pyqtSignal
from src.utils.theme_colors import theme_qss, tc
from PyQt6.QtGui import QFont, QColor


class ModernToast(QWidget):
    """
    Premium Toast Bildirimi
    
    Sağ alttan süzülerek çıkar, birkaç saniye gösterir, sonra kaybolur.
    """
    
    closed = pyqtSignal()
    
    def __init__(self, message="", toast_type="info", duration=3000, parent=None):
        super().__init__(parent)
        
        self.message_text = message
        self.toast_type = toast_type
        self.duration = duration
        
        # Frameless ve transparent
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                           Qt.WindowType.Tool | 
                           Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._setup_ui()
        self._setup_animations()
    
    def _setup_ui(self):
        """UI oluştur"""
        # Ana layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Container
        self.container = QWidget()
        self.container.setMinimumWidth(280)
        self.container.setMaximumWidth(420)
        
        # Toast tipine göre stil
        styles = {
            "success": {"bg": tc("success"), "icon": "✓", "shadow": tc("success")},
            "error": {"bg": tc("danger"), "icon": "✕", "shadow": tc("danger")},
            "warning": {"bg": tc("warning"), "icon": "⚠", "shadow": tc("warning")},
            "info": {"bg": tc("accent"), "icon": "ℹ", "shadow": tc("accent_hover")}
        }
        
        style = styles.get(self.toast_type, styles["info"])
        
        self.container.setStyleSheet(theme_qss(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {style['bg']}, stop:1 {self._lighten_color(style['bg'])});
                border-radius: 12px;
                border: 1px solid {style['shadow']};
            }}
        """))
        
        # Gölge
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.container.setGraphicsEffect(shadow)
        
        # Container layout
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(20, 15, 20, 15)
        container_layout.setSpacing(15)
        
        # İkon
        icon_label = QLabel(style["icon"])
        icon_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        icon_label.setStyleSheet(theme_qss("color: white; background: transparent;"))
        icon_label.setFixedSize(30, 30)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Mesaj
        msg_label = QLabel(self.message_text)
        msg_label.setFont(QFont("Segoe UI", 10))
        msg_label.setStyleSheet(theme_qss("""
            color: white; 
            background: transparent;
            line-height: 1.4;
        """))
        msg_label.setWordWrap(True)
        
        container_layout.addWidget(icon_label)
        container_layout.addWidget(msg_label, 1)
        
        main_layout.addWidget(self.container)
        
        # Minimum height ayarla
        self.setMinimumHeight(80)
        self.adjustSize()
    
    def _lighten_color(self, hex_color, factor=0.2):
        """Rengi açıklaştır"""
        color = QColor(hex_color)
        h, s, v, a = color.getHsv()
        v = min(255, int(v * (1 + factor)))
        color.setHsv(h, s, v, a)
        return color.name()
    
    def _setup_animations(self):
        """Animasyonları hazırla"""
        # Slide-in animasyonu
        self._slide_anim = QPropertyAnimation(self, b"pos")
        self._slide_anim.setDuration(400)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Opacity animasyonu
        self._opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self._opacity_anim.setDuration(300)
        self._opacity_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    
    def show_toast(self, parent_window=None):
        """Toast'ı göster"""
        # Parent varsa onun sağ altına yerleştir
        if parent_window:
            parent_geo = parent_window.geometry()
            x = parent_geo.x() + parent_geo.width() - self.width() - 20
            y = parent_geo.y() + parent_geo.height() - self.height() - 20
        else:
            # Ekranın sağ altına yerleştir
            from PyQt6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen().geometry()
            x = screen.width() - self.width() - 20
            y = screen.height() - self.height() - 80
        
        # Başlangıç: Ekran dışında
        start_pos = QPoint(x + 400, y)
        end_pos = QPoint(x, y)
        
        self.move(start_pos)
        self.show()
        
        # Slide-in
        self._slide_anim.setStartValue(start_pos)
        self._slide_anim.setEndValue(end_pos)
        self._slide_anim.start()
        
        # Fade-in
        self._opacity_anim.setStartValue(0.0)
        self._opacity_anim.setEndValue(1.0)
        self._opacity_anim.start()
        
        # Otomatik kapanma
        QTimer.singleShot(self.duration, self._hide_toast)
    
    def _hide_toast(self):
        """Toast'ı gizle"""
        # Fade-out
        self._opacity_anim.setStartValue(1.0)
        self._opacity_anim.setEndValue(0.0)
        self._opacity_anim.finished.connect(self._on_animation_finished)
        self._opacity_anim.start()
    
    def _on_animation_finished(self):
        """Animasyon bittiğinde"""
        self.closed.emit()
        self.close()
        self.deleteLater()


class ToastManager:
    """
    Toast Manager - Birden fazla toast'ı yönetir
    """
    
    def __init__(self, parent=None):
        self.parent = parent
        self.active_toasts = []
    
    def show_success(self, message, duration=3000):
        """Başarı tostu"""
        self._show_toast(message, "success", duration)
    
    def show_error(self, message, duration=4000):
        """Hata tostu"""
        self._show_toast(message, "error", duration)
    
    def show_warning(self, message, duration=3500):
        """Uyarı tostu"""
        self._show_toast(message, "warning", duration)
    
    def show_info(self, message, duration=3000):
        """Bilgi tostu"""
        self._show_toast(message, "info", duration)
    
    def _show_toast(self, message, toast_type, duration):
        """Toast oluştur ve göster"""
        toast = ModernToast(message, toast_type, duration, self.parent)
        toast.closed.connect(lambda: self._remove_toast(toast))
        
        # Yığılma: Önceki toast'lar varsa yukarı kaydır
        if self.active_toasts:
            offset = len(self.active_toasts) * (toast.height() + 15)
            current_pos = toast.pos()
            toast.move(current_pos.x(), current_pos.y() - offset)
        
        self.active_toasts.append(toast)
        toast.show_toast(self.parent)
    
    def _remove_toast(self, toast):
        """Toast'ı listeden kaldır"""
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)

