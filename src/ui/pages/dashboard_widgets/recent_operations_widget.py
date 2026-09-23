# -*- coding: utf-8 -*-
"""
RecentOperationsWidget - "Son İşlemler" panel in Resim 1.
Features:
- Header with "Son İşlemler" and "Tümünü Gör >" button
- List of recent activity rows with colored status icons, service text, and relative time
"""

from __future__ import annotations

from typing import Any, Dict, List
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.ui.pages._dashboard_utils import render_svg_icon
from src.utils.theme_colors import theme_qss


class RecentOperationRow(QFrame):
    """Single activity row in recent operations panel"""

    clicked = pyqtSignal(str)

    def __init__(
        self,
        tracking_no: str,
        status_text: str,
        time_text: str,
        icon_svg: str,
        color_hex: str,
        parent=None,
    ):
        super().__init__(parent)
        self.tracking_no = tracking_no
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(48)
        self.setStyleSheet("""
            QFrame {
                background-color: transparent;
                border: none;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: rgba(0, 0, 0, 0.03);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)

        # 1. Circle Icon
        icon_lbl = QLabel(self)
        icon_lbl.setFixedSize(32, 32)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet(f"""
            background-color: {color_hex};
            border-radius: 16px;
            border: none;
        """)
        pix = render_svg_icon(icon_svg, "#FFFFFF", size=16)
        if isinstance(pix, QIcon):
            pix = pix.pixmap(16, 16)
        icon_lbl.setPixmap(pix)
        layout.addWidget(icon_lbl)

        # 2. Text Box
        txt_box = QVBoxLayout()
        txt_box.setContentsMargins(0, 0, 0, 0)
        txt_box.setSpacing(1)

        lbl_servis = QLabel(f"Servis #{tracking_no}", self)
        lbl_servis.setStyleSheet(theme_qss(
            "font-size: 12px; font-weight: 800; color: @text; border: none; background: transparent;"
        ))
        txt_box.addWidget(lbl_servis)

        lbl_sub = QLabel(status_text, self)
        lbl_sub.setStyleSheet(theme_qss(
            "font-size: 11px; color: @text_muted; border: none; background: transparent;"
        ))
        txt_box.addWidget(lbl_sub)

        layout.addLayout(txt_box, 1)

        # 3. Relative Time
        lbl_time = QLabel(time_text, self)
        lbl_time.setStyleSheet(theme_qss(
            "font-size: 11px; font-weight: 600; color: @text_muted; border: none; background: transparent;"
        ))
        layout.addWidget(lbl_time)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.tracking_no)
        super().mousePressEvent(event)


class RecentOperationsWidget(QFrame):
    """
    Panel for "Son İşlemler" in Resim 1.
    """

    see_all_clicked = pyqtSignal()
    item_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RecentOperationsWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(theme_qss("""
            QFrame#RecentOperationsWidget {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 14px;
            }
        """))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # 1. Header with "Tümünü Gör >" button
        header = QHBoxLayout()
        lbl_heading = QLabel("Son \u0130\u015flemler", self)
        lbl_heading.setStyleSheet(theme_qss(
            "font-size: 14px; font-weight: 800; color: @text; border: none;"
        ))
        header.addWidget(lbl_heading)
        header.addStretch()

        self.btn_see_all = QPushButton("T\u00fcm\u00fcn\u00fc G\u00f6r \u203a", self)
        self.btn_see_all.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_see_all.setFixedHeight(28)
        self.btn_see_all.setStyleSheet(theme_qss("""
            QPushButton {
                background: transparent;
                color: #2563EB;
                font-size: 12px;
                font-weight: 700;
                border: none;
                padding: 0 6px;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """))
        self.btn_see_all.clicked.connect(self.see_all_clicked.emit)
        header.addWidget(self.btn_see_all)

        layout.addLayout(header)

        # 2. Rows Container
        self.rows_container = QWidget()
        self.rows_container.setStyleSheet("background: transparent;")
        self.rows_layout = QVBoxLayout(self.rows_container)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(4)

        layout.addWidget(self.rows_container, 1)

    def set_operations(self, operations: List[Dict[str, Any]]):
        """Update list with recent operations"""
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not operations:
            empty_lbl = QLabel("Hen\u00fcz servis kayd\u0131 bulunmuyor.", self)
            empty_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; padding: 20px 0;"))
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.rows_layout.addWidget(empty_lbl)
            return

        for op in operations[:5]:
            tno = str(op.get("tracking_no") or "")
            status = str(op.get("status") or "")
            rel_time = str(op.get("time_ago") or "Bug\u00fcn")
            color = str(op.get("color") or "#2563EB")
            svg = str(op.get("svg") or "")

            row = RecentOperationRow(tno, status, rel_time, svg, color, self)
            row.clicked.connect(self.item_clicked.emit)
            self.rows_layout.addWidget(row)

        self.rows_layout.addStretch()
