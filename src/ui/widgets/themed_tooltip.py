from PyQt6.QtCore import QEvent, QObject, QPoint, Qt
from PyQt6.QtWidgets import QApplication, QLabel

from src.utils.appearance_mode import AppearanceModeManager
from src.utils.theme_colors import tc


class ThemedToolTipFilter(QObject):
    def __init__(self, button, text, db=None):
        super().__init__(button)
        self.button = button
        self.text = str(text or "")
        self.db = db
        self.enabled = True
        self.label = QLabel(
            "",
            button.window(),
            Qt.WindowType.ToolTip,
        )
        self.label.setAttribute(
            Qt.WidgetAttribute.WA_ShowWithoutActivating,
            True,
        )
        self.label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )
        self.label.setObjectName("AyecThemedToolTip")
        self.label.setProperty("skipThemeTransform", True)
        self.label.setMargin(0)
        self.button.setToolTip("")
        self.button.installEventFilter(self)
        self.button.destroyed.connect(self.label.deleteLater)

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        if not self.enabled:
            self.label.hide()

    def _apply_style(self):
        if AppearanceModeManager.is_classic(self.db):
            background = "#FFFFFF"
            foreground = "#111827"
            border = "#94A3B8"
        else:
            background = tc("surface") or "#0F172A"
            foreground = tc("text") or "#F8FAFC"
            border = tc("border") or "#334155"
        self.label.setStyleSheet(
            "QLabel#AyecThemedToolTip {"
            f"background-color: {background};"
            f"color: {foreground};"
            f"border: 1px solid {border};"
            "border-radius: 3px;"
            "padding: 5px 8px;"
            "font-size: 11px;"
            "font-weight: 600;"
            "}"
        )

    def _show_tooltip(self):
        if not self.enabled or not self.text:
            return
        self._apply_style()
        self.label.setText(self.text)
        self.label.adjustSize()
        anchor = self.button.mapToGlobal(
            QPoint(self.button.width(), self.button.height())
        )
        x_pos = anchor.x() - self.label.width()
        y_pos = anchor.y() + 4
        screen = QApplication.screenAt(anchor)
        if screen is not None:
            bounds = screen.availableGeometry()
            x_pos = max(
                bounds.left() + 4,
                min(x_pos, bounds.right() - self.label.width() - 4),
            )
            if y_pos + self.label.height() > bounds.bottom():
                y_pos = (
                    self.button.mapToGlobal(QPoint(0, 0)).y()
                    - self.label.height()
                    - 4
                )
        self.label.move(x_pos, y_pos)
        self.label.show()
        self.label.raise_()

    def eventFilter(self, watched, event):
        if watched is self.button:
            if event.type() == QEvent.Type.Enter:
                self._show_tooltip()
            elif event.type() in {
                QEvent.Type.Leave,
                QEvent.Type.Hide,
                QEvent.Type.MouseButtonPress,
            }:
                self.label.hide()
        return super().eventFilter(watched, event)
