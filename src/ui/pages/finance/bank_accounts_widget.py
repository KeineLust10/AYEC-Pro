# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
)

from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.widgets.empty_state import EmptyState
from src.utils.theme_colors import qc, theme_qss
from src.utils.toast_notification import show_error, show_success
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.input_validator import InputValidator
from src.utils.system_config import SystemConfig
from src.ui.dialogs.simple_confirm import SimpleConfirmDialog


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            normalized = value.strip().replace("₺", "").replace("TL", "").replace(" ", "")
            normalized = normalized.replace(".", "").replace(",", ".")
            return float(normalized)
        return float(value)
    except (TypeError, ValueError):
        return default



class AddBankAccountDialog(BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, parent=None):
        super().__init__(parent=parent, title="Yeni Hesap Ekle", width=560, height=520)
        self.db = db
        self._build()

    def _build(self):
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.inp_bank = QLineEdit()
        self.inp_branch = QLineEdit()
        self.inp_name = QLineEdit()
        self.inp_no = QLineEdit()
        self.inp_iban = QLineEdit()
        self.inp_balance = QDoubleSpinBox()
        self.inp_balance.setMaximum(999999999999.99)
        self.inp_balance.setDecimals(2)
        self.inp_balance.setSuffix(f" {CurrencyHelper.get_symbol(self.db)}")

        for w in (self.inp_bank, self.inp_branch, self.inp_name, self.inp_no, self.inp_iban):
            w.setMinimumHeight(38)
            w.setStyleSheet(
                theme_qss(
                    "background:@surface; color:@text; border:1px solid @border; border-radius:8px; padding:6px 10px;"
                )
            )
        self.inp_balance.setMinimumHeight(38)

        form.addRow("Banka:", self.inp_bank)
        form.addRow("Şube:", self.inp_branch)
        form.addRow("Hesap Adı:", self.inp_name)
        form.addRow("Hesap No:", self.inp_no)
        form.addRow("IBAN:", self.inp_iban)
        form.addRow("Başlangıç Bakiyesi:", self.inp_balance)

        # Currency Chip Buttons
        chip_style = theme_qss("""
            QRadioButton {
                background: @surface_alt;
                color: @text_muted;
                padding: 6px 14px;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
                border: 1px solid @border;
            }
            QRadioButton::indicator { width: 0; height: 0; }
            QRadioButton:checked { background: @accent; color: @selection_text; border: 1px solid @accent; }
            QRadioButton:!checked:hover { background: @surface; color: @text; }
        """)
        self.btn_try = QRadioButton("TRY")
        self.btn_usd = QRadioButton("$ USD")
        self.btn_eur = QRadioButton("€ EUR")
        self.btn_grp = QButtonGroup(self)
        self.btn_grp.addButton(self.btn_try, 1)
        self.btn_grp.addButton(self.btn_usd, 2)
        self.btn_grp.addButton(self.btn_eur, 3)
        for b in [self.btn_try, self.btn_usd, self.btn_eur]:
            b.setStyleSheet(chip_style)
            b.setCursor(Qt.CursorShape.PointingHandCursor)

        # Default to global setting
        try:
            default_curr = CurrencyHelper.get_code(self.db)
            if default_curr == "USD":
                self.btn_usd.setChecked(True)
            elif default_curr == "EUR":
                self.btn_eur.setChecked(True)
            else:
                self.btn_try.setChecked(True)
        except Exception:
            self.btn_try.setChecked(True)

        def _update_suffix():
            code = "USD" if self.btn_usd.isChecked() else "EUR" if self.btn_eur.isChecked() else "TRY"
            sym = CurrencyHelper.get_symbol(self.db, code)
            self.inp_balance.setSuffix(f" {sym}")
        self.btn_try.toggled.connect(_update_suffix)
        self.btn_usd.toggled.connect(_update_suffix)
        self.btn_eur.toggled.connect(_update_suffix)
        _update_suffix()

        curr_row = QHBoxLayout()
        curr_row.addWidget(self.btn_try)
        curr_row.addWidget(self.btn_usd)
        curr_row.addWidget(self.btn_eur)
        curr_row.addStretch()
        form.addRow("Para Birimi:", curr_row)
        self.content_layout.addLayout(form)

        self.add_cancel_button("İptal")
        self.add_button("Kaydet", "success", self._save)
        self.inp_bank.setFocus()

    def _col_idx(self, name, fallback):
        try:
            return self._cols.index(name)
        except ValueError:
            return fallback

    def _row_currency(self):
        idx = self._col_idx("currency", 6)
        return str(self._v(self.account_row, idx, "TRY") or "TRY").upper()

    def _row_balance(self):
        idx = self._col_idx("current_balance", 9 if len(self.account_row) > 9 else 6)
        return _to_float(self._v(self.account_row, idx, 0.0), 0.0)

    def _row_active(self):
        idx = self._col_idx("is_active", 7 if len(self.account_row) > 7 else 1)
        return _to_int(self._v(self.account_row, idx, 1), 1) == 1

    def _save(self):
        if not self.inp_bank.text().strip():
            show_error(self, "Banka adı zorunludur.")
            return

        if SystemConfig.is_feature_active(self.db, "iban_verify"):
            ok_iban, iban_message = InputValidator.validate_iban(
                self.inp_iban.text().strip(),
                allow_empty=True,
            )
            if not ok_iban:
                show_error(self, iban_message)
                return

        currency = "USD" if self.btn_usd.isChecked() else "EUR" if self.btn_eur.isChecked() else "TRY"
        ok = self.db.add_bank_account(
            self.inp_bank.text().strip(),
            self.inp_branch.text().strip(),
            self.inp_name.text().strip(),
            self.inp_no.text().strip(),
            self.inp_iban.text().strip(),
            self.inp_balance.value(),
            currency,
        )
        if ok:
            self.accept()
        else:
            show_error(self, "Banka hesabı kaydedilemedi.")


