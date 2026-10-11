import math

from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtGui import QDoubleValidator

from src.ui.widgets.modern_inputs import InlineNumberStepper


class ReferenceCurrencyStepper(InlineNumberStepper):
    """Display the selected currency while keeping the existing TRY API."""

    def __init__(self, value=0, decimals=2, parent=None):
        self._display_rate = 1.0
        self._base_value = 0.0
        self._base_text = ''
        super().__init__(value=value, decimals=decimals, parent=parent)

    def value(self):
        text = self.spn_counted.text()
        if text == self._base_text:
            return self._base_value
        try:
            number = float(text.strip().replace(',', '.')) * self._display_rate
            if not math.isfinite(number):
                return self._minimum
            return max(self._minimum, min(self._maximum, number))
        except ValueError:
            return self._minimum

    def setValue(self, value):
        previous = self.value()
        number = float(value)
        if not math.isfinite(number):
            number = self._minimum
        self._base_value = max(self._minimum, min(self._maximum, number))
        self._base_text = f'{self._base_value / self._display_rate:.{self._decimals}f}'
        same_text = self.spn_counted.text() == self._base_text
        self.spn_counted.setText(self._base_text)
        if same_text and previous != self._base_value:
            self.valueChanged.emit(self._base_value)

    def set_display_rate(self, rate):
        number = float(rate)
        if not math.isfinite(number) or number <= 0:
            number = 1.0
        if number == self._display_rate:
            return
        base_value = self.value()
        with QSignalBlocker(self), QSignalBlocker(self.spn_counted):
            self._display_rate = number
            self._apply_validator()
            self.setValue(base_value)

    def _apply_validator(self):
        self.spn_counted.setValidator(QDoubleValidator(
            self._minimum / self._display_rate,
            self._maximum / self._display_rate,
            self._decimals,
            self.spn_counted,
        ))

    def _adjust(self, amount):
        self.setValue(self.value() + amount * self._display_rate)
