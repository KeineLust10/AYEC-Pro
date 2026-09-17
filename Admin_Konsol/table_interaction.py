"""Shared professional table interaction for the admin console."""

from PyQt6.QtCore import QEvent, QItemSelectionModel, QObject, Qt
from PyQt6.QtGui import QColor, QPainter, QPalette
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTableWidget,
)


class _FullRowDelegate(QStyledItemDelegate):
    """Paint hover and selection as one continuous row surface."""

    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self._table = table

    def paint(self, painter: QPainter, option, index):
        opt = QStyleOptionViewItem(option)
        selected = self._table.selectionModel().isRowSelected(
            index.row(), index.parent()
        )
        hovered = self._table.property("ayec_hover_row") == index.row()

        if selected:
            background = QColor("#1f4f8f")
        elif hovered:
            background = QColor("#172b48")
        elif index.row() % 2:
            background = QColor("#102038")
        else:
            background = QColor("#0f1c31")

        painter.save()
        painter.fillRect(opt.rect, background)

        opt.state &= ~QStyle.StateFlag.State_Selected
        opt.state &= ~QStyle.StateFlag.State_MouseOver
        opt.state &= ~QStyle.StateFlag.State_HasFocus
        opt.features &= ~QStyleOptionViewItem.ViewItemFeature.Alternate
        opt.palette.setColor(
            QPalette.ColorRole.Text,
            QColor("#ffffff") if selected else QColor("#e8f0fb"),
        )
        opt.palette.setColor(
            QPalette.ColorRole.HighlightedText,
            QColor("#ffffff"),
        )
        super().paint(painter, opt, index)

        painter.setPen(QColor("#1d3351" if not selected else "#3974bd"))
        painter.drawLine(opt.rect.bottomLeft(), opt.rect.bottomRight())

        if selected and index.column() == self._first_visible_column():
            painter.fillRect(opt.rect.left(), opt.rect.top(), 4, opt.rect.height(), QColor("#68a7ff"))
        painter.restore()

    def _first_visible_column(self) -> int:
        for column in range(self._table.columnCount()):
            if not self._table.isColumnHidden(column):
                return column
        return 0


class _TablePointerController(QObject):
    """Keep hover subtle and make every pointer click a full-row selection."""

    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self._table = table

    def eventFilter(self, watched, event):
        event_type = event.type()
        if event_type == QEvent.Type.MouseMove:
            index = self._table.indexAt(event.position().toPoint())
            row = index.row() if index.isValid() else -1
            if row != self._table.property("ayec_hover_row"):
                self._table.setProperty("ayec_hover_row", row)
                self._table.viewport().update()
        elif event_type == QEvent.Type.Leave:
            self._table.setProperty("ayec_hover_row", -1)
            self._table.viewport().update()
        elif event_type == QEvent.Type.MouseButtonPress:
            index = self._table.indexAt(event.position().toPoint())
            if index.isValid():
                flags = (
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                    | QItemSelectionModel.SelectionFlag.Rows
                )
                self._table.selectionModel().setCurrentIndex(index, flags)
                self._table.selectRow(index.row())
        return super().eventFilter(watched, event)


def apply_professional_table(table: QTableWidget) -> None:
    """Apply the shared read-only table standard once."""

    if table.property("ayec_professional_table"):
        return
    table.setProperty("ayec_professional_table", True)
    table.setProperty("ayec_hover_row", -1)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.setMouseTracking(True)
    table.viewport().setMouseTracking(True)
    table.setShowGrid(False)
    table.setAlternatingRowColors(False)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(48)
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setMinimumHeight(44)

    delegate = _FullRowDelegate(table)
    controller = _TablePointerController(table)
    table.setItemDelegate(delegate)
    table.viewport().installEventFilter(controller)
    table._ayec_row_delegate = delegate
    table._ayec_pointer_controller = controller
