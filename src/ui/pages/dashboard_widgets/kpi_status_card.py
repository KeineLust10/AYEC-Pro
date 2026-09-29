# -*- coding: utf-8 -*-
"""
KPIStatusCard - Modern status card matching Resim 1.
Features:
- Left colored circle with crisp icon
- Big bold count
- Status label & descriptive subtitle
- Faint watermark icon on right
- Clickable arrow button and card click redirecting to Service List
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QFont, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.pages._dashboard_utils import render_svg_icon
from src.utils.theme_colors import theme_qss


class KPIStatusCard(QFrame):
    """
    Main status card component as seen in Resim 1.
    Grid of 8 cards on the dashboard.
    """

    clicked = pyqtSignal()

    def __init__(
        self,
        key: str,
        title: str,
        count: int,
        subtitle: str,
        color_hex: str,
        icon_svg: str,
        watermark_svg: str = "",
        callback=None,
        parent=None,
    ):
        super().__init__(parent)
        self.key = key
        self.title_text = title
        self.count_val = count
        self.subtitle_text = subtitle
        self.color_hex = color_hex
        self.icon_svg = icon_svg
        self.watermark_svg = watermark_svg
        self.callback = callback

        if self.callback:
            self.clicked.connect(self.callback)

        self.setObjectName("KPIStatusCard")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(110)

        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # 1. Left Circle with Icon
        self.icon_lbl = QLabel(self)
        self.icon_lbl.setFixedSize(46, 46)
        self.icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_lbl.setStyleSheet(f"""
            background-color: {self.color_hex};
            border-radius: 23px;
            border: none;
        """)
        pix = render_svg_icon(self.icon_svg, "#FFFFFF", size=22)
        self.icon_lbl.setPixmap(pix)
        layout.addWidget(self.icon_lbl)

        # 2. Text Info (Title, Big Number, Subtitle)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        self.lbl_title = QLabel(self.title_text, self)
        self.lbl_title.setStyleSheet(theme_qss("""
            font-size: 13px;
            font-weight: 800;
            color: @text;
            border: none;
            background: transparent;
        """))
        info_layout.addWidget(self.lbl_title)

        self.lbl_count = QLabel(str(self.count_val), self)
        self.lbl_count.setStyleSheet(theme_qss(f"""
            font-size: 26px;
            font-weight: 900;
            color: {self.color_hex};
            border: none;
            background: transparent;
        """))
        info_layout.addWidget(self.lbl_count)

        self.lbl_sub = QLabel(self.subtitle_text, self)
        self.lbl_sub.setStyleSheet(theme_qss("""
            font-size: 11px;
            font-weight: 600;
            color: @text_muted;
            border: none;
            background: transparent;
        """))
        info_layout.addWidget(self.lbl_sub)

        layout.addLayout(info_layout, 1)

        # 3. Right Watermark Icon (faint/semi-transparent)
        if self.watermark_svg:
            self.watermark_lbl = QLabel(self)
            self.watermark_lbl.setFixedSize(54, 54)
            self.watermark_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.watermark_lbl.setStyleSheet("background: transparent; border: none;")
            wm_color = QColor(self.color_hex)
            wm_color.setAlphaF(0.12)
            wm_pix = render_svg_icon(self.watermark_svg, wm_color.name(QColor.NameFormat.HexArgb), size=44)
            self.watermark_lbl.setPixmap(wm_pix)
            layout.addWidget(self.watermark_lbl)

        # 4. Arrow button on bottom-right
        self.btn_arrow = QPushButton("\u2192", self)
        self.btn_arrow.setFixedSize(26, 26)
        self.btn_arrow.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_arrow.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.color_hex}1A;
                color: {self.color_hex};
                border: 1px solid {self.color_hex}33;
                border-radius: 13px;
                font-size: 13px;
                font-weight: 900;
            }}
            QPushButton:hover {{
                background-color: {self.color_hex};
                color: #FFFFFF;
            }}
        """)
        if self.callback:
            self.btn_arrow.clicked.connect(self.callback)
        layout.addWidget(self.btn_arrow, alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)

    def _apply_style(self):
        self.setStyleSheet(theme_qss(f"""
            QFrame#KPIStatusCard {{
                background-color: @surface;
                border: 1px solid @border;
                border-left: 4px solid {self.color_hex};
                border-radius: 14px;
            }}
            QFrame#KPIStatusCard:hover {{
                background-color: @surface_alt;
                border-color: {self.color_hex};
            }}
        """))

    def set_count(self, count: int):
        self.count_val = count
        self.lbl_count.setText(str(count))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
