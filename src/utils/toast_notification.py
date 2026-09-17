# -*- coding: utf-8 -*-
"""
Toast Notification System - AYEC Pro
Sağ alttan kayan modern bildirim sistemi
"""

from PyQt6.QtWidgets import QWidget, QLabel, QGraphicsOpacityEffect, QVBoxLayout, QHBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtProperty
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QAction
from src.utils.theme_colors import theme_qss, tc


class ToastNotification(QWidget):
    """
    Modern toast notification widget
    Sağ alttan kayarak gelen ve otomatik kapanan bildirim
    """
    
    def __init__(self, parent, message, toast_type="info", duration=3000, title=None):
        """
        Args:
            parent: Ana pencere
            message: Gösterilecek mesaj
            toast_type: "success", "error", "warning", "info"
            duration: Gösterim süresi (ms)
            title: Opsiyonel başlık
        """
        super().__init__(parent)
        
        # Handle cases where title and message might be swapped or duration is passed as string
        if isinstance(duration, str):
            try:
                duration = int(duration)
            except ValueError:
                # If duration is a string and not an int, it might be the actual message
                # and the 'message' arg might be the title
                title = message
                message = duration
                duration = 3500

        self.message = message
        self.title = title
        self.toast_type = toast_type
        self.duration = duration
        
        # Renk şemaları
        self.colors = {
            "success": {"bg": tc("success"), "text": "white", "icon": "✓"},
            "error": {"bg": tc("danger"), "text": "white", "icon": "✗"},
            "warning": {"bg": tc("warning"), "text": "white", "icon": "⚠"},
            "info": {"bg": tc("accent"), "text": "white", "icon": "ℹ"}
        }
        
        self.setup_ui()
        self.setup_animation()
        
    def setup_ui(self):
        """UI bileşenlerini oluştur"""
        if self.parent() is not None:
            self.setWindowFlags(Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)
        else:
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Boyut ayarları
        self.setFixedSize(380, 85)
        
        # Ana layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(15)
        
        # İkon
        color_scheme = self.colors.get(self.toast_type, self.colors["info"])
        
        icon_label = QLabel(color_scheme["icon"])
        icon_label.setStyleSheet(theme_qss(f"""
            font-size: 26px;
            color: {color_scheme['text']};
            background: transparent;
            font-weight: bold;
        """))
        icon_label.setFixedSize(40, 40)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Mesaj ve Başlık
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        if self.title:
            title_label = QLabel(self.title)
            title_label.setStyleSheet(theme_qss(f"font-weight: bold; font-size: 13px; color: {color_scheme['text']}; background: transparent; font-family: 'Segoe UI';"))
            text_layout.addWidget(title_label)
            
        msg_label = QLabel(self.message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(theme_qss(f"""
            font-size: 11px;
            font-weight: 500;
            color: {color_scheme['text']};
            background: transparent;
            font-family: 'Segoe UI';
        """))
        text_layout.addWidget(msg_label)
        
        layout.addWidget(icon_label)
        layout.addLayout(text_layout, 1)
        
        # Arka plan rengi
        self.bg_color = QColor(color_scheme["bg"])
        
    def paintEvent(self, event):
        """Özel çizim - yuvarlatılmış köşeler ve gölge"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Gölge efekti
        shadow_rect = self.rect().adjusted(5, 5, -5, -5)
        shadow_path = QPainterPath()
        shadow_path.addRoundedRect(shadow_rect.x(), shadow_rect.y(), 
                                   shadow_rect.width(), shadow_rect.height(), 20, 20)
        painter.fillPath(shadow_path, QColor(0, 0, 0, 45))
        
        # Ana arka plan
        main_rect = self.rect().adjusted(2, 2, -8, -8)
        main_path = QPainterPath()
        main_path.addRoundedRect(main_rect.x(), main_rect.y(),
                                 main_rect.width(), main_rect.height(), 20, 20)
        painter.fillPath(main_path, self.bg_color)
        
    def setup_animation(self):
        """Animasyonları ayarla"""
        # Opacity efekti
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Fade in animasyonu
        self.fade_in_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_anim.setDuration(400)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)
        self.fade_in_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Fade out animasyonu
        self.fade_out_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(350)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_out_anim.finished.connect(self.close)
        
        # Slide animasyonu
        self.slide_anim = QPropertyAnimation(self, b"geometry")
        self.slide_anim.setDuration(500)
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutBack)
        
    def show_notification(self):
        """Bildirimi aktif pencerenin sağ altına göster."""
        anchor = self.parent() if self.parent() and self.parent().isVisible() else None
        main_win = anchor.window() if (anchor and anchor.window()) else self.window()

        if anchor:
            try:
                self.setParent(anchor)
                self.setWindowFlags(Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)
            except Exception:
                pass
        elif main_win and self.parent() is not main_win:
            try:
                self.setParent(main_win)
                self.setWindowFlags(Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)
            except Exception:
                pass

        target_widget = anchor or main_win
        if not target_widget or not target_widget.isVisible() or target_widget.isMinimized():
            screen = QApplication.primaryScreen()
            screen_geo = screen.availableGeometry()
            end_x = screen_geo.right() - self.width() - 30
            end_y = screen_geo.bottom() - self.height() - 30
            start_x = screen_geo.right() + 30
            start_y = end_y
        elif self.parent() is target_widget:
            end_x = max(12, target_widget.width() - self.width() - 20)
            end_y = max(12, target_widget.height() - self.height() - 20)
            start_x = target_widget.width() + 30
            start_y = end_y
        else:
            bottom_right_local = target_widget.rect().bottomRight()
            bottom_right_global = target_widget.mapToGlobal(bottom_right_local)
            end_x = bottom_right_global.x() - self.width() - 30
            end_y = bottom_right_global.y() - self.height() - 30
            start_x = bottom_right_global.x() + 30
            start_y = end_y

        self.slide_anim.setStartValue(QRect(start_x, start_y, self.width(), self.height()))
        self.slide_anim.setEndValue(QRect(end_x, end_y, self.width(), self.height()))
        self.raise_()
        self.show()
        self.slide_anim.start()
        self.fade_in_anim.start()
        QTimer.singleShot(int(self.duration), self.hide_notification)
        
    def hide_notification(self):
        """Bildirimi gizle"""
        self.fade_out_anim.start()
        
    def mousePressEvent(self, event):
        """Tıklandığında kapat"""
        self.hide_notification()


# Yardimci fonksiyonlar - PROXY TO CENTRAL TOAST MANAGER
def _get_central_toast_manager():
    """Finds the main window and its toast manager."""
    from PyQt6.QtWidgets import QApplication
    for widget in QApplication.topLevelWidgets():
        if hasattr(widget, "toast") and hasattr(widget.toast, "show_toast"):
            return widget.toast
        try:
            top = widget.window()
            if top and hasattr(top, "toast") and hasattr(top.toast, "show_toast"):
                return top.toast
        except Exception:
            pass
    return None

def show_toast(parent, message, toast_type="info", duration=3000):
    """
    Toast notification göster (Merkezi yöneticiye yönlendirir)
    Artık (parent, title, message) şeklindeki çağrıları da destekler.
    """
    # Gelen duration bir string ise, muhtemelen (parent, title, message) şeklinde çağrılmıştır
    if isinstance(duration, str):
        title = message
        message = duration
        duration = 3500  # Varsayılan süre
    else:
        title = None

    # Toasts belong to the main application window, never to a modal dialog.
    display_msg = f"<b>{title}</b><br>{message}" if title else message
    manager = _get_central_toast_manager()
    if manager is not None:
        return manager.show_toast(display_msg, toast_type, duration)
    main_window = None
    for widget in QApplication.topLevelWidgets():
        if widget.objectName() == "ModernDesktopApp":
            main_window = widget
            break
        if getattr(widget, "db", None) is not None and widget.isVisible():
            main_window = widget
    if main_window is None:
        try:
            main_window = parent.window() if parent is not None else None
        except Exception:
            main_window = None
    if main_window is not None:
        toast = ToastNotification(main_window, display_msg, toast_type, duration)
        toast.show_notification()
        return toast
    
    # Fallback to local toast
    toast = ToastNotification(parent, message, toast_type, duration, title=title)
    toast.show_notification()
    return toast

def show_success(parent, message, duration=3000):
    return show_toast(parent, message, "success", duration)

def show_error(parent, message, duration=4000):
    return show_toast(parent, message, "error", duration)

def show_warning(parent, message, duration=3500):
    return show_toast(parent, message, "warning", duration)

def show_info(parent, message, duration=3000):
    return show_toast(parent, message, "info", duration)


class ToastManager:
    """
    Central Manager for Toast Notifications to ensure compatibility with
    direct calls like ToastManager.success(parent, message)
    """
    @staticmethod
    def success(parent, message, duration=3000):
        show_success(parent, message, duration)

    @staticmethod
    def error(parent, message, duration=5000):
        show_error(parent, message, duration)

    @staticmethod
    def warning(parent, message, duration=3500):
        show_warning(parent, message, duration)

    @staticmethod
    def info(parent, message, duration=3000):
        show_info(parent, message, duration)
