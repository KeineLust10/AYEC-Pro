# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QFormLayout, QComboBox, QLineEdit, QDateEdit,
                             QDoubleSpinBox, QPushButton, QHBoxLayout, QRadioButton, QButtonGroup)
from PyQt6.QtCore import Qt, QDate, QEvent, QTimer
from PyQt6.QtGui import QCursor
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.ui.widgets.premium_dialog import PremiumDialog
from src.utils.toast_notification import show_warning, show_error, show_success
from src.utils.logger import logger



class AddExpenseDialog(PremiumDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None):
        super().__init__("Gider Ekle", parent)
        self.db = db
        self.resize(400, 500)
        self.setup_ui()
        
        self._wire_ui_signals()
    def setup_ui(self):
        form = QFormLayout()
        form.setSpacing(15)
        self.bank_accounts = self._load_bank_accounts()
        
        self.cmb_cat = QComboBox()
        self.cmb_cat.addItems(["Dükkan Kirası", "Fatura (Elektrik/Su)", "Personel", "Yemek", "Malzeme", "Vergi", "Diğer"])
        self.cmb_cat.setEditable(True)
        form.addRow("Kategori:", self.cmb_cat)

        self.cmb_bank = QComboBox()
        self.cmb_bank.setEditable(True)
        self.cmb_bank.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        if self.cmb_bank.lineEdit():
            self.cmb_bank.lineEdit().setReadOnly(True)
            self.cmb_bank.lineEdit().setPlaceholderText("Banka hesabı seçin")
            self.cmb_bank.lineEdit().installEventFilter(self)
        self.cmb_bank.addItem("Banka hesabı seçin", None)
        for acc in self.bank_accounts:
            acc_id = self._bank_field(acc, "id", 0)
            bank = self._bank_field(acc, "bank_name", 1, "")
            acc_name = self._bank_field(acc, "account_holder", 2, "")
            acc_no = self._bank_field(acc, "account_number", 4, "")
            is_active_val = self._bank_field(acc, "is_active", 7, 0)
            if int(is_active_val or 0) != 1:
                continue
            label_parts = [str(bank or "").strip(), str(acc_name or "").strip()]
            label_parts = [p for p in label_parts if p]
            label = " - ".join(label_parts) if label_parts else "Banka Hesabı"
            if acc_no:
                label = f"{label} ({acc_no})"
            self.cmb_bank.addItem(label, acc_id)
        form.addRow("Banka Hesabı:", self.cmb_bank)
        
        self.inp_amount = QDoubleSpinBox()
        self.inp_amount.setRange(0, 1_000_000_000)
        self.inp_amount.setSuffix(f" {CurrencyHelper.get_symbol(self.db)}")
        self.inp_amount.setDecimals(2)

        # Currency Chip Buttons
        _c_style2 = theme_qss("""
            QRadioButton {
                background: @surface_alt; color: @text_muted;
                padding: 6px 12px; border-radius: 10px;
                font-weight: bold; font-size: 13px;
                border: 1px solid @border;
            }
            QRadioButton::indicator { width: 0; height: 0; }
            QRadioButton:checked { background: @danger; color: @selection_text; border: 1px solid @danger; }
            QRadioButton:!checked:hover { background: @surface; color: @text; }
        """)
        self.exp_btn_try = QRadioButton("TRY")
        self.exp_btn_usd = QRadioButton("$ USD")
        self.exp_btn_eur = QRadioButton("€ EUR")
        self.exp_btn_grp = QButtonGroup(self)
        self.exp_btn_grp.addButton(self.exp_btn_try, 1)
        self.exp_btn_grp.addButton(self.exp_btn_usd, 2)
        self.exp_btn_grp.addButton(self.exp_btn_eur, 3)
        for _b in [self.exp_btn_try, self.exp_btn_usd, self.exp_btn_eur]:
            _b.setStyleSheet(_c_style2)
            _b.setCursor(Qt.CursorShape.PointingHandCursor)
        try:
            _g = CurrencyHelper.get_code(self.db)
            if _g == "USD":
                self.exp_btn_usd.setChecked(True)
            elif _g == "EUR":
                self.exp_btn_eur.setChecked(True)
            else:
                self.exp_btn_try.setChecked(True)
        except Exception:
            self.exp_btn_try.setChecked(True)

        def _exp_suffix():
            _code = "USD" if self.exp_btn_usd.isChecked() else "EUR" if self.exp_btn_eur.isChecked() else "TRY"
            _s = CurrencyHelper.get_symbol(self.db, _code)
            self.inp_amount.setSuffix(f" {_s}")
        self.exp_btn_try.toggled.connect(_exp_suffix)
        self.exp_btn_usd.toggled.connect(_exp_suffix)
        self.exp_btn_eur.toggled.connect(_exp_suffix)
        _exp_suffix()

        exp_amount_row = QHBoxLayout()
        exp_amount_row.addWidget(self.inp_amount)
        exp_amount_row.addWidget(self.exp_btn_try)
        exp_amount_row.addWidget(self.exp_btn_usd)
        exp_amount_row.addWidget(self.exp_btn_eur)
        form.addRow("Tutar:", exp_amount_row)

        
        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Açıklama...")
        form.addRow("Açıklama:", self.inp_desc)
        
        self.inp_date = QDateEdit(QDate.currentDate())
        self.inp_date.setCalendarPopup(True)
        self.inp_date.setDisplayFormat("dd.MM.yyyy")
        form.addRow("Tarih:", self.inp_date)
        
        self.body_layout.addLayout(form)
        
        btn_save = QPushButton("Kaydet")
        btn_save.setFixedHeight(45)
        btn_save.setStyleSheet(theme_qss("background: @danger; color: @selection_text; border-radius: 8px; font-weight: bold;"))
        btn_save.clicked.connect(self.save)
        self.body_layout.addWidget(btn_save)
        
    def _wire_ui_signals(self):
        self.cmb_cat.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.cmb_bank.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _load_bank_accounts(self):
        try:
            return self.db.get_bank_accounts() or []
        except Exception:
            return []

    @staticmethod
    def _bank_field(account, key, index, default=None):
        if account is None:
            return default
        if hasattr(account, "keys"):
            try:
                if key in account.keys():
                    return account[key]
            except Exception:
                pass
        if isinstance(account, dict):
            if key in account:
                return account.get(key, default)
            if key == "account_holder":
                return account.get("account_name", default)
            if key == "account_number":
                return account.get("account_no", default)
        try:
            return account[index]
        except Exception:
            return default

    def eventFilter(self, obj, event):
        if obj == self.cmb_bank.lineEdit() and event.type() == QEvent.Type.MouseButtonRelease:
            if not self.cmb_bank.view().isVisible():
                QTimer.singleShot(0, self.cmb_bank.showPopup)
            return False
        return super().eventFilter(obj, event)
        
    def save(self):
        try:
            cat = self.cmb_cat.currentText()
            amt = self.inp_amount.value()
            desc = self.inp_desc.text()
            date = self.inp_date.date().toString("yyyy-MM-dd")
            bank_account_id = self.cmb_bank.currentData()
            if bank_account_id is None:
                show_warning(self, "Banka hesabı seçimi zorunludur.")
                return
            payment_method = "Banka"
            self.db.add_transaction(
                t_type="Gider",
                category=cat,
                amount=amt,
                description=desc,
                date=date,
                payment_method=payment_method,
                bank_account_id=bank_account_id,
                currency="USD" if self.exp_btn_usd.isChecked() else "EUR" if self.exp_btn_eur.isChecked() else "TRY",
                original_amount=amt,
            )
            self._refresh_bank_pages()
            account = self.db.get_bank_account_by_id(bank_account_id)
            acc_label = ""
            if account:
                bank = self._bank_field(account, "bank_name", 1, "")
                acc_name = self._bank_field(account, "account_holder", 2, "")
                label_parts = [str(bank or "").strip(), str(acc_name or "").strip()]
                label_parts = [p for p in label_parts if p]
                if label_parts:
                    acc_label = f" ({' - '.join(label_parts)})"
            show_success(self, f"Gider kaydedildi. {CurrencyHelper.format_amount(amt, db=self.db, currency_code='USD' if self.exp_btn_usd.isChecked() else 'EUR' if self.exp_btn_eur.isChecked() else 'TRY')}{acc_label} bakiyesinden düşüldü.")
            self.accept()
        except Exception as e:
            logger.error(f"Expense save error: {e}")
            show_error(self, f"Gider kaydedilirken hata oluştu: {e}")

    def _refresh_bank_pages(self):
        parent = self.parent()
        main_window = getattr(parent, "main_window", None) if parent else None
        if main_window and hasattr(main_window, "bank_page"):
            bank_page = getattr(main_window, "bank_page")
            if bank_page and hasattr(bank_page, "refresh_data"):
                bank_page.refresh_data()
