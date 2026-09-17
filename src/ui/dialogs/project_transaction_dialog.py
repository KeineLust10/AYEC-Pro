# -*- coding: utf-8 -*-

"""
Modern Project Transaction Dialog
Gelir/Gider ekleme pencereleri için premium tasarım.
"""

from PyQt6.QtWidgets import QVBoxLayout, QLabel, QComboBox, QPushButton, QDateEdit, QDoubleSpinBox
from PyQt6.QtCore import Qt, QDate
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.currency_helper import CurrencyHelper



class ProjectTransactionDialog(BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, project_id, txn_type, parent=None, sub_id=None):
        title = "💰 Gelir Ekle" if txn_type == "Gelir" else "💸 Gider Ekle"
        super().__init__(parent, title=title, width=450, height=520)
        self.db = db
        self.project_id = project_id
        self.txn_type = txn_type
        self.sub_id = sub_id
        self.currency_code, self.exchange_rate = self._get_project_currency_context()
        self.bank_accounts = self._load_bank_accounts()
        self.setup_transaction_ui()

    def _get_project_currency_context(self):
        try:
            currency, rate = self.db.get_project_currency(self.project_id)
            return (str(currency or "TRY").upper(), float(rate or 1.0))
        except Exception:
            return (CurrencyHelper.get_code(self.db), 1.0)

    def setup_transaction_ui(self):
        content = self.content_layout
        content.setSpacing(15)

        lbl_cat = QLabel("Kategori")
        lbl_cat.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-weight: bold; font-size: 11px;"))
        self.cmb_cat = QComboBox()
        self.cmb_cat.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        if self.txn_type == "Gider":
            cats = ["Malzeme", "İşçilik", "Taşeron Ödemesi", "Nakliye", "Resmi Gider", "Diğer"]
            self.cmb_cat.addItems(cats)
            if self.sub_id:
                self.cmb_cat.setCurrentText("Taşeron Ödemesi")
                self.cmb_cat.setEnabled(False)
        else:
            self.cmb_cat.addItems(["Daire Satışı", "Proje Hakedişi", "Diğer"])
        self.cmb_cat.currentIndexChanged.connect(self.on_category_changed)
        content.addWidget(lbl_cat)
        content.addWidget(self.cmb_cat)

        lbl_amt = QLabel("Tutar")
        lbl_amt.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-weight: bold; font-size: 11px;"))
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 100000000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(f" {CurrencyHelper.get_label(self.currency_code)}")
        DesignTokens.apply_spinbox_styles(self.spin_amount)
        self.spin_amount.setFixedHeight(45)
        self.spin_amount.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.spin_amount.setKeyboardTracking(False)
        content.addWidget(lbl_amt)
        content.addWidget(self.spin_amount)

        lbl_bank = QLabel("Banka Hesabı")
        lbl_bank.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-weight: bold; font-size: 11px;"))
        self.cmb_bank = QComboBox()
        self.cmb_bank.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        self.cmb_bank.addItem("Nakit", None)
        for acc in self.bank_accounts:
            acc_id, bank, branch, acc_name, acc_no, iban, balance_val, is_active_val, created_at = acc
            if int(is_active_val or 0) != 1:
                continue
            label_parts = [str(bank or "").strip(), str(acc_name or "").strip()]
            label_parts = [p for p in label_parts if p]
            label = " - ".join(label_parts) if label_parts else "Banka Hesabı"
            if acc_no:
                label = f"{label} ({acc_no})"
            self.cmb_bank.addItem(label, acc_id)
        content.addWidget(lbl_bank)
        content.addWidget(self.cmb_bank)

        lbl_date = QLabel("Tarih")
        lbl_date.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-weight: bold; font-size: 11px;"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.date_edit.setFixedHeight(45)
        content.addWidget(lbl_date)
        content.addWidget(self.date_edit)

        lbl_desc = QLabel("Açıklama")
        lbl_desc.setStyleSheet(theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-weight: bold; font-size: 11px;"))
        self.txt_desc = QComboBox()
        self.txt_desc.setEditable(True)
        self.txt_desc.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.txt_desc.setFixedHeight(45)
        self.txt_desc.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.txt_desc.setCurrentText("")
        self.txt_desc.setEditable(True)
        self.txt_desc.lineEdit().setPlaceholderText("İşlem detayı...")
        content.addWidget(lbl_desc)
        content.addWidget(self.txt_desc)

        content.addStretch()

        btn_layout = QVBoxLayout()
        self.btn_cancel = QPushButton("Vazgeç")
        self.btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_save = QPushButton("Kaydet")
        variant = "success" if self.txn_type == "Gelir" else "destructive"
        self.btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss(variant)))
        self.btn_save.clicked.connect(self.save)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)

        from PyQt6.QtWidgets import QHBoxLayout
        buttons = QHBoxLayout()
        buttons.setSpacing(15)
        buttons.addWidget(self.btn_cancel, 1)
        buttons.addWidget(self.btn_save, 2)
        content.addLayout(buttons)

    def _load_bank_accounts(self):
        try:
            return self.db.get_bank_accounts() or []
        except Exception:
            return []

    def on_category_changed(self):
        current = self.cmb_cat.currentText()
        if self.txt_desc.isEditable():
            self.txt_desc.lineEdit().setPlaceholderText(f"{current} detayı...")

    def save(self):
        bank_account_id = self.cmb_bank.currentData()
        payment_method = "Nakit" if bank_account_id is None else "Banka"
        entered_amount = float(self.spin_amount.value() or 0.0)
        currency = str(self.currency_code or "TRY").upper()
        exchange_rate = float(self.exchange_rate or 1.0)

        if currency == "TRY":
            amount_try = entered_amount
            original_amount = None
        else:
            amount_try = CurrencyHelper.convert_amount(self.db, entered_amount, currency, "TRY")
            original_amount = entered_amount

        data = {
            "project_id": self.project_id,
            "type": self.txn_type,
            "category": self.cmb_cat.currentText(),
            "amount": amount_try,
            "payment_method": payment_method,
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "description": self.txt_desc.currentText(),
            "status": "Ödendi",
            "ref_table": "subcontractors" if self.sub_id else None,
            "ref_id": self.sub_id,
            "bank_account_id": bank_account_id,
            "original_amount": original_amount,
            "original_currency": currency,
            "exchange_rate": exchange_rate,
        }
        self.db.add_project_transaction(data)
        self.accept()

    def _wire_ui_signals(self):
        self.cmb_bank.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.txt_desc.currentIndexChanged.connect(self._on_ui_widget_changed)
