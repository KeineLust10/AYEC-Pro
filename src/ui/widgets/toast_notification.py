"""
Premium Toast Notification Widget
Modern, animated notifications with gradient backgrounds and smooth transitions.
"""
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QProgressBar, QGraphicsOpacityEffect, QWidget, QMessageBox, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal
from src.utils.theme_colors import theme_qss, tc
from PyQt6.QtGui import QFont, QColor
import logging

logger = logging.getLogger("AYECProLogger")

class ToastNotification(QFrame):
    """
    Modern toast notification with animations and optional features.
    """
    closed = pyqtSignal()
    
    def __init__(self, message, toast_type="info", duration=4000, progress=None, action=None, parent=None):
        super().__init__(parent)
        self.toast_type = toast_type
        
        # Ensure duration is always an int to prevent TypeError: '>' not supported between 'str' and 'int'
        try:
            self.duration = int(duration)
        except (ValueError, TypeError):
            self.duration = 4000
            
        self.is_hovered = False
        
        self.setObjectName("ToastNotification")
        self.setFixedWidth(320)
        self.setMinimumHeight(80)
        
        from src.utils.design_system import DesignTokens
        # Modern Gradient based on type
        colors = {
            "success": (tc("success"), tc("success")),
            "info": (DesignTokens.ACCENT, tc("accent_hover")),
            "warning": (tc("warning"), tc("warning")),
            "error": (DesignTokens.DESTRUCTIVE, tc("danger"))
        }
        
        c1, c2 = colors.get(toast_type, colors["info"])
        
        self.setStyleSheet(theme_qss(f"""
            #ToastNotification {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {c1}, stop:1 {c2});
                border-radius: {DesignTokens.RADIUS_LG};
                border: 1px solid @border;
            }}
        """))
        
        # Shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Icon
        icons = {
            "success": "✅",
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌"
        }
        
        lbl_icon = QLabel(icons.get(toast_type, "ℹ️"))
        lbl_icon.setFont(QFont("Segoe UI Emoji", 24))
        lbl_icon.setStyleSheet(theme_qss("background: transparent; color: white;"))
        lbl_icon.setFixedSize(32, 32)
        layout.addWidget(lbl_icon)
        
        # Content area
        content_layout = QVBoxLayout()
        content_layout.setSpacing(6)
        
        # Message
        lbl_message = QLabel(message)
        lbl_message.setFont(QFont("Segoe UI", 10))
        lbl_message.setStyleSheet(theme_qss("color: white; background: transparent;"))
        lbl_message.setWordWrap(True)
        content_layout.addWidget(lbl_message)
        
        # Progress bar (optional)
        if progress is not None:
            self.progress_bar = QProgressBar()
            self.progress_bar.setFixedHeight(4)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setValue(progress)
            self.progress_bar.setStyleSheet(theme_qss("""
                QProgressBar {
                    background: rgba(255,255,255,0.3);
                    border-radius: 2px;
                    border: none;
                }
                QProgressBar::chunk {
                    background: white;
                    border-radius: 2px;
                }
            """))
            content_layout.addWidget(self.progress_bar)
        else:
            self.progress_bar = None
        
        # Action button (optional)
        if action:
            action_text, action_callback = action
            btn_action = QPushButton(action_text)
            btn_action.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            btn_action.setFixedHeight(28)
            btn_action.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_action.setStyleSheet(theme_qss("""
                QPushButton {
                    background: rgba(255,255,255,0.2);
                    color: white;
                    border: 1px solid rgba(255,255,255,0.3);
                    border-radius: 6px;
                    padding: 4px 12px;
                }
                QPushButton:hover {
                    background: rgba(255,255,255,0.3);
                }
            """))
            btn_action.clicked.connect(action_callback)
            btn_action.clicked.connect(self.dismiss)
            content_layout.addWidget(btn_action)
        
        layout.addLayout(content_layout, 1)
        
        # Close button
        btn_close = QPushButton("×")
        btn_close.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(0,0,0,0.2);
                color: white;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background: rgba(0,0,0,0.4);
            }
        """)
        btn_close.clicked.connect(self.dismiss)
        layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignTop)
        
        # Auto-dismiss timer
        if self.duration > 0:
            self.dismiss_timer = QTimer()
            self.dismiss_timer.setSingleShot(True)
            self.dismiss_timer.timeout.connect(self.dismiss)
            self.dismiss_timer.start(self.duration)
        else:
            self.dismiss_timer = None
    
    def set_progress(self, value):
        """Update progress bar value."""
        if self.progress_bar:
            self.progress_bar.setValue(value)
    
    def enterEvent(self, event):
        """Pause auto-dismiss on hover."""
        self.is_hovered = True
        if self.dismiss_timer and self.dismiss_timer.isActive():
            self.dismiss_timer.stop()
    
    def leaveEvent(self, event):
        """Resume auto-dismiss on leave."""
        self.is_hovered = False
        if self.dismiss_timer and self.duration > 0:
            self.dismiss_timer.start(1000)  # Give 1 more second
    
    def dismiss(self):
        """Dismiss notification with animation."""
        # Emit closed signal immediately so manager removes it from active list
        self.closed.emit()
        
        # Slide-out animation
        self.slide_out_animation = QPropertyAnimation(self, b"geometry")
        self.slide_out_animation.setDuration(200)
        self.slide_out_animation.setEasingCurve(QEasingCurve.Type.InQuad)
        
        current_geo = self.geometry()
        end_geo = QRect(
            current_geo.x() + 400,  # Slide to right
            current_geo.y(),
            current_geo.width(),
            current_geo.height()
        )
        
        self.slide_out_animation.setStartValue(current_geo)
        self.slide_out_animation.setEndValue(end_geo)
        self.slide_out_animation.finished.connect(self.deleteLater)
        self.slide_out_animation.start()

def show_toast(parent_window, message, toast_type="success", duration=4000):
    """
    Helper function to show a toast easily.
    Standardized to bottom-right stacking relative to the MAIN APPLICATION WINDOW.
    """
    if not parent_window:
        logger.info("Toast without parent: %s", message)
        return

    # ALWAYS find the true application window, never the active dialog.
    main_window = None
    for candidate in QApplication.topLevelWidgets():
        if candidate.objectName() == "ModernDesktopApp":
            main_window = candidate
            break
        if getattr(candidate, "db", None) is not None and candidate.isVisible():
            main_window = candidate
    if main_window is None:
        current = parent_window
        while current is not None and current.parent():
            current = current.parent()
        main_window = current or parent_window
    
    # 2. Try to use ToastManager (Higher priority for stacking)
    if hasattr(main_window, "toast") and hasattr(main_window.toast, "show_toast"):
        main_window.toast.show_toast(message, toast_type, duration)
        return

    # 3. Look for NotificationContainer (Alternate)
    from PyQt6.QtWidgets import QWidget
    container = main_window.findChild(QWidget, "NotificationContainer")
    if container and hasattr(container, "add_notification"):
        container.add_notification(message, toast_type, duration)
        return
        
    # 4. Fallback: Create floating toast in bottom-right corner of the top-level window
    # IMPORTANT: Parent is main_window, so coordinates are relative to main window
    toast = ToastNotification(message, toast_type, duration, parent=main_window)
    toast.show()
    
    # Precise positioning in bottom-right of MAIN WINDOW (Fixed)
    win_rect = main_window.rect()
    
    # Standard margins (30px from bottom, 30px from right)
    target_x = win_rect.width() - toast.width() - 30
    target_y = win_rect.height() - toast.height() - 30
    
    # If the window is too small, ensure it stays visible
    target_x = max(10, target_x)
    target_y = max(10, target_y)
    
    toast.move(target_x, target_y)
    toast.raise_()

    # Simple animation (fade in)
    anim = QPropertyAnimation(toast, b"windowOpacity")
    anim.setDuration(300)
    anim.setStartValue(0)
    anim.setEndValue(1)
    anim.start()
    toast._fade_anim = anim # Keep reference

def show_error(parent, message):
    show_toast(parent, message, "error")

def show_success(parent, message):
    show_toast(parent, message, "success")

def show_warning(parent, message):
    show_toast(parent, message, "warning")

def show_info(parent, message):
    show_toast(parent, message, "info")

class NotificationContainer(QWidget):
    """
    Invisible container to stack toast notifications at the bottom-right of the window.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True) # Let clicks pass through empty areas
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)     # Crucial for transparency
        
        # Fixed size and alignment
        self.setFixedWidth(400) 
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 30, 30) # 30px margin from bottom and right
        self.layout.setSpacing(12)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        
        self.notifications = []

    def paintEvent(self, event):
        # Do not paint background at all
        pass

    def add_notification(self, message, toast_type="info", duration=4000, action=None):
        # ... logic as before ...
        toast = ToastNotification(message, toast_type, duration, parent=self)
        if action:
             toast.set_action(action)
             
        # Enable mouse events only for the toast itself (handled by toast widget)
        # self.setAttribute(Qt.WA_TransparentForMouseEvents, False) # Can't toggle parent easily
        
        self.layout.addWidget(toast)
        self.notifications.append(toast)
        toast.show()
        
        # Simple entry animation
        anim = QPropertyAnimation(toast, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.start()

        # Cleanup
        toast.dismiss_timer.timeout.connect(lambda: self.remove_notification(toast))

    def remove_notification(self, toast):
        if toast in self.notifications:
            self.layout.removeWidget(toast)
            toast.close()
            self.notifications.remove(toast)

