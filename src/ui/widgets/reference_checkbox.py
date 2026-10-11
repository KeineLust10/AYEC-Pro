"""Native checkbox with a token-colored hairline indicator and vector check mark."""

from PyQt6.QtCore import QRectF, QPointF, Qt
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtWidgets import QCheckBox
from src.utils.theme_colors import qc


class ReferenceCheckBox(QCheckBox):
    def __init__(self, parent=None, checked_token="finance_primary"):
        super().__init__(parent)
        self.checked_token = checked_token

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(3, (self.height() - 14) / 2, 14, 14)
        outline = qc(self.checked_token if self.isChecked() else "finance_outline")
        background = qc(self.checked_token if self.isChecked() else "finance_surface_alt")
        if not self.isEnabled():
            outline.setAlpha(150)
            background.setAlpha(150)
        painter.setPen(QPen(outline, 1))
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 3, 3)
        if self.isChecked():
            painter.setPen(QPen(qc("finance_canvas"), 1.8))
            painter.drawLine(QPointF(rect.left() + 3, rect.top() + 7), QPointF(rect.left() + 6, rect.top() + 10))
            painter.drawLine(QPointF(rect.left() + 6, rect.top() + 10), QPointF(rect.left() + 11, rect.top() + 4))
        if self.hasFocus():
            painter.setPen(QPen(qc("finance_primary"), 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(-2, -2, 2, 2), 4, 4)
        painter.end()
