# -*- coding: utf-8 -*-
"""
MonthlyTrendWidget - "Aylık Servis Trendi" panel in Resim 1.
Features:
- Header with dropdown ("Son 9 Ay", "Son 6 Ay", "Son 12 Ay")
- Custom Bar Chart widget with QPainter:
  - Y-axis grid lines and ticks (0, 10, 20, 30, 40)
  - 9 rounded top bars in modern blue
  - Month names along the X-axis (Oca, Şub, Mar, Nis, May, Haz, Tem, Ağu, Eyl)
"""

from __future__ import annotations

from typing import List, Tuple
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen, QBrush
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from src.utils.theme_colors import theme_qss


class BarChartCanvas(QWidget):
    """Draws the monthly trend bar chart with antialiasing"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        # Default 9 months data (month_label, value)
        self.data_points: List[Tuple[str, int]] = [
            ("Oca", 14),
            ("\u015eub", 18),
            ("Mar", 20),
            ("Nis", 25),
            ("May", 19),
            ("Haz", 21),
            ("Tem", 26),
            ("A\u011fu", 32),
            ("Eyl", 36),
        ]

    def set_data(self, data_points: List[Tuple[str, int]]):
        self.data_points = data_points
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        left_margin = 32
        right_margin = 16
        top_margin = 16
        bottom_margin = 28

        chart_w = w - left_margin - right_margin
        chart_h = h - top_margin - bottom_margin

        if chart_w <= 0 or chart_h <= 0:
            return

        max_val = max([val for _, val in self.data_points] + [40])
        # Round max_val up to next multiple of 10
        y_max = ((max_val + 9) // 10) * 10
        y_steps = 4
        y_step_val = y_max // y_steps

        # 1. Draw horizontal grid lines and Y-axis labels
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        for i in range(y_steps + 1):
            y_val = i * y_step_val
            y_pos = top_margin + chart_h - (i * (chart_h / y_steps))

            # Grid line
            painter.setPen(QPen(QColor("#E2E8F0"), 1, Qt.PenStyle.SolidLine))
            painter.drawLine(int(left_margin), int(y_pos), int(w - right_margin), int(y_pos))

            # Label
            painter.setPen(QColor("#94A3B8"))
            painter.drawText(
                QRectF(0, y_pos - 8, left_margin - 6, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(y_val),
            )

        # 2. Draw Bars and X-axis labels
        n = len(self.data_points)
        if n == 0:
            return

        slot_w = chart_w / n
        bar_w = min(26.0, slot_w * 0.60)
        bar_color = QColor("#3B82F6")

        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))

        for idx, (label, val) in enumerate(self.data_points):
            cx = left_margin + (idx + 0.5) * slot_w
            bx = cx - (bar_w / 2.0)

            bar_h = (val / y_max) * chart_h if y_max > 0 else 0
            by = top_margin + chart_h - bar_h

            # Draw bar with rounded top corners
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bar_color))
            painter.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), 4, 4)

            # X-axis Month Label
            painter.setPen(QColor("#64748B"))
            painter.drawText(
                QRectF(cx - (slot_w / 2), h - bottom_margin + 6, slot_w, 18),
                Qt.AlignmentFlag.AlignCenter,
                label,
            )


class MonthlyTrendWidget(QFrame):
    """
    Panel for "Aylık Servis Trendi" in Resim 1.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MonthlyTrendWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(theme_qss("""
            QFrame#MonthlyTrendWidget {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 14px;
            }
        """))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header
        header = QHBoxLayout()
        lbl_heading = QLabel("Ayl\u0131k Servis Trendi", self)
        lbl_heading.setStyleSheet(theme_qss(
            "font-size: 14px; font-weight: 800; color: @text; border: none;"
        ))
        header.addWidget(lbl_heading)
        header.addStretch()

        self.combo_period = QComboBox(self)
        self.combo_period.setFixedHeight(28)
        self.combo_period.setStyleSheet(theme_qss("""
            QComboBox {
                background-color: @surface_alt;
                color: @text;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid @border;
                border-radius: 6px;
                padding: 0 8px;
            }
            QComboBox::drop-down { border: none; }
        """))
        self.combo_period.addItem("Son 9 Ay", 9)
        self.combo_period.addItem("Son 6 Ay", 6)
        self.combo_period.addItem("Son 12 Ay", 12)
        header.addWidget(self.combo_period)
        layout.addLayout(header)

        # Canvas
        self.canvas = BarChartCanvas(self)
        layout.addWidget(self.canvas, 1)

    def set_data(self, points: List[Tuple[str, int]]):
        self.canvas.set_data(points)
