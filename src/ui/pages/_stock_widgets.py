# -*- coding: utf-8 -*-
# _stock_widgets.py
# Widgetler için modül

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsDropShadowEffect
from src.utils.theme_colors import theme_qss, tc


class StockStatCard(QFrame):
    """Modern istatistik karti."""

    clicked = pyqtSignal()

    def __init__(self, title, value, icon, color, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("StockStatCard")
        self.setFixedHeight(104)
        self.setMinimumWidth(220)
        self.setStyleSheet(
            theme_qss(f"""
            QFrame#StockStatCard {{
                background-color: @surface;
                border-radius: 16px;
                border: 1px solid {color};
                border-top: 4px solid {color};
            }}
            QFrame#StockStatCard:hover {{
                background-color: @surface_alt;
                border: 2px solid {color};
                border-top: 4px solid {color};
            }}
        """)
        )
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 10))
        shadow.setOffset(0, 2)
        self.setGraphicsEffect(shadow)

        # Kritik karti icin ozel renk temasi
        is_critical = "Kritik" in title
        bg_color = tc("danger_bg") if is_critical else tc("surface_alt")
        icon_color = tc("danger") if is_critical else color
        border_style = f"border: 1px solid {icon_color};"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(14)

        icon_lbl = QLabel(icon)
        icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        icon_lbl.setFixedSize(52, 52)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(
            theme_qss(
                f"background-color: {bg_color}; color: {icon_color}; font-size: 24px; border-radius: 26px; {border_style}"
            )
        )
        layout.addWidget(icon_lbl)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        self.val_lbl = QLabel(str(value))
        self.val_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        value_font_size = 20 if len(str(value)) <= 18 else 16
        self.val_lbl.setStyleSheet(
            theme_qss(
                f"font-size: {value_font_size}px; font-weight: 900; color: @text; border: none; background: transparent;"
            )
        )
        title_lbl = QLabel(title)
        title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        title_lbl.setStyleSheet(
            theme_qss(
                "font-size: 13px; font-weight: 700; color: @text; border: none; background: transparent;"
            )
        )

        text_layout.addWidget(self.val_lbl)
        text_layout.addWidget(title_lbl)

        layout.addLayout(text_layout)
        layout.addStretch(1)

        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