class EditBankAccountDialog(BaseModernDialog):
    def __init__(self, db, account_row, parent=None):
        super().__init__(parent=parent, title="Hesap Düzenle", width=560, height=540)
        self.db = db
        self.account_row = account_row
        self._cols = list(self.db._get_table_columns("bank_accounts") or []) if hasattr(self.db, "_get_table_columns") else []
        self._build()

    @staticmethod
    def _v(row, idx, default=""):
        if not row or idx >= len(row):
            return default
        value = row[idx]
        return default if value is None else value

    def _build(self):
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.inp_bank = QLineEdit(str(self._v(self.account_row, 1, "")))
        self.inp_branch = QLineEdit(str(self._v(self.account_row, 2, "")))
        self.inp_name = QLineEdit(str(self._v(self.account_row, 3, "")))
        self.inp_no = QLineEdit(str(self._v(self.account_row, 4, "")))
        self.inp_iban = QLineEdit(str(self._v(self.account_row, 5, "")))

        self.inp_balance = QDoubleSpinBox()
        self.inp_balance.setMaximum(999999999999.99)
        self.inp_balance.setDecimals(2)
        self.inp_balance.setSuffix(f" {CurrencyHelper.get_symbol(self.db, self._row_currency())}")
        self.inp_balance.setValue(self._row_balance())

        self.chk_active = QCheckBox("Aktif")
        self.chk_active.setChecked(self._row_active())

        for w in (self.inp_bank, self.inp_branch, self.inp_name, self.inp_no, self.inp_iban):
            w.setMinimumHeight(38)
            w.setStyleSheet(
                theme_qss(
                    "background:@surface; color:@text; border:1px solid @border; border-radius:8px; padding:6px 10px;"
                )
            )
        self.inp_balance.setMinimumHeight(38)

        form.addRow("Banka:", self.inp_bank)
        form.addRow("Şube:", self.inp_branch)
        form.addRow("Hesap Adı:", self.inp_name)
        form.addRow("Hesap No:", self.inp_no)
        form.addRow("IBAN:", self.inp_iban)
        form.addRow("Bakiye:", self.inp_balance)
        form.addRow("Durum:", self.chk_active)
        self.content_layout.addLayout(form)

        self.add_cancel_button("İptal")
        self.add_button("Kaydet", "success", self._save)

    def _save(self):
        account_id = _to_int(self._v(self.account_row, 0, 0), 0)
        if SystemConfig.is_feature_active(self.db, "iban_verify"):
            ok_iban, iban_message = InputValidator.validate_iban(
                self.inp_iban.text().strip(),
                allow_empty=True,
            )
            if not ok_iban:
                show_error(self, iban_message)
                return
        ok = self.db.update_bank_account(
            account_id,
            self.inp_bank.text().strip(),
            self.inp_branch.text().strip(),
            self.inp_name.text().strip(),
            self.inp_no.text().strip(),
            self.inp_iban.text().strip(),
            self.inp_balance.value(),
            self._row_currency(),
        )
        if not ok:
            show_error(self, "Hesap güncellenemedi.")
            return

        if hasattr(self.db, "set_bank_account_active"):
            self.db.set_bank_account_active(account_id, self.chk_active.isChecked())
        self.accept()

    def _col_idx(self, name, fallback):
        try:
            return self._cols.index(name)
        except ValueError:
            return fallback

    def _row_currency(self):
        idx = self._col_idx("currency", 6)
        return str(self._v(self.account_row, idx, "TRY") or "TRY").upper()

    def _row_balance(self):
        idx = self._col_idx("current_balance", 9 if len(self.account_row or []) > 9 else 6)
        return _to_float(self._v(self.account_row, idx, 0.0), 0.0)

    def _row_active(self):
        idx = self._col_idx("is_active", 7 if len(self.account_row or []) > 7 else 1)
        return _to_int(self._v(self.account_row, idx, 1), 1) == 1


