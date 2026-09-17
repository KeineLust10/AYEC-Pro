from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QPoint, QSize, pyqtSignal

class DraggableAssistantFabButton(QPushButton):
    """Floating assistant button that can be repositioned by drag."""
    position_changed = pyqtSignal(QPoint)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._dragging = False
        self._moved = False
        self._press_global = QPoint()
        self._start_pos = QPoint()
        self._drag_threshold = 6
        self._default_icon = None

    def set_default_icon(self, icon):
        self._default_icon = icon
        if icon is not None and not icon.isNull():
            self.setText("")
            self.setIcon(icon)
            self.setIconSize(QSize(32, 32))

    def restore_default_icon(self):
        if self._default_icon is not None and not self._default_icon.isNull():
            self.setText("")
            self.setIcon(self._default_icon)
            self.setIconSize(QSize(32, 32))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._moved = False
            self._press_global = event.globalPosition().toPoint()
            self._start_pos = self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging and (event.buttons() & Qt.MouseButton.LeftButton):
            delta = event.globalPosition().toPoint() - self._press_global
            if not self._moved and delta.manhattanLength() >= self._drag_threshold:
                self._moved = True
            if self._moved:
                parent = self.parentWidget()
                if parent is not None:
                    new_pos = self._start_pos + delta
                    max_x = max(0, parent.width() - self.width())
                    max_y = max(0, parent.height() - self.height())
                    x = max(0, min(new_pos.x(), max_x))
                    y = max(0, min(new_pos.y(), max_y))
                    self.move(x, y)
                    self.position_changed.emit(QPoint(x, y))
                    event.accept()
                    return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        was_moved = self._moved
        self._dragging = False
        self._moved = False
        if was_moved:
            event.accept()
            return
        super().mouseReleaseEvent(event)
