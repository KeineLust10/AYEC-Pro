# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
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
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QDoubleSpinBox,
)

from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.widgets.empty_state import EmptyState
from src.ui.widgets.financial_reference_controls import ReferenceMetricValueLabel, FinancialReferenceIconButton
from src.utils.design_system import DesignTokens
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



class _LedgerDetailDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.text = ""


class _LedgerDetailLabel(QLabel):
    def __init__(self, text):
        super().__init__(text)
        self._detail_text = text
        self.setToolTip(text)
        self.setWordWrap(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        available = max(0, self.width() - 2 * self.margin())
        self.setText("\n".join(self.fontMetrics().elidedText(line, Qt.TextElideMode.ElideRight, available) for line in self._detail_text.splitlines()))


def _account_field(row, columns, names, fallback):
    if columns:
        for name in names:
            if name in columns:
                index = columns.index(name)
                value = row[index] if row and index < len(row) else None
                if value is not None and str(value).strip():
                    return str(value)
        return ""
    value = row[fallback] if row and fallback < len(row) else None
    return "" if value is None else str(value)


def _account_fields(row, columns):
    return tuple(_account_field(row, columns, names, index) for names, index in (
        (("bank_name", "bank"), 1),
        (("branch_name", "branch_code", "branch"), 2),
        (("account_name", "account_holder", "name"), 3),
        (("account_no", "account_number"), 4),
        (("iban",), 5),
    ))


def _account_edit_value(row, columns, names, fallback, entered):
    if entered != _account_field(row, columns, names, fallback).strip():
        return entered
    index = next((columns.index(name) for name in names if name in columns), fallback) if columns else fallback
    return row[index] if row and index < len(row) else None


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

        bank, branch, name, number, iban = _account_fields(self.account_row, self._cols)
        self.inp_bank = QLineEdit(bank)
        self.inp_branch = QLineEdit(branch)
        self.inp_name = QLineEdit(name)
        self.inp_no = QLineEdit(number)
        self.inp_iban = QLineEdit(iban)

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
        fields = (
            (("bank_name", "bank"), 1, self.inp_bank),
            (("branch_name", "branch_code", "branch"), 2, self.inp_branch),
            (("account_name", "account_holder", "name"), 3, self.inp_name),
            (("account_no", "account_number"), 4, self.inp_no),
            (("iban",), 5, self.inp_iban),
        )
        values = [_account_edit_value(self.account_row, self._cols, names, index, widget.text().strip()) for names, index, widget in fields]
        ok = self.db.update_bank_account(
            account_id,
            *values,
            self.inp_balance.value() if self.inp_balance.value() != self._row_balance() else None,
            None,
        )
        if not ok:
            show_error(self, "Hesap güncellenemedi.")
            return

        if hasattr(self.db, "set_bank_account_active") and self.chk_active.isChecked() != self._row_active():
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

        bank, branch, name, number, iban = _account_fields(self.account_row, self._cols)
        fields = [
            ("Hesap ID:", str(self._v(self.account_row, 0, "-"))),
            ("Banka:", bank or "-"),
            ("\u015eube:", branch or "-"),
            ("Hesap Ad\u0131:", name or "-"),
            ("Hesap No:", number or "-"),
            ("IBAN:", iban or "-"),
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
            curr_col = "COALESCE(currency, 'TRY')" if "currency" in cols else "'TRY'"
            if "try_equivalent" in cols:
                curr_col = f"CASE WHEN try_equivalent IS NOT NULL THEN 'TRY' ELSE {curr_col} END"
            where = "bank_account_id=?"
            if "is_deleted" in cols:
                where += " AND COALESCE(is_deleted,0)=0"
            query = (
                f"SELECT date,type,category,COALESCE({amount_col},amount),description,{curr_col} "
                f"FROM accounting WHERE {where} ORDER BY date DESC,id DESC LIMIT 50"
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
        bank, _, name, _, _ = _account_fields(self.from_row, self._cols)
        from_name = bank + " - " + name
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
            bank, _, name, _, iban = _account_fields(acc, self._cols)
            display = f"{bank} - {name} ({iban}) [{self._row_currency(acc)}]"
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


class StatementPreviewDialog(BaseModernDialog):
    def __init__(self, rows, parent=None):
        super().__init__(
            parent=parent, title="Banka Ekstresi \u00d6nizleme", width=850, height=560
        )
        self.rows = rows
        summary = QLabel(f"{len(rows)} hareket okundu. Kay\u0131tlar otomatik i\u015flenmedi.")
        summary.setStyleSheet(theme_qss("color:@finance_text_muted;font-size:12px;"))
        self.content_layout.addWidget(summary)
        table = QTableWidget(len(rows), 4)
        table.setHorizontalHeaderLabels([
            "Tarih", "Tutar", "Referans", "A\u00e7\u0131klama"
        ])
        table.verticalHeader().hide()
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        for index, row in enumerate(rows):
            for column, value in enumerate((
                row["date"], str(row["amount"]), row["reference"], row["description"]
            )):
                table.setItem(index, column, QTableWidgetItem(value))
        self.content_layout.addWidget(table)
        self.add_button("CSV D\u0131\u015fa Aktar", "secondary", self._export_csv)
        self.add_button("Kapat", "default", self.accept)

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Ekstreyi D\u0131\u015fa Aktar", "banka_ekstresi.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                output = csv.writer(handle)
                output.writerow(("Date", "Amount", "Reference", "Description"))
                for row in self.rows:
                    output.writerow((
                        row["date"], row["amount"], row["reference"], row["description"]
                    ))
        except OSError as exc:
            show_error(self, f"CSV yaz\u0131lamad\u0131: {exc}")


class BankAccountsWidget(QWidget):
    def __init__(self, db, parent=None, auth_manager=None):
        super().__init__(parent)
        self.db = db
        self._auth = auth_manager
        self._all_rows = []
        self._bank_cols = []
        self._history_kind = "all"
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

    def _account_text(self, row, names, fallback):
        return _account_field(row, self._bank_cols, names, fallback)

    def _account_display_fields(self, row):
        return _account_fields(row, self._bank_cols)

    def _set_account_view(self, table_view):
        self.account_cards_scroll.setVisible(not table_view)
        self.account_summary.setVisible(table_view)
        self.table.setVisible(table_view and self.table.rowCount() > 0)

    def _rebuild_account_cards(self, rows):
        while self.account_cards_layout.count():
            item = self.account_cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.account_card_buttons = {}
        def card_order(row):
            bank, _, name, number, _ = self._account_display_fields(row)
            identity = f"{bank} {name} {number}".casefold()
            kind = 2 if "pos" in identity else 1 if "kasa" in identity or "cash" in identity else 0
            return kind, _to_int(self._val(row, 0, 0))

        for row in sorted(rows, key=card_order):
            account_id = _to_int(self._val(row, 0, 0))
            bank, branch, name, number, iban = self._account_display_fields(row)
            button = QPushButton()
            button.setCheckable(True)
            button.setProperty("account_id", account_id)
            button.setObjectName("BankAccountCard")
            button.setAccessibleName(bank)
            button.setFixedHeight(96)
            button.setStyleSheet(theme_qss(
                "QPushButton#BankAccountCard{background:@finance_surface;border:1px solid transparent;border-radius:4px;}"
                "QPushButton#BankAccountCard:checked{border:1px solid @finance_primary;}"
                "QPushButton#BankAccountCard:hover{background:@finance_surface_alt;}"
                "QPushButton#BankAccountCard QLabel{background:transparent;border:none;color:@finance_text;}"
            ))
            layout = QGridLayout(button)
            layout.setContentsMargins(10, 8, 10, 8)
            layout.setVerticalSpacing(3)
            heading = QLabel(bank)
            heading.setTextFormat(Qt.TextFormat.PlainText)
            heading.setToolTip(bank)
            heading.setStyleSheet(theme_qss("font-size:13px;font-weight:700;color:@finance_text;"))
            status = QLabel("Aktif" if self._row_active(row) else "Pasif")
            status.setAlignment(Qt.AlignmentFlag.AlignRight)
            status.setStyleSheet(theme_qss("font-size:10px;color:@success;" if self._row_active(row) else "font-size:10px;color:@finance_text_muted;"))
            identity = QLabel(iban or name or number or "-")
            identity.setTextFormat(Qt.TextFormat.PlainText)
            identity.setToolTip(identity.text())
            identity.setStyleSheet(theme_qss("font-family:'JetBrains Mono','DejaVu Sans';font-size:10px;color:@finance_text_muted;"))
            caption = QLabel("Kullan\u0131labilir Bakiye")
            caption.setStyleSheet(theme_qss("font-size:10px;color:@finance_text_muted;"))
            kind = card_order(row)[0]
            amount = ReferenceMetricValueLabel(
                CurrencyHelper.format_amount(self._row_balance(row), db=self.db, currency_code=self._row_currency(row)),
                primary_size=20, primary_token="finance_tertiary" if kind == 2 else "finance_text",
            )
            if kind == 2:
                caption.setText("Blokajdaki Net Tutar")
            elif kind == 1:
                caption.setText("Kasa Mevcudu")
            layout.addWidget(heading, 0, 0)
            layout.addWidget(status, 0, 1)
            layout.addWidget(identity, 1, 0, 1, 2)
            layout.addWidget(caption, 2, 0, 1, 2)
            layout.addWidget(amount, 3, 0, 1, 2)
            button.setToolTip("\n".join((bank, branch, name, number, iban)))
            for label in button.findChildren(QLabel):
                label.setTextFormat(Qt.TextFormat.PlainText)
                label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            button.clicked.connect(lambda checked=False, rid=account_id: self._select_card_account(rid))
            self.account_cards_layout.addWidget(button)
            self.account_card_buttons[account_id] = button
        distribution = QFrame()
        distribution.setObjectName("BankFundDistribution")
        distribution.setStyleSheet(theme_qss("QFrame#BankFundDistribution{background:@finance_surface;border:none;border-radius:4px;}"))
        distribution_layout = QVBoxLayout(distribution)
        distribution_layout.setContentsMargins(8, 8, 8, 8)
        distribution_layout.setSpacing(4)
        heading = QLabel("FON DAGILIMI")
        heading.setStyleSheet(theme_qss("font-size:10px;font-weight:700;color:@finance_text_muted;"))
        distribution_layout.addWidget(heading)
        bar = QHBoxLayout()
        bar.setSpacing(0)
        legend = QHBoxLayout()
        legend.setSpacing(4)
        self.fund_distribution = {}
        display_currency = CurrencyHelper.get_code(self.db)
        for index, row in enumerate(sorted(rows, key=card_order)):
            amount = CurrencyHelper.convert_amount(self.db, self._row_balance(row), self._row_currency(row), display_currency)
            if amount <= 0:
                continue
            bank = self._account_display_fields(row)[0]
            account_id = _to_int(row[0])
            self.fund_distribution[account_id] = amount
            color = ("@finance_secondary", "@finance_primary", "@finance_text", "@finance_text_muted", "@finance_tertiary")[index % 5]
            segment = QFrame()
            segment.setFixedHeight(6)
            segment.setStyleSheet(theme_qss(f"background:{color};border:none;"))
            segment.setToolTip(bank + ": " + CurrencyHelper.format_amount(amount, db=self.db, currency_code=display_currency))
            bar.addWidget(segment, max(1, round(amount)))
            label = QLabel(bank.split()[0] if bank else "-")
            label.setToolTip(bank)
            label.setStyleSheet(theme_qss(f"font-size:9px;color:{color};"))
            legend.addWidget(label, 1)
        distribution_layout.addLayout(bar)
        distribution_layout.addLayout(legend)
        distribution.setToolTip("Pozitif hesap bakiyelerinin dagilimi")
        distribution.setVisible(bool(self.fund_distribution))
        self.account_cards_layout.addWidget(distribution)
        self.account_cards_layout.addStretch(1)

    def _select_card_account(self, account_id):
        for row in range(self.table.rowCount()):
            if _to_int(self.table.item(row, 0).text()) == account_id:
                self.table.selectRow(row)
                self._sync_summary()
                return

    def _build_ui(self):
        self.setObjectName("BankAccountsWidget")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(theme_qss(
            "QWidget#BankAccountsWidget{background:@finance_canvas;}"
            "QLabel{background:transparent;border:none;}"
        ))
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        top_card = QFrame()
        top_card.setObjectName("BankAccountsTopCard")
        top_card.setStyleSheet(theme_qss("QFrame#BankAccountsTopCard{background:@finance_canvas;border:none;border-radius:4px;}"))
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(0, 0, 0, 0)

        left = QVBoxLayout()
        title = QLabel("Hazine & Nakit Ak\u0131\u015f Kontrol\u00fc")
        title.setWordWrap(True)
        title.setStyleSheet(theme_qss("font-size:18px;font-weight:800;color:@finance_text;"))
        subtitle = QLabel("\u00c7oklu banka hesap bakiyeleri, fiziki kasalar, sanal POS blokajlar\u0131 ve virman mutabakat paneli")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(theme_qss("font-size:11px;color:@finance_text_muted;"))
        left.addWidget(title)
        left.addWidget(subtitle)
        top_layout.addLayout(left, 1)

        actions = QGridLayout()
        actions.setSpacing(4)
        self.btn_add = QPushButton("Yeni Hesap / Kasa")
        self.btn_statement = QPushButton("Banka Ekstresi (OFX/MT940)")
        self.btn_transfer = QPushButton("Virman & Transfer")
        self.btn_refresh = QPushButton("Yenile")
        self.btn_import = QPushButton("İçe Aktar")
        self.btn_export = QPushButton("Dışa Aktar")
        self.btn_add.setStyleSheet(
            theme_qss(
                "QPushButton{background:@accent;color:@selection_text;border:1px solid @finance_outline;border-radius:4px;padding:2px 6px;font-size:10px;font-weight:700;min-height:24px;}"
                "QPushButton:hover{background:@accent_hover;}"
            )
        )
        for b in (self.btn_statement, self.btn_transfer, self.btn_refresh, self.btn_import, self.btn_export):
            b.setStyleSheet(
                theme_qss(
                    "QPushButton{background:@finance_surface;color:@finance_text;border:1px solid @finance_outline;border-radius:4px;padding:2px 6px;font-size:10px;font-weight:700;min-height:24px;}"
                    "QPushButton:hover{background:@surface;}"
                )
            )
        for index, button in enumerate((self.btn_statement, self.btn_transfer, self.btn_add)):
            actions.addWidget(button, 0, index)
        more = QPushButton("Diger")
        more.setFixedWidth(52)
        more.setStyleSheet(theme_qss(
            "QPushButton{background:@finance_surface;color:@finance_text;"
            "border:1px solid @finance_outline;border-radius:4px;font-size:10px;min-height:24px;}"
        ))
        more_menu = QMenu(more)
        for label, button in (
            ("Yenile", self.btn_refresh),
            ("I\u00e7e Aktar", self.btn_import),
            ("D\u0131\u015fa Aktar", self.btn_export),
        ):
            more_menu.addAction(label, button.click)
        more.setMenu(more_menu)
        actions.addWidget(more, 0, 3)
        top_layout.addLayout(actions)
        root.addWidget(top_card)

        kpi_row = QHBoxLayout()
        self.lbl_total_accounts = QLabel("0")
        self.lbl_active_accounts = QLabel("0")
        self.lbl_total_balance = ReferenceMetricValueLabel(CurrencyHelper.format_amount(0, db=self.db, currency_code=CurrencyHelper.get_code(self.db)), primary_size=24, primary_token="finance_secondary")
        self.lbl_pos_balance = ReferenceMetricValueLabel(CurrencyHelper.format_amount(0, db=self.db, currency_code=CurrencyHelper.get_code(self.db)), primary_size=24, primary_token="finance_tertiary")
        self.lbl_bank_balance = ReferenceMetricValueLabel("-", primary_size=24)
        self.lbl_cash_balance = ReferenceMetricValueLabel("-", primary_size=24)

        def make_kpi(title_text, value_lbl, color="@finance_text"):
            card = QFrame()
            card.setObjectName("BankAccountsKpiCard")
            card.setStyleSheet(theme_qss("QFrame#BankAccountsKpiCard{background:@finance_surface;border:none;border-radius:4px;}"))
            lay = QVBoxLayout(card)
            lay.setContentsMargins(10, 10, 10, 10)
            lay.setSpacing(8)
            cap = QLabel(title_text)
            cap.setStyleSheet(theme_qss("font-size:10px;font-weight:700;color:@finance_text_muted;"))
            value_lbl.setStyleSheet(theme_qss(f"font-family:'JetBrains Mono','DejaVu Sans';font-size:24px;font-weight:800;color:{color};"))
            lay.addWidget(cap)
            lay.addWidget(value_lbl)
            card.setFixedHeight(94)
            return card

        kpi_row.addWidget(make_kpi("TOPLAM LIKIDITE & SICAK NAKIT", self.lbl_total_balance, "@finance_secondary"))
        kpi_row.addWidget(make_kpi("BANKA HESAP BAKIYELERI", self.lbl_bank_balance))
        kpi_row.addWidget(make_kpi("FIZIKI ATOLYE & SAHA KASALARI", self.lbl_cash_balance))
        kpi_row.addWidget(make_kpi("POS BLOKAJ & BEKLEYEN", self.lbl_pos_balance, "@finance_tertiary"))
        root.addLayout(kpi_row)

        list_card = QFrame()
        list_card.setObjectName("BankAccountsListCard")
        list_card.setStyleSheet(theme_qss("QFrame#BankAccountsListCard{background:@finance_canvas;border:none;}"))
        list_layout = QVBoxLayout(list_card)
        list_layout.setContentsMargins(0, 0, 0, 0)

        list_title = QLabel("Tan\u0131ml\u0131 Hesaplar & Kasalar")
        list_title.setStyleSheet(theme_qss("font-size:14px;font-weight:800;color:@finance_text;"))
        list_heading = QHBoxLayout()
        list_heading.addWidget(list_title, 1)
        self.btn_loans = QPushButton("Krediler")
        self.btn_loans.setFixedHeight(26)
        self.btn_loans.setStyleSheet(theme_qss(
            "QPushButton{background:@finance_surface;color:@finance_text;"
            "border:1px solid @finance_outline;border-radius:4px;padding:2px 8px;}"
        ))
        list_heading.addWidget(self.btn_loans)
        self.btn_account_table = QPushButton("Tablo")
        self.btn_account_table.setToolTip("Tablo / Toplu Se\u00e7im")
        self.btn_account_table.setCheckable(True)
        self.btn_account_table.setFixedHeight(26)
        self.btn_account_table.toggled.connect(self._set_account_view)
        list_heading.addWidget(self.btn_account_table)
        self.btn_account_filters = QPushButton("Filtre")
        self.btn_account_filters.setCheckable(True)
        self.btn_account_filters.setFixedHeight(26)
        list_heading.addWidget(self.btn_account_filters)

        self.account_filter_panel = QFrame()
        filters = QGridLayout(self.account_filter_panel)
        filters.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Banka, şube, hesap adı, hesap no, IBAN")
        self.search.setMinimumHeight(26)
        self.search.setStyleSheet(theme_qss("background:@surface_alt; color:@text; border:1px solid @border; border-radius:8px; padding:6px 10px;"))
        self.filter_status = QComboBox()
        self.filter_status.addItems(["Tümü", "Aktif", "Pasif"])
        self.filter_status.setMinimumHeight(26)
        self.lbl_count = QLabel("0 sonuç")
        self.btn_bulk_toggle = QPushButton("Seçileni Pasifleştir/Aktifleştir")
        self.btn_bulk_delete = QPushButton("Seçileni Sil")
        self.btn_bulk_toggle.setStyleSheet(
            theme_qss("QPushButton{background:@surface_alt;color:@text;border:1px solid @border;border-radius:8px;padding:8px 12px;font-weight:700;}")
        )
        self.btn_bulk_delete.setStyleSheet(
            theme_qss("QPushButton{background:@danger;color:@selection_text;border:none;border-radius:8px;padding:8px 12px;font-weight:700;}")
        )
        filters.addWidget(self.search, 0, 0, 1, 2)
        filters.addWidget(self.filter_status, 0, 2)
        filters.addWidget(self.btn_bulk_toggle, 1, 0, 1, 2)
        filters.addWidget(self.btn_bulk_delete, 1, 2)
        counts = QHBoxLayout()
        counts.addWidget(self.lbl_count)
        counts.addWidget(QLabel("Hesap:"))
        counts.addWidget(self.lbl_total_accounts)
        counts.addWidget(QLabel("Aktif:"))
        counts.addWidget(self.lbl_active_accounts)
        filters.addLayout(counts, 2, 0, 1, 3)
        self.account_filter_panel.hide()
        self.btn_account_filters.toggled.connect(self.account_filter_panel.setVisible)

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
        accounts_panel = QFrame()
        accounts_panel.setObjectName("BankAccountsColumn")
        accounts_panel.setStyleSheet(theme_qss(
            "QFrame#BankAccountsColumn{background:@finance_canvas;border:none;}"
        ))
        accounts_layout = QVBoxLayout(accounts_panel)
        accounts_layout.setContentsMargins(0, 0, 0, 0)
        accounts_layout.setSpacing(8)
        accounts_layout.addLayout(list_heading)
        accounts_layout.addWidget(self.account_filter_panel)
        accounts_layout.addWidget(summary)
        self.account_summary = summary
        summary.hide()
        self.account_cards_scroll = QScrollArea()
        self.account_cards_scroll.setWidgetResizable(True)
        self.account_cards_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.account_cards_scroll.setStyleSheet(theme_qss("QScrollArea{background:@finance_canvas;border:none;}"))
        self.account_cards_container = QWidget()
        self.account_cards_container.setStyleSheet(theme_qss("background:@finance_canvas;"))
        self.account_cards_layout = QVBoxLayout(self.account_cards_container)
        self.account_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.account_cards_layout.setSpacing(8)
        self.account_cards_scroll.setWidget(self.account_cards_container)
        accounts_layout.addWidget(self.account_cards_scroll, 1)

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
        accounts_layout.addWidget(self.table, 1)
        self.table.hide()
        self.accounts_empty_state = EmptyState(
            "Henüz banka hesabı yok",
            "Bu filtrede gösterilecek banka hesabı bulunamadı.",
            parent=self,
        )
        self.accounts_empty_state.hide()
        accounts_layout.addWidget(self.accounts_empty_state)

        movements_panel = QFrame()
        movements_panel.setObjectName("BankMovementsColumn")
        movements_panel.setStyleSheet(theme_qss(
            "QFrame#BankMovementsColumn{background:@finance_canvas;border:none;}"
        ))
        movements_layout = QVBoxLayout(movements_panel)
        movements_layout.setContentsMargins(0, 0, 0, 0)
        movements_layout.setSpacing(8)
        movement_filters = QGridLayout()
        movement_filters.setSpacing(4)
        self.history_filter_group = QButtonGroup(self)
        self.history_filter_buttons = {}
        for index, (kind, title) in enumerate((("all", "T\u00dcM HAREKETLER"), ("income", "GELEN HAVALE"), ("expense", "GIDEN GIDER"), ("cash", "KASA NAKIT"), ("pos", "POS BLOKE"))):
            button = QPushButton(title)
            button.setCheckable(True)
            button.setFixedHeight(26)
            button.setStyleSheet(theme_qss(
                "QPushButton{background:@finance_surface;color:@finance_text_muted;border:none;border-radius:4px;padding:2px;font-size:9px;font-weight:700;}"
                "QPushButton:checked{background:@finance_primary;color:@selection_text;}"
            ))
            button.clicked.connect(lambda checked=False, key=kind: self._set_history_kind(key))
            self.history_filter_group.addButton(button)
            self.history_filter_buttons[kind] = button
            movement_filters.addWidget(button, 0, index)
        self.history_filter_buttons["all"].setChecked(True)
        self.history_search = QLineEdit()
        self.history_search.setPlaceholderText("Fi\u015f, a\u00e7\u0131klama, hesap ara...")
        self.history_search.setFixedHeight(26)
        self.history_search.textChanged.connect(lambda: self._load_history(self._selected_account_id()))
        movement_filters.addWidget(self.history_search, 1, 0, 1, 3)
        self.history_selected_account = QCheckBox("Se\u00e7ili hesap")
        self.history_selected_account.toggled.connect(lambda: self._load_history(self._selected_account_id()))
        movement_filters.addWidget(self.history_selected_account, 1, 3, 1, 2)
        movements_layout.addLayout(movement_filters)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setItemDelegateForColumn(4, _LedgerDetailDelegate(self.history_table))
        self.history_table.setHorizontalHeaderLabels(["ZAMAN / FIS", "T\u00dcR", "KATEGORI", "TUTAR & Y\u00d6N", "ISLEM DETAYI & HESAP", "HESAP ID", "FIS ID", "AKSIYON"])
        self.history_table.horizontalHeader().moveSection(4, 1)
        self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.history_table.setColumnWidth(0, 100)
        self.history_table.setColumnWidth(3, 145)
        self.history_table.setColumnWidth(7, 62)
        for column in (1, 2, 5, 6):
            self.history_table.setColumnHidden(column, True)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.history_table.setStyleSheet(theme_qss(
            "QTableWidget{background:@finance_surface;color:@finance_text;alternate-background-color:@finance_surface_high;border:none;gridline-color:@finance_surface;}"
            "QTableWidget::item{padding:4px;border:none;border-bottom:1px solid @finance_surface_high;}"
            "QHeaderView::section{background:@finance_canvas;color:@finance_text_muted;border:none;padding:4px;font-size:9px;font-weight:700;}"
        ))
        self.history_table.setShowGrid(False)
        self.history_table.setAlternatingRowColors(False)
        self.history_table.horizontalHeader().setFixedHeight(30)
        self.history_table.verticalHeader().setDefaultSectionSize(48)
        movements_layout.addWidget(self.history_table)
        self.history_empty_state = EmptyState(
            "Hareket geçmişi yok",
            "Seçili hesaba ait hareket kaydı bulunamadı.",
            parent=self,
        )
        self.history_empty_state.hide()
        movements_layout.addWidget(self.history_empty_state)
        movements_layout.addStretch(1)

        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(accounts_panel, 41)
        body.addWidget(movements_panel, 59)
        list_layout.addLayout(body, 1)

        root.addWidget(list_card, 1)

        footer = QHBoxLayout()
        footer.setSpacing(8)
        status_footer = QHBoxLayout()
        for index, (title_text, detail_text, accent) in enumerate((
            ("Gunluk Mutabakat Durumu", "Ekstre eslestirme sonucu dogrulanmadi", "@finance_outline"),
            ("Otomatik Cari Tanima", "Otomatik eslestirme sonucu dogrulanmadi", "@finance_outline"),
            ("TCMB Doviz Durumu", "Kur zaman damgasi dogrulanmadi", "@finance_outline"),
        )):
            card = QFrame()
            card.setStyleSheet(theme_qss(
                f"QFrame {{ background: @finance_surface; border: 1px solid @finance_outline; "
                f"border-top: 2px solid {accent}; border-radius: 4px; }}"
            ))
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 6, 10, 6)
            heading = QLabel(title_text)
            heading.setStyleSheet(theme_qss("color: @finance_text; font-weight: 800; border: none;"))
            detail = QLabel(detail_text)
            detail.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px; border: none;"))
            card_layout.addWidget(heading)
            card_layout.addWidget(detail)
            if index < 2:
                status_footer.addWidget(card, 1)
            else:
                footer.addWidget(card, 1)
        movements_layout.insertLayout(movements_layout.count() - 1, status_footer)
        root.addLayout(footer)

        self.btn_add.clicked.connect(self.open_add_dialog)
        self.btn_statement.clicked.connect(self.import_statement)
        self.btn_transfer.clicked.connect(self._open_transfer_dialog)
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
            bank, branch, acc_name, acc_no, iban = self._account_display_fields(row)
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
        pos_balance = 0.0
        bank_balance = 0.0
        cash_balance = 0.0
        display_currency = CurrencyHelper.get_code(self.db)
        active_count = 0

        for row in visible:
            r = self.table.rowCount()
            self.table.insertRow(r)

            rid = self._val(row, 0, "")
            bank, branch, acc_name, acc_no, iban = self._account_display_fields(row)
            bal = self._row_balance(row)
            row_currency = self._row_currency(row)
            is_active = self._row_active(row)

            total_balance += CurrencyHelper.convert_amount(self.db, bal, row_currency, display_currency)
            account_kind = f"{bank} {acc_name} {acc_no}".casefold()
            if "pos" in account_kind:
                pos_balance += CurrencyHelper.convert_amount(self.db, bal, row_currency, display_currency)
            elif "kasa" in account_kind or "cash" in account_kind:
                cash_balance += CurrencyHelper.convert_amount(self.db, bal, row_currency, display_currency)
            else:
                bank_balance += CurrencyHelper.convert_amount(self.db, bal, row_currency, display_currency)
            if is_active == 1:
                active_count += 1

            self.table.setItem(r, 0, QTableWidgetItem(str(rid)))
            self.table.setItem(r, 1, QTableWidgetItem(bank))
            self.table.setItem(r, 2, QTableWidgetItem(branch))
            self.table.setItem(r, 3, QTableWidgetItem(acc_name))
            self.table.setItem(r, 4, QTableWidgetItem(acc_no))
            self.table.setItem(r, 5, QTableWidgetItem(iban))
            self.table.setItem(r, 6, QTableWidgetItem(CurrencyHelper.format_amount(bal, db=self.db, currency_code=row_currency)))
            for column in (0, 4, 5, 6):
                item = self.table.item(r, column)
                numeric_font = QFont(DesignTokens.MONO_FONT_NAME)
                numeric_font.setPixelSize(11)
                numeric_font.setBold(column == 6)
                item.setFont(numeric_font)
                item.setToolTip(item.text())

            if is_active != 1:
                for c in range(7):
                    item = self.table.item(r, c)
                    if item:
                        item.setForeground(qc("text_muted"))

        self.lbl_count.setText(f"{len(visible)} sonuç")
        self.lbl_total_accounts.setText(str(len(visible)))
        self.lbl_active_accounts.setText(str(active_count))
        self.lbl_total_balance.setText(CurrencyHelper.format_amount(total_balance, db=self.db, currency_code=display_currency))
        self.lbl_pos_balance.setText(CurrencyHelper.format_amount(pos_balance, db=self.db, currency_code=display_currency))
        self.lbl_bank_balance.setText(CurrencyHelper.format_amount(bank_balance, db=self.db, currency_code=display_currency))
        self.lbl_cash_balance.setText(CurrencyHelper.format_amount(cash_balance, db=self.db, currency_code=display_currency))
        self._rebuild_account_cards(visible)
        has_rows = self.table.rowCount() > 0
        self._set_account_view(self.btn_account_table.isChecked())
        self.accounts_empty_state.setVisible(not has_rows)

        if self.table.rowCount() > 0:
            self.table.selectRow(0)
        else:
            self._sync_summary()

    def _sync_summary(self):
        row = self.table.currentRow()
        selected_id = self._selected_account_id()
        for account_id, button in getattr(self, "account_card_buttons", {}).items():
            button.setChecked(account_id == selected_id)
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

    def _set_history_kind(self, kind):
        self._history_kind = kind
        self._load_history(self._selected_account_id())

    def _show_ledger_account(self, account_id):
        self._select_card_account(account_id)
        self._show_account_detail()

    def _filter_ledger_account(self, account_id):
        self._select_card_account(account_id)
        self.history_selected_account.setChecked(True)

    def _load_history(self, account_id):
        self.history_table.setRowCount(0)
        cur = self.db.conn.cursor()
        cols = self.db._get_table_columns("accounting") if hasattr(self.db, "_get_table_columns") else []
        if "bank_account_id" not in cols:
            self.history_table.hide()
            self.history_empty_state.show()
            return
        amount_col = "try_equivalent" if "try_equivalent" in cols else "amount"
        curr_col = "COALESCE(currency, 'TRY')" if "currency" in cols else "'TRY'"
        if "try_equivalent" in cols:
            curr_col = f"CASE WHEN try_equivalent IS NOT NULL THEN 'TRY' ELSE {curr_col} END"
        account_rows = {_to_int(row[0]): row for row in self._all_rows}
        params = list(account_rows)
        if self.history_selected_account.isChecked():
            params = [account_id] if account_id in account_rows else []
        if not params:
            self.history_table.hide()
            self.history_empty_state.show()
            return
        where = "bank_account_id IN (" + ",".join("?" for _ in params) + ")"
        if "is_deleted" in cols:
            where += " AND COALESCE(is_deleted, 0)=0"
        query = (
            f"SELECT date,type,category,COALESCE({amount_col},amount),description,{curr_col},bank_account_id,id "
            f"FROM accounting WHERE {where} ORDER BY date DESC,id DESC LIMIT 200"
        )
        cur.execute(query, params)
        search = self.history_search.text().strip().casefold()
        for row in cur.fetchall() or []:
            bank, _, name, number, _ = self._account_display_fields(account_rows[_to_int(row[6])])
            identity = f"{bank} {name} {number}".casefold()
            direction = str(row[1] or "").casefold()
            income = direction in ("gelir", "income", "credit", "tahsilat")
            expense = direction in ("gider", "expense", "debit")
            if self._history_kind == "income" and not income:
                continue
            if self._history_kind == "expense" and not expense:
                continue
            if self._history_kind == "cash" and not ("kasa" in identity or "cash" in identity):
                continue
            if self._history_kind == "pos" and "pos" not in identity:
                continue
            if search and search not in " ".join(str(value or "") for value in (*row, bank, name)).casefold():
                continue
            r = self.history_table.rowCount()
            self.history_table.insertRow(r)
            stamp = str(row[0] or "-")
            try:
                date = datetime.fromisoformat(stamp)
                display_stamp = date.strftime("%d.%m %H:%M" if "T" in stamp or " " in stamp else "%d.%m.%Y")
            except ValueError:
                display_stamp = stamp
            date_item = QTableWidgetItem(display_stamp + f"\n#{row[7]}")
            date_item.setData(Qt.ItemDataRole.UserRole, stamp)
            date_item.setToolTip(stamp)
            date_font = QFont(DesignTokens.MONO_FONT_NAME)
            date_font.setPixelSize(11)
            date_item.setFont(date_font)
            self.history_table.setItem(r, 0, date_item)
            self.history_table.setItem(r, 1, QTableWidgetItem(str(row[1] or "")))
            self.history_table.setItem(r, 2, QTableWidgetItem(str(row[2] or "")))
            amt = _to_float(row[3], 0.0)
            signed = -abs(amt) if expense else abs(amt) if income else amt
            amount_text = CurrencyHelper.format_amount(signed, db=self.db, currency_code=str(row[5]))
            amount_item = QTableWidgetItem(("+" if income else "") + amount_text)
            amount_item.setForeground(qc("finance_secondary" if income else "finance_tertiary" if expense else "finance_text"))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            amount_font = QFont(date_font)
            amount_font.setBold(True)
            amount_item.setFont(amount_font)
            amount_item.setToolTip(amount_item.text())
            self.history_table.setItem(r, 3, amount_item)
            self.history_table.setItem(r, 4, QTableWidgetItem(str(row[4] or "")))
            detail = _LedgerDetailLabel(str(row[4] or "-") + "\n" + " | ".join(str(value) for value in (row[1], row[2], bank) if value))
            detail.setTextFormat(Qt.TextFormat.PlainText)
            detail.setMargin(4)
            detail.setStyleSheet(theme_qss("font-size:11px;color:@finance_text;background:transparent;"))
            self.history_table.setCellWidget(r, 4, detail)
            self.history_table.setItem(r, 5, QTableWidgetItem(str(row[6])))
            self.history_table.setItem(r, 6, QTableWidgetItem(str(row[7])))
            actions = QWidget()
            action_layout = QHBoxLayout(actions)
            action_layout.setContentsMargins(2, 0, 2, 0)
            action_layout.setSpacing(2)
            for title, tooltip, callback in (
                ("?", "Hesap detay\u0131", self._show_ledger_account),
                (">", "Hesab\u0131n hareketlerini g\u00f6ster", self._filter_ledger_account),
            ):
                button = FinancialReferenceIconButton(
                    "ledger_account_detail" if title == "?" else "ledger_account_movements",
                    "document" if title == "?" else "transfer",
                )
                button.setFixedSize(24, 24)
                button.setToolTip(tooltip)
                button.setAccessibleName("ledger_account_detail" if title == "?" else "ledger_account_movements")
                button.setStyleSheet(theme_qss("QPushButton{background:transparent;color:@finance_text_muted;border:none;border-radius:4px;}QPushButton:hover{background:@finance_surface_alt;color:@finance_primary;}"))
                button.clicked.connect(lambda checked=False, rid=_to_int(row[6]), handler=callback: handler(rid))
                action_layout.addWidget(button)
            self.history_table.setCellWidget(r, 7, actions)
        has_rows = self.history_table.rowCount() > 0
        self.history_table.setFixedHeight(30 + min(8, self.history_table.rowCount()) * 48 + 2)
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

    def import_statement(self):
        from pathlib import Path
        from src.utils.bank_statement_parser import parse_bank_statement

        path, _ = QFileDialog.getOpenFileName(
            self, "Banka Ekstresi", "", "Statements (*.ofx *.mt940 *.sta *.txt)"
        )
        if not path:
            return
        try:
            source = Path(path)
            if source.stat().st_size > 10 * 1024 * 1024:
                raise ValueError("Ekstre dosyas\u0131 10 MB s\u0131n\u0131r\u0131n\u0131 a\u015f\u0131yor.")
            raw = source.read_bytes()
            for encoding in ("utf-8-sig", "cp1254", "latin-1"):
                try:
                    content = raw.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            rows = parse_bank_statement(content, source.suffix)
        except (OSError, ValueError) as exc:
            show_error(self, f"Ekstre okunamad\u0131: {exc}")
            return
        StatementPreviewDialog(rows, self).exec()

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

