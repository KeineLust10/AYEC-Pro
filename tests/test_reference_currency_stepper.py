import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from src.ui.widgets.reference_currency_stepper import ReferenceCurrencyStepper


def test_currency_display_preserves_exact_base_values_and_emits_try():
    app = QApplication.instance() or QApplication([])
    control = ReferenceCurrencyStepper(value=2450.01)
    changes = []
    control.valueChanged.connect(changes.append)
    try:
        control.set_display_rate(44)
        assert control.text() == '55.68'
        assert control.value() == 2450.01
        assert changes == []
        control.setValue(2450.02)
        assert control.text() == '55.68'
        assert changes == [2450.02]
        control.setValue(2450.01)
        for rate in (55.731, 2, 44, 1):
            control.set_display_rate(rate)
            assert control.value() == 2450.01
        assert control.text() == '2450.01'
        control.set_display_rate(44)
        control.spn_counted.setText('85.00')
        assert control.value() == 3740
        assert changes[-1] == 3740
        QTest.mouseClick(control.increase, Qt.MouseButton.LeftButton)
        assert control.text() == '86.00'
        assert control.value() == 3784
        QTest.mouseClick(control.decrease, Qt.MouseButton.LeftButton)
        assert control.text() == '85.00'
        assert control.value() == 3740
        control.setValue(987.65)
        assert control.value() == 987.65
        control.set_display_rate(1)
        assert control.text() == '987.65'
    finally:
        control.deleteLater()
        app.processEvents()


@pytest.mark.parametrize('rate', [0, -1, float('nan'), float('inf')])
def test_invalid_display_rates_do_not_corrupt_base_amounts(rate):
    app = QApplication.instance() or QApplication([])
    control = ReferenceCurrencyStepper(value=125)
    try:
        control.set_display_rate(2)
        control.set_display_rate(rate)
        assert control.text() == '125.00'
        assert control.value() == 125
    finally:
        control.deleteLater()
        app.processEvents()
