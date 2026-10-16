import logging
import time
import traceback

from PyQt6.QtCore import QEvent, QObject, Qt
from PyQt6.QtWidgets import QWidget


class MenuWindowDiagnostics(QObject):
    """Temporary menu-click and small-window diagnostic logger."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._logger = logging.getLogger(__name__)
        self._last_menu = "startup"
        self._last_menu_time = time.monotonic()
        self._reported_windows = set()

    def record_menu_click(self, section, label, page_id=None):
        self._last_menu = f"{section} > {label} (page={page_id})"
        self._last_menu_time = time.monotonic()
        self._reported_windows.clear()
        self._logger.info("Menu diagnostic click: %s", self._last_menu)

    def eventFilter(self, watched, event):
        if event.type() != QEvent.Type.Show or not isinstance(watched, QWidget):
            return False
        try:
            if (
                watched.objectName() in {"qtooltip_label", "AyecThemedToolTip"}
                or watched.windowFlags() & Qt.WindowType.ToolTip
            ):
                return False
            if not watched.isWindow() or watched.width() > 500 or watched.height() > 500:
                return False
            title = str(watched.windowTitle() or "").strip()
            if title and title.lower() != "ayec pro":
                return False
            key = (id(watched), self._last_menu)
            if key in self._reported_windows:
                return False
            self._reported_windows.add(key)
            parent = watched.parent()
            elapsed_ms = int((time.monotonic() - self._last_menu_time) * 1000)
            stack = " <- ".join(
                f"{frame.name}@{frame.filename}:{frame.lineno}"
                for frame in traceback.extract_stack(limit=9)[:-1]
            )
            self._logger.error(
                "Small blank top-level window: menu=%r elapsed_ms=%s "
                "class=%s title=%r object=%r geometry=%s flags=%s parent=%s stack=%s",
                self._last_menu,
                elapsed_ms,
                type(watched).__name__,
                title,
                watched.objectName(),
                watched.geometry().getRect(),
                int(watched.windowFlags()),
                type(parent).__name__ if parent is not None else None,
                stack,
            )
        except RuntimeError:
            return False
        return False
