from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout

from src.utils.theme_colors import theme_qss


class TransactionReferenceCard(QFrame):
    quantity_requested = pyqtSignal(str, int)
    action_requested = pyqtSignal(str, str)

    def __init__(self, item, index, amount, unit_price, parent=None, *, vat_text='', try_reference='', code=''):
        super().__init__(parent)
        self.item_id = str(item['id'])
        self.setObjectName('TransactionLineCard')
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        self.setStyleSheet(theme_qss(
            'QFrame#TransactionLineCard { background: @finance_surface_lowest; '
            'border: 1px solid @finance_outline; border-radius: 12px; } '
            'QLabel { background: transparent; border: none; color: @finance_text; } '
            'QPushButton { background: @finance_surface; color: @finance_text_muted; '
            'border: 1px solid @finance_outline; border-radius: 8px; '
            'padding: 0; font-size: 13px; min-height: 24px; } '
            'QPushButton:hover { background: @finance_surface_high; color: @finance_text; }'
        ))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        top = QHBoxLayout()
        number = QLabel(str(index))
        number.setFixedSize(24, 24)
        number.setAlignment(Qt.AlignmentFlag.AlignCenter)
        number.setStyleSheet(theme_qss(
            'background: @finance_active_bg; color: @finance_primary; '
            'border: 1px solid @finance_outline; border-radius: 4px;'
        ))
        number.hide()
        self.title = QLabel(str(item.get('service') or ''))
        self.title.setWordWrap(True)
        self.title.setToolTip(self.title.text())
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.title.setStyleSheet(theme_qss(
            'background: transparent; border: none; color: @finance_text; '
            'font-size: 13px; font-weight: 600;'
        ))
        self.amount = QLabel(amount)
        self.amount.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        self.amount.setStyleSheet(theme_qss(
            'background: transparent; border: none; color: @finance_text; '
            'font-size: 12px; font-weight: 700;'
        ))
        top.addWidget(number, 0, Qt.AlignmentFlag.AlignTop)
        top.addWidget(self.title, 1)
        service = item.get('type') == 'service'
        self.kind_label = QLabel('Hizmet' if service else '\u00dcr\u00fcn')
        self.kind_label.setStyleSheet(theme_qss(
            'background: @finance_success_bg; color: @finance_secondary; '
            'border: 1px solid @finance_outline; border-radius: 4px; '
            'padding: 2px 5px; font-size: 10px;'
            if service else
            'background: @finance_active_bg; color: @finance_primary; '
            'border: 1px solid @finance_outline; border-radius: 4px; '
            'padding: 2px 5px; font-size: 10px;'
        ))
        top.addWidget(self.kind_label, 0, Qt.AlignmentFlag.AlignTop)
        self.kind_label.hide()
        amount_column = QVBoxLayout()
        amount_column.setSpacing(3)
        amount_column.addWidget(self.amount)
        self.try_reference = QLabel(try_reference)
        self.try_reference.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.try_reference.setStyleSheet(theme_qss(
            'background: transparent; border: none; color: @finance_text_muted; font-size: 11px;'
        ))
        self.try_reference.setVisible(bool(try_reference))
        amount_column.addWidget(self.try_reference)
        top.addLayout(amount_column)
        layout.addLayout(top)
        self.description = QLabel(str(code or item.get('description') or ''))
        self.description.setWordWrap(True)
        self.description.setToolTip(self.description.text())
        self.description.setStyleSheet(theme_qss(
            'background: @finance_active_bg; border: 1px solid @finance_outline; '
            'border-radius: 4px; padding: 3px 6px; color: @finance_primary; '
            'font: 10px "JetBrains Mono";'
        ))
        self.description.setVisible(bool(self.description.text()))
        layout.addWidget(self.description)
        layout.removeWidget(self.description)
        layout.insertWidget(0, self.description, 0, Qt.AlignmentFlag.AlignLeft)
        self.date = QLabel(str(item.get('date') or ''))
        self.date.hide()
        self.date.setStyleSheet(theme_qss(
            'background: transparent; border: none; color: @finance_text_muted; font-size: 10px;'
        ))
        metadata = QHBoxLayout()
        metadata.addWidget(self.date)
        metadata.addStretch()
        self.tax = QLabel(f'KDV: {vat_text}' if vat_text else '')
        self.tax.setToolTip('Teklifin genel KDV orani')
        self.tax.setStyleSheet(theme_qss(
            'background: transparent; border: none; color: @finance_text_muted; font-size: 10px;'
        ))
        self.tax.setVisible(False)
        metadata.addWidget(self.tax)
        layout.addLayout(metadata)
        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(theme_qss('background: @finance_outline; border: none;'))
        layout.addWidget(rule)
        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        self.minus = self._button('-', 'Adet azalt', 'decrease')
        self.plus = self._button('+', 'Adet artir', 'increase')
        self.quantity = QLabel(f"{float(item.get('qty', 1)):g}")
        self.quantity.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quantity.setMinimumWidth(24)
        unit = 'Hizmet' if service else 'Adet'
        self.unit_price = QLabel(f'x {unit_price} / {unit}')
        self.unit_price.setStyleSheet(theme_qss(
            'background: transparent; border: none; color: @finance_text_muted; font-size: 11px;'
        ))
        self.edit = self._button('\u270e', 'Kalemi duzenle', 'edit')
        self.remove = self._button('\u00d7', 'Sepetten cikar', 'remove')
        self.minus.clicked.connect(lambda: self.quantity_requested.emit(self.item_id, -1))
        self.plus.clicked.connect(lambda: self.quantity_requested.emit(self.item_id, 1))
        self.edit.clicked.connect(lambda: self.action_requested.emit(self.item_id, 'edit'))
        self.remove.clicked.connect(lambda: self.action_requested.emit(self.item_id, 'remove'))
        for widget in (self.minus, self.quantity, self.plus, self.unit_price):
            bottom.addWidget(widget)
        bottom.addStretch()
        bottom.addWidget(self.edit)
        bottom.addWidget(self.remove)
        layout.addLayout(bottom)
        for label in (
            self.title, self.amount, self.try_reference, self.description,
            self.date, self.quantity, self.unit_price, self.kind_label, self.tax,
        ):
            label.setTextFormat(Qt.TextFormat.PlainText)

    def _button(self, text, tooltip, action):
        button = QPushButton(text)
        button.setObjectName(f'TransactionLine_{action}')
        button.setFixedSize(26, 26)
        button.setToolTip(tooltip)
        button.setAccessibleName(f'{tooltip}: {self.item_id}')
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button
