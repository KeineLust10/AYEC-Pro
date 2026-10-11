"""Token-driven status pills that preserve table item text and selection."""

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import QApplication, QStyle, QStyledItemDelegate, QStyleOptionViewItem

from src.utils.theme_colors import qc


class ReferenceStatusDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        text = item.text
        item.text = ''
        style = item.widget.style() if item.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, item, painter, item.widget)
        width = min(option.rect.width() - 8, option.fontMetrics.horizontalAdvance(text) + 32)
        pill = QRectF(option.rect.center().x() - width / 2, option.rect.center().y() - 12, width, 24)
        foreground = qc('finance_action_income' if text == 'Aktif' else 'text_muted')
        outline = QColor(foreground)
        outline.setAlpha(90)
        painter.save()
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setBrush(qc('finance_surface_lowest'))
        painter.setPen(QPen(outline, 1))
        painter.drawRoundedRect(pill, 12, 12)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(foreground)
        painter.drawEllipse(QRectF(pill.x() + 8, pill.center().y() - 3, 6, 6))
        painter.setPen(foreground)
        painter.setFont(option.font)
        text_rect = pill.adjusted(20, 0, -6, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.restore()
