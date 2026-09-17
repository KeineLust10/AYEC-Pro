"""
Toast Manager
Manages toast notifications: positioning, queuing, stacking, and sound effects.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import QObject, QTimer, QPoint, pyqtSignal, QUrl
from PyQt6.QtMultimedia import QSoundEffect
from src.ui.widgets.toast_notification import ToastNotification
import os

class ToastManager(QObject):
    """
    Manages toast notifications with queuing and positioning.
    """
    
    def __init__(self, parent_widget):
        super().__init__()
        self.parent_widget = parent_widget
        self.active_toasts = []
        self.notification_history = []
        self.max_visible = 3
        self.sounds_enabled = True
        
        # Sound files (optional - will work without them)
        self.sounds = {
            "success": self._get_sound_path("success.wav"),
            "error": self._get_sound_path("error.wav"),
            "warning": self._get_sound_path("warning.wav"),
        }
    
    def _get_sound_path(self, filename):
        """Get sound file path if it exists."""
        sound_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sounds")
        sound_path = os.path.join(sound_dir, filename)
        return sound_path if os.path.exists(sound_path) else None
    
    def show_toast(self, message, toast_type="info", duration=4000, progress=None, action=None):
        """
        Show a toast notification.
        
        Args:
            message: Notification message
            toast_type: "success", "info", "warning", or "error"
            duration: Auto-dismiss duration in ms (0 = no auto-dismiss)
            progress: Initial progress value (0-100) or None
            action: Tuple of (button_text, callback) or None
            
        Returns:
            ToastNotification instance
        """
        # Create toast
        toast = ToastNotification(
            message=message,
            toast_type=toast_type,
            duration=duration,
            progress=progress,
            action=action,
            parent=self.parent_widget
        )
        toast.ensurePolished()
        if toast.layout() is not None:
            toast.layout().activate()
        toast.adjustSize()
        
        # Add to history
        self.notification_history.insert(0, {
            "message": message,
            "type": toast_type,
            "timestamp": self._get_timestamp()
        })
        
        # Keep only last 20
        if len(self.notification_history) > 20:
            self.notification_history = self.notification_history[:20]
        
        # Play sound
        if self.sounds_enabled and toast_type in self.sounds:
            sound_path = self.sounds[toast_type]
            if sound_path and os.path.exists(sound_path):
                try:
                    self._play_sound(sound_path)
                except Exception:
                    pass  # Silently fail if sound doesn't work
        
        # Position toast
        self._position_toast(toast)
        
        # Add to active list
        self.active_toasts.append(toast)
        
        # Connect close signal
        toast.closed.connect(lambda: self._on_toast_closed(toast))
        
        # Show with slide-in animation
        toast.show()
        self._animate_slide_in(toast)
        
        # Remove oldest if too many
        if len(self.active_toasts) > self.max_visible:
            oldest = self.active_toasts[0]
            oldest.dismiss()
        
        return toast

    def _position_toast(self, toast):
        """Calculate and set the initial position of a toast."""
        # Use window() to get the actual application window dimensions
        window = self.parent_widget.window()
        
        # If the window is not visible or minimized, fallback to primary screen
        from PyQt6.QtWidgets import QApplication
        if not window.isVisible() or window.isMinimized():
            screen = QApplication.primaryScreen()
            win_rect = screen.availableGeometry()
            is_fallback = True
        else:
            win_rect = window.rect()
            is_fallback = False
            
        # Calculate position relative to container
        # Reserve the assistant alert lane at the lower-right corner.
        horizontal_margin = 30
        vertical_margin = 145
        spacing = 15
        
        # Every new toast enters the bottom notification lane. Older toasts
        # are moved upward separately after the new toast is shown.
        y_offset = vertical_margin
        
        # Calculate X/Y in absolute or relative coordinates
        x = win_rect.width() - toast.width() - horizontal_margin
        y = win_rect.height() - toast.height() - y_offset
        
        if is_fallback:
             # If fallback to screen, add screen top-left offset if any
             x += win_rect.x()
             y += win_rect.y()
        else:
             # If the parent is not the window, we need to map the coordinates
             if self.parent_widget != window:
                  abs_pos = QPoint(x, y)
                  # Map from window to parent_widget's local coordinates
                  local_pos = self.parent_widget.mapFrom(window, abs_pos)
                  x, y = local_pos.x(), local_pos.y()
        
        # Set initial position (off-screen to the right for slide-in)
        start_x = win_rect.width() + 50
        if not is_fallback and self.parent_widget != window:
             start_x = self.parent_widget.width() + 50
        elif is_fallback:
             start_x += win_rect.x()

        toast.setGeometry(
            start_x,
            y,
            toast.width(),
            toast.height()
        )
    
    def _animate_slide_in(self, toast):
        """Animate toast sliding in from right."""
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect
        from PyQt6.QtWidgets import QApplication
        
        window = self.parent_widget.window()
        
        # If the window is not visible or minimized, fallback to primary screen
        if not window.isVisible() or window.isMinimized():
            screen = QApplication.primaryScreen()
            win_rect = screen.availableGeometry()
            is_fallback = True
        else:
            win_rect = window.rect()
            is_fallback = False
            
        horizontal_margin = 30
        vertical_margin = 145
        spacing = 15
        
        # The newest toast always finishes in the bottom notification lane.
        y_offset = vertical_margin
        
        final_x = win_rect.width() - toast.width() - horizontal_margin
        final_y = win_rect.height() - toast.height() - y_offset
        
        if is_fallback:
             final_x += win_rect.x()
             final_y += win_rect.y()
        else:
            # Map to parent if necessary
            if self.parent_widget != window:
                 local_pos = self.parent_widget.mapFrom(window, QPoint(final_x, final_y))
                 final_x, final_y = local_pos.x(), local_pos.y()
        
        # Slide-in animation
        animation = QPropertyAnimation(toast, b"geometry")
        animation.setDuration(350)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        start_geo = toast.geometry()
        end_geo = QRect(final_x, final_y, toast.width(), toast.height())
        
        animation.setStartValue(start_geo)
        animation.setEndValue(end_geo)
        animation.start()
        
        toast._slide_animation = animation
        self._reposition_toasts(exclude_toast=toast)
    
    def _on_toast_closed(self, toast):
        """Handle toast close event."""
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
        
        # Reposition remaining toasts
        QTimer.singleShot(100, self._reposition_toasts)
    
    def _reposition_toasts(self, exclude_toast=None):
        """Reposition all active toasts correctly stacked at bottom-right."""
        from PyQt6.QtWidgets import QApplication
        window = self.parent_widget.window()
        
        # If the window is not visible or minimized, fallback to primary screen
        if not window.isVisible() or window.isMinimized():
            screen = QApplication.primaryScreen()
            win_rect = screen.availableGeometry()
            is_fallback = True
        else:
            win_rect = window.rect()
            is_fallback = False
            
        horizontal_margin = 30
        vertical_margin = 145
        spacing = 15
        
        y_offset = vertical_margin
        for toast in reversed(self.active_toasts):
            if toast.isVisible():
                from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QRect
                
                final_x = win_rect.width() - toast.width() - horizontal_margin
                final_y = win_rect.height() - toast.height() - y_offset
                
                if is_fallback:
                     final_x += win_rect.x()
                     final_y += win_rect.y()
                else:
                    # Map to parent if necessary
                    if self.parent_widget != window:
                         local_pos = self.parent_widget.mapFrom(window, QPoint(final_x, final_y))
                         final_x, final_y = local_pos.x(), local_pos.y()
                
                if toast is not exclude_toast:
                    # Smooth reposition animation
                    animation = QPropertyAnimation(toast, b"geometry")
                    animation.setDuration(300)
                    animation.setEasingCurve(QEasingCurve.Type.OutQuad)
                    animation.setStartValue(toast.geometry())
                    animation.setEndValue(QRect(final_x, final_y, toast.width(), toast.height()))
                    animation.start()
                    toast._reposition_animation = animation
                
                y_offset += toast.height() + spacing

    def reposition_toasts(self):
        """Public resize hook used by the main window."""
        self._reposition_toasts()
    
    def _get_timestamp(self):
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def get_history(self):
        """Get notification history."""
        return self.notification_history
    
    def clear_history(self):
        """Clear notification history."""
        self.notification_history = []
    
    def set_sounds_enabled(self, enabled):
        """Enable or disable notification sounds."""
        self.sounds_enabled = enabled

    def _play_sound(self, path):
        """Play sound using QSoundEffect."""
        self.effect = QSoundEffect()
        self.effect.setSource(QUrl.fromLocalFile(path))
        self.effect.play()
