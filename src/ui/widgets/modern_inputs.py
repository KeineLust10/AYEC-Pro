# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import QLineEdit, QComboBox, QCompleter, QHBoxLayout, QLabel, QToolButton, QWidget
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QDoubleValidator
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss


class InlineNumberStepper(QWidget):
    """Clear editable number control with explicit decrease and increase actions."""

    valueChanged = pyqtSignal(float)

    def __init__(self, value=0, decimals=0, parent=None):
        super().__init__(parent)
        self._minimum = 0.0
        self._maximum = 999999999.0
        self._decimals = decimals
        self._suffix = ""

        self.decrease = self._create_button("-")
        self.spn_counted = QLineEdit()
        self.spn_counted.setFixedSize(62, 28)
        self.spn_counted.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spn_counted.setStyleSheet(theme_qss("""
            QLineEdit {
                background: @surface_alt;
                color: @text;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 800;
                padding: 0px 4px;
                selection-background-color: @accent;
                selection-color: @selection_text;
            }
            QLineEdit:focus { background: @surface; }
        """))
        self.suffix_label = QLabel()
        self.suffix_label.setStyleSheet(theme_qss("font-size: 12px; font-weight: 700; color: @text_muted;"))
        self.suffix_label.setVisible(False)
        self.increase = self._create_button("+")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.decrease)
        layout.addWidget(self.spn_counted)
        layout.addWidget(self.suffix_label)
        layout.addWidget(self.increase)

        self.setDecimals(decimals)
        self.setValue(value)
        self.decrease.clicked.connect(lambda: self._adjust(-1))
        self.increase.clicked.connect(lambda: self._adjust(1))
        self.spn_counted.textChanged.connect(self._emit_value_changed)

    @staticmethod
    def _create_button(label):
        button = QToolButton()
        button.setText(label)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(24, 24)
        button.setStyleSheet(theme_qss("""
            QToolButton {
                background: @surface_alt;
                color: @text_muted;
                border: none;
                border-radius: 12px;
                font-size: 16px;
                font-weight: 800;
            }
            QToolButton:hover {
                background: @accent;
                color: @selection_text;
            }
            QToolButton:pressed { background: @accent_hover; }
        """))
        return button

    def setRange(self, minimum, maximum):
        self._minimum = float(minimum)
        self._maximum = float(maximum)
        self._apply_validator()
        self.setValue(self.value())

    def setDecimals(self, decimals):
        self._decimals = max(0, int(decimals))
        self._apply_validator()
        self.setValue(self.value())

    def setSuffix(self, suffix):
        self._suffix = str(suffix or "").strip()
        self.suffix_label.setText(self._suffix)
        self.suffix_label.setVisible(bool(self._suffix))

    def value(self):
        try:
            return max(self._minimum, min(self._maximum, float(self.spn_counted.text().strip().replace(",", "."))))
        except ValueError:
            return self._minimum

    def text(self):
        return self.spn_counted.text()

    def setValue(self, value):
        number = max(self._minimum, min(self._maximum, float(value)))
        if self._decimals:
            text = f"{number:.{self._decimals}f}"
        else:
            text = f"{number:.0f}"
        self.spn_counted.setText(text)

    def _apply_validator(self):
        self.spn_counted.setValidator(
            QDoubleValidator(self._minimum, self._maximum, self._decimals, self.spn_counted)
        )

    def _adjust(self, amount):
        self.setValue(self.value() + amount)

    def _emit_value_changed(self, _text):
        self.valueChanged.emit(self.value())


class ValidatedLineEdit(QLineEdit):
    validation_changed = pyqtSignal(bool)

    def __init__(self, placeholder="", parent=None, validator_func=None):
        super().__init__(parent)
        self.validator_func = validator_func
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(40)
        self.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.textChanged.connect(self.validate)
        self.is_valid = True

    def validate(self):
        if not self.validator_func:
            return

        text = self.text()
        self.is_valid = self.validator_func(text)

        if not text:
            self.setStyleSheet(theme_qss(DesignTokens.get_input_qss(state="normal")))
            self.setToolTip("")
            self.is_valid = True
        elif self.is_valid:
            self.setStyleSheet(theme_qss(DesignTokens.get_input_qss(state="success")))
            self.setToolTip("Geçerli veri")
        else:
            self.setStyleSheet(theme_qss(DesignTokens.get_input_qss(state="error")))
            self.setToolTip("Hatalı veri")

        self.validation_changed.emit(self.is_valid)


