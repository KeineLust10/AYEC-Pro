"""
Action Button Widget
Aksiyon butonu widget'i
"""
from PyQt6.QtGui import QColor
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton


class ActionButton(QPushButton):
    """Aksiyon butonu widget'i."""

    def __init__(self, text, icon, color, callback):
        super().__init__()
        self.setText(f"{icon} {text}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(50)

        base_color = QColor(color)
        border_color = base_color.name()
        text_color = "#F8FAFC" if base_color.lightness() < 150 else "#0F172A"
        hover_bg = self.with_alpha(base_color, 0.20)
        pressed_bg = self.with_alpha(base_color, 0.28)

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {border_color};
                border: 1px solid {self.with_alpha(base_color, 0.45)};
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {hover_bg};
                color: {text_color};
                border: 1px solid {border_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_bg};
                color: {text_color};
                border: 1px solid {border_color};
            }}
        """)

        if callback:
            self.clicked.connect(callback)

    @staticmethod
    def with_alpha(color, alpha):
        rgba = QColor(color)
        rgba.setAlphaF(alpha)
        return rgba.name(QColor.NameFormat.HexArgb)
