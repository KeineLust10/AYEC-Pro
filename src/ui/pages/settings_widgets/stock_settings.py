# -*- coding: utf-8 -*-

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.utils.theme_colors import theme_qss


class StockSettingsWidget(QWidget):
    """Stok yönetimi ayarları."""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def _spin_style(self):
        return theme_qss(
            """
            QSpinBox {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px 38px 6px 10px;
                min-height: 34px;
            }
            QSpinBox:focus { border-color: @accent; }
            QSpinBox::up-button, QSpinBox::down-button {
                subcontrol-origin: border;
                width: 30px;
                background-color: @accent;
                border-left: 1px solid @border;
            }
            QSpinBox::up-button {
                subcontrol-position: top right;
                border-top-right-radius: 7px;
                border-bottom: 1px solid @border;
            }
            QSpinBox::down-button {
                subcontrol-position: bottom right;
                border-bottom-right-radius: 7px;
                border-top: 1px solid @border;
            }
            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: @accent_hover;
            }
            QSpinBox::up-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 7px solid @selection_text;
            }
            QSpinBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 7px solid @selection_text;
            }
            QSpinBox::up-button:disabled, QSpinBox::down-button:disabled {
                background-color: @surface;
            }
            """
        )

    def _line_style(self):
        return theme_qss(
            """
            QLineEdit {
                background: @surface_alt;
                color: @text;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 6px 10px;
                min-height: 34px;
            }
            QLineEdit:focus { border-color: @accent; }
            """
        )

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 10, 24, 16)
        root.setSpacing(10)

        title = QLabel("Stok Yönetim Ayarları")
        title.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))

        subtitle = QLabel("Minimum stok, otomatik kodlama ve finans entegrasyon davranışını buradan yönetin.")
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))

        root.addWidget(title)
        root.addWidget(subtitle)

        card = QFrame()
        card.setStyleSheet(
            theme_qss(
                """
                QFrame {
                    background: @surface;
                    border: 1px solid @border;
                    border-radius: 12px;
                }
                """
            )
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 12, 16, 16)
        card_layout.setSpacing(10)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(12)

        self.min_stock = QSpinBox()
        self.min_stock.setRange(0, 100000)
        self.min_stock.setStyleSheet(self._spin_style())

        self.reorder_days = QSpinBox()
        self.reorder_days.setRange(0, 365)
        self.reorder_days.setStyleSheet(self._spin_style())

        self.default_profit = QSpinBox()
        self.default_profit.setRange(0, 500)
        self.default_profit.setSuffix(" %")
        self.default_profit.setStyleSheet(self._spin_style())

        self.stock_prefix = QLineEdit()
        self.stock_prefix.setStyleSheet(self._line_style())

        left_form = QFormLayout()
        left_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        left_form.setVerticalSpacing(10)
        left_form.addRow("Minimum stok eşiği", self.min_stock)
        left_form.addRow("Yeniden sipariş günü", self.reorder_days)

        right_form = QFormLayout()
        right_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        right_form.setVerticalSpacing(10)
        right_form.addRow("Varsayılan kâr oranı", self.default_profit)
        right_form.addRow("Stok kodu öneki", self.stock_prefix)

        grid.addLayout(left_form, 0, 0)
        grid.addLayout(right_form, 0, 1)
        card_layout.addLayout(grid)

        rule = QFrame()
        rule.setFixedHeight(1)
        rule.setStyleSheet(theme_qss("background: @border; border: none;"))
        card_layout.addWidget(rule)

        self.chk_auto_code = QCheckBox("Stok kodunu otomatik üret")
        self.chk_warn_negative = QCheckBox("Negatif stokta uyarı göster")
        self.chk_sync_finance = QCheckBox("Stok hareketlerini finans modülüne yansıt")

        for chk in (self.chk_auto_code, self.chk_warn_negative, self.chk_sync_finance):
            chk.setStyleSheet(
                theme_qss("QCheckBox { color: @text; font-size: 12px; } QCheckBox::indicator { width: 14px; height: 14px; }")
            )
            card_layout.addWidget(chk)

        root.addWidget(card)
        root.addStretch()

        actions = QHBoxLayout()
        actions.addStretch()

        btn_save = QPushButton("Kaydet")
        btn_save.setMinimumWidth(130)
        btn_save.setStyleSheet(
            theme_qss("background: @accent; color: @selection_text; border: none; border-radius: 8px; padding: 10px 16px; font-weight: 700;")
        )
        btn_save.clicked.connect(self.save_data)

        actions.addWidget(btn_save)
        root.addLayout(actions)

    def _wire_ui_signals(self):
        self.chk_auto_code.stateChanged.connect(self.save_data)
        self.chk_warn_negative.stateChanged.connect(self.save_data)
        self.chk_sync_finance.stateChanged.connect(self.save_data)

    def load_data(self):
        self.min_stock.setValue(int(self.db.get_setting("stock_min_level", "5") or 5))
        self.reorder_days.setValue(int(self.db.get_setting("stock_reorder_days", "7") or 7))
        self.default_profit.setValue(int(self.db.get_setting("stock_default_profit_pct", "20") or 20))
        self.stock_prefix.setText(self.db.get_setting("stock_code_prefix", "STK"))
        self.chk_auto_code.setChecked(self.db.get_setting("stock_auto_code", "1") == "1")
        self.chk_warn_negative.setChecked(self.db.get_setting("stock_warn_negative", "1") == "1")
        self.chk_sync_finance.setChecked(self.db.get_setting("stock_sync_finance", "1") == "1")

    def save_data(self):
        self.db.set_setting("stock_min_level", str(self.min_stock.value()))
        self.db.set_setting("stock_reorder_days", str(self.reorder_days.value()))
        self.db.set_setting("stock_default_profit_pct", str(self.default_profit.value()))
        self.db.set_setting("stock_code_prefix", self.stock_prefix.text().strip() or "STK")
        self.db.set_setting("stock_auto_code", "1" if self.chk_auto_code.isChecked() else "0")
        self.db.set_setting("stock_warn_negative", "1" if self.chk_warn_negative.isChecked() else "0")
        self.db.set_setting("stock_sync_finance", "1" if self.chk_sync_finance.isChecked() else "0")

        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification("Stok ayarları kaydedildi.", "success")