class AccountDetailDialog(BaseModernDialog):
    def __init__(self, db, account_row, parent=None):
        super().__init__(parent=parent, title="Hesap Detayı", width=600, height=560)
        self.db = db
        self.account_row = account_row
        self._cols = list(self.db._get_table_columns("bank_accounts") or []) if hasattr(self.db, "_get_table_columns") else []
        self._build()

    @staticmethod
    def _v(row, idx, default=""):
        if not row or idx >= len(row):
            return default
        value = row[idx]
        return default if value is None else value

    def _build(self):
        form = QGridLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        fields = [
            ("Hesap ID:", str(self._v(self.account_row, 0, "-"))),
            ("Banka:", str(self._v(self.account_row, 1, "-"))),
            ("Şube:", str(self._v(self.account_row, 2, "-"))),
            ("Hesap Adı:", str(self._v(self.account_row, 3, "-"))),
            ("Hesap No:", str(self._v(self.account_row, 4, "-"))),
            ("IBAN:", str(self._v(self.account_row, 5, "-"))),
            ("Para Birimi:", self._row_currency()),
            ("Bakiye:", CurrencyHelper.format_amount(self._row_balance(), db=self.db, currency_code=self._row_currency())),
            ("Durum:", "Aktif" if self._row_active() else "Pasif"),
        ]

        for i, (label_text, value_text) in enumerate(fields):
            key_lbl = QLabel(label_text)
            key_lbl.setStyleSheet(theme_qss("font-weight:700; font-size:13px; color:@text_muted;"))
            key_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            val_lbl = QLabel(str(value_text))
            val_lbl.setStyleSheet(theme_qss("font-size:14px; color:@text;"))
            val_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            form.addWidget(key_lbl, i, 0)
            form.addWidget(val_lbl, i, 1)

        status_val = fields[-1][1]
        status_widget = form.itemAtPosition(len(fields) - 1, 1).widget()
        if status_val == "Aktif":
            status_widget.setStyleSheet(theme_qss(
                "font-size:14px; font-weight:700; color:@success; padding:2px 10px;"
            ))
        else:
            status_widget.setStyleSheet(theme_qss(
                "font-size:14px; font-weight:700; color:@danger; padding:2px 10px;"
            ))

        self.content_layout.addLayout(form)

        account_id = _to_int(self._v(self.account_row, 0, 0), 0)
        history_title = QLabel("Son Hareketler")
        history_title.setStyleSheet(theme_qss("font-size:15px; font-weight:800; color:@text; margin-top:10px;"))
        self.content_layout.addWidget(history_title)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Tarih", "Tür", "Kategori", "Tutar", "Açıklama"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setMinimumHeight(160)
        self.content_layout.addWidget(self.history_table)
        self._load_history(account_id)

        self.add_button("Kapat", "default", self.accept)

    def _col_idx(self, name, fallback):
        try:
            return self._cols.index(name)
        except ValueError:
            return fallback

    def _row_currency(self):
        idx = self._col_idx("currency", 6)
        return str(self._v(self.account_row, idx, "TRY") or "TRY").upper()

    def _row_balance(self):
        idx = self._col_idx("current_balance", 9 if len(self.account_row) > 9 else 6)
        return _to_float(self._v(self.account_row, idx, 0.0), 0.0)

    def _row_active(self):
        idx = self._col_idx("is_active", 7 if len(self.account_row) > 7 else 1)
        return _to_int(self._v(self.account_row, idx, 1), 1) == 1

    def _load_history(self, account_id):
        self.history_table.setRowCount(0)
        if not account_id:
            return
        try:
            cur = self.db.conn.cursor()
            cols = self.db._get_table_columns("accounting") if hasattr(self.db, "_get_table_columns") else []
            if "bank_account_id" not in cols:
                return
            amount_col = "try_equivalent" if "try_equivalent" in cols else "amount"
            curr_col = "currency" if "currency" in cols else "NULL"
            query = (
                f"SELECT date, type, category, COALESCE({amount_col}, amount), description, COALESCE({curr_col}, 'TRY') "
                "FROM accounting WHERE bank_account_id=? ORDER BY date DESC, id DESC LIMIT 50"
            )
            cur.execute(query, (account_id,))
            rows = cur.fetchall() or []
            for row in rows:
                r = self.history_table.rowCount()
                self.history_table.insertRow(r)
                self.history_table.setItem(r, 0, QTableWidgetItem(str(row[0] or "")))
                self.history_table.setItem(r, 1, QTableWidgetItem(str(row[1] or "")))
                self.history_table.setItem(r, 2, QTableWidgetItem(str(row[2] or "")))
                amt = _to_float(row[3], 0.0)
                row_curr = str(row[5]) if len(row) > 5 else CurrencyHelper.get_code(self.db)
                amount_text = CurrencyHelper.format_amount(amt, db=self.db, currency_code=row_curr)
                self.history_table.setItem(r, 3, QTableWidgetItem(amount_text))
                self.history_table.setItem(r, 4, QTableWidgetItem(str(row[4] or "")))
        except Exception:
            pass


class TransferDialog(BaseModernDialog):
    def __init__(self, db, from_account_row, all_accounts, parent=None):
        super().__init__(parent=parent, title="Hesaplar Arası Transfer", width=560, height=440)
        self.db = db
        self.from_row = from_account_row
        self.all_accounts = all_accounts
        self._cols = list(self.db._get_table_columns("bank_accounts") or []) if hasattr(self.db, "_get_table_columns") else []
        self._build()

    @staticmethod
    def _v(row, idx, default=""):
        if not row or idx >= len(row):
            return default
        value = row[idx]
        return default if value is None else value

    def _build(self):
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(14)

        from_id = _to_int(self._v(self.from_row, 0, 0), 0)
        from_name = str(self._v(self.from_row, 1, "")) + " - " + str(self._v(self.from_row, 3, ""))
        from_balance = self._row_balance(self.from_row)
        from_currency = self._row_currency(self.from_row)

        lbl_from = QLabel(from_name)
        lbl_from.setStyleSheet(theme_qss("font-size:14px; font-weight:700; color:@text;"))
        form.addRow("Kaynak Hesap:", lbl_from)

        lbl_balance = QLabel(CurrencyHelper.format_amount(from_balance, db=self.db, currency_code=from_currency))
        lbl_balance.setStyleSheet(theme_qss("font-size:13px; color:@text_muted;"))
        form.addRow("Mevcut Bakiye:", lbl_balance)

        self.cmb_target = QComboBox()
        self.cmb_target.setMinimumHeight(38)
        self._target_ids = []
        for acc in self.all_accounts:
            acc_id = _to_int(self._v(acc, 0, 0), 0)
            is_active = 1 if self._row_active(acc) else 0
            if acc_id == from_id or is_active != 1:
                continue
            display = f"{self._v(acc, 1, '')} - {self._v(acc, 3, '')} ({self._v(acc, 5, '')}) [{self._row_currency(acc)}]"
            self.cmb_target.addItem(display)
            self._target_ids.append(acc_id)
        form.addRow("Hedef Hesap:", self.cmb_target)

        self.inp_amount = QDoubleSpinBox()
        self.inp_amount.setMinimum(0.01)
        self.inp_amount.setMaximum(from_balance if from_balance > 0 else 999999999.99)
        self.inp_amount.setDecimals(2)
        self.inp_amount.setSuffix(f" {CurrencyHelper.get_symbol(self.db, from_currency)}")
        self.inp_amount.setMinimumHeight(38)
        form.addRow("Tutar:", self.inp_amount)

        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Açıklama (isteğe bağlı)")
        self.inp_desc.setMinimumHeight(38)
        self.inp_desc.setStyleSheet(
            theme_qss(
                "background:@surface; color:@text; border:1px solid @border; border-radius:8px; padding:6px 10px;"
            )
        )
        form.addRow("Açıklama:", self.inp_desc)

        self.content_layout.addLayout(form)
        self.add_cancel_button("İptal")
        self.add_button("Transfer Et", "success", self._execute_transfer)

    def _col_idx(self, name, fallback):
        try:
            return self._cols.index(name)
        except ValueError:
            return fallback

    def _row_currency(self, row):
        idx = self._col_idx("currency", 6)
        return str(self._v(row, idx, "TRY") or "TRY").upper()

    def _row_balance(self, row):
        idx = self._col_idx("current_balance", 9 if len(row) > 9 else 6)
        return _to_float(self._v(row, idx, 0.0), 0.0)

    def _row_active(self, row):
        idx = self._col_idx("is_active", 7 if len(row) > 7 else 1)
        return _to_int(self._v(row, idx, 1), 1) == 1

    def _execute_transfer(self):
        if not self._target_ids:
            show_error(self, "Hedef hesap seçilmedi.")
            return

        idx = self.cmb_target.currentIndex()
        if idx < 0 or idx >= len(self._target_ids):
            show_error(self, "Geçersiz hedef hesap.")
            return

        to_id = self._target_ids[idx]
        from_id = _to_int(self._v(self.from_row, 0, 0), 0)
        amount = self.inp_amount.value()
        desc = self.inp_desc.text().strip()

        if amount <= 0:
            show_error(self, "Tutar sıfırdan büyük olmalıdır.")
            return

        if not hasattr(self.db, "transfer_between_accounts"):
            show_error(self, "Transfer özelliği desteklenmiyor.")
            return

        ok, msg = self.db.transfer_between_accounts(from_id, to_id, amount, desc)
        if ok:
            show_success(self, f"Transfer tamamlandi: {CurrencyHelper.format_amount(amount, db=self.db, currency_code=self._row_currency(self.from_row))}")
            self.accept()
        else:
            show_error(self, f"Transfer başarısız: {msg}")


