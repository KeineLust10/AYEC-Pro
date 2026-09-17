# -*- coding: utf-8 -*-

"""Bank settings widget."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper


class BankSettingsWidget(QWidget):
    """Banka hesap ve finans bağlantı ayarları."""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Banka Hesap Ayarları")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        root.addWidget(title)

        card = QFrame()
        card.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 12px; }"))
        form = QFormLayout(card)
        form.setContentsMargins(18, 18, 18, 18)
        form.setVerticalSpacing(12)

        self.default_bank_name = QLineEdit()
        self.default_bank_name.setStyleSheet(theme_qss("background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; padding: 8px;"))

        self.default_iban = QLineEdit()
        self.default_iban.setPlaceholderText("TR00 0000 0000 0000 0000 0000 00")
        self.default_iban.setStyleSheet(self.default_bank_name.styleSheet())

        self.default_currency = QComboBox()
        self.default_currency.addItems(CurrencyHelper.get_supported_codes())
        self.default_currency.setStyleSheet(theme_qss("background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; padding: 6px;"))

        self.fx_update_minutes = QSpinBox()
        self.fx_update_minutes.setRange(5, 1440)
        self.fx_update_minutes.setSuffix(" dk")
        self.fx_update_minutes.setStyleSheet(self.default_currency.styleSheet())

        self.chk_auto_fx = QCheckBox("Döviz kurlarını otomatik güncelle")
        self.chk_auto_fx.setStyleSheet(theme_qss("color: @text;"))

        self.chk_bank_to_finance = QCheckBox("Banka hareketlerini finans modülüne otomatik işle")
        self.chk_bank_to_finance.setStyleSheet(theme_qss("color: @text;"))

        self.chk_negative_balance_warn = QCheckBox("Bakiye negatife düştüğünde uyarı ver")
        self.chk_negative_balance_warn.setStyleSheet(theme_qss("color: @text;"))

        form.addRow("Varsayılan banka adı:", self.default_bank_name)
        form.addRow("Varsayılan IBAN:", self.default_iban)
        form.addRow("Varsayılan para birimi:", self.default_currency)
        form.addRow("Kur güncelleme sıklığı:", self.fx_update_minutes)
        form.addRow("", self.chk_auto_fx)
        form.addRow("", self.chk_bank_to_finance)
        form.addRow("", self.chk_negative_balance_warn)

        root.addWidget(card)

        row = QHBoxLayout()
        row.addStretch()

        btn_save = QPushButton("Kaydet")
        btn_save.setStyleSheet(theme_qss("background: @accent; color: @selection_text; border: none; border-radius: 8px; padding: 10px 20px; font-weight: 700;"))
        btn_save.clicked.connect(self.save_data)
        row.addWidget(btn_save)

        root.addLayout(row)

    def _wire_ui_signals(self):
        self.default_currency.currentIndexChanged.connect(self.save_data)
        self.chk_auto_fx.stateChanged.connect(self.save_data)
        self.chk_bank_to_finance.stateChanged.connect(self.save_data)
        self.chk_negative_balance_warn.stateChanged.connect(self.save_data)

    def load_data(self):
        self._suppress_ui_handlers = True
        self.default_bank_name.setText(self.db.get_setting("bank_default_name", ""))
        self.default_iban.setText(self.db.get_setting("bank_default_iban", ""))

        cur = self.db.get_setting("bank_default_currency", CurrencyHelper.get_code(self.db))
        idx = self.default_currency.findText(CurrencyHelper.normalize_code(cur))
        self.default_currency.setCurrentIndex(idx if idx >= 0 else 0)

        self.fx_update_minutes.setValue(int(self.db.get_setting("bank_fx_update_minutes", "60") or 60))
        self.chk_auto_fx.setChecked(self.db.get_setting("bank_auto_fx", "1") == "1")
        self.chk_bank_to_finance.setChecked(self.db.get_setting("bank_sync_finance", "1") == "1")
        self.chk_negative_balance_warn.setChecked(self.db.get_setting("bank_warn_negative", "1") == "1")
        self._suppress_ui_handlers = False

    def save_data(self):
        self.db.set_setting("bank_default_name", self.default_bank_name.text().strip())
        self.db.set_setting("bank_default_iban", self.default_iban.text().strip())
        self.db.set_setting("bank_default_currency", self.default_currency.currentText())
        self.db.set_setting("bank_fx_update_minutes", str(self.fx_update_minutes.value()))
        self.db.set_setting("bank_auto_fx", "1" if self.chk_auto_fx.isChecked() else "0")
        self.db.set_setting("bank_sync_finance", "1" if self.chk_bank_to_finance.isChecked() else "0")
        self.db.set_setting("bank_warn_negative", "1" if self.chk_negative_balance_warn.isChecked() else "0")

        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification("Banka ayarları kaydedildi.", "success")
