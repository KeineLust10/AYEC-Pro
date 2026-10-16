# -*- coding: utf-8 -*-
# _stock_widgets.py
# Widgetler için modül

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QFontMetrics, QPainter
from PyQt6.QtWidgets import QFrame, QLabel, QHBoxLayout, QVBoxLayout, QSizePolicy
from src.utils.theme_colors import theme_qss, qc
from src.ui.widgets.financial_reference_controls import FinancialMetricGlyph


class StockAmountLabel(QLabel):
    """Keep complete amount data while fitting primary and reference lines."""

    def __init__(self, value, token, parent=None):
        super().__init__(str(value), parent)
        self.token = token
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setToolTip(self.text())
        self.setMinimumHeight(36)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setStyleSheet('background: transparent; border: none; padding: 0;')

    def setText(self, value):
        super().setText(str(value))
        self.setToolTip(str(value))

    def amount_font(self, text, maximum=20):
        font = QFont(self.font())
        font.setBold(True)
        for size in range(maximum, 8, -1):
            font.setPixelSize(size)
            if QFontMetrics(font).horizontalAdvance(text) <= max(1, self.width() - 4):
                break
        return font

    def paintEvent(self, event):
        lines = self.text().split(' | ', 1)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setPen(qc(self.token))
        font = self.amount_font(lines[0])
        painter.setFont(font)
        metrics = QFontMetrics(font)
        painter.drawText(0, metrics.ascent() + 2, lines[0])
        if len(lines) > 1:
            painter.setPen(qc('finance_text_muted'))
            reference = self.amount_font(lines[1], 11)
            painter.setFont(reference)
            painter.drawText(0, metrics.height() + QFontMetrics(reference).ascent() + 3, lines[1])
        painter.end()


class StockStatCard(QFrame):
    """Dense reference KPI with the original click-to-filter contract."""

    clicked = pyqtSignal()

    def __init__(self, title, value, icon, color, parent=None, *, token='finance_text', glyph='tax'):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("StockStatCard")
        self.setFixedHeight(82)
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            theme_qss("""
            QFrame#StockStatCard {
                background-color: @finance_surface;
                border-radius: 14px;
                border: 1px solid @finance_outline;
            }
            QFrame#StockStatCard:hover {
                background-color: @finance_surface_high;
                border: 1px solid @finance_primary;
            }
        """)
        )
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        icon_box = QFrame()
        icon_box.setFixedSize(38, 38)
        icon_box.setStyleSheet(theme_qss(
            "QFrame { background: @finance_surface_high; border: 1px solid @finance_outline; border-radius: 13px; }"
        ))
        icon_layout = QHBoxLayout(icon_box)
        icon_layout.setContentsMargins(8, 8, 8, 8)
        self.icon_lbl = FinancialMetricGlyph(glyph, token, glyph_size=20)
        self.icon_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        icon_layout.addWidget(self.icon_lbl)
        layout.addWidget(icon_box, 0, Qt.AlignmentFlag.AlignVCenter)
        content = QVBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(5)
        self.title_lbl = QLabel(title)
        self.title_lbl.setWordWrap(True)
        self.title_lbl.setTextFormat(Qt.TextFormat.PlainText)
        self.title_lbl.setToolTip(title)
        self.title_lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.title_lbl.setStyleSheet(theme_qss(
            'background: transparent; border: none; color: @finance_text_muted; '
            'font-size: 11px; font-weight: 700;'
        ))
        self.title_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.val_lbl = StockAmountLabel(value, token)
        self.val_lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        content.addStretch(1)
        content.addWidget(self.val_lbl)
        content.addWidget(self.title_lbl)
        content.addStretch()
        layout.addLayout(content, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
