# -*- coding: utf-8 -*-
"""
DistributionDonutWidget - "Servis Durum Dağılımı" panel in Resim 1.
Features:
- Header with dropdown ("Bu Ay", "Tümü", etc.)
- Donut chart drawn with QPainter with center hole displaying:
  "Toplam\n{total}\nServis"
- Right side legend with colored dots, status titles, and counts
- Clicking any status in the legend navigates to Service List with that filter!
"""

from __future__ import annotations

from typing import Dict, List, Tuple
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen, QBrush
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.utils.theme_colors import theme_qss


class DonutCanvas(QWidget):
    """Draws the donut chart with center hole and text"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(160, 160)
        self.segments: List[Tuple[float, QColor]] = []
        self.total_count = 0

    def set_data(self, data_list: List[Tuple[int, str]], total_count=None):
        """data_list: list of (count, hex_color)"""
        segment_total = sum(cnt for cnt, _ in data_list)
        self.total_count = segment_total if total_count is None else int(total_count or 0)
        self.segments = []
        if segment_total == 0:
            self.segments.append((1.0, QColor("#E2E8F0")))
        else:
            for cnt, col in data_list:
                if cnt > 0:
                    fraction = cnt / segment_total
                    self.segments.append((fraction, QColor(col)))
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(10, 10, self.width() - 20, self.height() - 20)
        start_angle = 90 * 16

        painter.setPen(Qt.PenStyle.NoPen)
        for frac, color in self.segments:
            span_angle = int(round(frac * 360 * 16))
            painter.setBrush(QBrush(color))
            painter.drawPie(rect, start_angle, -span_angle)
            start_angle -= span_angle

        # Inner hole
        hole_margin = 32
        hole_rect = QRectF(
            rect.x() + hole_margin,
            rect.y() + hole_margin,
            rect.width() - (hole_margin * 2),
            rect.height() - (hole_margin * 2),
        )
        # Background color matching surface
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(hole_rect)

        # Center Text: Toplam / count / Servis
        painter.setPen(QColor("#64748B"))
        font_sub = QFont("Segoe UI", 8, QFont.Weight.Bold)
        painter.setFont(font_sub)
        painter.drawText(
            QRectF(hole_rect.x(), hole_rect.y() + 10, hole_rect.width(), 16),
            Qt.AlignmentFlag.AlignCenter,
            "Toplam",
        )

        painter.setPen(QColor("#0F172A"))
        font_val = QFont("Segoe UI", 16, QFont.Weight.Black)
        painter.setFont(font_val)
        painter.drawText(
            QRectF(hole_rect.x(), hole_rect.y() + 26, hole_rect.width(), 26),
            Qt.AlignmentFlag.AlignCenter,
            str(self.total_count),
        )

        painter.setPen(QColor("#64748B"))
        painter.setFont(font_sub)
        painter.drawText(
            QRectF(hole_rect.x(), hole_rect.y() + 52, hole_rect.width(), 16),
            Qt.AlignmentFlag.AlignCenter,
            "Servis",
        )


class DistributionDonutWidget(QFrame):
    """
    Panel for "Servis Durum Dağılımı" in Resim 1.
    """

    status_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DistributionDonutWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(theme_qss("""
            QFrame#DistributionDonutWidget {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 14px;
            }
        """))

        self.legend_items: List[Tuple[str, str, QLabel, QPushButton]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # 1. Header
        header = QHBoxLayout()
        lbl_heading = QLabel("Servis Durum Da\u011f\u0131l\u0131m\u0131", self)
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
        self.combo_period.addItem("Bu Ay", "month")
        self.combo_period.addItem("Bug\u00fcn", "today")
        self.combo_period.addItem("Bu Hafta", "week")
        self.combo_period.addItem("T\u00fcm\u00fc", "all")
        header.addWidget(self.combo_period)
        layout.addLayout(header)

        # 2. Content Row: Donut + Legend
        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 4, 0, 4)
        content_row.setSpacing(14)

        self.canvas = DonutCanvas(self)
        content_row.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)

        # Legend list in scrollable area
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        legend_container = QWidget()
        legend_container.setStyleSheet("background: transparent;")
        self.legend_layout = QVBoxLayout(legend_container)
        self.legend_layout.setContentsMargins(0, 0, 0, 0)
        self.legend_layout.setSpacing(6)

        # Status defs: (key, title, color_hex)
        self.statuses_def = [
            ("done", "Tamir Edilenler", "#05A85B"),
            ("active", "Tamirde Olanlar", "#E53935"),
            ("waiting", "\u0130\u015fleme Al\u0131nacaklar", "#1E88E5"),
            ("iptal", "\u0130ptal / \u0130ade", "#D32F2F"),
            ("cargo_waiting", "Kargoya Verilenler", "#D81B60"),
            ("teslim", "Teslim Edilenler", "#00ACC1"),
            ("part", "Par\u00e7a Bekleyenler", "#8E24AA"),
            ("debt", "Bor\u00e7lu Olanlar", "#43A047"),
        ]

        self.count_labels: Dict[str, QLabel] = {}

        for key, title, color in self.statuses_def:
            row_btn = QPushButton(legend_container)
            row_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            row_btn.setFixedHeight(22)
            row_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: rgba(0, 0, 0, 0.04);
                    border-radius: 4px;
                }
            """)
            row_btn.clicked.connect(lambda checked=False, k=key: self.status_selected.emit(k))

            r_lay = QHBoxLayout(row_btn)
            r_lay.setContentsMargins(4, 0, 4, 0)
            r_lay.setSpacing(8)

            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            r_lay.addWidget(dot)

            lbl_txt = QLabel(title)
            lbl_txt.setStyleSheet(theme_qss("font-size: 11px; font-weight: 600; color: @text; border: none;"))
            r_lay.addWidget(lbl_txt)
            r_lay.addStretch()

            lbl_cnt = QLabel("0")
            lbl_cnt.setStyleSheet(theme_qss("font-size: 11px; font-weight: 800; color: @text; border: none;"))
            r_lay.addWidget(lbl_cnt)
            self.count_labels[key] = lbl_cnt

            self.legend_layout.addWidget(row_btn)

        self.legend_layout.addStretch()
        scroll.setWidget(legend_container)
        content_row.addWidget(scroll, 1)

        layout.addLayout(content_row)

    def update_counts(self, counts: Dict[str, int], total_count=None):
        data_list = []
        for key, _, color in self.statuses_def:
            cnt = counts.get(key, 0)
            if key in self.count_labels:
                self.count_labels[key].setText(str(cnt))
            data_list.append((cnt, color))
        self.canvas.set_data(data_list, total_count=total_count)
