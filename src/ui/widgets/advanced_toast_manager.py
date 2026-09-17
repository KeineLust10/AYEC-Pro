# -*- coding: utf-8 -*-
"""
Advanced Toast Notification Manager - AYEC Pro
Gelişmiş kayan bildirim yönetim sistemi
"""

from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QPoint
from src.utils.theme_colors import theme_qss, tc
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QLinearGradient, QAction


class AdvancedToast(QWidget):
    """
    Gelişmiş Toast Notification Widget
    - Otomatik kaybolma (3-5 saniye)
    - Animasyon efektleri (kayarak açılma/kapanma)
    - Konumlandırma (ekranın alt/üst/orta kısmı)
    - Renk şeması (başarı/uyarı/hata/bilgi)
    - Tıklanabilir kapatma butonu
    - Fare üzerine gelince kaybolmayı durdurma
    """
    
    closed = pyqtSignal(object)  # Toast kapandığında sinyal gönder
    
    # Toast tipleri
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    
    # Pozisyon sabitleri
    TOP_RIGHT = "top_right"
    TOP_LEFT = "top_left"
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM_LEFT = "bottom_left"
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"
    
    def __init__(self, parent, message, toast_type=INFO, duration=4000, position=BOTTOM_RIGHT):
        """
        Args:
            parent: Ana pencere
            message: Gösterilecek mesaj
            toast_type: "success", "error", "warning", "info"
            duration: Gösterim süresi (ms) - 0 ise sonsuz
            position: Toast pozisyonu
        """
        super().__init__(parent)
        
        self.message = message
        self.toast_type = toast_type
        self.duration = duration
        self.position = position
        self.is_hovered = False
        self.is_closing = False
        
        # Renk şemaları - Modern gradient renkler
        self.color_schemes = {
            self.SUCCESS: {
                "gradient_start": tc("success"),  # Emerald
                "gradient_end": tc("success"),
                "text": "white",
                "icon": "✓",
                "icon_bg": tc("success")
            },
            self.ERROR: {
                "gradient_start": tc("danger"),  # Red
                "gradient_end": tc("danger"),
                "text": "white",
                "icon": "✗",
                "icon_bg": tc("danger")
            },
            self.WARNING: {
                "gradient_start": tc("warning"),  # Amber
                "gradient_end": tc("warning"),
                "text": "white",
                "icon": "⚠",
                "icon_bg": tc("warning")
            },
            self.INFO: {
                "gradient_start": tc("accent"),  # Blue
                "gradient_end": tc("accent_hover"),
                "text": "white",
                "icon": "ℹ",
                "icon_bg": tc("accent_pressed")
            }
        }
        
        self.setup_ui()
        self.setup_animations()
        
    def setup_ui(self):
        """UI bileşenlerini oluştur"""
        # Window flags
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Boyut ayarları - Responsive
        self.setMinimumWidth(320)
        self.setMaximumWidth(400)
        self.setMinimumHeight(70)
        self.setMaximumHeight(150)
        
        # Renk şeması
        self.scheme = self.color_schemes.get(self.toast_type, self.color_schemes[self.INFO])
        
        # Gölge efekti
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)
        
        # Ana layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 15, 20, 15)
        main_layout.setSpacing(15)
        
        # İkon container
        icon_container = QWidget()
        icon_container.setFixedSize(40, 40)
        icon_container.setStyleSheet(theme_qss(f"""
            background-color: {self.scheme['icon_bg']};
            border-radius: 20px;
        """))
        
        icon_layout = QVBoxLayout(icon_container)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        
        # İkon
        icon_label = QLabel(self.scheme["icon"])
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet(theme_qss(f"""
            font-size: 20px;
            font-weight: bold;
            color: {self.scheme['text']};
            background: transparent;
        """))
        icon_layout.addWidget(icon_label)
        
        # Mesaj
        msg_label = QLabel(self.message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(theme_qss(f"""
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11pt;
            font-weight: 500;
            color: {self.scheme['text']};
            background: transparent;
            padding: 5px;
        """))
        
        # Kapatma butonu
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(theme_qss(f"""
            QPushButton {{
                background: rgba(255, 255, 255, 0.2);
                color: {self.scheme['text']};
                border: none;
                border-radius: 14px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.3);
            }}
            QPushButton:pressed {{
                background: rgba(255, 255, 255, 0.4);
            }}
        """))
        close_btn.clicked.connect(self.dismiss)
        
        # Layout'a ekle
        main_layout.addWidget(icon_container)
        main_layout.addWidget(msg_label, 1)
        main_layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignTop)
        
        # Boyutu içeriğe göre ayarla
        self.adjustSize()
        
    def paintEvent(self, event):
        """Özel çizim - gradient arka plan ve yuvarlatılmış köşeler"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Gradient arka plan
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0, QColor(self.scheme["gradient_start"]))
        gradient.setColorAt(1, QColor(self.scheme["gradient_end"]))
        
        # Yuvarlatılmış dikdörtgen
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        
        painter.fillPath(path, gradient)
        
    def setup_animations(self):
        """Animasyonları ayarla"""
        # Opacity animasyonu
        self.opacity_effect = QGraphicsOpacityEffect(self)
        
        # Fade in
        self.fade_in_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_anim.setDuration(300)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Fade out
        self.fade_out_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(250)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_anim.finished.connect(self._on_animation_finished)
        
        # Slide animasyonu
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(400)
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
        # Otomatik kapanma timer'ı
        if self.duration > 0:
            self.auto_close_timer = QTimer(self)
            self.auto_close_timer.setSingleShot(True)
            self.auto_close_timer.timeout.connect(self.dismiss)
        else:
            self.auto_close_timer = None
            
    def show_toast(self, target_pos):
        """Toast'ı göster ve animasyonları başlat"""
        if not self.parent():
            return
            
        # Başlangıç pozisyonu (ekran dışı)
        start_pos = self._get_start_position(target_pos)
        
        # Pozisyonu ayarla
        self.move(start_pos)
        self.show()
        
        # Slide animasyonu
        self.slide_anim.setStartValue(start_pos)
        self.slide_anim.setEndValue(target_pos)
        self.slide_anim.start()
        
        # Fade in
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_in_anim.start()
        
        # Otomatik kapanma
        if self.auto_close_timer:
            self.auto_close_timer.start(self.duration)
            
    def _get_start_position(self, target_pos):
        """Animasyon başlangıç pozisyonunu hesapla"""
        if self.position in [self.BOTTOM_RIGHT, self.TOP_RIGHT]:
            # Sağdan gelsin
            return QPoint(target_pos.x() + 400, target_pos.y())
        elif self.position in [self.BOTTOM_LEFT, self.TOP_LEFT]:
            # Soldan gelsin
            return QPoint(target_pos.x() - 400, target_pos.y())
        else:
            # Yukarıdan veya aşağıdan gelsin
            if "top" in self.position:
                return QPoint(target_pos.x(), target_pos.y() - 100)
            else:
                return QPoint(target_pos.x(), target_pos.y() + 100)
                
    def dismiss(self):
        """Toast'ı kapat"""
        if self.is_closing:
            return
            
        self.is_closing = True
        
        # Timer'ı durdur
        if self.auto_close_timer and self.auto_close_timer.isActive():
            self.auto_close_timer.stop()
            
        # Fade out animasyonu
        self.fade_out_anim.start()
        
    def _on_animation_finished(self):
        """Animasyon bittiğinde"""
        self.closed.emit(self)
        self.deleteLater()
        
    def enterEvent(self, event):
        """Fare üzerine geldiğinde - otomatik kapanmayı durdur"""
        self.is_hovered = True
        if self.auto_close_timer and self.auto_close_timer.isActive():
            self.auto_close_timer.stop()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        """Fare ayrıldığında - otomatik kapanmayı devam ettir"""
        self.is_hovered = False
        if self.auto_close_timer and not self.is_closing:
            # Kalan süreyi azalt (1 saniye ver)
            self.auto_close_timer.start(1000)
        super().leaveEvent(event)


