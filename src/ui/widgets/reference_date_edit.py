from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QDateEdit

from src.utils.design_system import DesignTokens
from src.utils.theme_colors import tc, theme_qss


class ReferenceDateEdit(QDateEdit):
    """Native date input with a painted calendar and the original Qt popup."""

    def __init__(self, date, parent=None, *, compact=False):
        super().__init__(date, parent)
        self.setCalendarPopup(True)
        self.setDisplayFormat('dd.MM.yyyy')
        self.setFixedHeight(32 if compact else 38)
        self.setProperty("referenceFont", "mono")
        date_padding = '0 5px' if compact else '0 10px'
        date_height = 30 if compact else 36
        date_font = 9 if compact else 12
        drop_width = 20 if compact else 28
        self.setStyleSheet(theme_qss(
            'QDateEdit { background: @finance_surface_lowest; color: @finance_text; '
            'border: 1px solid @finance_outline; border-radius: 4px; '
            f'padding: {date_padding}; min-height: {date_height}px; max-height: {date_height}px; font-size: {date_font}px; font-family: "{DesignTokens.MONO_FONT_NAME}"; }} '
            f'QDateEdit::drop-down {{ width: {drop_width}px; background: transparent; border: none; }} '
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
