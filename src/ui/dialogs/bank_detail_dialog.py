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
    QMessageBox,
    QTimeEdit,
)
from PyQt6.QtCore import Qt, QDate, QTime
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.widgets.modern_dialog import NoWheelScrollArea
from src.utils.currency_helper import CurrencyHelper
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.design_system import DesignTokens
from src.utils.logger import logger


from src.ui.dialogs.bank_detail_dialog_components import BankCardDialog, AlertEditDialog
from src.ui.dialogs.bank_detail_transactions_mixin import BankDetailTransactionsMixin


class BankDetailDialog(BankDetailTransactionsMixin, BaseModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, acc_data, parent=None):
        super().__init__(parent, title="Banka Hesabı Detayları", width=1320, height=900)
        self.db = db
        self.acc = acc_data or []
        self.acc_id = self.acc[0] if self.acc else None
        self.account_cols = self._get_table_columns("bank_accounts")
        self.accounting_cols = self._get_table_columns("accounting")
        self.loan_cols = self._get_table_columns("loans")
        self.card_cols = self._get_table_columns("bank_cards")
        self.account = self._load_account()
        self.loans = self._load_loans()
        self.bank_accounts = self._load_bank_accounts()
        self.txn_page = 1
        self.txn_page_size = 25
        self.txn_total = 0
        self.setup_ui()
        self._wire_ui_signals()
        if self.acc_id and hasattr(self, "table_tx"):
            self._load_transactions()

    def _get_table_columns(self, table_name):
        try:
            self.db.cursor.execute(
                "PRAGMA table_info({table_name})".format(
                    table_name=self._safe_identifier(table_name)
                )
            )
            return [r[1] for r in self.db.cursor.fetchall()]
        except Exception:
            return []

    @staticmethod
    def _bank_field(acc, key, index, default=None):
        try:
            if hasattr(acc, "keys") and key in acc.keys():
                return acc[key]
        except Exception:
            pass
        try:
            return acc[index]
        except Exception:
            return default

    def _load_account(self):
        if not self.acc_id:
            return {}
        try:
            if self.account_cols:
                self.db.cursor.execute("SELECT * FROM bank_accounts WHERE id=?", (self.acc_id,))
                row = self.db.cursor.fetchone()
                if row:
                    return {self.account_cols[i]: row[i] for i in range(min(len(self.account_cols), len(row)))}
        except Exception as e:
            logger.debug(f"BankDetailDialog _load_account fallback used: {e}")
        fallback = {}
        if self.acc:
            if len(self.acc) > 1:
                fallback["bank_name"] = self._bank_field(self.acc, "bank_name", 1)
            if len(self.acc) > 2:
                fallback["branch_name"] = self._bank_field(
                    self.acc,
                    "branch_code",
                    5,
                    self._bank_field(self.acc, "branch_name", 2),
                )
            if len(self.acc) > 3:
                fallback["account_holder"] = self._bank_field(
                    self.acc,
                    "account_holder",
                    2,
                    self._bank_field(self.acc, "account_name", 3),
                )
            if len(self.acc) > 4:
                fallback["account_number"] = self._bank_field(
                    self.acc,
                    "account_number",
                    4,
                    self._bank_field(self.acc, "account_no", 4),
                )
            if len(self.acc) > 5:
                fallback["iban"] = self._bank_field(self.acc, "iban", 3)
            if len(self.acc) > 6:
                fallback["current_balance"] = self._bank_field(self.acc, "current_balance", 9)
            if len(self.acc) > 7:
                fallback["is_active"] = self._bank_field(self.acc, "is_active", 7)
            if len(self.acc) > 8:
                fallback["created_at"] = self._bank_field(self.acc, "created_at", 8)
        return fallback

    def _load_loans(self):
        if not self.acc_id or not self.loan_cols:
            return []
        try:
            deleted_col = None
            try:
                self.db.cursor.execute("PRAGMA table_info(loans)")
                cols = [c[1] for c in self.db.cursor.fetchall()]
                deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
            except Exception:
                deleted_col = None
            if "bank_account_id" in self.loan_cols:
                query = "SELECT * FROM loans WHERE bank_account_id=?"
                if deleted_col:
                    query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
                query += " ORDER BY start_date DESC"
                self.db.cursor.execute(query, (self.acc_id,))
            else:
                query = "SELECT * FROM loans"
                if deleted_col:
                    query += f" WHERE {deleted_col}=0 OR {deleted_col} IS NULL"
                query += " ORDER BY start_date DESC"
                self.db.cursor.execute(query)
            rows = self.db.cursor.fetchall()
            return [{self.loan_cols[i]: row[i] for i in range(min(len(self.loan_cols), len(row)))} for row in rows]
        except Exception:
            return []

    def _load_bank_accounts(self):
        mapping = {}
        try:
            accounts = self.db.get_bank_accounts() or []
            for acc in accounts:
                acc_id = self._bank_field(acc, "id", 0)
                parts = [
                    str(self._bank_field(acc, "bank_name", 1, "") or "").strip(),
                    str(self._bank_field(acc, "account_holder", 2, "") or "").strip()
                    or str(self._bank_field(acc, "account_name", 3, "") or "").strip(),
                ]
                parts = [p for p in parts if p]
                label = " - ".join(parts) if parts else "Banka Hesabı"
                acc_no = self._bank_field(
                    acc,
                    "account_number",
                    4,
                    self._bank_field(acc, "account_no", 4),
                )
                if acc_no:
                    label = f"{label} ({acc_no})"
                mapping[int(acc_id)] = label
        except Exception as e:
            logger.debug(f"BankDetailDialog _load_bank_accounts fallback used: {e}")
        return mapping

    def _get_value(self, *keys, fallback="—"):
        for key in keys:
            if isinstance(self.account, dict) and key in self.account:
                val = self.account.get(key)
                if val not in [None, ""]:
                    return val
        return fallback

    def _format_money(self, value, currency="TRY"):
        try:
            return CurrencyHelper.format_amount(float(value), db=self.db, currency_code=currency)
        except Exception:
            return CurrencyHelper.format_amount(0, db=self.db, currency_code=currency)

    def _display_currency(self):
        return CurrencyHelper.get_code(self.db)

    def _format_display_money(self, value, source_currency="TRY"):
        try:
            amount = float(value or 0)
        except Exception:
            amount = 0.0
        target = self._display_currency()
        converted = CurrencyHelper.convert_amount(self.db, amount, source_currency or target, target)
        return CurrencyHelper.format_amount(converted, db=self.db, currency_code=target)

    def _get_account_status(self):
        val = self._get_value("is_active", fallback=1)
        try:
            return "Aktif" if int(val) == 1 else "Pasif"
        except Exception:
            return "Aktif"

    def _get_last_transaction_date(self):
        if not self.acc_id or "bank_account_id" not in self.accounting_cols:
            return "—"
        try:
            self.db.cursor.execute(
                "SELECT MAX(date) FROM accounting WHERE bank_account_id=? OR related_account_id=?",
                (self.acc_id, self.acc_id),
            )
            row = self.db.cursor.fetchone()
            return row[0] if row and row[0] else "—"
        except Exception:
            return "—"

    def setup_ui(self):
        if not self.acc_id:
            self.content_layout.addWidget(QLabel("Banka hesabı bulunamadı."))
            return

        header = self._build_header_card()
        self.content_layout.addWidget(header)

        tabs = QTabWidget()
        tabs.setStyleSheet(theme_qss("""
            QTabWidget::pane { border: none; }
            QTabBar::tab {
                background: transparent;
                color: @text_muted;
                padding: 10px 20px;
                font-weight: 600;
                border-bottom: 2px solid transparent;
            }
            QTabBar::tab:selected {
                color: @accent_hover;
                border-bottom: 2px solid @accent_hover;
            }
        """))

        tab_general = QWidget()
        self._setup_general_tab(tab_general)
        tabs.addTab(tab_general, "Genel Bilgiler")

        tab_loans = QWidget()
        self._setup_loan_tab(tab_loans)
        tabs.addTab(tab_loans, "Kredi Bilgileri")

        tab_tx = QWidget()
        self._setup_transactions_tab(tab_tx)
        tabs.addTab(tab_tx, "Hesap Hareketleri")

        tab_summary = QWidget()
        self._setup_summary_tab(tab_summary)
        tabs.addTab(tab_summary, "Özet & Analiz")

        tab_extra = QWidget()
        self._setup_extra_tab(tab_extra)
        tabs.addTab(tab_extra, "Kartlar & Bildirimler")

        self.content_layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_edit = QPushButton("Düzenle")
        btn_edit.setFixedSize(120, 40)
        btn_edit.setStyleSheet(theme_qss(DesignTokens.get_button_qss("warning")))
        btn_edit.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_edit.clicked.connect(self.on_edit)

        btn_close = QPushButton("Kapat")
        btn_close.setFixedSize(100, 40)
        btn_close.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)

        btn_layout.addWidget(btn_edit)
        btn_layout.addWidget(btn_close)
        self.content_layout.addLayout(btn_layout)

    def _wire_ui_signals(self):
        self.cmb_tx_type.currentIndexChanged.connect(self._on_ui_widget_changed)
        self.chk_tx_date.stateChanged.connect(self._on_ui_widget_changed)

    def _build_header_card(self):
        card = QFrame()
        card.setStyleSheet(theme_qss("background: @surface_alt; border-radius: 12px; border: 1px solid @border;"))
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)

        left = QVBoxLayout()
        bank_name = self._get_value("bank_name", fallback="Banka Bilgisi Yok")
        account_name = self._get_value("account_holder", "account_name", fallback="")
        lbl_bank = QLabel(str(bank_name))
        lbl_bank.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        lbl_bank.setStyleSheet(theme_qss("color: @text;"))
        lbl_acc = QLabel(str(account_name))
        lbl_acc.setStyleSheet(theme_qss("color: @text_muted; font-size: 13px;"))
        left.addWidget(lbl_bank)
        left.addWidget(lbl_acc)
        layout.addLayout(left)
        layout.addStretch()

        status = self._get_account_status()
        color = tc("success") if status == "Aktif" else tc("danger")
        lbl_status = QLabel(status)
        lbl_status.setStyleSheet(theme_qss(f"background: {color}; color: @selection_text; padding: 6px 16px; border-radius: 16px; font-weight: 700;"))
        layout.addWidget(lbl_status)
        return card

    def _setup_general_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = NoWheelScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(14)

        info_card = QFrame()
        info_card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(12)
        title = QLabel("Hesap Genel Bilgileri")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @selection_text;"))
        info_layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(14)

        def add_item(row, col, label, value, highlight=False):
            lbl = QLabel(label)
            lbl.setStyleSheet(theme_qss("color: @disabled_text; font-size: 11px; font-weight: 600;"))
            val = QLabel(str(value))
            val.setStyleSheet(theme_qss("color: @selection_text; font-size: 14px; font-weight: 600;" if highlight else "color: @selection_text; font-size: 14px;"))
            grid.addWidget(lbl, row * 2, col)
            grid.addWidget(val, row * 2 + 1, col)

        account_no = self._get_value("account_number", "account_no", fallback="—")
        branch_name = self._get_value("branch_name", "branch_code", fallback="—")
        iban = self._get_value("iban", fallback="—")
        currency = self._get_value("currency", fallback="TRY")
        balance_val = float(self._get_value("current_balance", fallback=0) or 0)
        blocked = 0.0
        available = balance_val - blocked
        created_at = self._get_value("created_at", fallback="—")
        last_tx = self._get_last_transaction_date()
        acc_type = "Kredi" if self.loans else "Vadesiz"

        add_item(0, 0, "Hesap Adı", self._get_value("account_holder", "account_name", fallback="—"))
        add_item(0, 1, "Hesap No", account_no)
        add_item(0, 2, "Şube", branch_name)
        add_item(1, 0, "IBAN", iban, True)
        add_item(1, 1, "Hesap Türü", acc_type)
        add_item(1, 2, "Döviz Cinsi", currency)
        add_item(2, 0, "Güncel Bakiye", self._format_money(balance_val, currency))
        add_item(2, 1, "Kullanılabilir", self._format_money(available, currency))
        add_item(2, 2, "Bloke Tutar", self._format_money(blocked, currency))
        add_item(3, 0, "Açılış Tarihi", created_at)
        add_item(3, 1, "Son İşlem Tarihi", last_tx)
        add_item(3, 2, "Durum", self._get_account_status())

        info_layout.addLayout(grid)
        c_layout.addWidget(info_card)
        c_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _setup_loan_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = NoWheelScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(14)

        if not self.loans:
            empty = QLabel("Bu hesaba bağlı kredi bulunamadı.")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(theme_qss("color: @disabled_text; font-size: 14px; font-weight: 600;"))
            c_layout.addWidget(empty)
            c_layout.addStretch()
            scroll.setWidget(container)
            layout.addWidget(scroll)
            return

        loan = self.loans[0]
        loan_id = loan.get("id")
        installments = self._load_installments(loan_id)

        total_limit = float(loan.get("amount") or 0)
        total_payment = float(loan.get("total_payment") or total_limit)
        paid = sum(float(inst.get("total_amount") or 0) for inst in installments if str(inst.get("status")) == "Ödendi")
        remaining = max(total_payment - paid, 0.0)
        used = total_payment - remaining

        summary_card = QFrame()
        summary_card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        s_layout = QVBoxLayout(summary_card)
        s_layout.setContentsMargins(16, 16, 16, 16)
        s_layout.setSpacing(12)
        s_title = QLabel("Kredi Özeti")
        s_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        s_title.setStyleSheet(theme_qss("color: @selection_text;"))
        s_layout.addWidget(s_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)

        def add_item(row, col, label, value, color=tc("selection_text")):
            lbl = QLabel(label)
            lbl.setStyleSheet(theme_qss("color: @disabled_text; font-size: 11px; font-weight: 600;"))
            val = QLabel(str(value))
            val.setStyleSheet(theme_qss(f"color: {color}; font-size: 14px; font-weight: 600;"))
            grid.addWidget(lbl, row * 2, col)
            grid.addWidget(val, row * 2 + 1, col)

        add_item(0, 0, "Toplam Kredi Limiti", self._format_display_money(total_limit))
        add_item(0, 1, "Kullanılan Limit", self._format_display_money(used), "@warning")
        add_item(0, 2, "Kalan Bakiye", self._format_display_money(remaining), tc("success"))
        add_item(1, 0, "Faiz Oranı", f"%{loan.get('interest_rate', 0)}")
        add_item(1, 1, "Vade", f"{loan.get('term_months', 0)} Ay")
        add_item(1, 2, "Durum", loan.get("status", "—"))

        start_date = loan.get("start_date", "—")
        end_date = installments[-1].get("due_date") if installments else "—"
        add_item(2, 0, "Başlangıç Tarihi", start_date)
        add_item(2, 1, "Vade Bitişi", end_date)
        add_item(2, 2, "Taksit Sayısı", len(installments))

        s_layout.addLayout(grid)
        c_layout.addWidget(summary_card)

        plan_card = QFrame()
        plan_card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        p_layout = QVBoxLayout(plan_card)
        p_layout.setContentsMargins(16, 16, 16, 16)
        p_layout.setSpacing(12)
        p_title = QLabel("Taksit Planı")
        p_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        p_title.setStyleSheet(theme_qss("color: @selection_text;"))
        p_layout.addWidget(p_title)

        table = QTableWidget()
        from PyQt6.QtWidgets import QAbstractItemView
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["No", "Vade", "Tutar", "Durum"])
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setAlternatingRowColors(True)
        table.setWordWrap(True)
        table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        table.setRowCount(len(installments))
        for i, inst in enumerate(installments):
            inst_no = inst.get("installment_no", i + 1)
            due = inst.get("due_date", "—")
            amount = float(inst.get("total_amount") or 0)
            status = inst.get("status", "Bekliyor")
            table.setItem(i, 0, QTableWidgetItem(str(inst_no)))
            table.setItem(i, 1, QTableWidgetItem(str(due)))
            table.setItem(i, 2, QTableWidgetItem(self._format_display_money(amount)))
            status_item = QTableWidgetItem(str(status))
            if status == "Ödendi":
                status_item.setForeground(qc("success"))
            elif status == "Gecikmiş":
                status_item.setForeground(qc("danger"))
            else:
                status_item.setForeground(qc("warning"))
            status_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            table.setItem(i, 3, status_item)
        p_layout.addWidget(table, 1)
        c_layout.addWidget(plan_card, 1)
        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _setup_transactions_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        filter_row = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Açıklama veya referans arayın")
        self.txt_search.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.cmb_tx_type = QComboBox()
        self.cmb_tx_type.addItems(["Tümü", "Gelir", "Gider", "Transfer", "Havale", "EFT", "Otomatik Ödeme", "Faiz", "Masraf"])
        self.cmb_tx_type.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))

        self.chk_tx_date = QCheckBox("Tarih Filtrele")
        self.chk_tx_date.setStyleSheet(theme_qss(f"""
            QCheckBox {{
                color: {DesignTokens.FOREGROUND};
                font-weight: 600;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 6px;
                border: 2px solid {DesignTokens.BORDER};
                background: @surface;
            }}
            QCheckBox::indicator:checked {{
                background: {DesignTokens.ACCENT};
                border: 2px solid {DesignTokens.ACCENT};
            }}
            QCheckBox::indicator:checked:hover {{
                background: @accent_hover;
                border: 2px solid @accent_hover;
            }}
        """))
        self.tx_date_from = QDateEdit()
        self.tx_date_from.setCalendarPopup(True)
        self.tx_date_from.setDate(QDate.currentDate().addMonths(-1))
        self.tx_date_from.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.tx_date_to = QDateEdit()
        self.tx_date_to.setCalendarPopup(True)
        self.tx_date_to.setDate(QDate.currentDate())
        self.tx_date_to.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.spin_amount_min = QDoubleSpinBox()
        self.spin_amount_min.setRange(0, 1000000000)
        self.spin_amount_min.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
        DesignTokens.apply_spinbox_styles(self.spin_amount_min)
        self.spin_amount_min.setFixedWidth(140)

        self.spin_amount_max = QDoubleSpinBox()
        self.spin_amount_max.setRange(0, 1000000000)
        self.spin_amount_max.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
        DesignTokens.apply_spinbox_styles(self.spin_amount_max)
        self.spin_amount_max.setFixedWidth(140)

        btn_apply = QPushButton("Filtrele")
        btn_apply.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_apply.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_apply.clicked.connect(self._apply_filters)

        btn_clear = QPushButton("Temizle")
        btn_clear.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.clicked.connect(self._reset_filters)

        btn_excel = QPushButton("Excel")
        btn_excel.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline")))
        btn_excel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_excel.clicked.connect(lambda: self._export_transactions("excel"))

        btn_pdf = QPushButton("PDF")
        btn_pdf.setStyleSheet(theme_qss(DesignTokens.get_button_qss("outline")))
        btn_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pdf.clicked.connect(lambda: self._export_transactions("pdf"))

        filter_row.addWidget(self.txt_search, 2)
        filter_row.addWidget(self.cmb_tx_type)
        filter_row.addWidget(self.chk_tx_date)
        filter_row.addWidget(self.tx_date_from)
        filter_row.addWidget(self.tx_date_to)
        filter_row.addWidget(QLabel("Min"))
        filter_row.addWidget(self.spin_amount_min)
        filter_row.addWidget(QLabel("Max"))
        filter_row.addWidget(self.spin_amount_max)
        filter_row.addWidget(btn_apply)
        filter_row.addWidget(btn_clear)
        filter_row.addWidget(btn_excel)
        filter_row.addWidget(btn_pdf)

        layout.addLayout(filter_row)

        self.table_tx = QTableWidget()
        self.table_tx.setColumnCount(8)
        self.table_tx.setHorizontalHeaderLabels([
            "Tarih", "Saat", "Ref", "Tür", "Açıklama", "Tutar", "Yöntem", "Gönderen/Alan"
        ])
        self.table_tx.verticalHeader().setVisible(False)
        self.table_tx.setAlternatingRowColors(True)
        self.table_tx.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        self.table_tx.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_tx.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table_tx.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table_tx.itemDoubleClicked.connect(self._open_tx_detail)
        layout.addWidget(self.table_tx)

        footer = QHBoxLayout()
        self.lbl_tx_count = QLabel("0 kayıt")
        self.lbl_tx_count.setStyleSheet(theme_qss("color: @text_muted;"))

        self.btn_prev = QPushButton("Önceki")
        self.btn_prev.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_prev.clicked.connect(lambda: self._change_page(-1))

        self.btn_next = QPushButton("Sonraki")
        self.btn_next.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_next.clicked.connect(lambda: self._change_page(1))

        self.lbl_page = QLabel("1 / 1")
        self.lbl_page.setStyleSheet(theme_qss("color: @text; font-weight: 600;"))

        self.cmb_page_size = QComboBox()
        self.cmb_page_size.addItems(["25", "50", "100"])
        self.cmb_page_size.setCurrentText("25")
        self.cmb_page_size.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        self.cmb_page_size.currentTextChanged.connect(self._change_page_size)

        footer.addWidget(self.lbl_tx_count)
        footer.addStretch()
        footer.addWidget(QLabel("Sayfa Boyutu"))
        footer.addWidget(self.cmb_page_size)
        footer.addWidget(self.btn_prev)
        footer.addWidget(self.lbl_page)
        footer.addWidget(self.btn_next)
        layout.addLayout(footer)

    def _setup_summary_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = NoWheelScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(14)

        totals = self._compute_summary_totals()

        kpi_row = QHBoxLayout()
        kpi_row.addWidget(self._build_stat_card("Toplam Giriş", self._format_money(totals["income"]), tc("success")))
        kpi_row.addWidget(self._build_stat_card("Toplam Çıkış", self._format_money(totals["expense"]), tc("danger")))
        kpi_row.addWidget(self._build_stat_card("Net", self._format_money(totals["net"]), tc("selection_text")))
        c_layout.addLayout(kpi_row)

        trend_card = QFrame()
        trend_card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        trend_layout = QVBoxLayout(trend_card)
        trend_layout.setContentsMargins(16, 16, 16, 16)
        trend_layout.setSpacing(10)
        trend_title = QLabel("Haftalık / Aylık Analiz")
        trend_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        trend_title.setStyleSheet(theme_qss("color: @selection_text;"))
        trend_layout.addWidget(trend_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(10)

        def add_metric(row, col, label, value, color=tc("selection_text")):
            l = QLabel(label)
            l.setStyleSheet(theme_qss("color: @disabled_text; font-size: 11px; font-weight: 600;"))
            v = QLabel(value)
            v.setStyleSheet(theme_qss(f"color: {color}; font-size: 14px; font-weight: 600;"))
            grid.addWidget(l, row * 2, col)
            grid.addWidget(v, row * 2 + 1, col)

        add_metric(0, 0, "Son 7 Gün Giriş", self._format_money(totals["week_income"]), tc("success"))
        add_metric(0, 1, "Son 7 Gün Çıkış", self._format_money(totals["week_expense"]), tc("danger"))
        add_metric(1, 0, "Son 30 Gün Giriş", self._format_money(totals["month_income"]), tc("success"))
        add_metric(1, 1, "Son 30 Gün Çıkış", self._format_money(totals["month_expense"]), tc("danger"))
        trend_layout.addLayout(grid)
        c_layout.addWidget(trend_card)

        category_card = QFrame()
        category_card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        cat_layout = QVBoxLayout(category_card)
        cat_layout.setContentsMargins(16, 16, 16, 16)
        cat_layout.setSpacing(10)
        cat_title = QLabel("Kategorilere Göre Harcama Dağılımı")
        cat_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        cat_title.setStyleSheet(theme_qss("color: @selection_text;"))
        cat_layout.addWidget(cat_title)

        cat_table = QTableWidget()
        from PyQt6.QtWidgets import QAbstractItemView
        cat_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        cat_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        cat_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        cat_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cat_table.setColumnCount(2)
        cat_table.setHorizontalHeaderLabels(["Kategori", "Tutar"])
        cat_table.verticalHeader().setVisible(False)
        cat_table.setAlternatingRowColors(True)
        cat_table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        header = cat_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        category_rows = self._get_category_distribution()
        cat_table.setRowCount(len(category_rows))
        for i, (cat, amount) in enumerate(category_rows):
            cat_table.setItem(i, 0, QTableWidgetItem(cat))
            cat_table.setItem(i, 1, QTableWidgetItem(self._format_display_money(amount)))

        cat_layout.addWidget(cat_table)
        c_layout.addWidget(category_card)
        c_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)

    def _setup_extra_tab(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = NoWheelScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(14)

        alerts_card = QFrame()
        alerts_card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        alerts_layout = QVBoxLayout(alerts_card)
        alerts_layout.setContentsMargins(16, 16, 16, 16)
        alerts_layout.setSpacing(10)
        alerts_title = QLabel("Yaklaşan Otomatik Ödemeler ve Bildirimler")
        alerts_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        alerts_title.setStyleSheet(theme_qss("color: @selection_text;"))
        alerts_layout.addWidget(alerts_title)

        self.alert_table = QTableWidget()
        from PyQt6.QtWidgets import QAbstractItemView
        self.alert_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.alert_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.alert_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.alert_table.setColumnCount(4)
        self.alert_table.setHorizontalHeaderLabels(["Bildirim", "Saat", "Durum", "İşlem"])
        self.alert_table.verticalHeader().setVisible(False)
        self.alert_table.setAlternatingRowColors(True)
        self.alert_table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        self.alert_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.alert_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.alert_table.itemDoubleClicked.connect(self._open_alert_from_table)
        alerts_layout.addWidget(self.alert_table)
        c_layout.addWidget(alerts_card)

        cards_card = QFrame()
        cards_card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        cards_layout = QVBoxLayout(cards_card)
        cards_layout.setContentsMargins(16, 16, 16, 16)
        cards_layout.setSpacing(10)
        cards_header = QHBoxLayout()
        cards_title = QLabel("Hesapla İlişkili Kredi Kartları")
        cards_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        cards_title.setStyleSheet(theme_qss("color: @selection_text;"))
        cards_header.addWidget(cards_title)
        cards_header.addStretch()
        btn_add_card = QPushButton("Kart Ekle")
        btn_add_card.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_add_card.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_card.clicked.connect(self._open_add_card_dialog)
        cards_header.addWidget(btn_add_card)
        cards_layout.addLayout(cards_header)

        self.cards_table = QTableWidget()
        from PyQt6.QtWidgets import QAbstractItemView
        self.cards_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.cards_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.cards_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.cards_table.setColumnCount(5)
        self.cards_table.setHorizontalHeaderLabels(["Kart", "Limit", "Borç", "Durum", "İşlem"])
        self.cards_table.verticalHeader().setVisible(False)
        self.cards_table.setAlternatingRowColors(True)
        self.cards_table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        self.cards_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        c_header = self.cards_table.horizontalHeader()
        c_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        c_header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        c_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        c_header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        c_header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        cards_layout.addWidget(self.cards_table)
        c_layout.addWidget(cards_card)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self._refresh_alerts()
        self._refresh_cards()

    def _build_stat_card(self, title, value, color):
        card = QFrame()
        card.setStyleSheet(theme_qss(DesignTokens.get_card_qss(hover=False)))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        lbl_value = QLabel(value)
        lbl_value.setStyleSheet(theme_qss(f"color: {color}; font-size: 18px; font-weight: 700;"))
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_value)
        return card

    def _calculate_early_payment(self, interest_rate):
        amount = float(self.spin_early_amount.value())
        months = int(self.spin_early_months.value())
        discount = amount * (float(interest_rate) / 100.0) * (months / 12.0) if months > 0 else 0.0
        estimated = max(amount - discount, 0.0)
        self.lbl_early_result.setText(
            "Tahmini erken ödeme tutarı: "
            f"{self._format_display_money(estimated)}"
        )

    def _load_installments(self, loan_id):
        if not loan_id:
            return []
        try:
            rows = self.db.get_loan_installments(loan_id)
            cols = [c[1] for c in self.db.cursor.execute("PRAGMA table_info(loan_installments)").fetchall()]
            if cols:
                return [{cols[i]: row[i] for i in range(min(len(cols), len(row)))} for row in rows]
            return [dict(r) for r in rows]
        except Exception:
            return []

    def on_edit(self):
        self.done(10)


