# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QFormLayout, QComboBox, QLineEdit, QDateEdit,
                             QDoubleSpinBox, QPushButton)
from PyQt6.QtCore import QDate
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.ui.widgets.premium_dialog import PremiumDialog
from src.utils.toast_notification import show_warning, show_error



class AddTransferDialog(PremiumDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None):
        super().__init__("Banka Transferi", parent)
        self.db = db
        self.resize(420, 520)
        self.setup_ui()

        self._wire_ui_signals()
    def setup_ui(self):
        form = QFormLayout()
        form.setSpacing(15)

        self.accounts = self._load_bank_accounts()

        self.cmb_from = QComboBox()
        self.cmb_to = QComboBox()
        for acc in self.accounts:
            acc_id = self._bank_field(acc, "id", 0)
            bank = self._bank_field(acc, "bank_name", 1)
            acc_name = self._bank_field(acc, "account_holder", 2)
            if not acc_name:
                acc_name = self._bank_field(acc, "account_name", 2)
            acc_no = self._bank_field(acc, "account_number", 4)
            if not acc_no:
                acc_no = self._bank_field(acc, "account_no", 4)
            is_active_val = self._bank_field(acc, "is_active", 7, 1)
            if int(is_active_val or 0) != 1:
                continue
            label_parts = [str(bank or "").strip(), str(acc_name or "").strip()]
            label_parts = [p for p in label_parts if p]
            label = " - ".join(label_parts) if label_parts else "Banka Hesabı"
            if acc_no:
                label = f"{label} ({acc_no})"
            self.cmb_from.addItem(label, acc_id)
            self.cmb_to.addItem(label, acc_id)

        form.addRow("Kaynak Hesap:", self.cmb_from)
        form.addRow("Hedef Hesap:", self.cmb_to)

        self.inp_amount = QDoubleSpinBox()
        self.inp_amount.setRange(0, 100000000)
        self.inp_amount.setSuffix(f" {CurrencyHelper.get_symbol(self.db)}")
        form.addRow("Tutar:", self.inp_amount)

        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Transfer açıklaması...")
        form.addRow("Açıklama:", self.inp_desc)

        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setCalendarPopup(True)
        self.inp_date.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Tarih:", self.inp_date)

        self.body_layout.addLayout(form)

        btn_save = QPushButton("Kaydet")
        btn_save.setFixedHeight(45)
        btn_save.setStyleSheet(theme_qss("background: @accent; color: @selection_text; border-radius: 8px; font-weight: bold;"))
        btn_save.clicked.connect(self.save)
        self.body_layout.addWidget(btn_save)

    def _wire_ui_signals(self):
        self.cmb_from.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_to.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _load_bank_accounts(self):
        try:
            return self.db.get_bank_accounts() or []
        except Exception:
            return []

    @staticmethod
    def _bank_field(account, key, index, default=None):
        if isinstance(account, dict):
            return account.get(key, default)
        try:
            if hasattr(account, "keys") and key in account.keys():
                return account[key]
        except Exception:
            pass
        try:
            return account[index]
        except Exception:
            return default

    def save(self):
        try:
            from_id = self.cmb_from.currentData()
            to_id = self.cmb_to.currentData()
            amt = self.inp_amount.value()
            desc = self.inp_desc.text()
            date = self.inp_date.date().toString("yyyy-MM-dd")
            if not from_id or not to_id:
                show_warning(self, "Kaynak ve hedef hesap seçilmelidir.")
                return
            if from_id == to_id:
                show_warning(self, "Kaynak ve hedef hesap aynı olamaz.")
                return
            if amt <= 0:
                show_warning(self, "Tutar sıfırdan büyük olmalıdır.")
                return

            ok = self.db.add_bank_transfer(from_id, to_id, amt, desc, date, payment_method="Transfer")
            if ok:
                self.accept()
            else:
                show_error(self, "Transfer kaydedilemedi.")
        except Exception as e:
            show_error(self, f"Transfer kaydedilirken hata oluştu: {e}")