class ToastManager(QWidget):
    """
    Toast Notification Manager
    Çoklu toast'ları yönetir ve üst üste gelmelerini önler
    """
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.setObjectName("ToastManager")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Aktif toast'lar
        self.active_toasts = []
        
        # Pozisyon ayarları
        self.spacing = 15  # Toast'lar arası boşluk
        self.margin = 20   # Ekran kenarından boşluk
        
    def add_toast(self, message, toast_type=AdvancedToast.INFO, duration=4000, 
                  position=AdvancedToast.BOTTOM_RIGHT):
        """
        Yeni toast ekle
        
        Args:
            message: Mesaj metni
            toast_type: Toast tipi (success, error, warning, info)
            duration: Gösterim süresi (ms)
            position: Toast pozisyonu
        """
        # Toast oluştur
        toast = AdvancedToast(self.parent(), message, toast_type, duration, position)
        toast.closed.connect(self._on_toast_closed)
        
        # Pozisyon hesapla
        target_pos = self._calculate_position(toast, position)
        
        # Toast'ı göster
        toast.show_toast(target_pos)
        
        # Listeye ekle
        self.active_toasts.append(toast)
        
        return toast
        
    def _calculate_position(self, toast, position):
        """Toast pozisyonunu hesapla"""
        if not self.parent():
            return QPoint(0, 0)
            
        parent_rect = self.parent().rect()
        toast_width = toast.width()
        toast_height = toast.height()
        
        # Aynı pozisyondaki toast'ların sayısını bul
        same_position_count = sum(1 for t in self.active_toasts if t.position == position)
        
        # Offset hesapla (üst üste gelmeyi önle)
        offset = same_position_count * (toast_height + self.spacing)
        
        # Pozisyona göre koordinatları hesapla
        if position == AdvancedToast.BOTTOM_RIGHT:
            x = parent_rect.width() - toast_width - self.margin
            y = parent_rect.height() - toast_height - self.margin - offset
            
        elif position == AdvancedToast.BOTTOM_LEFT:
            x = self.margin
            y = parent_rect.height() - toast_height - self.margin - offset
            
        elif position == AdvancedToast.TOP_RIGHT:
            x = parent_rect.width() - toast_width - self.margin
            y = self.margin + offset
            
        elif position == AdvancedToast.TOP_LEFT:
            x = self.margin
            y = self.margin + offset
            
        elif position == AdvancedToast.TOP_CENTER:
            x = (parent_rect.width() - toast_width) // 2
            y = self.margin + offset
            
        elif position == AdvancedToast.BOTTOM_CENTER:
            x = (parent_rect.width() - toast_width) // 2
            y = parent_rect.height() - toast_height - self.margin - offset
            
        else:
            x = parent_rect.width() - toast_width - self.margin
            y = parent_rect.height() - toast_height - self.margin - offset
            
        return QPoint(x, y)
        
    def _on_toast_closed(self, toast):
        """Toast kapandığında"""
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
            
        # Kalan toast'ları yeniden konumlandır
        self._reposition_toasts()
        
    def _reposition_toasts(self):
        """Aktif toast'ları yeniden konumlandır"""
        # Pozisyona göre grupla
        position_groups = {}
        for toast in self.active_toasts:
            if toast.position not in position_groups:
                position_groups[toast.position] = []
            position_groups[toast.position].append(toast)
            
        # Her grup için yeniden konumlandır
        for position, toasts in position_groups.items():
            for i, toast in enumerate(toasts):
                target_pos = self._calculate_position_for_index(toast, position, i)
                
                # Smooth transition
                anim = QPropertyAnimation(toast, b"pos")
                anim.setDuration(200)
                anim.setStartValue(toast.pos())
                anim.setEndValue(target_pos)
                anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                anim.start()
                
    def _calculate_position_for_index(self, toast, position, index):
        """Belirli bir index için pozisyon hesapla"""
        if not self.parent():
            return QPoint(0, 0)
            
        parent_rect = self.parent().rect()
        toast_width = toast.width()
        toast_height = toast.height()
        
        offset = index * (toast_height + self.spacing)
        
        if position == AdvancedToast.BOTTOM_RIGHT:
            x = parent_rect.width() - toast_width - self.margin
            y = parent_rect.height() - toast_height - self.margin - offset
            
        elif position == AdvancedToast.BOTTOM_LEFT:
            x = self.margin
            y = parent_rect.height() - toast_height - self.margin - offset
            
        elif position == AdvancedToast.TOP_RIGHT:
            x = parent_rect.width() - toast_width - self.margin
            y = self.margin + offset
            
        elif position == AdvancedToast.TOP_LEFT:
            x = self.margin
            y = self.margin + offset
            
        elif position == AdvancedToast.TOP_CENTER:
            x = (parent_rect.width() - toast_width) // 2
            y = self.margin + offset
            
        elif position == AdvancedToast.BOTTOM_CENTER:
            x = (parent_rect.width() - toast_width) // 2
            y = parent_rect.height() - toast_height - self.margin - offset
            
        else:
            x = parent_rect.width() - toast_width - self.margin
            y = parent_rect.height() - toast_height - self.margin - offset
            
        return QPoint(x, y)
        
    def clear_all(self):
        """Tüm toast'ları temizle"""
        for toast in self.active_toasts[:]:
            toast.dismiss()


