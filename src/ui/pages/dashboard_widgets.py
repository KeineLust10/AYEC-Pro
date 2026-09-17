# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt

from src.utils.theme_colors import theme_qss


class StatusBadge(QLabel):
    """Renkli durum kutucuğu"""
    def __init__(self, text, color_bg, color_text, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(theme_qss(f"""
            QLabel {{
                background-color: {color_bg};
                color: {color_text};
                border-radius: 12px;
                padding: 6px 14px;
                font-weight: 700;
                font-size: 11px;
                font-family: 'Segoe UI', sans-serif;
                letter-spacing: 0.5px;
            }}
        """))
        self.setFixedSize(130, 30)


