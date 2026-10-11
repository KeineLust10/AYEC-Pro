from PyQt6.QtCore import QByteArray, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QWidget

from src.utils.theme_colors import tc


class LoanerMetricIcon(QWidget):
    PATHS = {
        "computer": '<rect x="3" y="4" width="18" height="13" rx="1"/><path d="M8 21h8M12 17v4"/>',
        "warehouse": '<path d="M3 21V8l9-5 9 5v13M8 21V11h8v10M8 15h8M8 18h8"/>',
        "warning": '<path d="M12 3 2 21h20ZM12 9v5M12 17v1"/>',
        "shield": '<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z"/><path d="m8 12 3 3 5-6"/>',
        "clipboard": '<path d="M8 5H5v16h14V5h-3M8 3h8v4H8Z"/><path d="m8 14 3 3 5-6"/>',
        "outbound": '<circle cx="12" cy="12" r="9"/><path d="m8 16 8-8M10 8h6v6"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
        "check": '<circle cx="12" cy="12" r="9"/><path d="m7 12 3 3 7-7"/>',
        "truck": '<path d="M2 5h12v13H2ZM14 10h4l4 4v4h-8"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="19" r="2"/>',
    }

    def __init__(self, kind, color_token, parent=None):
        super().__init__(parent)
        self.kind = kind
        self.color_token = color_token
        self.setFixedSize(28, 28)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(tc("finance_surface_alt", default=tc("surface_alt"))))
        painter.drawRoundedRect(QRectF(self.rect()), 4, 4)
        color = tc(self.color_token, default=tc("text"))
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{}</svg>'.format(color, self.PATHS[self.kind])
        QSvgRenderer(QByteArray(svg.encode("ascii"))).render(painter, QRectF(4, 4, self.width() - 8, self.height() - 8))


class LoanerCategoryRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.counts = []
        self.setFixedSize(88, 88)

    def set_categories(self, categories):
        self.counts = [int(count) for _name, count in sorted(categories.items())]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        total = sum(self.counts)
        tokens = ("finance_primary", "finance_secondary", "finance_tertiary", "warning")
        rect = QRectF(7, 7, 74, 74)
        start = 90 * 16
        if not total:
            painter.setPen(QPen(QColor(tc("border")), 8))
            painter.drawEllipse(rect)
        for index, count in enumerate(self.counts):
            span = round(360 * 16 * count / max(1, total))
            painter.setPen(QPen(QColor(tc(tokens[index % len(tokens)], default=tc("primary"))), 8))
            painter.drawArc(rect, start, -span)
            start -= span
        painter.setPen(QColor(tc("finance_text", default=tc("text"))))
        number_font = QFont(self.font())
        number_font.setPixelSize(17)
        number_font.setWeight(QFont.Weight.Bold)
        painter.setFont(number_font)
        painter.drawText(QRectF(10, 28, 68, 24), Qt.AlignmentFlag.AlignCenter, str(total))
        label_font = QFont(self.font())
        label_font.setPixelSize(9)
        painter.setFont(label_font)
        painter.setPen(QColor(tc("finance_text_muted", default=tc("text_muted"))))
        painter.drawText(QRectF(10, 50, 68, 14), Qt.AlignmentFlag.AlignCenter, "ADET")
