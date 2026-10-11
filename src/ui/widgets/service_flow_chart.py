from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtWidgets import QWidget, QSizePolicy
from src.utils.theme_colors import tc


class ServiceFlowChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.counts = [0] * 24
        self.setMinimumHeight(86)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_counts(self, counts):
        values = [max(0, int(value)) for value in counts]
        if len(values) != 24:
            raise ValueError("Service flow needs 24 hourly bins")
        self.counts = values
        self.setToolTip("\n".join("{:02d}:00 - {} cihaz".format(hour, value) for hour, value in enumerate(self.counts) if value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        active = [hour for hour, count in enumerate(self.counts) if count]
        start = min(9, min(active)) if active else 9
        end = max(18, max(active)) if active else 18
        maximum = max(self.counts) or 1
        baseline = self.height() - 20
        width = max(1, (self.width() - 12) / (end - start + 1))
        painter.setPen(QPen(QColor(tc("finance_outline")), 1))
        painter.drawLine(6, baseline, self.width() - 6, baseline)
        painter.setPen(Qt.PenStyle.NoPen)
        for index, hour in enumerate(range(start, end + 1)):
            count = self.counts[hour]
            if count:
                height = count / maximum * (baseline - 8)
                color = "finance_primary" if count == maximum else "finance_outline"
                painter.setBrush(QColor(tc(color)))
                painter.drawRoundedRect(QRectF(6 + index * width + 2, baseline - height, max(1, width - 4), height), 2, 2)
        painter.setPen(QColor(tc("finance_text_muted")))
        font = self.font()
        font.setPointSize(7)
        painter.setFont(font)
        labels = {start, end, start + (end - start) // 2}
        if end - start <= 12:
            labels.update(hour for hour in (12, 14, 16) if start <= hour <= end)
        for hour in sorted(labels):
            left = 6 + (hour - start) * width
            painter.drawText(QRectF(left, baseline + 3, width, 15), Qt.AlignmentFlag.AlignCenter, "{:02d}:00".format(hour))
