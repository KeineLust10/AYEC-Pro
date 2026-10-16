from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QPen, QPainter, QPalette, QColor, QFont, QFontMetrics
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtWidgets import QLabel, QPushButton, QStylePainter, QStyleOptionButton, QStyle, QWidget, QStyledItemDelegate, QStyleOptionViewItem

from src.utils.theme_colors import qc
from src.utils.design_system import DesignTokens


class ReferenceTotalLabel(QLabel):
    """Render the unchanged amount text with separate primary/reference sizes."""

    def __init__(self, text='', parent=None, *, primary_size=40, secondary_size=20, primary_token='finance_secondary'):
        super().__init__(text, parent)
        self.primary_size = primary_size
        self.secondary_size = secondary_size
        self.primary_token = primary_token
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setMinimumHeight(primary_size + secondary_size + 16)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setToolTip(text)

    def setText(self, text):
        super().setText(str(text))
        self.setToolTip(str(text))

    def amount_font(self, text, maximum):
        font = QFont(self.font())
        font.setFamily(DesignTokens.MONO_FONT_NAME)
        font.setBold(True)
        size = maximum
        width = max(1, self.contentsRect().width() - 4)
        while size > 10:
            font.setPixelSize(size)
            if QFontMetrics(font).horizontalAdvance(text) <= width:
                break
            size -= 1
        font.setPixelSize(size)
        return font

    def paintEvent(self, event):
        lines = self.text().splitlines() or ['']
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        primary = self.amount_font(lines[0], self.primary_size)
        first_height = QFontMetrics(primary).height() + 4
        secondary = '\n'.join(lines[1:])
        secondary_font = self.amount_font(secondary, self.secondary_size)
        second_height = QFontMetrics(secondary_font).height() + 4 if secondary else 0
        top = (self.height() - first_height - second_height) // 2
        painter.setPen(qc(self.primary_token))
        painter.setFont(primary)
        painter.drawText(QRect(0, top, self.width(), first_height), Qt.AlignmentFlag.AlignCenter, lines[0])
        if secondary:
            painter.setPen(qc('finance_text'))
            painter.setFont(secondary_font)
            painter.drawText(QRect(0, top + first_height, self.width(), second_height), Qt.AlignmentFlag.AlignCenter, secondary)
        painter.end()


class ReferenceMetricValueLabel(ReferenceTotalLabel):
    """Compact KPI value using the same adaptive mono amount typography."""

    def __init__(self, text='-', parent=None, *, primary_token='finance_text', primary_size=21):
        super().__init__(text, parent, primary_size=primary_size, secondary_size=0,
                         primary_token=primary_token)
        self.setMinimumHeight(28)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def minimumSizeHint(self):
        return QSize(0, 28)

    def sizeHint(self):
        return QSize(80, 28)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        painter.setFont(self.amount_font(self.text(), self.primary_size))
        painter.setPen(qc(self.primary_token))
        painter.drawText(self.contentsRect(), self.alignment(), self.text())
        painter.end()


