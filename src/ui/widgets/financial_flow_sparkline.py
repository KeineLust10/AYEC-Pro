import math

from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

from src.utils.theme_colors import tc


class FinancialFlowSparkline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values = []
        self.setMinimumWidth(160)
        self.setFixedHeight(32)

    def set_values(self, values):
        converted = [float(value) for value in values]
        if not all(math.isfinite(value) for value in converted):
            raise ValueError("Flow values must be finite")
        self.values = converted
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.values:
            return
        low, high = min(self.values + [0]), max(self.values + [0])
        span = high - low or 1
        points = [QPointF(4 + index * (self.width() - 8) / max(1, len(self.values) - 1), self.height() - 4 - (value - low) * (self.height() - 8) / span) for index, value in enumerate(self.values)]
        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)
        painter.setPen(QPen(QColor(tc("finance_secondary")), 2))
        painter.drawPath(path)
        painter.setBrush(QColor(tc("finance_secondary")))
        painter.drawEllipse(points[-1], 2, 2)
