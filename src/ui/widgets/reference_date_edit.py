from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QDateEdit

from src.utils.design_system import DesignTokens
from src.utils.theme_colors import tc, theme_qss


class ReferenceDateEdit(QDateEdit):
    """Native date input with a painted calendar and the original Qt popup."""

    def __init__(self, date, parent=None):
        super().__init__(date, parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat('dd.MM.yyyy')
        self.setFixedHeight(38)
        self.setProperty("referenceFont", "mono")
        self.setStyleSheet(theme_qss(
            'QDateEdit { background: @finance_surface_lowest; color: @finance_text; '
            'border: 1px solid @finance_outline; border-radius: 4px; '
            f'padding: 0 10px; min-height: 36px; max-height: 36px; font-size: 12px; font-family: "{DesignTokens.MONO_FONT_NAME}"; }} '
            'QDateEdit::drop-down { width: 28px; background: transparent; border: none; } '
            'QDateEdit::down-arrow { image: none; width: 0; height: 0; border: none; }'
        ))
        self.setFont(QFont(DesignTokens.MONO_FONT_NAME))

    def showEvent(self, event):
        super().showEvent(event)
        self.setFont(QFont(DesignTokens.MONO_FONT_NAME))

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(tc('finance_text_muted')), 1.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        left = 8 if self.layoutDirection() == Qt.LayoutDirection.RightToLeft else self.width() - 22
        top = (self.height() - 14) // 2
        painter.drawRoundedRect(left, top + 2, 14, 12, 2, 2)
        painter.drawLine(left, top + 6, left + 14, top + 6)
        painter.drawLine(left + 4, top, left + 4, top + 4)
        painter.drawLine(left + 10, top, left + 10, top + 4)
        for x in (4, 7, 10):
            painter.drawPoint(left + x, top + 9)
        painter.end()