def draw_financial_glyph(painter, kind):
    painter.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "cart":
        painter.drawLine(2, 3, 5, 3)
        painter.drawLine(5, 3, 7, 13)
        painter.drawLine(7, 13, 15, 13)
        painter.drawLine(15, 13, 17, 6)
        painter.drawLine(5, 5, 17, 5)
        painter.drawEllipse(7, 15, 2, 2)
        painter.drawEllipse(14, 15, 2, 2)
    elif kind in ("income", "expense", "collection"):
        if kind == "collection":
            painter.drawLine(3, 10, 7, 14)
            painter.drawLine(7, 14, 15, 5)
        else:
            painter.drawLine(3, 9, 15, 9)
            if kind == "income":
                painter.drawLine(9, 3, 9, 15)
    elif kind == "transfer":
        painter.drawLine(2, 5, 15, 5)
        painter.drawLine(12, 2, 15, 5)
        painter.drawLine(12, 8, 15, 5)
        painter.drawLine(3, 13, 16, 13)
        painter.drawLine(3, 13, 6, 10)
        painter.drawLine(3, 13, 6, 16)
    elif kind in ("trend_up", "trend_down"):
        points = ((2, 14), (7, 9), (10, 11), (16, 4)) if kind == "trend_up" else ((2, 4), (7, 9), (10, 7), (16, 14))
        for first, second in zip(points, points[1:]):
            painter.drawLine(*first, *second)
        x, y = points[-1]
        painter.drawLine(x - 5, y, x, y)
        painter.drawLine(x, y, x, y + (5 if kind == "trend_up" else -5))
    elif kind == "bank":
        painter.drawLine(2, 5, 9, 2)
        painter.drawLine(9, 2, 16, 5)
        painter.drawLine(2, 6, 16, 6)
        for x in (4, 9, 14):
            painter.drawLine(x, 8, x, 14)
        painter.drawLine(2, 16, 16, 16)
    elif kind == "print":
        painter.drawRect(3, 6, 12, 8)
        painter.drawRect(5, 2, 8, 4)
        painter.drawRect(5, 11, 8, 5)
        painter.drawPoint(12, 9)
    elif kind == "repair":
        painter.drawArc(QRect(9, 1, 8, 8), 45 * 16, 270 * 16)
        painter.drawLine(2, 15, 10, 7)
        painter.drawLine(4, 17, 12, 9)
        painter.drawLine(2, 15, 4, 17)
    elif kind == "hourglass":
        painter.drawLine(4, 2, 14, 2)
        painter.drawLine(4, 16, 14, 16)
        painter.drawLine(5, 3, 5, 5)
        painter.drawLine(5, 5, 13, 13)
        painter.drawLine(13, 13, 13, 15)
        painter.drawLine(13, 3, 13, 5)
        painter.drawLine(13, 5, 5, 13)
        painter.drawLine(5, 13, 5, 15)
    elif kind == "truck":
        painter.drawRect(1, 4, 10, 8)
        painter.drawRect(11, 7, 5, 5)
        painter.drawEllipse(3, 11, 4, 4)
        painter.drawEllipse(11, 11, 4, 4)
    elif kind == "clock":
        painter.drawEllipse(2, 2, 14, 14)
        painter.drawLine(9, 4, 9, 9)
        painter.drawLine(9, 9, 12, 11)
    elif kind == "warning":
        painter.drawLine(9, 2, 1, 16)
        painter.drawLine(1, 16, 17, 16)
        painter.drawLine(17, 16, 9, 2)
        painter.drawLine(9, 6, 9, 11)
        painter.drawPoint(9, 14)
    elif kind == "inventory":
        painter.drawRect(3, 5, 12, 11)
        painter.drawRect(2, 2, 14, 3)
        painter.drawLine(7, 9, 11, 9)
    elif kind == "wallet":
        painter.drawRoundedRect(2, 4, 14, 11, 2, 2)
        painter.drawRect(10, 7, 6, 5)
        painter.drawPoint(12, 9)
    elif kind == "delete":
        painter.drawLine(2, 4, 16, 4)
        painter.drawRect(6, 1, 6, 3)
        painter.drawLine(4, 5, 5, 16)
        painter.drawLine(5, 16, 13, 16)
        painter.drawLine(13, 16, 14, 5)
        painter.drawLine(7, 7, 7, 13)
        painter.drawLine(11, 7, 11, 13)
    elif kind == "bookmark":
        painter.drawLine(4, 2, 14, 2)
        painter.drawLine(4, 2, 4, 16)
        painter.drawLine(14, 2, 14, 16)
        painter.drawLine(4, 16, 9, 12)
        painter.drawLine(9, 12, 14, 16)
    else:
        painter.drawRect(4, 2, 10, 14)
        painter.drawLine(6, 6, 12, 6)
        if kind in ("excel", "tax"):
            for y in (9, 12):
                painter.drawLine(6, y, 12, y)
            painter.drawLine(9, 8, 9, 14)
        elif kind == "pending":
            painter.drawEllipse(10, 10, 6, 6)
            painter.drawLine(13, 11, 13, 13)
            painter.drawLine(13, 13, 15, 13)
        else:
            painter.drawLine(6, 10, 12, 10)
            painter.drawLine(6, 13, 10, 13)


class FinancialMetricGlyph(QWidget):
    def __init__(self, kind, token, parent=None, glyph_size=18):
        super().__init__(parent)
        self.kind, self.token = kind, token
        self.setFixedSize(glyph_size, glyph_size)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(qc(self.token), 1.4))
        painter.scale(self.width() / 18, self.height() / 18)
        draw_financial_glyph(painter, self.kind)


