"""Kanban cards retain complete record text and token-backed mono metadata."""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QLabel

from src.ui.widgets.kanban_board import KanbanCard
from src.utils.design_system import DesignTokens
from src.utils.reference_typography import apply_reference_font
from src.utils.theme_manager import ThemeManager


def test_card_record_text_is_complete_plain_text_and_signals_keep_tracking_identity():
    app = QApplication.instance() or QApplication([])
    previous_font = app.font()
    previous_theme = ThemeManager._current_theme
    previous_stylesheet = app.styleSheet()
    apply_reference_font(app)
    data = {
        'tracking_no': 'SRV-2026-081', 'customer_name': 'Customer <Actual> With A Long Display Name',
        'device_brand': 'Actual Brand', 'device_model': 'Long Model Identifier That Must Not Be Shortened',
        'fault_description': 'Power supply diagnosis and circuit board repair with an intermittent startup failure.',
        'status': 'Tamirde', 'urgency': 'Normal', 'entry_date': '2026-09-21', 'price': 1700,
    }
    card = KanbanCard(data)
    card.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
    card.setFixedWidth(230)
    ThemeManager.apply_theme(app, 'Koyu Mavi', window=card, animate=False)
    card.show()
    app.processEvents()
    try:
        expected = {
            'KanbanTrackingBadge': '#SRV-2026-081',
            'KanbanTitle': data['device_brand'] + ' ' + data['device_model'],
            'KanbanCustomer': data['fault_description'],
            'KanbanTrack': data['customer_name'],
        }
        for name, text in expected.items():
            label = card.findChild(QLabel, name)
            assert label.text() == text
            assert label.textFormat() == Qt.TextFormat.PlainText
            assert label.wordWrap()
        for name in ('KanbanTrackingBadge', 'KanbanPrice', 'KanbanDate'):
            assert card.findChild(QLabel, name).font().family() == DesignTokens.MONO_FONT_NAME
        calls = []
        card.clicked.connect(lambda tracking: calls.append(('open', tracking)))
        card.action_triggered.connect(lambda action, tracking: calls.append((action, tracking)))
        card.clicked.emit(card.tracking_no)
        card.action_triggered.emit('info', card.tracking_no)
        assert calls == [('open', data['tracking_no']), ('info', data['tracking_no'])]
        assert card.device_data == data
        assert not card.grab().isNull()
    finally:
        card.close()
        card.deleteLater()
        app.processEvents()
        ThemeManager._activate_runtime_cache(previous_theme)
        app.setStyleSheet(previous_stylesheet)
        app.setFont(previous_font)