# Global yardımcı fonksiyonlar
_global_toast_manager = None


def get_toast_manager(parent):
    """Global toast manager'ı al veya oluştur"""
    global _global_toast_manager
    
    if _global_toast_manager is None or _global_toast_manager.parent() != parent:
        _global_toast_manager = ToastManager(parent)
        
    return _global_toast_manager


def show_success(parent, message, duration=3000, position=AdvancedToast.BOTTOM_RIGHT):
    """Başarı bildirimi göster"""
    manager = get_toast_manager(parent)
    return manager.add_toast(message, AdvancedToast.SUCCESS, duration, position)


def show_error(parent, message, duration=5000, position=AdvancedToast.BOTTOM_RIGHT):
    """Hata bildirimi göster"""
    manager = get_toast_manager(parent)
    return manager.add_toast(message, AdvancedToast.ERROR, duration, position)


def show_warning(parent, message, duration=4000, position=AdvancedToast.BOTTOM_RIGHT):
    """Uyarı bildirimi göster"""
    manager = get_toast_manager(parent)
    return manager.add_toast(message, AdvancedToast.WARNING, duration, position)


def show_info(parent, message, duration=3000, position=AdvancedToast.BOTTOM_RIGHT):
    """Bilgi bildirimi göster"""
    manager = get_toast_manager(parent)
    return manager.add_toast(message, AdvancedToast.INFO, duration, position)