class ModernComboBox(QComboBox):
    def __init__(self, parent=None, items=None, editable=False):
        super().__init__(parent)
        self._popup_pending = False
        self._last_popup_time = 0
        self.setEditable(editable)
        self.setMinimumHeight(42)
        if items:
            self.addItems(items)
        self.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))

        if editable:
            self.lineEdit().setStyleSheet(theme_qss("""
                QLineEdit {
                    background: transparent;
                    color: @text;
                    border: none;
                    padding: 1px 8px 1px 2px;
                    margin: 0px;
                    selection-background-color: @selection_bg;
                    selection-color: @selection_text;
                }
            """))
            self.lineEdit().setMinimumHeight(40)
            self.lineEdit().setAlignment(Qt.AlignmentFlag.AlignVCenter)
            self.set_completion_items(items or [])
            self.lineEdit().installEventFilter(self)

    def set_completion_items(self, items):
        if not self.isEditable():
            return
        completer = QCompleter(list(items or []), self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(completer)

    def showPopup(self):
        import time
        current_time = time.time()
        
        # Prevent recursive calls and debounce rapid calls (100ms window)
        if self._popup_pending or (current_time - self._last_popup_time < 0.1):
            return
            
        self._popup_pending = True
        self._last_popup_time = current_time
        
        try:
            super().showPopup()
        finally:
            # Reset flag after a short delay to allow popup to fully open
            QTimer.singleShot(50, lambda: setattr(self, '_popup_pending', False))

    def mousePressEvent(self, event):
        # Handle both editable and non-editable cases
        if not self.isEditable():
            # For non-editable combobox, let Qt handle it normally
            super().mousePressEvent(event)
            # Ensure popup opens on click
            if not self.view().isVisible():
                QTimer.singleShot(0, self.showPopup)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        import time
        if time.time() - self._last_popup_time < 0.3:
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def focusInEvent(self, event):
        super().focusInEvent(event)

    def eventFilter(self, obj, event):
        if self.isEditable() and obj is self.lineEdit():
            if event.type() == QEvent.Type.KeyPress and event.key() in (
                Qt.Key.Key_Tab,
                Qt.Key.Key_Backtab,
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            ):
                completer = self.completer()
                popup = completer.popup() if completer else None
                if popup is not None and popup.isVisible():
                    index = popup.currentIndex()
                    if not index.isValid() and completer.completionCount() > 0:
                        completer.setCurrentRow(0)
                    completion = str(completer.currentCompletion() or "").strip()
                    if completion:
                        match_index = self.findText(
                            completion, Qt.MatchFlag.MatchFixedString
                        )
                        if match_index >= 0:
                            self.setCurrentIndex(match_index)
                        else:
                            self.setEditText(completion)
                        popup.hide()
                        if event.key() == Qt.Key.Key_Backtab:
                            self.focusPreviousChild()
                        elif event.key() == Qt.Key.Key_Tab:
                            self.focusNextChild()
                        return True
            # Handle mouse press on editable line edit
            if event.type() == QEvent.Type.MouseButtonPress:
                if not self.view().isVisible():
                    # Open popup immediately on press
                    QTimer.singleShot(0, self.showPopup)
                    return True  # Consume the event
            # Also handle release for safety
            elif event.type() == QEvent.Type.MouseButtonRelease:
                import time
                if time.time() - self._last_popup_time < 0.3:
                    event.accept()
                    return True
                if not self.view().isVisible():
                    QTimer.singleShot(0, self.showPopup)
        return super().eventFilter(obj, event)