class FinancialReferenceActionButton(QPushButton):
    """One real button with the reference's vertically stacked icon and label."""

    def __init__(self, text, glyph, parent=None, stacked=True, *, centered_inline=False, key_hint=''):
        super().__init__(text, parent)
        self.glyph = glyph
        self.stacked = stacked
        self.centered_inline = centered_inline
        self.key_hint = key_hint

    def key_hint_width(self):
        if not self.key_hint:
            return 0
        font = QFont(self.font())
        font.setPixelSize(10)
        return QFontMetrics(font).horizontalAdvance(self.key_hint) + 12

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.text = ""
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        group = QPalette.ColorGroup.Active if self.isEnabled() else QPalette.ColorGroup.Disabled
        color = option.palette.color(group, QPalette.ColorRole.ButtonText)
        pen = QPen(color, 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.save()
        hint_width = self.key_hint_width()
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        group_width = text_width + 26 + (hint_width + 8 if hint_width else 0)
        inline_left = max(5, (self.width() - group_width) // 2) if self.centered_inline else 5
        painter.translate((self.width() - 18) / 2 if self.stacked else inline_left, 5 if self.stacked else (self.height() - 18) / 2)
        draw_financial_glyph(painter, self.glyph)
        painter.restore()
        painter.setPen(color)
        if self.stacked:
            painter.drawText(QRect(3, 27, self.width() - 6, self.height() - 29), Qt.AlignmentFlag.AlignCenter, self.text())
        else:
            width = text_width if hint_width else self.width() - inline_left - 25
            painter.drawText(QRect(inline_left + 21, 0, width, self.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
            if hint_width:
                rectangle = QRect(inline_left + 26 + text_width + 4, (self.height() - 20) // 2, hint_width, 20)
                painter.save()
                painter.setBrush(qc('finance_surface_high'))
                painter.setPen(QPen(qc('finance_outline'), 1))
                painter.drawRoundedRect(rectangle, 4, 4)
                font = QFont(self.font())
                font.setPixelSize(10)
                painter.setFont(font)
                painter.setPen(qc('finance_text'))
                painter.drawText(rectangle, Qt.AlignmentFlag.AlignCenter, self.key_hint)
                painter.restore()


class FinancialReferenceIconButton(QPushButton):
    def __init__(self, label, glyph, parent=None):
        super().__init__(parent)
        self.glyph = glyph
        self.setAccessibleName(label)
        self.setToolTip(label)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(option.palette.color(QPalette.ColorRole.ButtonText), 1.4))
        painter.translate(3, 3)
        draw_financial_glyph(painter, self.glyph)


class FinancialReferenceLedgerDelegate(QStyledItemDelegate):
    """Paint badges from the original item roles without replacing ledger data."""

    def sizeHint(self, option, index):
        base = super().sizeHint(option, index)
        payload = index.data(Qt.ItemDataRole.UserRole)
        if not isinstance(payload, dict) or payload.get('kind') == 'date_group':
            return base
        font = QFont(option.font)
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or '')
        if index.column() in (1, 6):
            font.setPixelSize(10)
            font.setBold(True)
            if index.column() == 1:
                text = text.upper()
            return QSize(max(base.width(), QFontMetrics(font).horizontalAdvance(text) + 20),
                         max(base.height(), 26))
        if index.column() in (0, 3, 4, 5, 7):
            font.setFamily(DesignTokens.MONO_FONT_NAME)
            font.setPixelSize(11)
            font.setBold(index.column() == 5)
            return QSize(max(base.width(), QFontMetrics(font).horizontalAdvance(text) + 12),
                         base.height())
        return base

    def paint(self, painter, option, index):
        payload = index.data(Qt.ItemDataRole.UserRole)
        if isinstance(payload, dict) and payload.get("kind") == "date_group" and option.rect.width() >= 600:
            self._paint_date_group(painter, option, index, payload)
            return
        if not isinstance(payload, dict) or payload.get("kind") == "date_group":
            super().paint(painter, option, index)
            return
        style_option = QStyleOptionViewItem(option)
        self.initStyleOption(style_option, index)
        text = style_option.text
        style_option.text = ""
        widget = style_option.widget
        painter.save()
        widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, style_option, painter, widget)
        foreground = index.data(Qt.ItemDataRole.ForegroundRole)
        color = foreground.color() if hasattr(foreground, "color") else qc("finance_text")
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        if selected:
            color = qc("accent_foreground")
        background = QColor(color)
        background.setAlpha(32)
        font = QFont(option.font)
        font.setPixelSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if index.column() not in (1, 6):
            font.setBold(index.column() == 5)
            font.setPixelSize(11)
            if index.column() in (0, 3, 4, 5, 7):
                font.setFamily(DesignTokens.MONO_FONT_NAME)
            painter.setFont(font)
            painter.setPen(color)
            rect = option.rect.adjusted(5, 4, -5, -4)
            alignment = int(style_option.displayAlignment) | int(Qt.AlignmentFlag.AlignVCenter)
            if index.column() == 2:
                lines = text.splitlines()
                title = lines[0] if lines else text
                font.setBold(True)
                painter.setFont(font)
                title = painter.fontMetrics().elidedText(title, Qt.TextElideMode.ElideRight, rect.width())
                if len(lines) > 1:
                    title_rect = QRect(rect.left(), rect.top(), rect.width(), 16)
                    painter.drawText(title_rect, Qt.AlignmentFlag.AlignVCenter, title)
                    font.setBold(False)
                    font.setPixelSize(10)
                    painter.setFont(font)
                    painter.setPen(color if selected else qc("finance_text_muted"))
                    detail_rect = QRect(rect.left(), rect.top() + 17, rect.width(), max(0, rect.height() - 17))
                    painter.drawText(detail_rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop) | int(Qt.TextFlag.TextWordWrap), "\n".join(lines[1:]))
                else:
                    painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter, title)
                painter.restore()
                return
            painter.drawText(rect, alignment, text)
            painter.restore()
            return
        label = text.upper() if index.column() == 1 else text
        maximum_width = max(1, option.rect.width() - 10)
        label = painter.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight, maximum_width - 10)
        width = min(maximum_width, painter.fontMetrics().horizontalAdvance(label) + 10)
        rect = QRect(option.rect.left() + 5, option.rect.center().y() - 9, width, 18)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(background)
        painter.drawRoundedRect(rect, 3, 3)
        painter.setPen(color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        painter.restore()

    def _paint_date_group(self, painter, option, index, payload):
        style_option = QStyleOptionViewItem(option)
        self.initStyleOption(style_option, index)
        style_option.text = ""
        painter.save()
        try:
            widget = style_option.widget
            widget.style().drawControl(QStyle.ControlElement.CE_ItemViewItem, style_option, painter, widget)
            painter.setClipRect(option.rect, Qt.ClipOperation.IntersectClip)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            font = QFont(option.font)
            font.setPixelSize(10)
            font.setBold(True)
            painter.setFont(font)
            selected = bool(option.state & QStyle.StateFlag.State_Selected)
            foreground = qc("accent_foreground" if selected else "finance_text")
            painter.setPen(QPen(foreground, 1.4))
            x, y = option.rect.left() + 7, option.rect.center().y()
            if payload.get("expanded"):
                painter.drawLine(x, y - 2, x + 3, y + 1)
                painter.drawLine(x + 3, y + 1, x + 6, y - 2)
            else:
                painter.drawLine(x + 1, y - 3, x + 4, y)
                painter.drawLine(x + 4, y, x + 1, y + 3)
            date = str(payload.get("display_date") or "-") + " G\u00fcn\u00fc"
            date_width = painter.fontMetrics().horizontalAdvance(date)
            painter.drawText(QRect(x + 12, option.rect.top(), date_width + 4, option.rect.height()), Qt.AlignmentFlag.AlignVCenter, date)
            label = str(payload.get("count", 0)) + " \u0130\u015eLEM"
            badge_width = painter.fontMetrics().horizontalAdvance(label) + 10
            badge = QRect(x + 18 + date_width, y - 8, badge_width, 16)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(qc("finance_surface_high"))
            painter.drawRoundedRect(badge, 2, 2)
            painter.setPen(foreground)
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, label)
            right = option.rect.right() - 8
            parts = [("Ciro: " + str(payload.get("income_text", "--")), foreground),
                     ("Gider: " + str(payload.get("expense_text", "--")), foreground),
                     ("Net: " + str(payload.get("net_text", "--")), foreground if selected else qc("finance_tertiary" if payload.get("net_negative") else "finance_secondary"))]
            available = max(3, right - badge.right() - 16 - 24)
            if sum(painter.fontMetrics().horizontalAdvance(label) for label, _ in parts) > available:
                parts = [(painter.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight, available // 3), color) for label, color in parts]
            for label, color in reversed(parts):
                width = painter.fontMetrics().horizontalAdvance(label)
                painter.setPen(color)
                painter.drawText(QRect(right - width, option.rect.top(), width, option.rect.height()), Qt.AlignmentFlag.AlignVCenter, label)
                right -= width + 12
        finally:
            painter.restore()
