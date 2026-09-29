# -*- coding: utf-8 -*-
"""
SecondaryMetricCard - 4 metric cards below status cards in Resim 1.
Shows:
- Left icon in rounded box
- Big count/currency
- Subtitle
- Top-right growth badge (+22%, +12%, +8%, +15%)
- Mini bar chart graphic
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.ui.pages._dashboard_utils import render_svg_icon
from src.utils.theme_colors import theme_qss


class MiniBarGraphic(QWidget):
    """Draws a mini 4-bar indicator next to trend percentages"""

    def __init__(self, color_hex: str = "#10B981", parent=None):
        super().__init__(parent)
        self.color_hex = color_hex
        self.setFixedSize(28, 22)

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.color_hex))

        heights = [8, 12, 16, 20]
        w = 4
        gap = 3
        start_x = 0
        h_total = self.height()

        for idx, bh in enumerate(heights):
            x = start_x + idx * (w + gap)
            y = h_total - bh
            painter.drawRoundedRect(x, y, w, bh, 2, 2)


class SecondaryMetricCard(QFrame):
    """
    Metric card widget matching Resim 1 second row:
    Bugünkü Servisler, Açık Randevular, Bekleyen İşler, Gelir.
    """

    def __init__(
        self,
        title: str,
        value: str,
        subtitle: str,
        trend_text: str,
        icon_color: str,
        icon_svg: str,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("SecondaryMetricCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(96)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # 1. Left Icon Container
        self.icon_box = QLabel(self)
        self.icon_box.setFixedSize(44, 44)
        self.icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_box.setStyleSheet(f"""
            background-color: {icon_color};
            border-radius: 12px;
            border: none;
        """)
        pix = render_svg_icon(icon_svg, "#FFFFFF", size=22)
        if isinstance(pix, QIcon):
            pix = pix.pixmap(22, 22)
        self.icon_box.setPixmap(pix)
        layout.addWidget(self.icon_box)

        # 2. Text Info
        vals_layout = QVBoxLayout()
        vals_layout.setContentsMargins(0, 0, 0, 0)
        vals_layout.setSpacing(2)

        self.lbl_title = QLabel(title, self)
        self.lbl_title.setStyleSheet(theme_qss("""
            font-size: 12px;
            font-weight: 700;
            color: @text_muted;
            border: none;
            background: transparent;
        """))
        vals_layout.addWidget(self.lbl_title)

        self.lbl_value = QLabel(value, self)
        self.lbl_value.setStyleSheet(theme_qss("""
            font-size: 22px;
            font-weight: 900;
            color: @text;
            border: none;
            background: transparent;
        """))
        vals_layout.addWidget(self.lbl_value)

        self.lbl_sub = QLabel(subtitle, self)
        self.lbl_sub.setStyleSheet(theme_qss("""
            font-size: 11px;
            color: @text_muted;
            border: none;
            background: transparent;
        """))
        vals_layout.addWidget(self.lbl_sub)

        layout.addLayout(vals_layout, 1)

        # 3. Right Trend & Mini Bar
        right_box = QVBoxLayout()
        right_box.setContentsMargins(0, 0, 0, 0)
        right_box.setSpacing(6)
        right_box.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        badge = QLabel(f" {trend_text} ", self)
        badge.setFixedHeight(22)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setStyleSheet("""
            background-color: #D1FAE5;
            color: #059669;
            font-size: 11px;
            font-weight: 800;
            border-radius: 6px;
            padding: 0 6px;
        """)
        right_box.addWidget(badge, alignment=Qt.AlignmentFlag.AlignRight)

        mini_bars = MiniBarGraphic("#10B981", self)
        right_box.addWidget(mini_bars, alignment=Qt.AlignmentFlag.AlignRight)

        layout.addLayout(right_box)

        self.setStyleSheet(theme_qss("""
            QFrame#SecondaryMetricCard {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 14px;
            }
            QFrame#SecondaryMetricCard:hover {
                border-color: @accent;
            }
        """))

    def set_value(self, val: str):
        self.lbl_value.setText(val)