class BankAccountsWidget(QWidget):
    def __init__(self, db, parent=None, auth_manager=None):
        super().__init__(parent)
        self.db = db
        self._auth = auth_manager
        self._all_rows = []
        self._bank_cols = []
        self._build_ui()
        self._apply_rbac()
        self.load_data()

    def _can_manage_bank(self):
        if not self._auth:
            return True
        user = getattr(self._auth, "current_user", None)
        if not user:
            return True
        from src.utils.role_utils import is_admin_role
        role = user.get("role", "") if isinstance(user, dict) else getattr(user, "role", "")
        return is_admin_role(role)

    def _apply_rbac(self):
        if not self._can_manage_bank():
            for btn in (self.btn_add, self.btn_import):
                if hasattr(self, btn.__class__.__name__):
                    pass
                btn.setEnabled(False)
                btn.setToolTip("Bu işlem için yetkiniz yok")

    @staticmethod
    def _val(row, idx, default=""):
        if not row or idx >= len(row):
            return default
        value = row[idx]
        return default if value is None else value

    def _col_idx(self, name, fallback):
        try:
            return self._bank_cols.index(name)
        except ValueError:
            return fallback

    def _row_currency(self, row):
        idx = self._col_idx("currency", 6)
        return str(self._val(row, idx, "TRY") or "TRY").upper()

    def _row_balance(self, row):
        idx = self._col_idx("current_balance", 9 if len(row) > 9 else 6)
        return _to_float(self._val(row, idx, 0.0), 0.0)

    def _row_active(self, row):
        idx = self._col_idx("is_active", 7 if len(row) > 7 else 1)
        return _to_int(self._val(row, idx, 1), 1)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        top_card = QFrame()
        top_card.setObjectName("BankAccountsTopCard")
        top_card.setStyleSheet(theme_qss("QFrame#BankAccountsTopCard{background:@surface; border:1px solid @border; border-radius:12px;}"))
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(16, 16, 16, 16)

        left = QVBoxLayout()
        title = QLabel("Banka Hesapları")
        title.setStyleSheet(theme_qss("font-size:28px; font-weight:800; color:@text;"))
        subtitle = QLabel("Hesapları yönetin, bakiyeleri ve işlemleri tek ekranda takip edin.")
        subtitle.setStyleSheet(theme_qss("font-size:13px; color:@text_muted;"))
        left.addWidget(title)
        left.addWidget(subtitle)
        top_layout.addLayout(left, 1)

        actions = QHBoxLayout()
        self.btn_add = QPushButton("Yeni Hesap")
        self.btn_refresh = QPushButton("Yenile")
        self.btn_import = QPushButton("İçe Aktar")
        self.btn_export = QPushButton("Dışa Aktar")
        self.btn_add.setStyleSheet(
            theme_qss(
                "QPushButton{background:@accent;color:@selection_text;border:none;border-radius:9px;padding:10px 16px;font-weight:700;}"
                "QPushButton:hover{background:@accent_hover;}"
            )
        )
        for b in (self.btn_refresh, self.btn_import, self.btn_export):
            b.setStyleSheet(
                theme_qss(
                    "QPushButton{background:@surface_alt;color:@text;border:1px solid @border;border-radius:9px;padding:10px 16px;font-weight:700;}"
                    "QPushButton:hover{background:@surface;}"
                )
            )
        for b in (self.btn_add, self.btn_refresh, self.btn_import, self.btn_export):
            actions.addWidget(b)
        top_layout.addLayout(actions)
        root.addWidget(top_card)

        kpi_row = QHBoxLayout()
        self.lbl_total_accounts = QLabel("0")
        self.lbl_active_accounts = QLabel("0")
        self.lbl_total_balance = QLabel(CurrencyHelper.format_amount(0, db=self.db, currency_code=CurrencyHelper.get_code(self.db)))

        def make_kpi(title_text, value_lbl):
            card = QFrame()
            card.setObjectName("BankAccountsKpiCard")
            card.setStyleSheet(theme_qss("QFrame#BankAccountsKpiCard{background:@surface; border:1px solid @border; border-radius:12px;}"))
            lay = QVBoxLayout(card)
            cap = QLabel(title_text)
            cap.setStyleSheet(theme_qss("font-size:12px; color:@text_muted;"))
            value_lbl.setStyleSheet(theme_qss("font-size:26px; font-weight:800; color:@text;"))
            lay.addWidget(cap)
            lay.addWidget(value_lbl)
            return card

        kpi_row.addWidget(make_kpi("Toplam Hesap", self.lbl_total_accounts))
        kpi_row.addWidget(make_kpi("Aktif Hesap", self.lbl_active_accounts))
        kpi_row.addWidget(make_kpi("Toplam Bakiye", self.lbl_total_balance))
        root.addLayout(kpi_row)

        list_card = QFrame()
        list_card.setObjectName("BankAccountsListCard")
        list_card.setStyleSheet(theme_qss("QFrame#BankAccountsListCard{background:@surface; border:1px solid @border; border-radius:12px;}"))
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(12, 12, 12, 12)

        list_title = QLabel("Hesap Listesi")
        list_title.setStyleSheet(theme_qss("font-size:18px; font-weight:800; color:@text;"))
        list_layout.addWidget(list_title)

        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Banka, şube, hesap adı, hesap no, IBAN")
        self.search.setMinimumHeight(38)
        self.search.setStyleSheet(theme_qss("background:@surface_alt; color:@text; border:1px solid @border; border-radius:8px; padding:6px 10px;"))
        self.filter_status = QComboBox()
        self.filter_status.addItems(["Tümü", "Aktif", "Pasif"])
        self.filter_status.setMinimumHeight(38)
        self.lbl_count = QLabel("0 sonuç")
        self.btn_bulk_toggle = QPushButton("Seçileni Pasifleştir/Aktifleştir")
        self.btn_bulk_delete = QPushButton("Seçileni Sil")
        self.btn_bulk_toggle.setStyleSheet(
            theme_qss("QPushButton{background:@surface_alt;color:@text;border:1px solid @border;border-radius:8px;padding:8px 12px;font-weight:700;}")
        )
        self.btn_bulk_delete.setStyleSheet(
            theme_qss("QPushButton{background:@danger;color:@selection_text;border:none;border-radius:8px;padding:8px 12px;font-weight:700;}")
        )
        filters.addWidget(self.search, 1)
        filters.addWidget(self.filter_status)
        filters.addWidget(self.btn_bulk_toggle)
        filters.addWidget(self.btn_bulk_delete)
        filters.addWidget(self.lbl_count)
        list_layout.addLayout(filters)

        summary = QFrame()
        summary.setObjectName("BankAccountsSummary")
        summary.setStyleSheet(theme_qss("QFrame#BankAccountsSummary{background:@surface_alt; border:1px solid @border; border-radius:10px;}"))
        sg = QGridLayout(summary)
        sg.setContentsMargins(10, 10, 10, 10)
        sg.addWidget(QLabel("Seçili Hesap Özeti"), 0, 0, 1, 2)

        self.sum_bank = QLabel("-")
        self.sum_name = QLabel("-")
        self.sum_iban = QLabel("-")
        self.sum_balance = QLabel("-")
        self.sum_status = QLabel("-")
        rows = [("Banka", self.sum_bank), ("Hesap", self.sum_name), ("IBAN", self.sum_iban), ("Bakiye", self.sum_balance), ("Durum", self.sum_status)]
        for i, (key, val_lbl) in enumerate(rows, start=1):
            k_lbl = QLabel(key)
            k_lbl.setStyleSheet(theme_qss("font-weight:700; color:@text_muted;"))
            val_lbl.setStyleSheet(theme_qss("color:@text;"))
            sg.addWidget(k_lbl, i, 0)
            sg.addWidget(val_lbl, i, 1)
        list_layout.addWidget(summary)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Banka", "Şube", "Hesap Adı", "Hesap No", "IBAN", "Bakiye"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setColumnHidden(0, True)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        list_layout.addWidget(self.table)
        self.accounts_empty_state = EmptyState(
            "Henüz banka hesabı yok",
            "Bu filtrede gösterilecek banka hesabı bulunamadı.",
            parent=self,
        )
        self.accounts_empty_state.hide()
        list_layout.addWidget(self.accounts_empty_state)

        history_title = QLabel("Bakiye Hareket Geçmişi")
        history_title.setStyleSheet(theme_qss("font-size:16px; font-weight:800; color:@text; margin-top:8px;"))
        list_layout.addWidget(history_title)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(["Tarih", "Tür", "Kategori", "Tutar", "Açıklama"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setMinimumHeight(180)
        list_layout.addWidget(self.history_table)
        self.history_empty_state = EmptyState(
            "Hareket geçmişi yok",
            "Seçili hesaba ait hareket kaydı bulunamadı.",
            parent=self,
        )
        self.history_empty_state.hide()
        list_layout.addWidget(self.history_empty_state)

        root.addWidget(list_card, 1)

        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_refresh.clicked.connect(self.load_data)
        self.btn_import.clicked.connect(self.import_accounts)
        self.btn_export.clicked.connect(self.export_accounts)
        self.search.textChanged.connect(self._apply_filters)
        self.filter_status.currentIndexChanged.connect(self._apply_filters)
        self.table.itemSelectionChanged.connect(self._sync_summary)
        self.table.customContextMenuRequested.connect(self._open_context_menu)
        self.table.itemDoubleClicked.connect(lambda *_: self.open_edit_dialog())
        self.btn_bulk_toggle.clicked.connect(self.bulk_toggle_selected)
        self.btn_bulk_delete.clicked.connect(self.bulk_delete_selected)

    def _selected_account_id(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return _to_int(item.text() if item else None, default=-1) if item else None

    def _selected_account_ids(self):
        ids = []
        selection = self.table.selectionModel()
        if not selection:
            return ids
        for mi in selection.selectedRows(0):
            ids.append(_to_int(mi.data(), default=-1))
        return [i for i in ids if i >= 0]

    def _selected_source_row(self):
        account_id = self._selected_account_id()
        if account_id is None or account_id < 0:
            return None
        for src in self._all_rows:
            if _to_int(self._val(src, 0, 0), 0) == account_id:
                return src
        return None

    def _wire_ui_signals(self):
        self.chk_active.stateChanged.connect(self._on_ui_widget_changed)
        self.cmb_target.currentIndexChanged.connect(self._on_ui_widget_changed)

    def load_data(self):
        self._bank_cols = list(self.db._get_table_columns("bank_accounts") or []) if hasattr(self.db, "_get_table_columns") else []
        self._all_rows = list(self.db.get_bank_accounts() or [])
        self._apply_filters()

    def _apply_filters(self):
        text = (self.search.text() or "").strip().lower()
        status_filter = self.filter_status.currentText()

        visible = []
        for row in self._all_rows:
            bank = str(self._val(row, 1, ""))
            branch = str(self._val(row, 2, ""))
            acc_name = str(self._val(row, 3, ""))
            acc_no = str(self._val(row, 4, ""))
            iban = str(self._val(row, 5, ""))
            status = self._row_active(row)

            if status_filter == "Aktif" and status != 1:
                continue
            if status_filter == "Pasif" and status == 1:
                continue

            haystack = " ".join([bank, branch, acc_name, acc_no, iban]).lower()
            if text and text not in haystack:
                continue
            visible.append(row)

        self.table.setRowCount(0)
        total_balance = 0.0
        display_currency = CurrencyHelper.get_code(self.db)
        active_count = 0

        for row in visible:
            r = self.table.rowCount()
            self.table.insertRow(r)

            rid = self._val(row, 0, "")
            bank = str(self._val(row, 1, ""))
            branch = str(self._val(row, 2, ""))
            acc_name = str(self._val(row, 3, ""))
            acc_no = str(self._val(row, 4, ""))
            iban = str(self._val(row, 5, ""))
            bal = self._row_balance(row)
            row_currency = self._row_currency(row)
            is_active = self._row_active(row)

            total_balance += CurrencyHelper.convert_amount(self.db, bal, row_currency, display_currency)
            if is_active == 1:
                active_count += 1

            self.table.setItem(r, 0, QTableWidgetItem(str(rid)))
            self.table.setItem(r, 1, QTableWidgetItem(bank))
            self.table.setItem(r, 2, QTableWidgetItem(branch))
            self.table.setItem(r, 3, QTableWidgetItem(acc_name))
            self.table.setItem(r, 4, QTableWidgetItem(acc_no))
            self.table.setItem(r, 5, QTableWidgetItem(iban))
            self.table.setItem(r, 6, QTableWidgetItem(CurrencyHelper.format_amount(bal, db=self.db, currency_code=row_currency)))

            if is_active != 1:
                for c in range(7):
                    item = self.table.item(r, c)
                    if item:
                        item.setForeground(qc("text_muted"))

        self.lbl_count.setText(f"{len(visible)} sonuç")
        self.lbl_total_accounts.setText(str(len(visible)))
        self.lbl_active_accounts.setText(str(active_count))
        self.lbl_total_balance.setText(CurrencyHelper.format_amount(total_balance, db=self.db, currency_code=display_currency))
        has_rows = self.table.rowCount() > 0
        self.table.setVisible(has_rows)
        self.accounts_empty_state.setVisible(not has_rows)

        if self.table.rowCount() > 0:
            self.table.selectRow(0)
        else:
            self._sync_summary()

    def _sync_summary(self):
        row = self.table.currentRow()
        if row < 0:
            self.sum_bank.setText("-")
            self.sum_name.setText("-")
            self.sum_iban.setText("-")
            self.sum_balance.setText("-")
            self.sum_status.setText("-")
            self.history_table.setRowCount(0)
            self.history_table.hide()
            self.history_empty_state.show()
            return

        item_bank = self.table.item(row, 1)
        item_name = self.table.item(row, 3)
        item_iban = self.table.item(row, 5)
        item_balance = self.table.item(row, 6)
        if item_bank is None or item_name is None or item_iban is None or item_balance is None:
            return
        self.sum_bank.setText(item_bank.text())
        self.sum_name.setText(item_name.text())
        self.sum_iban.setText(item_iban.text())
        self.sum_balance.setText(item_balance.text())

        rid = self._selected_account_id()
        status_text = "Aktif"
        for src in self._all_rows:
            if _to_int(self._val(src, 0, 0), 0) == rid:
                status_text = "Aktif" if self._row_active(src) == 1 else "Pasif"
                break
        self.sum_status.setText(status_text)
        self._load_history(rid)

    def _load_history(self, account_id):
        self.history_table.setRowCount(0)
        if account_id is None:
            return

        cur = self.db.conn.cursor()
        cols = self.db._get_table_columns("accounting") if hasattr(self.db, "_get_table_columns") else []
        if "bank_account_id" not in cols:
            return

        amount_col = "try_equivalent" if "try_equivalent" in cols else "amount"
        curr_col = "currency" if "currency" in cols else "NULL"
        query = (
            f"SELECT date, type, category, COALESCE({amount_col}, amount), description, COALESCE({curr_col}, 'TRY') "
            "FROM accounting WHERE bank_account_id=? ORDER BY date DESC, id DESC LIMIT 200"
        )
        cur.execute(query, (account_id,))
        rows = cur.fetchall() or []
        for row in rows:
            r = self.history_table.rowCount()
            self.history_table.insertRow(r)
            self.history_table.setItem(r, 0, QTableWidgetItem(str(row[0] or "")))
            self.history_table.setItem(r, 1, QTableWidgetItem(str(row[1] or "")))
            self.history_table.setItem(r, 2, QTableWidgetItem(str(row[2] or "")))
            amt = _to_float(row[3], 0.0)
            row_curr = str(row[5]) if len(row) > 5 else CurrencyHelper.get_code(self.db)
            amount_text = CurrencyHelper.format_amount(amt, db=self.db, currency_code=row_curr)
            self.history_table.setItem(r, 3, QTableWidgetItem(amount_text))
            self.history_table.setItem(r, 4, QTableWidgetItem(str(row[4] or "")))
        has_rows = self.history_table.rowCount() > 0
        self.history_table.setVisible(has_rows)
        self.history_empty_state.setVisible(not has_rows)

    def _open_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=105):
            return
        row = self.table.rowAt(position.y())
        if row >= 0:
            self.table.selectRow(row)
        selected_ids = self._selected_account_ids()
        if not selected_ids:
            return

        menu = QMenu(self)
        act_detail = menu.addAction("Detay Gör")
        act_edit = menu.addAction("Düzenle")
        act_transfer = menu.addAction("Transfer Yap")
        src = self._selected_source_row()
        is_active = _to_int(self._val(src, 7, 1), 1) == 1 if src else True
        act_toggle = menu.addAction("Pasifleştir" if is_active else "Aktifleştir")
        act_delete = menu.addAction("Sil")
        menu.addSeparator()
        act_bulk_toggle = menu.addAction("Çoklu Pasifleştir/Aktifleştir")
        act_bulk_delete = menu.addAction("Çoklu Sil")

        if not self._can_manage_bank():
            for a in (act_edit, act_transfer, act_toggle, act_delete, act_bulk_toggle, act_bulk_delete):
                a.setEnabled(False)

        action = menu.exec(self.table.viewport().mapToGlobal(position))
        if action == act_detail:
            self._show_account_detail()
        elif action == act_edit:
            self.open_edit_dialog()
        elif action == act_transfer:
            self._open_transfer_dialog()
        elif action == act_toggle:
            self.toggle_account_active()
        elif action == act_delete:
            self.delete_selected_account()
        elif action == act_bulk_toggle:
            self.bulk_toggle_selected()
        elif action == act_bulk_delete:
            self.bulk_delete_selected()

    def _show_account_detail(self):
        src = self._selected_source_row()
        if not src:
            return
        dlg = AccountDetailDialog(self.db, src, self)
        dlg.exec()

    def _open_transfer_dialog(self):
        src = self._selected_source_row()
        if not src:
            return
        active_accounts = [
            r for r in self._all_rows
            if self._row_active(r) == 1
        ]
        if len(active_accounts) < 2:
            show_error(self, "Transfer için en az 2 aktif hesap gereklidir.")
            return
        dlg = TransferDialog(self.db, src, active_accounts, self)
        if dlg.exec():
            self.load_data()

    def open_edit_dialog(self):
        src = self._selected_source_row()
        if not src:
            return
        dlg = EditBankAccountDialog(self.db, src, self)
        if dlg.exec():
            show_success(self, "Hesap güncellendi.")
            self.load_data()

    def toggle_account_active(self):
        src = self._selected_source_row()
        if not src:
            return
        account_id = _to_int(self._val(src, 0, 0), 0)
        current = self._row_active(src) == 1
        if hasattr(self.db, "set_bank_account_active") and self.db.set_bank_account_active(account_id, not current):
            show_success(self, "Hesap durumu güncellendi.")
            self.load_data()
        else:
            show_error(self, "Hesap durumu güncellenemedi.")

    def delete_selected_account(self):
        src = self._selected_source_row()
        if not src:
            return
        account_id = _to_int(self._val(src, 0, 0), 0)
        bank_name = str(self._val(src, 1, ""))
        dlg = SimpleConfirmDialog(
            self, 
            title="Banka Hesabı Sil", 
            text=f"'{bank_name}' hesabını silmek istediğinize emin misiniz?\nBu işlem geri alınamaz.",
            ok_text="Evet, Sil",
            cancel_text="Vazgeç"
        )
        if not dlg.exec():
            return
        ok = self.db.delete_bank_account(account_id)
        if ok:
            show_success(self, "Hesap silindi.")
            self.load_data()
        else:
            show_error(self, "Hesap silinemedi.")

    def bulk_toggle_selected(self):
        ids = self._selected_account_ids()
        if not ids:
            show_error(self, "Lütfen en az bir hesap seçin.")
            return
        changed = 0
        for account_id in ids:
            src = next((r for r in self._all_rows if _to_int(self._val(r, 0, 0), 0) == account_id), None)
            if not src:
                continue
            current = self._row_active(src) == 1
            if hasattr(self.db, "set_bank_account_active") and self.db.set_bank_account_active(account_id, not current):
                changed += 1
        if changed:
            show_success(self, f"{changed} hesap durumu güncellendi.")
            self.load_data()
        else:
            show_error(self, "Seçili hesaplar güncellenemedi.")

    def bulk_delete_selected(self):
        ids = self._selected_account_ids()
        if not ids:
            show_error(self, "Lütfen en az bir hesap seçin.")
            return
        dlg = SimpleConfirmDialog(
            self,
            title="Çoklu Sil",
            text=f"Seçilen {len(ids)} hesabı silmek istediğinize emin misiniz?\nBu işlem tüm seçili hesapları silecektir.",
            ok_text="Evet, Hepsini Sil",
            cancel_text="Vazgeç"
        )
        if not dlg.exec():
            return
        deleted = 0
        for account_id in ids:
            if self.db.delete_bank_account(account_id):
                deleted += 1
        if deleted:
            show_success(self, f"{deleted} hesap silindi.")
            self.load_data()
        else:
            show_error(self, "Seçili hesaplar silinemedi.")

    def import_accounts(self):
        try:
            from PyQt6.QtWidgets import QFileDialog
            from src.ui.utils.ui_helpers import show_success, show_error
            path, _ = QFileDialog.getOpenFileName(
                self, "Banka Hesapları İçe Aktar", "", "Excel Dosyası (*.xlsx *.xls)",
            )
            if not path: return

            import pandas as pd
            import numpy as np

            df = None
            if path.endswith(".csv"):
                for enc in ["utf-8-sig", "utf-8", "cp1254", "latin-1"]:
                    for sep in [",", ";", "\t"]:
                        try:
                            temp_df = pd.read_csv(path, sep=sep, encoding=enc, dtype=str, keep_default_na=False)
                            if len(temp_df.columns) > 1 or (len(temp_df.columns) == 1 and sep == ","):
                                df = temp_df
                                break
                        except Exception:
                            pass
                    if df is not None: break
                if df is None:
                    try: df = pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig", dtype=str)
                    except Exception:
                        show_error(self, "CSV dosyası okunamadı.")
                        return
            else:
                try: df = pd.read_excel(path, dtype=str, keep_default_na=False)
                except Exception as e:
                    show_error(self, f"Excel okunamadı: {e}")
                    return

            if df is None or df.empty:
                show_error(self, "Dosya boş veya okunamadı.")
                return

            def _norm_col(c):
                c = str(c).lower().strip()
                for src_char, dst_char in [("ı","i"),("ğ","g"),("ü","u"),("ş","s"),("ö","o"),("ç","c")]:
                    c = c.replace(src_char, dst_char)
                return c.replace("_", " ").replace("-", " ")

            col_map = {
                "banka": "bank_name", "bank": "bank_name", "bank name": "bank_name", "banka adi": "bank_name",
                "sube": "branch_name", "branch": "branch_name", "branch name": "branch_name", "sube adi": "branch_name",
                "hesap": "account_name", "account": "account_name", "account name": "account_name", "hesap adi": "account_name",
                "hesap no": "account_no", "account no": "account_no", "account number": "account_no",
                "iban": "iban",
                "para birimi": "currency", "currency": "currency", "doviz": "currency", "döviz": "currency",
                "bakiye": "current_balance", "balance": "current_balance", "current balance": "current_balance", "tutar": "current_balance"
            }

            header_found = False
            matched_cols = {}
            for col in df.columns:
                n = _norm_col(col)
                if n in col_map:
                    matched_cols[col_map[n]] = str(col)
                    
            if "bank_name" in matched_cols or "iban" in matched_cols:
                header_found = True
            else:
                for idx, row in df.head(10).iterrows():
                    test_matched = {}
                    for col in df.columns:
                        n = _norm_col(row[col])
                        if n in col_map:
                            test_matched[col_map[n]] = str(col)
                    if "bank_name" in test_matched or "iban" in test_matched:
                        matched_cols = test_matched
                        header_found = True
                        df = df.iloc[idx+1:].reset_index(drop=True)
                        break

            if not header_found or ("bank_name" not in matched_cols and "iban" not in matched_cols):
                show_error(self, "Dosyada uygun başlıklar ('Banka', 'IBAN' vb.) bulunamadı!")
                return

            def parse_val(val, to_type=float):
                if val is None: return 0 if to_type in (int, float) else ""
                try:
                    if pd.isna(val): return 0 if to_type in (int, float) else ""
                except Exception:
                    pass
                val_str = str(val).strip()
                if not val_str or val_str.lower() in ["nan", "nat", "null", "none"]:
                    return 0 if to_type in (int, float) else ""
                if to_type in (int, float):
                    val_str = val_str.replace(".", "").replace(",", ".") if "," in val_str and "." in val_str else val_str.replace(",", ".")
                    try: return to_type(float(val_str))
                    except (ValueError, TypeError):
                        return 0 if to_type is int else 0.0
                return val_str

            success, fails = 0, 0
            for _, row in df.iterrows():
                try:
                    bank_col = matched_cols.get("bank_name")
                    bank = str(row[bank_col]).strip() if bank_col and pd.notnull(row[bank_col]) else ""
                    iban_col = matched_cols.get("iban")
                    iban = str(row[iban_col]).strip() if iban_col and pd.notnull(row[iban_col]) else ""
                    
                    if not bank and not iban: continue

                    self.db.add_bank_account(
                        bank or "Bilinmeyen Banka",
                        str(row[matched_cols["branch_name"]]).strip() if "branch_name" in matched_cols and pd.notnull(row[matched_cols["branch_name"]]) else "",
                        str(row[matched_cols["account_name"]]).strip() if "account_name" in matched_cols and pd.notnull(row[matched_cols["account_name"]]) else bank,
                        str(row[matched_cols["account_no"]]).strip() if "account_no" in matched_cols and pd.notnull(row[matched_cols["account_no"]]) else "",
                        iban,
                        parse_val(row[matched_cols["current_balance"]], float) if "current_balance" in matched_cols else 0.0,
                        str(row[matched_cols["currency"]]).strip().upper() if "currency" in matched_cols and pd.notnull(row[matched_cols["currency"]]) else CurrencyHelper.get_code(self.db)
                    )
                    success += 1
                except Exception:
                    fails += 1
            
            show_success(self, f"İçe aktarma tamamlandı.\nBaşarılı: {success}\nHatalı: {fails}")
            self.load_data()
        except Exception as e:
            show_error(self, f"İçe Aktarma Hatası: {e}")

    def export_accounts(self):
        try:
            from PyQt6.QtWidgets import QFileDialog
            from src.ui.utils.ui_helpers import show_success, show_error, show_warning
            path, _ = QFileDialog.getSaveFileName(
                self, "Banka Hesapları Dışa Aktar", "banka_hesaplari.xlsx", "Excel Dosyası (*.xlsx)"
            )
            if not path:
                return

            if not self._all_rows:
                show_warning(self, "Dışa aktarılacak hesap bulunamadı.")
                return

            import pandas as pd
            
            dict_rows = []
            for s in self._all_rows:
                dict_rows.append({
                    "id": self._val(s, 0, 0),
                    "bank_name": self._val(s, 1, ""),
                    "branch_name": self._val(s, 2, ""),
                    "account_name": self._val(s, 3, ""),
                    "account_no": self._val(s, 4, ""),
                    "iban": self._val(s, 5, ""),
                    "currency": self._row_currency(s),
                    "current_balance": self._row_balance(s),
                    "is_active": self._row_active(s),
                })

            df = pd.DataFrame(dict_rows)
            rename_map = {
                "bank_name": "Banka", "branch_name": "Şube", "account_name": "Hesap Adı",
                "account_no": "Hesap No", "iban": "IBAN", "currency": "Para Birimi", "current_balance": "Bakiye",
                "is_active": "Aktiflik"
            }
            df = df.rename(columns=rename_map)
            keep_cols = [rename_map[k] for k in rename_map if rename_map[k] in df.columns]
            df = df[keep_cols]

            df.to_excel(path, index=False)
                
            show_success(self, f"Dışa aktarma tamamlandı:\n{path}")
        except Exception as e:
            show_error(self, f"Dışa Aktarma Hatası: {e}")
    def open_add_dialog(self):
        dlg = AddBankAccountDialog(self.db, self)
        if dlg.exec():
            self.load_data()

