# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QGridLayout,
    QWidget,
    QTabWidget,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QComboBox,
    QDateEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QFileDialog,
    QTimeEdit,
)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.design_system import DesignTokens
from src.utils.message_helper import show_error, show_warning



class BankCardDialog(BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, bank_account_id, card_data=None, parent=None):
        self.db = db
        self.bank_account_id = bank_account_id
        self.card_data = card_data or {}
        super().__init__(parent, title="Kredi Kartı", width=520, height=420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Kart Bilgileri")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @selection_text;"))
        layout.addWidget(title)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.txt_name = QLineEdit()
        self.txt_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.txt_last4 = QLineEdit()
        self.txt_last4.setMaxLength(4)
        self.txt_last4.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.spin_limit = QDoubleSpinBox()
        self.spin_limit.setRange(0, 1000000000)
        self.spin_limit.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
        DesignTokens.apply_spinbox_styles(self.spin_limit)

        self.spin_debt = QDoubleSpinBox()
        self.spin_debt.setRange(0, 1000000000)
        self.spin_debt.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
        DesignTokens.apply_spinbox_styles(self.spin_debt)

        self.spin_due_day = QSpinBox()
        self.spin_due_day.setRange(1, 31)
        DesignTokens.apply_spinbox_styles(self.spin_due_day)

        self.spin_statement_day = QSpinBox()
        self.spin_statement_day.setRange(1, 31)
        DesignTokens.apply_spinbox_styles(self.spin_statement_day)

        self.chk_active = QCheckBox("Aktif")
        self.chk_active.setChecked(True)

        form.addWidget(QLabel("Kart Adı"), 0, 0)
        form.addWidget(self.txt_name, 0, 1)
        form.addWidget(QLabel("Son 4 Hane"), 1, 0)
        form.addWidget(self.txt_last4, 1, 1)
        form.addWidget(QLabel("Limit"), 2, 0)
        form.addWidget(self.spin_limit, 2, 1)
        form.addWidget(QLabel("Güncel Borç"), 3, 0)
        form.addWidget(self.spin_debt, 3, 1)
        form.addWidget(QLabel("Son Ödeme Günü"), 4, 0)
        form.addWidget(self.spin_due_day, 4, 1)
        form.addWidget(QLabel("Ekstre Günü"), 5, 0)
        form.addWidget(self.spin_statement_day, 5, 1)
        form.addWidget(self.chk_active, 6, 1)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Kaydet")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        self.content_layout.addLayout(layout)
        self._load()

    def _load(self):
        if not self.card_data:
            return
        self.txt_name.setText(str(self.card_data.get("card_name") or ""))
        self.txt_last4.setText(str(self.card_data.get("card_last4") or ""))
        self.spin_limit.setValue(float(self.card_data.get("card_limit") or 0))
        self.spin_debt.setValue(float(self.card_data.get("current_debt") or 0))
        if self.card_data.get("due_day"):
            self.spin_due_day.setValue(int(self.card_data.get("due_day")))
        if self.card_data.get("statement_day"):
            self.spin_statement_day.setValue(int(self.card_data.get("statement_day")))
        self.chk_active.setChecked(int(self.card_data.get("is_active") or 0) == 1)

    def _save(self):
        name = self.txt_name.text().strip()
        last4 = self.txt_last4.text().strip()
        if not name:
            show_warning(self, "Uyarı", "Kart adı boş olamaz.")
            return
        if last4 and len(last4) != 4:
            show_warning(self, "Uyarı", "Son 4 hane 4 karakter olmalı.")
            return
        limit_val = float(self.spin_limit.value())
        debt_val = float(self.spin_debt.value())
        due_day = int(self.spin_due_day.value())
        statement_day = int(self.spin_statement_day.value())
        is_active = self.chk_active.isChecked()
        if self.card_data.get("id"):
            ok = self.db.update_bank_card(
                self.card_data.get("id"),
                name,
                last4,
                limit_val,
                debt_val,
                due_day,
                statement_day,
                is_active,
            )
        else:
            ok = self.db.add_bank_card(
                self.bank_account_id,
                name,
                last4,
                limit_val,
                debt_val,
                due_day,
                statement_day,
                is_active,
            )
        if ok:
            self.accept()
        else:
            show_error(self, "Hata", "Kart kaydedilemedi.")

class AlertEditDialog(BaseModernDialog):
    def __init__(self, db, alert, parent=None):
        self.db = db
        self.alert = alert if isinstance(alert, dict) else {}
        super().__init__(parent, title="Otomatik Ödeme Talimatı", width=420, height=260)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Talimat Düzenle")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @selection_text;"))
        layout.addWidget(title)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        self.txt_label = QLineEdit()
        self.txt_label.setReadOnly(True)
        self.txt_label.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm")
        self.time_edit.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.chk_active = QCheckBox("Aktif")
        self.chk_active.setChecked(True)

        form.addWidget(QLabel("Bildirim"), 0, 0)
        form.addWidget(self.txt_label, 0, 1)
        form.addWidget(QLabel("Saat"), 1, 0)
        form.addWidget(self.time_edit, 1, 1)
        form.addWidget(self.chk_active, 2, 1)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton("Vazgeç")
        btn_cancel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Kaydet")
        btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_save.clicked.connect(self._save)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        self.content_layout.addLayout(layout)
        self._load()

    def _load(self):
        self.txt_label.setText(str(self.alert.get("label") or ""))
        time_val = str(self.alert.get("time") or "")
        time_obj = QTime.fromString(time_val, "HH:mm")
        if not time_obj.isValid():
            time_obj = QTime.currentTime()
        self.time_edit.setTime(time_obj)
        self.chk_active.setChecked(int(self.alert.get("is_enabled") or 0) == 1)

    def _save(self):
        alert_type = self.alert.get("alert_type")
        if not alert_type:
            return
        time_str = self.time_edit.time().toString("HH:mm")
        is_active = self.chk_active.isChecked()
        try:
            self.db.update_scheduled_alert(alert_type, trigger_time=time_str, is_enabled=1 if is_active else 0)
            self.accept()
        except Exception:
            show_error(self, "Hata", "Talimat güncellenemedi.")

    def _wire_ui_signals(self):
        self.chk_active.stateChanged.connect(self._on_ui_widget_changed)
        self.chk_active.stateChanged.connect(self._on_ui_widget_changed)
