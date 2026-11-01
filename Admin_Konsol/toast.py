"""Lightweight bottom-right toast notifications for the Admin Console."""

from PyQt6.QtCore import QEvent, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


_TONES = {
    "info": ("#4d8eff", "#adc6ff", "i"),
    "success": ("#4edea3", "#4edea3", "+"),
    "warning": ("#ffb454", "#ffcf8a", "!"),
    "error": ("#ff6b73", "#ffb4ab", "!"),
}


class _Toast(QFrame):
    expired = pyqtSignal(object)

    def __init__(self, message, level, parent=None):
        super().__init__(parent)
        accent, foreground, icon = _TONES.get(level, _TONES["info"])
        self.setObjectName("adminToast")
        self.setStyleSheet(
            "QFrame#adminToast { background: #1a1f2e; "
            f"border: 1px solid {accent}; border-left: 4px solid {accent}; "
            "border-radius: 7px; }"
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 9, 14, 9)
        layout.setSpacing(10)
        badge = QLabel(icon)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(22, 22)
        badge.setStyleSheet(
            f"background: {accent}; color: #0e1321; border-radius: 11px; "
            "font: 700 12px 'Segoe UI', Arial;"
        )
        text = QLabel(str(message or ""))
        text.setWordWrap(True)
        text.setObjectName("adminToastText")
        text.setTextFormat(Qt.TextFormat.PlainText)
        text.setStyleSheet(
            f"color: {foreground}; font: 600 10pt 'Segoe UI', Arial; "
            "background: transparent; border: none;"
        )
        text.setAccessibleName("Bildirim")
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignTop)
        layout.addWidget(text, 1)
        self.setMinimumWidth(280)
        self.setMaximumWidth(420)

    def expire(self):
        self.expired.emit(self)


class _ToastHost(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 12, 16, 16)
        self._layout.setSpacing(8)
        self._layout.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setStyleSheet("background: transparent;")
        self.setGeometry(window.rect())
        window.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize:
            self.setGeometry(watched.rect())
        return super().eventFilter(watched, event)

    def show_message(self, message, level, duration):
        toast = _Toast(message, level, self)
        self._layout.addWidget(toast, 0, Qt.AlignmentFlag.AlignRight)
        toast.show()
        self.show()
        self.raise_()
        toast.expired.connect(self._remove)
        timer = QTimer(toast)
        timer.setSingleShot(True)
        timer.timeout.connect(toast.expire)
        timer.start(max(1000, int(duration)))
        return toast

    def _remove(self, toast):
        if toast is None:
            return
        self._layout.removeWidget(toast)
        toast.deleteLater()
        if self._layout.count() == 0:
            self.hide()


def show_toast(parent, message, level="info", duration=4500):
    """Show a transient notification in the top-level window's lower-right corner."""
    if parent is None:
        return None
    window = parent.window()
    host = getattr(window, "_admin_toast_host", None)
    if host is None:
        host = _ToastHost(window)
        window._admin_toast_host = host
    return host.show_message(message, level, duration)
