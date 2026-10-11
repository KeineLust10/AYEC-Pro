"""Ledger content-sized columns must include reference badge/mono geometry."""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import QApplication, QHeaderView, QTableWidget, QTableWidgetItem

from src.ui.widgets.financial_reference_controls import FinancialReferenceLedgerDelegate, ReferenceMetricValueLabel
from src.utils.design_system import DesignTokens
from src.utils.reference_typography import load_reference_fonts


def test_content_sizing_preserves_complete_status_badges_and_numeric_amounts():
    app = QApplication.instance() or QApplication([])
    load_reference_fonts()
    table = QTableWidget(1, 8)
    table.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    table.setItemDelegate(FinancialReferenceLedgerDelegate(table))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    values = ['23:28', 'T TAHSILAT', 'Actual description', '7,375.00 EUR', '55.7310',
              '411,016.12 TRY', 'Tamamland\u0131', '459,007.57 TRY']
    for column, value in enumerate(values):
        item = QTableWidgetItem(value)
        item.setData(Qt.ItemDataRole.UserRole, {'record_id': 12})
        table.setItem(0, column, item)
    table.resize(1300, 120)
    table.show()
    app.processEvents()
    try:
        for column in (1, 6):
            font = QFont(table.font())
            font.setPixelSize(10)
            font.setBold(True)
            assert table.columnWidth(column) >= QFontMetrics(font).horizontalAdvance(values[column]) + 20
        for column in (0, 3, 4, 5, 7):
            font = QFont(table.font())
            font.setFamily(DesignTokens.MONO_FONT_NAME)
            font.setPixelSize(11)
            font.setBold(column == 5)
            assert table.columnWidth(column) >= QFontMetrics(font).horizontalAdvance(values[column]) + 12
        assert [table.item(0, column).text() for column in range(8)] == values
        assert table.item(0, 6).data(Qt.ItemDataRole.UserRole) == {'record_id': 12}
        assert not table.grab().isNull()
    finally:
        table.deleteLater()
        app.processEvents()


def test_metric_amount_adapts_without_changing_the_display_currency_text():
    app = QApplication.instance() or QApplication([])
    load_reference_fonts()
    label = ReferenceMetricValueLabel('1,598,618.60 TRY')
    label.resize(140, 32)
    try:
        font = label.amount_font(label.text(), label.primary_size)
        assert font.family() == DesignTokens.MONO_FONT_NAME
        assert QFontMetrics(font).horizontalAdvance(label.text()) <= label.contentsRect().width() - 4
        assert label.text() == '1,598,618.60 TRY'
        assert label.toolTip() == label.text()
        assert not label.grab().isNull()
        label.setText('2,500,000.00 EUR')
        assert label.text() == '2,500,000.00 EUR'
        assert label.toolTip() == label.text()
    finally:
        label.deleteLater()
        app.processEvents()
