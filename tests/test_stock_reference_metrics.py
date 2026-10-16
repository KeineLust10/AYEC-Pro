import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.database import Database
from src.ui.pages.stock_page import StockPage
from src.ui.pages._stock_widgets import StockAmountLabel
from src.utils.currency_helper import CurrencyHelper
from src.utils.page_ids import PageIds
from tools.quality.desktop_visual_acceptance import seed_visual_fixture


def test_stock_metrics_preserve_real_values_and_native_filter_slots(monkeypatch, tmp_path):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv('AYEC_VISUAL_ACCEPTANCE', '1')
    monkeypatch.setattr(StockPage, 'load_stock_list', lambda self: None)
    reloads = []
    monkeypatch.setattr(StockPage, 'reload_data', lambda self: reloads.append(self.metric_filter))
    db = Database(str(tmp_path / 'stock_metrics.db'))
    seed_visual_fixture(db, currency_rates=True)
    page = StockPage(db)
    page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    try:
        stats = db.get_stock_stats()
        original = [tuple(row) for row in db.conn.execute('SELECT * FROM parts ORDER BY id')]
        page._update_stats_ui(stats)
        page.resize(1008, 988)
        page.show()
        app.processEvents()
        cards = [page.stats_layout.itemAt(i).widget() for i in range(4)]
        expected = [
            str(stats['total_types']),
            CurrencyHelper.format_amount(stats['total_value'], db=db, currency_code=stats['display_currency']),
            str(stats['critical_count']),
            CurrencyHelper.format_amount(stats['potential_profit_try'], db=db, currency_code='TRY'),
        ]
        assert [card.val_lbl.text() for card in cards] == expected
        for card, metric in zip(cards, ['all', 'value', 'critical', 'profit']):
            assert card.height() == 82
            assert card.graphicsEffect() is None
            assert 'border-radius: 14px' in card.styleSheet()
            assert 'transparent' in card.val_lbl.styleSheet()
            assert QFontMetrics(card.val_lbl.amount_font(card.val_lbl.text())).horizontalAdvance(card.val_lbl.text()) <= card.val_lbl.width() - 4
            page.current_page = 4
            QTest.mouseClick(card, Qt.MouseButton.LeftButton)
            assert page.metric_filter == metric
            assert page.current_page == 0
            assert page.critical_filter == (metric == 'critical')
            if metric != 'all':
                QTest.mouseClick(card, Qt.MouseButton.LeftButton)
                assert page.metric_filter == 'all'
        assert reloads == ['all', 'value', 'all', 'critical', 'all', 'profit', 'all']
        critical_stats = dict(stats, critical_count=3)
        page._update_stats_ui(critical_stats)
        critical = page.stats_layout.itemAt(2).widget()
        assert critical.val_lbl.text() == '3'
        assert critical.icon_lbl.kind == 'warning'
        assert critical.icon_lbl.token == 'finance_expense'
        foreign = dict(stats, display_currency='USD', total_value=stats['total_value_try'] / 44)
        page._update_stats_ui(foreign)
        amount = page.stats_layout.itemAt(1).widget().val_lbl
        assert amount.text() == (
            CurrencyHelper.format_amount(foreign['total_value'], db=db, currency_code='USD')
            + ' | ' + CurrencyHelper.format_amount(stats['total_value_try'], db=db, currency_code='TRY')
        )
        assert amount.toolTip() == amount.text()
        parts, total = db.get_parts_paginated(limit=15, offset=0)
        page._fill_table(parts)
        assert total == stats['total_types']
        assert page.table_stock.columnCount() == 12
        assert page.table_stock.columnWidth(2) >= 210
        assert page.table_stock.verticalHeader().defaultSectionSize() == 56
        assert page.table_stock.horizontalHeaderItem(2).text() == "Par\u00e7a / \u00dcr\u00fcn Tan\u0131m\u0131"
        assert page.table_stock.cellWidget(0, 11) is not None
        action_cell = page.table_stock.cellWidget(0, 11)
        assert action_cell.findChild(type(page.btn_critical)) is not None
        assert any(button.toolTip() == "Stok Hareketi" for button in action_cell.findChildren(type(page.btn_critical)))
        for row in range(page.table_stock.rowCount()):
            name = page.table_stock.item(row, 2)
            assert name.toolTip() == name.text()
            assert name.textAlignment() & Qt.AlignmentFlag.AlignLeft
            purchase = page.table_stock.item(row, page._purchase_price_column())
            assert not purchase.toolTip()
        page._load_categories_fresh()
        all_button = next(
            page.cat_layout.itemAt(i).widget()
            for i in range(page.cat_layout.count())
            if page.cat_layout.itemAt(i).widget() is not None
            and page.cat_layout.itemAt(i).widget().property('stock_category_key') == 'T\u00fcm\u00fc'
        )
        active_part_count = db.conn.execute(
            'SELECT COUNT(*) FROM parts WHERE COALESCE(is_deleted, 0) = 0'
        ).fetchone()[0]
        assert all_button.text() == f'T\u00fcm\u00fc ({active_part_count})'
        assert all_button.isChecked()
        page._select_stock_category('Bilgisayar Bile\u015fenleri')
        assert page.selected_category == 'Bilgisayar Bile\u015fenleri'
        assert not all_button.isChecked()
        assert [tuple(row) for row in db.conn.execute('SELECT * FROM parts ORDER BY id')] == original
    finally:
        page.close()
        page.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()
        db.close()


def test_stock_summary_cards_navigate_to_their_destinations(monkeypatch, tmp_path):
    from types import SimpleNamespace

    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv('AYEC_VISUAL_ACCEPTANCE', '1')
    monkeypatch.setattr(StockPage, 'load_stock_list', lambda self: None)
    destinations = []
    main_window = SimpleNamespace(on_menu_click=destinations.append)
    db = Database(str(tmp_path / 'stock_summary_navigation.db'))
    page = StockPage(db, main_window=main_window)
    try:
        summary = page.layout().itemAt(page.layout().count() - 1).layout()
        for index in range(summary.count()):
            summary.itemAt(index).widget().click()
        assert destinations == [PageIds.STOCK_LOCATIONS, PageIds.CONSIGNMENT, PageIds.INCOME_EXPENSE]
    finally:
        page.close()
        db.close()


@pytest.mark.parametrize('width', [180, 212, 280])
def test_stock_amount_fits_both_lines_without_changing_data(width):
    app = QApplication.instance() or QApplication([])
    text = '347,533.36 $ | 15,291,468.00 \u20ba'
    label = StockAmountLabel(text, 'finance_secondary')
    label.resize(width, 44)
    for index, line in enumerate(text.split(' | ')):
        font = label.amount_font(line, 24 if index == 0 else 11)
        assert QFontMetrics(font).horizontalAdvance(line) <= width - 4
    assert label.text() == text
    assert label.toolTip() == text
    label.setText('0.00 \u20ba')
    assert label.toolTip() == label.text() == '0.00 \u20ba'
    label.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
