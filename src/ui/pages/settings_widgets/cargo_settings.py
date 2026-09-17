# -*- coding: utf-8 -*-

"""Cargo settings widget."""

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


class CargoSettingsWidget(QWidget):
    """Kargo firma ve gönderi ayarları."""

    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 10, 24, 16)
        root.setSpacing(10)

        title = QLabel("Kargo Firma Ayarları")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        root.addWidget(title)

        card = QFrame()
        card.setStyleSheet(theme_qss("QFrame { background: @surface; border: 1px solid @border; border-radius: 12px; }"))
        form = QFormLayout(card)
        form.setContentsMargins(18, 14, 18, 18)
        form.setVerticalSpacing(12)

        self.default_cargo = QComboBox()
        self.default_cargo.addItems(["Yurtiçi", "MNG", "Aras", "Sürat", "PTT", "UPS", "DHL"])
        self.default_cargo.setStyleSheet(theme_qss("background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; padding: 6px;"))

        self.branch_code = QLineEdit()
        self.branch_code.setStyleSheet(theme_qss("background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 8px; padding: 8px;"))

        self.sender_name = QLineEdit()
        self.sender_name.setStyleSheet(self.branch_code.styleSheet())

        self.sender_phone = QLineEdit()
        self.sender_phone.setStyleSheet(self.branch_code.styleSheet())

        self.delivery_days = QSpinBox()
        self.delivery_days.setRange(1, 30)
        self.delivery_days.setSuffix(" gün")
        self.delivery_days.setStyleSheet(self.default_cargo.styleSheet())

        self.chk_auto_track = QCheckBox("Takip numarasını otomatik doğrula")
        self.chk_auto_track.setStyleSheet(theme_qss("color: @text;"))

        self.chk_sms_notify = QCheckBox("Kargo çıkışında müşteriye SMS bildirimi gönder")
        self.chk_sms_notify.setStyleSheet(theme_qss("color: @text;"))

        self.chk_require_receiver = QCheckBox("Teslim alacak kişi bilgisi zorunlu")
        self.chk_require_receiver.setStyleSheet(theme_qss("color: @text;"))

        form.addRow("Varsayılan kargo firması:", self.default_cargo)
        form.addRow("Şube kodu:", self.branch_code)
        form.addRow("Gönderici adı:", self.sender_name)
        form.addRow("Gönderici telefonu:", self.sender_phone)
        form.addRow("Tahmini teslim süresi:", self.delivery_days)
        form.addRow("", self.chk_auto_track)
        form.addRow("", self.chk_sms_notify)
        form.addRow("", self.chk_require_receiver)

        root.addWidget(card)
        root.addStretch()

        row = QHBoxLayout()
        row.addStretch()

        btn_save = QPushButton("Kaydet")
        btn_save.setStyleSheet(theme_qss("background: @accent; color: @selection_text; border: none; border-radius: 8px; padding: 10px 20px; font-weight: 700;"))
        btn_save.clicked.connect(self.save_data)
        row.addWidget(btn_save)

        root.addLayout(row)

    def _wire_ui_signals(self):
        self.default_cargo.currentIndexChanged.connect(self.save_data)
        self.chk_auto_track.stateChanged.connect(self.save_data)
        self.chk_sms_notify.stateChanged.connect(self.save_data)
        self.chk_require_receiver.stateChanged.connect(self.save_data)

    def load_data(self):
        cargo = self.db.get_setting("cargo_default_company", "Yurtiçi")
        idx = self.default_cargo.findText(cargo)
        self.default_cargo.setCurrentIndex(idx if idx >= 0 else 0)

        self.branch_code.setText(self.db.get_setting("cargo_branch_code", ""))
        self.sender_name.setText(self.db.get_setting("cargo_sender_name", ""))
        self.sender_phone.setText(self.db.get_setting("cargo_sender_phone", ""))
        self.delivery_days.setValue(int(self.db.get_setting("cargo_delivery_days", "3") or 3))
        self.chk_auto_track.setChecked(self.db.get_setting("cargo_auto_track", "1") == "1")
        self.chk_sms_notify.setChecked(self.db.get_setting("cargo_sms_notify", "0") == "1")
        self.chk_require_receiver.setChecked(self.db.get_setting("cargo_require_receiver", "1") == "1")

    def save_data(self):
        self.db.set_setting("cargo_default_company", self.default_cargo.currentText())
        self.db.set_setting("cargo_branch_code", self.branch_code.text().strip())
        self.db.set_setting("cargo_sender_name", self.sender_name.text().strip())
        self.db.set_setting("cargo_sender_phone", self.sender_phone.text().strip())
        self.db.set_setting("cargo_delivery_days", str(self.delivery_days.value()))
        self.db.set_setting("cargo_auto_track", "1" if self.chk_auto_track.isChecked() else "0")
        self.db.set_setting("cargo_sms_notify", "1" if self.chk_sms_notify.isChecked() else "0")
        self.db.set_setting("cargo_require_receiver", "1" if self.chk_require_receiver.isChecked() else "0")

        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification("Kargo ayarları kaydedildi.", "success")
