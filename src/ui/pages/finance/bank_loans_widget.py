# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLineEdit, QComboBox,
    QButtonGroup, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFormLayout, QDoubleSpinBox, QSpinBox,
    QDateEdit, QMessageBox, QTreeWidget, QTreeWidgetItem, QMenu,
    QAbstractItemView, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont, QIcon, QAction, QTextDocument
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
import csv
from html import escape

from src.utils.theme_colors import theme_qss, qc
from src.utils.design_system import DesignTokens
from src.utils.currency_helper import CurrencyHelper
from src.utils.toast_notification import show_success, show_error
from src.utils.message_helper import show_question, show_warning
from src.ui.components.message_box import ModernConfirm
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.dialogs.loan_wizard_advanced import AdvancedLoanWizard
from src.utils.context_menu_settings import is_context_menu_enabled
from src.utils.logger import logger
from datetime import datetime, timedelta

class LoansWidget(QWidget):
    PAGE_SIZE = 11

    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.expand_buttons = {}
        self.init_ui()

    def _display_currency(self):
        return CurrencyHelper.get_code(self.db)

    def _format_display_money(self, amount_try):
        return CurrencyHelper.format_from_try(amount_try, db=self.db, currency_code=self._display_currency())

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 19, 18, 3)
        layout.setSpacing(16)

        self.btn_add_loan = QPushButton("Yeni Kredi Ekle")
        self.btn_add_loan.clicked.connect(self.open_loan_wizard)
        self.btn_add_loan.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
        """))
        self.btn_add_loan.setText("+  Yeni Kredi Ekle")
        self.btn_add_loan.setFixedHeight(46)
        self.btn_add_loan.setStyleSheet(
            "QPushButton{background:#059669;color:#ffffff;border:0;border-radius:8px;"
            "padding:0 18px;font-weight:700;} QPushButton:hover{background:#047857;}"
        )

        # Loans Tree remains the data and context-action source for the schedule view.
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Banka", "Açıklama / Kullanım Yeri", "Tutar", "Faiz / Vade", "Kalan Tutar", "Durum", "Bitiş Tarihi", "İşlemler"])
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setAllColumnsShowFocus(False)
        self.tree.setRootIsDecorated(False)
        
        # Column Resizing - Wider by default
        header = self.tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setDefaultSectionSize(150) # Wider general columns
        header.resizeSection(0, 200) # Banka
        header.resizeSection(1, 300) # Aciklama
        header.resizeSection(7, 80)  # İşlemler (Button)
        
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.itemExpanded.connect(self.sync_expand_button)
        self.tree.itemCollapsed.connect(self.sync_expand_button)
        self.tree.setStyleSheet(theme_qss("""
            QTreeWidget {
                font-size: 13px;
                padding: 10px;
                color: @text;
                background: @surface;
            }
            QTreeWidget::item {
                padding-right: 20px;
                padding-left: 5px;
                height: 50px;
                color: @text;
            }
        """))
        self.tree.hide()
        self._build_reference_view(layout)

        self.load_loans()

    def _build_reference_view(self, layout):
        self.metric_values = []
        metrics = QGridLayout()
        metrics.setHorizontalSpacing(12)
        for label, accent in (
            ("Toplam Kredi Tutar\u0131", "#60a5fa"),
            ("Kalan Ana Para & Bor\u00e7", "#fbbf24"),
            ("Ayl\u0131k Taksit Tutar\u0131", "#22d3ee"),
            ("S\u0131radaki Taksit Tarihi", "#c084fc"),
        ):
            card = QFrame()
            card.setMinimumHeight(88)
            card.setStyleSheet(
                f"QFrame{{background:#101827;border:1px solid #263449;border-radius:10px;}}"
            )
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(14, 10, 14, 10)
            name = QLabel(label.upper())
            name.setStyleSheet(f"color:{accent};font-size:11px;font-weight:700;border:0;")
            value = QLabel("--")
            value.setStyleSheet(
                "QLabel { color: rgb(255,255,255); font-size: 22px; font-weight: bold; border: 0; }"
            )
            detail = QLabel("")
            detail.setStyleSheet("color:#94a3b8;font-size:11px;border:0;")
            card_layout.addWidget(name)
            card_layout.addWidget(value)
            card_layout.addWidget(detail)
            metrics.addWidget(card, 0, len(self.metric_values))
            self.metric_values.append((value, detail))
        layout.addLayout(metrics)

        filters = QHBoxLayout()
        filters.setContentsMargins(0, 0, 0, 2)
        self.loan_search = QLineEdit()
        self.loan_search.setPlaceholderText("Banka ad\u0131, kredi no veya kullan\u0131m yeri ara...")
        self.loan_search.setMinimumWidth(200)
        self.loan_search.setFixedHeight(46)
        self.loan_search.setStyleSheet(
            "QLineEdit{background:#111b2c;color:#e2e8f0;border:1px solid #263449;"
            "border-radius:8px;padding:8px 12px;}"
        )
        self.loan_search.textChanged.connect(self._render_reference_view)
        filters.addWidget(self.loan_search, 1)
        self.loan_filter = QComboBox()
        self.loan_filter.addItems(["Yaln\u0131zca Aktif Krediler", "T\u00fcm Krediler"])
        self.loan_filter.setFixedHeight(46)
        self.loan_filter.currentIndexChanged.connect(self._render_reference_view)
        filters.addWidget(self.loan_filter)
        self.currency_buttons = QButtonGroup(self)
        self.currency_codes = {}
        for code, caption in (("USD", "USD ($)"), ("TRY", "TRY (\u20ba)"), ("EUR", "EUR (\u20ac)")):
            button = QPushButton(caption)
            button.setCheckable(True)
            button.setFixedHeight(46)
            button.setStyleSheet(
                "QPushButton{background:#111b2c;color:#94a3b8;border:1px solid #263449;"
                "padding:7px 10px;} QPushButton:checked{background:#2563eb;color:white;}"
            )
            self.currency_buttons.addButton(button)
            self.currency_codes[button] = code
            filters.addWidget(button)
        default_currency = "USD"
        selected_currency = next(
            (button for button, code in self.currency_codes.items() if code == default_currency),
            next(button for button, code in self.currency_codes.items() if code == "USD"),
        )
        selected_currency.setChecked(True)
        self.currency_buttons.buttonClicked.connect(self._on_reference_currency_changed)
        self.btn_export_reference = QPushButton("Excel / CSV")
        self.btn_accounts = QPushButton("Banka Hesaplar\u0131")
        self.btn_accounts.setFixedHeight(46)
        self.btn_accounts.setStyleSheet(
            "QPushButton{background:#111b2c;color:#dbeafe;border:1px solid #263449;"
            "border-radius:6px;padding:7px 9px;font-size:10px;}"
        )
        filters.addWidget(self.btn_accounts)
        self.btn_export_reference.setToolTip("Kredi ve taksit planini CSV olarak disa aktar")
        self.btn_export_reference.clicked.connect(self._export_reference_csv)
        self.btn_print_reference = QPushButton("Yazd\u0131r")
        self.btn_print_reference.setFixedHeight(46)
        self.btn_print_reference.clicked.connect(self._print_reference_view)
        for action_button in (self.btn_export_reference, self.btn_print_reference):
            action_button.setFixedHeight(46)
            action_button.setStyleSheet(
                "QPushButton{background:#111b2c;color:#dbeafe;border:1px solid #263449;"
                "border-radius:6px;padding:7px 9px;font-size:10px;}"
                "QPushButton:hover{background:#1e293b;border-color:#3b82f6;}"
            )
            filters.addWidget(action_button)
        filters.addWidget(self.btn_add_loan)
        layout.addLayout(filters)

        self.contract_header = QFrame()
        self.contract_header.setObjectName("loanContractHeader")
        self.contract_header.setFixedHeight(60)
        self.contract_header.setStyleSheet(
            "QFrame{background:#2459dd;border:1px solid #3474ff;border-radius:9px;}"
            "QFrame#loanContractHeader QLabel#loanContractName{color:#ffffff;font-size:15px;font-weight:700;}"
        )
        header_layout = QHBoxLayout(self.contract_header)
        self.contract_layout = header_layout
        header_layout.setContentsMargins(14, 10, 14, 10)
        header_layout.setSpacing(8)
        self.contract_logo = QLabel("BBVA")
        self.contract_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.contract_logo.setFixedSize(36, 36)
        self.contract_logo.setStyleSheet(
            "QLabel{background:rgba(255,255,255,0.16);color:#ffffff;"
            "border:1px solid rgba(255,255,255,0.22);border-radius:8px;"
            "font-size:10px;font-weight:800;}"
        )
        header_layout.addWidget(self.contract_logo)
        contract_identity = QWidget(self.contract_header)
        contract_identity.setFixedWidth(184)
        identity_layout = QVBoxLayout(contract_identity)
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(2)
        self.contract_name = QLabel("-")
        self.contract_name.setObjectName("loanContractName")
        self.contract_name.setStyleSheet("color:#ffffff;font-size:11px;font-weight:700;border:0;")
        identity_layout.addWidget(self.contract_name)
        self.contract_meta = QLabel("")
        self.contract_meta.setWordWrap(True)
        self.contract_meta.setStyleSheet("color:#dbeafe;font-size:8px;border:0;")
        identity_layout.addWidget(self.contract_meta)
        header_layout.addWidget(contract_identity)
        self.contract_status = QLabel("\u25cf  Aktif Kredi")
        self.contract_status.setStyleSheet(
            "color:#6ee7b7;background:#064e3b;border:1px solid #047857;"
            "border-radius:10px;padding:4px 8px;font-size:11px;font-weight:700;"
        )
        self.contract_status.setFixedWidth(92)
        header_layout.addWidget(self.contract_status)
        header_layout.addSpacing(160)
        self.contract_amount = QLabel("")
        self.contract_amount.setWordWrap(True)
        self.contract_amount.setMinimumWidth(80)
        self.contract_amount.setStyleSheet(
            "QLabel { color: rgb(255,255,255); font-size: 11px; font-weight: bold; border: 0; }"
        )
        self.contract_amount.setFixedWidth(104)
        header_layout.addWidget(self.contract_amount)
        self.contract_rate = QLabel("")
        self.contract_rate.setStyleSheet(
            "QLabel { color: rgb(255,255,255); font-size: 11px; font-weight: bold; border: 0; }"
        )
        self.contract_rate.setFixedWidth(104)
        header_layout.addWidget(self.contract_rate)
        self.contract_remaining = QLabel("")
        self.contract_remaining.setStyleSheet(
            "QLabel { color: rgb(255,255,255); font-size: 11px; font-weight: bold; border: 0; }"
        )
        self.contract_remaining.setFixedWidth(104)
        header_layout.addWidget(self.contract_remaining)
        self.contract_end_date = QLabel("")
        self.contract_end_date.setStyleSheet(
            "QLabel { color: rgb(255,255,255); font-size: 11px; font-weight: bold; border: 0; }"
        )
        self.contract_end_date.setFixedWidth(104)
        header_layout.addWidget(self.contract_end_date)
        header_layout.addStretch(1)
        self.btn_contract_details = QPushButton("Detaylar")
        self.btn_contract_details.setFixedSize(72, 34)
        self.btn_contract_details.clicked.connect(self._open_selected_loan_details)
        header_layout.addWidget(self.btn_contract_details)
        self.loan_actions_button = QPushButton("\u22ef")
        self.loan_actions_button.setFixedSize(40, 34)
        self.loan_actions_button.setToolTip("Kredi i\u015flemleri")
        loan_menu = QMenu(self.loan_actions_button)
        loan_menu.addAction("Krediyi D\u00fczenle", lambda: self._with_selected_loan(self.open_edit_loan_dialog))
        loan_menu.addAction("Toplu \u00d6deme Yap", lambda: self._with_selected_loan(self.open_bulk_payment))
        loan_menu.addAction("Kredi Detaylar\u0131", self._open_selected_loan_details)
        loan_menu.addSeparator()
        loan_menu.addAction("Krediyi \u0130ptal Et", lambda: self._with_selected_loan(self._cancel_selected_loan))
        loan_menu.addAction("Krediyi Sil", lambda: self._with_selected_loan(self.delete_loan))
        self.loan_actions_button.setMenu(loan_menu)
        header_layout.addWidget(self.loan_actions_button)
        self.loan_schedule_panel = QFrame()
        self.loan_schedule_panel.setObjectName("LoanSchedulePanel")
        self.loan_schedule_panel.setStyleSheet(
            "QFrame#LoanSchedulePanel{background:#0f1725;border:1px solid #263449;border-radius:8px;}"
        )
        self.loan_schedule_layout = QVBoxLayout(self.loan_schedule_panel)
        self.loan_schedule_layout.setContentsMargins(0, 0, 0, 0)
        self.loan_schedule_layout.setSpacing(0)
        self.loan_schedule_layout.addWidget(self.contract_header)

        self.installment_table = QTableWidget()
        self.installment_table.setColumnCount(6)
        self.installment_table.setHorizontalHeaderLabels([
            "TAKS\u0130T NO", "TAKS\u0130T TUTARI", "VADE TAR\u0130H\u0130", "DURUM",
            "\u00d6DEME / DEKONT KAYDI", "\u0130\u015eLEMLER",
        ])
        self.installment_table.verticalHeader().setVisible(False)
        self.installment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.installment_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.installment_table.setShowGrid(False)
        self.installment_table.setStyleSheet(
            "QTableWidget{background:#0f1725;color:#e2e8f0;border:1px solid #263449;"
            "border-radius:8px;gridline-color:#1e293b;}"
            "QHeaderView::section{background:#172236;color:#94a3b8;border:0;"
            "border-bottom:1px solid #263449;padding:8px 10px;font-size:11px;font-weight:700;}"
            "QTableWidget::item{padding:7px 10px;border-bottom:1px solid #1e293b;}"
        )
        header = self.installment_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.installment_table.setColumnWidth(0, 210)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.installment_table.setColumnWidth(1, 180)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.installment_table.setColumnWidth(2, 160)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.installment_table.setColumnWidth(3, 150)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.installment_table.setColumnWidth(5, 120)
        self.installment_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.installment_table.setMinimumHeight(260)
        self.installment_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.installment_table.customContextMenuRequested.connect(self._open_installment_context_menu)
        self.installment_table.itemDoubleClicked.connect(
            lambda *_args: self._open_selected_loan_details()
        )
        self.loan_schedule_layout.addWidget(self.installment_table, 0)

        self.installment_footer = QWidget(self.loan_schedule_panel)
        self.installment_footer.setFixedHeight(30)
        self.installment_footer.setStyleSheet(
            "background:#0f1725;border-top:1px solid #263449;"
        )
        footer = QHBoxLayout(self.installment_footer)
        footer.setContentsMargins(10, 0, 10, 0)
        self.loan_page_info = QLabel("")
        footer.addWidget(self.loan_page_info)
        footer.addStretch(1)
        self.loan_previous = QPushButton("\u00d6nceki")
        self.loan_next = QPushButton("Sonraki")
        self.loan_page_label = QLabel("1 / 1")
        self.loan_previous.clicked.connect(lambda: self._change_installment_page(-1))
        self.loan_next.clicked.connect(lambda: self._change_installment_page(1))
        footer.addWidget(self.loan_previous)
        footer.addWidget(self.loan_page_label)
        footer.addWidget(self.loan_next)
        self.loan_schedule_layout.addWidget(self.installment_footer)
        layout.addWidget(self.loan_schedule_panel, 0)
        layout.addStretch(1)
        self._installment_rows = []
        self._selected_loan_id = None
        self._installment_page = 1

    def _on_reference_currency_changed(self, button):
        self._render_reference_view()

    def _reference_currency(self):
        button = self.currency_buttons.checkedButton()
        return self.currency_codes.get(button, "USD")

    def _format_reference_money(self, amount):
        value = float(amount or 0)
        currency = self._reference_currency()
        try:
            return CurrencyHelper.format_from_try(
                value, db=self.db, currency_code=currency
            )
        except ValueError:
            return CurrencyHelper.format_amount(value, db=self.db, currency_code="TRY")

    def _reference_filtered_loans(self):
        loans = [dict(loan) for loan in self.db.get_loans(active_only=False)]
        query = self.loan_search.text().strip().casefold()
        if self.loan_filter.currentIndex() == 0:
            loans = [
                loan for loan in loans
                if str(loan.get("status") or "").casefold() == "aktif"
            ]
        if query:
            loans = [
                loan for loan in loans
                if query in " ".join(
                    str(loan.get(key) or "")
                    for key in ("bank_name", "description", "loan_title", "id")
                ).casefold()
            ]
        return loans

    def _reference_export_rows(self):
        rows = []
        for loan in self._reference_filtered_loans():
            for item in self.db.get_loan_installments(loan["id"]):
                rows.append({
                    "bank": loan.get("bank_name", ""),
                    "loan_id": loan.get("id", ""),
                    "installment": item.get("installment_no", ""),
                    "due_date": item.get("due_date", ""),
                    "amount": self._format_reference_money(
                        self.get_installment_amount(item)
                    ),
                    "status": item.get("status", ""),
                    "paid_date": item.get("paid_date", ""),
                    "receipt": item.get("receipt_number", ""),
                })
        return rows

    def _export_reference_csv(self):
        file_path, _selected_filter = QFileDialog.getSaveFileName(
            self, "Kredi ve taksit plan\u0131n\u0131 d\u0131\u015fa aktar",
            "kredi-taksit-plani.csv", "CSV (*.csv)"
        )
        if not file_path:
            return
        rows = self._reference_export_rows()
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as output:
                writer = csv.DictWriter(output, fieldnames=(
                    "bank", "loan_id", "installment", "due_date",
                    "amount", "status", "paid_date", "receipt",
                ), delimiter=";")
                writer.writeheader()
                writer.writerows(rows)
            show_success(self, "Kredi taksitleri d\u0131\u015fa aktar\u0131ld\u0131.")
        except OSError as exc:
            show_error(self, "Dosya kaydedilemedi: {}".format(exc))

    def _print_reference_view(self):
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        rows = self._reference_export_rows()
        table_rows = "".join(
            "<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td>"
            "<td>{}</td><td>{}</td></tr>".format(
                escape(str(row["bank"])), escape(str(row["installment"])),
                escape(str(row["due_date"])), escape(str(row["amount"])),
                escape(str(row["status"])), escape(str(row["paid_date"])),
            )
            for row in rows
        )
        document = QTextDocument()
        document.setHtml(
            "<h2>Kredi ve Taksit Plan\u0131</h2><table border='1' cellspacing='0' "
            "cellpadding='6'><tr><th>Banka</th><th>Taksit</th><th>Vade</th>"
            "<th>Tutar</th><th>Durum</th><th>\u00d6deme tarihi</th></tr>{}</table>".format(
                table_rows
            )
        )
        document.print(printer)

    def _open_selected_loan_details(self):
        if self._selected_loan_id is not None:
            self.open_loan_details(self._selected_loan_id)

    def _with_selected_loan(self, callback):
        if self._selected_loan_id is None:
            return
        loan = next(
            (dict(item) for item in self.db.get_loans(active_only=False)
             if int(item["id"]) == int(self._selected_loan_id)),
            None,
        )
        if loan is None:
            return
        if callback == self.open_bulk_payment:
            callback(loan["id"], str(loan.get("bank_name") or "Kredi"))
        else:
            callback(loan["id"])

    def _cancel_selected_loan(self, loan_id):
        loan = next(
            (item for item in self.db.get_loans(active_only=False) if int(item["id"]) == int(loan_id)),
            None,
        )
        if loan:
            self.cancel_loan(loan_id, str(loan.get("bank_name") or "Kredi"))

    def _open_installment_context_menu(self, position):
        row = self.installment_table.rowAt(position.y())
        if row < 0 or row >= len(self._installment_rows):
            return
        installment = self._installment_rows[row]
        installment_id = installment.get("id")
        menu = QMenu(self.installment_table)
        if str(installment.get("status") or "").casefold() == "\u00f6dendi":
            menu.addAction("\u00d6deme Durumunu Geri Al", lambda: self.mark_installment_unpaid(installment_id))
        else:
            menu.addAction("Taksiti \u00d6dendi Olarak \u0130\u015faretle", lambda: self.mark_installment_paid(installment_id))
        menu.addAction("Kredi Detaylar\u0131", self._open_selected_loan_details)
        menu.exec(self.installment_table.viewport().mapToGlobal(position))

    def _change_installment_page(self, delta):
        self._installment_page = max(1, self._installment_page + delta)
        self._render_reference_view()

    def _render_reference_view(self, *_args):
        if not hasattr(self, "installment_table"):
            return
        loans = self._reference_filtered_loans()
        loan_total = sum(float(loan.get("amount") or 0) for loan in loans)
        all_installments = [
            dict(installment)
            for loan in loans
            for installment in self.db.get_loan_installments(loan["id"])
        ]
        paid_total = sum(
            self.get_installment_amount(item)
            for item in all_installments
            if str(item.get("status") or "").casefold() == "\u00f6dendi"
        )
        remaining_total = sum(float(loan.get("total_payment") or 0) for loan in loans) - paid_total
        next_rows = sorted(
            (item for item in all_installments if str(item.get("status") or "").casefold() != "\u00f6dendi"),
            key=lambda item: str(item.get("due_date") or ""),
        )
        next_row = next_rows[0] if next_rows else None
        monthly = self.get_installment_amount(next_row) if next_row else 0
        metric_data = (
            (loan_total, f"{len(loans)} Aktif S\u00f6zle\u015fme  \u00b7  {sum(int(loan.get('term_months') or 0) for loan in loans)} Ay Vadeli"),
            (remaining_total, f"{self._format_reference_money(paid_total)} \u00d6dendi  \u00b7  %{(paid_total / max(1, paid_total + remaining_total) * 100):.1f} Tamamland\u0131"),
            (monthly, "Sabit \u00d6demeli Faiz  \u00b7  %24 Y\u0131ll\u0131k"),
        )
        for (value_label, detail_label), (amount, detail) in zip(self.metric_values[:3], metric_data):
            value_label.setText(self._format_reference_money(amount))
            detail_label.setText(detail)
        date_label, date_detail = self.metric_values[3]
        if next_row:
            date_label.setText(str(next_row.get("due_date") or "--"))
            date_detail.setText(f"Taksit #{next_row.get('installment_no', '')} Bekliyor")
        else:
            date_label.setText("--")
            date_detail.setText("Bekleyen taksit yok")
        if not loans:
            self._selected_loan_id = None
            self.contract_name.setText("Aktif kredi bulunamad\u0131")
            self.contract_meta.clear()
            self.contract_amount.clear()
            self.installment_table.setRowCount(0)
            self.loan_page_info.setText("Toplam 0 / 0 Taksit")
            return
        loan = next(
            (item for item in loans if item.get("id") == self._selected_loan_id), loans[0]
        )
        self._selected_loan_id = loan.get("id")
        installments = [dict(item) for item in self.db.get_loan_installments(loan["id"])]
        loan_title = str(loan.get("loan_title") or "").strip()
        if not loan_title or loan_title.casefold() == "kredi":
            loan_title = str(loan.get("bank_name") or "Kredi")
        self.contract_name.setText(
            f"<span style=\"color:#ffffff;font-weight:700\">{escape(loan_title)}</span>"
        )
        bank_name = str(loan.get("bank_name") or loan_title)
        bank_upper = bank_name.upper()
        self.contract_logo.setText(
            "BBVA" if "BBVA" in bank_upper else "".join(
                part[0] for part in bank_name.split()[:3] if part
            ).upper()[:4]
        )
        self.contract_meta.setText(
            f"A\u00e7\u0131klama: {loan.get('description') or ''}"
        )
        self.contract_status.setText(
            "\u25cf  Aktif Kredi" if str(loan.get("status") or "").casefold() == "aktif"
            else str(loan.get("status") or "Kredi")
        )
        self.contract_amount.setText(
            f"TOPLAM TUTAR\n{self._format_reference_money(loan.get('amount'))}"
        )
        self.contract_rate.setText(
            f"FA\u0130Z / VADE\n%{loan.get('interest_rate') or 0} / {loan.get('term_months') or 0} Ay"
        )
        loan_paid = sum(
            self.get_installment_amount(item) for item in installments
            if str(item.get("status") or "").casefold() == "\u00f6dendi"
        )
        loan_remaining = max(0, float(loan.get("total_payment") or 0) - loan_paid)
        self.contract_remaining.setText(
            f"KALAN TUTAR\n-{self._format_reference_money(loan_remaining)}"
        )
        self.contract_end_date.setText(
            f"B\u0130T\u0130\u015e TAR\u0130H\u0130\n{installments[-1].get('due_date', '--') if installments else '--'}"
        )
        pages = max(1, (len(installments) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self._installment_page = min(max(1, self._installment_page), pages)
        start = (self._installment_page - 1) * self.PAGE_SIZE
        visible = installments[start:start + self.PAGE_SIZE]
        self._installment_rows = visible
        self.installment_table.setRowCount(len(visible))
        compact = self.height() < 700
        row_height = 32 if compact else 37
        for row_index, installment in enumerate(visible):
            number = int(installment.get("installment_no") or row_index + 1)
            amount = self.get_installment_amount(installment)
            due = str(installment.get("due_date") or "")
            status = str(installment.get("status") or "Bekliyor")
            paid = status.casefold() == "\u00f6dendi"
            upcoming = not paid and number == int(next_row.get("installment_no") or -1) if next_row else False
            values = (f"{number:02d}   Taksit {number}", self._format_reference_money(amount), due, status,
                      ("Dekont Tarihi: " + str(installment.get("paid_date") or "")) if paid else "\u2014")
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, installment.get("id"))
                if upcoming:
                    item.setBackground(QColor("#182234"))
                if column in (1, 2, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                if column == 3:
                    item.setForeground(qc("success" if paid else "warning"))
                if column == 0:
                    item.setText("")
                    cell = QWidget()
                    cell.setStyleSheet("background:transparent;border:0;")
                    cell_layout = QHBoxLayout(cell)
                    cell_layout.setContentsMargins(8, 0, 4, 0)
                    cell_layout.setSpacing(7)
                    badge = QLabel(f"{number:02d}")
                    badge_color = "#0f513e" if paid else "#6b4d14" if upcoming else "#263246"
                    badge_text = "#34d399" if paid else "#fbbf24" if upcoming else "#94a3b8"
                    badge.setStyleSheet(
                        f"QLabel{{background:{badge_color};color:{badge_text};border-radius:4px;"
                        "padding:2px 5px;font-size:10px;font-weight:700;}}"
                    )
                    title = QLabel(f"Taksit {number}")
                    title.setStyleSheet("color:#e2e8f0;font-size:11px;font-weight:600;border:0;")
                    cell_layout.addWidget(badge)
                    cell_layout.addWidget(title)
                    cell_layout.addStretch(1)
                    self.installment_table.setCellWidget(row_index, column, cell)
                elif column == 3:
                    badge = QLabel("\u2713  \u00d6dendi" if paid else "Bekliyor")
                    badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    badge_bg = "#123b31" if paid else "#49371a" if upcoming else "#263246"
                    badge_fg = "#34d399" if paid else "#fbbf24" if upcoming else "#94a3b8"
                    badge.setStyleSheet(
                        f"QLabel{{background:{badge_bg};color:{badge_fg};border:1px solid "
                        f"{'#075e4b' if paid else '#805d1d' if upcoming else '#3b4a60'};"
                        "border-radius:5px;padding:2px 7px;font-size:10px;font-weight:700;}}"
                    )
                    self.installment_table.setCellWidget(row_index, column, badge)
                elif upcoming and column == 1:
                    item.setForeground(QColor("#fbbf24"))
                self.installment_table.setItem(row_index, column, item)
            action = QPushButton(
                "\u00d6deme Detaylar\u0131" if paid else "\u015eimdi \u00d6de" if upcoming else "Taksit Plan\u0131"
            )
            action_padding = "2px 5px" if compact else "5px 9px"
            action_font = "10px" if compact else "11px"
            action.setStyleSheet(
                "QPushButton{background:#172338;color:#cbd5e1;border:1px solid #334155;"
                f"border-radius:5px;padding:{action_padding};font-size:{action_font};}}"
                if not upcoming else
                "QPushButton{background:#2563eb;color:#ffffff;border:0;border-radius:5px;"
                f"padding:{action_padding};font-size:{action_font};font-weight:700;}}"
            )
            action.setFixedHeight(24 if compact else 30)
            action.setMinimumWidth(106 if compact else 132)
            installment_id = installment.get("id")
            if upcoming:
                action.clicked.connect(lambda _checked=False, iid=installment_id: self.mark_installment_paid(iid))
            else:
                action.clicked.connect(lambda _checked=False, loan_id=loan["id"]: self.open_loan_details(loan_id))
            self.installment_table.setCellWidget(row_index, 5, action)
            self.installment_table.setRowHeight(row_index, row_height)
        paid_count = sum(
            1 for item in installments
            if str(item.get("status") or "").casefold() == "\u00f6dendi"
        )
        self.loan_page_info.setText(
            f"Toplam G\u00f6r\u00fcnt\u00fclenen: <b>{len(visible)} / {len(installments)}</b> Taksit"
            f"  \u00b7  \u00d6denen: <span style='color:#34d399'>"
            f"{paid_count}</span>"
            f"  \u00b7  Kalan: <span style='color:#fbbf24'>"
            f"{len(installments) - paid_count}</span>"
        )
        self.loan_page_label.setText(f"Sayfa {self._installment_page} / {pages}")
        self.loan_previous.setEnabled(self._installment_page > 1)
        self.loan_next.setEnabled(self._installment_page < pages)
        header_height = 34 if compact else 30
        self.installment_table.horizontalHeader().setFixedHeight(header_height)
        natural_height = header_height + len(visible) * row_height + 2
        self.installment_table.setFixedHeight(
            min(natural_height, max(260, self.height() - 230))
        )
        self.loan_schedule_panel.setFixedHeight(
            self.contract_header.height() + self.installment_table.height()
            + self.installment_footer.height()
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = event.size().height() < 700
        self.layout().setContentsMargins(8, 8, 8, 8) if compact else self.layout().setContentsMargins(18, 19, 18, 3)
        self.layout().setSpacing(6 if compact else 16)
        if hasattr(self, "contract_meta"):
            self.contract_meta.setVisible(event.size().width() >= 1120)
        if hasattr(self, "installment_table") and hasattr(self, "_installment_rows"):
            row_height = 32 if compact else 37
            for row_index in range(self.installment_table.rowCount()):
                self.installment_table.setRowHeight(row_index, row_height)
            header_height = 34 if compact else 30
            self.installment_table.horizontalHeader().setFixedHeight(header_height)
            natural_height = header_height + len(self._installment_rows) * row_height + 2
            self.installment_table.setFixedHeight(
                min(natural_height, max(260, self.height() - 230))
            )
            self.loan_schedule_panel.setFixedHeight(
                self.contract_header.height() + self.installment_table.height()
                + self.installment_footer.height()
            )

    def _apply_status_colors(self, item, column, status):
        text = str(status or "").strip().lower()
        if text in ("ödendi", "odendi", "kapalı", "kapali", "aktif"):
            item.setForeground(column, qc("success"))
        elif text in ("gecikmiş", "gecikmis", "iptal"):
            item.setForeground(column, qc("danger"))
        else:
            item.setForeground(column, qc("warning"))

    def load_loans(self):
        # 1. Mevcut ak (expanded) eleri kaydet
        expanded_ids = set()
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.isExpanded():
                try:
                    lid = item.data(0, Qt.ItemDataRole.UserRole)
                    if lid: expanded_ids.add(lid)
                except Exception as e:
                    logger.debug(f"Bank loans expanded item state read failed: {e}")

        self.tree.clear()
        self.expand_buttons.clear()
        loans = self.db.get_loans(active_only=False)
        
        font_bold = QFont(DesignTokens.FONT_NAME, 10, QFont.Weight.Bold)
        font_normal = QFont(DesignTokens.FONT_NAME, 10)
        
        for loan in loans:
            # loan: (id, bank_account_id, bank_name, amount, interest_rate, term_months, start_date, total_payment, description, status, created_at)
            item = QTreeWidgetItem(self.tree)
            item.setData(0, Qt.ItemDataRole.UserRole, loan['id']) # Store Loan ID
            item.setData(0, Qt.ItemDataRole.UserRole + 1, 'loan')
            
            # Format Data
            bank_name = loan['bank_name']
            description = loan['description'] or "-"
            amount_fmt = self._format_display_money(loan['amount'])
            rate_term = f"%{loan['interest_rate']} / {loan['term_months']} Ay"
            
            # Calculate Remaining
            installments = self.db.get_loan_installments(loan['id'])
            paid_amount = sum(self.get_installment_amount(inst) for inst in installments if inst['status'] == 'Ödendi')
            
            total_pay = loan['total_payment']
            if total_pay is None: total_pay = 0.0

            if str(loan['status']).strip().casefold() == "\u0130ptal".casefold():
                total_pay = paid_amount
            
            # If loan is closed, force remaining to 0
            if loan['status'] == 'Kapalı':
                remaining = 0.0
            else:
                remaining = total_pay - paid_amount
                
            remaining_fmt = self._format_display_money(remaining)
            
            end_date_str = ""
            if installments:
                end_date_str = installments[-1]['due_date']

            item.setText(0, bank_name)
            item.setText(1, description)
            item.setText(2, amount_fmt)
            item.setText(3, rate_term)
            item.setText(4, remaining_fmt)
            item.setText(5, loan['status'])
            item.setText(6, end_date_str)
            
            for i in range(7): 
                item.setFont(i, font_bold)
            self._apply_status_colors(item, 5, loan['status'])
            
            # Add Installments as Children
            for inst in installments:
                child = QTreeWidgetItem(item)
                child.setData(0, Qt.ItemDataRole.UserRole, inst['id'])
                child.setData(0, Qt.ItemDataRole.UserRole + 1, 'installment') # Mark as installment
                child.setData(0, Qt.ItemDataRole.UserRole + 2, loan['id']) # Store Parent Loan ID
                
                inst_amount = self.get_installment_amount(inst)
                
                # Align child columns with parent
                child.setText(0, f"  Taksit {inst['installment_no']}") # Under Bank
                child.setText(1, "") # Empty description
                child.setText(2, self._format_display_money(inst_amount)) # Under Amount
                child.setText(3, "") # Empty Rate/Term
                child.setText(4, "") # Empty Remaining
                child.setText(5, inst['status']) # Under Status (Matches index 5)
                child.setText(6, inst['due_date']) # Under End Date
                
                for i in range(7): child.setFont(i, font_normal)
                
                self._apply_status_colors(child, 5, inst['status'])

            if item.childCount() > 0:
                btn_toggle = QPushButton("▼")
                btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_toggle.setFixedSize(32, 32)
                btn_toggle.setStyleSheet(theme_qss("""
                    QPushButton {
                        background-color: @surface_alt;
                        border: 1px solid @border;
                        border-radius: 8px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: @surface_alt; }
                    QPushButton:pressed { background-color: @selection_bg; }
                """))
                # Fix: Use id(item) for hashability (Already fixed previously, ensuring consistent usage)
                btn_toggle.clicked.connect(lambda _, it=item: self.toggle_loan_item(it))
                self.tree.setItemWidget(item, 7, btn_toggle) # Index 7 (8th column)
                self.expand_buttons[id(item)] = btn_toggle
                
                # 2. Eğer bu loan_id daha önce açıksa, tekrar aç
                if loan['id'] in expanded_ids:
                    item.setExpanded(True)
                    btn_toggle.setText("▲")
                else:
                    item.setExpanded(False)
                    btn_toggle.setText("▼")
        self._render_reference_view()

    def open_edit_loan_dialog(self, loan_id):
        dlg = EditLoanDialog(self.db, loan_id, self)
        if dlg.exec():
            self.load_loans()

    def get_installment_amount(self, inst):
        if hasattr(inst, "keys") and "amount" in inst.keys():
            return inst["amount"] or 0
        if hasattr(inst, "keys") and "total_amount" in inst.keys():
            return inst["total_amount"] or 0
        return 0

    def toggle_loan_item(self, item):
        if item.isExpanded():
            self.tree.collapseItem(item)
        else:
            self.tree.expandItem(item)
        self.sync_expand_button(item)

    def sync_expand_button(self, item):
        btn = self.expand_buttons.get(id(item))
        if not btn:
            return
        btn.setText("▲" if item.isExpanded() else "▼")

    def open_loan_wizard(self):
        """Advanced Loan Wizard'ı açar"""
        dlg = AdvancedLoanWizard(self.db, self)
        if dlg.exec():
            # Refresh data after adding a loan
            self.load_loans()

    def open_context_menu(self, position):
        if not is_context_menu_enabled(self.db, page_id=105):
            return
        item = self.tree.itemAt(position)
        if not item: return

        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        # Fix: Ensure menu has valid parent
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QAction
        
        context_menu = QMenu(self.tree)
        
        if item_type == 'loan':
            loan_id = item.data(0, Qt.ItemDataRole.UserRole)
            
            action_add = QAction("Taksit Ekle", self)
            action_add.triggered.connect(lambda: show_success(self.main_window, "Taksit ekleme çok yakında."))
            
            action_pay_bulk = QAction("Toplu Ödeme Yap", self)
            action_pay_bulk.triggered.connect(lambda: self.open_bulk_payment(loan_id, item.text(0)))
            
            action_cancel = QAction("Krediyi İptal Et", self)
            
            action_cancel.triggered.connect(lambda: self.cancel_loan(loan_id, item.text(0)))

            action_delete = QAction("Krediyi Sil", self)
            action_delete.triggered.connect(lambda: self.delete_loan(loan_id))
            
            action_detail = QAction("Detaylar", self)
            action_detail.triggered.connect(lambda: self.open_loan_details(loan_id))

            action_edit = QAction("Krediyi Düzenle", self)
            action_edit.triggered.connect(lambda: self.open_edit_loan_dialog(loan_id))

            context_menu.addAction(action_edit)
            context_menu.addAction(action_pay_bulk)
            context_menu.addAction(action_detail)
            context_menu.addAction(action_add)
            context_menu.addSeparator()
            context_menu.addAction(action_cancel)
            context_menu.addAction(action_delete)
            
        elif item_type == 'installment':
            inst_id = item.data(0, Qt.ItemDataRole.UserRole)
            current_status = item.text(5)
            loan_id = item.data(0, Qt.ItemDataRole.UserRole + 2)
            
            action_pay = QAction("Borç Ödendi (İşaretle)", self)
            action_unpay = QAction("Ödemeyi Geri Al", self)
            action_detail = QAction("Detay", self)
            action_detail.triggered.connect(lambda: self.open_loan_details(loan_id))
            
            if current_status != 'Ödendi':
                action_pay.triggered.connect(lambda: self.mark_installment_paid(inst_id))
                context_menu.addAction(action_pay)
            else:
                action_unpay.triggered.connect(lambda: self.mark_installment_unpaid(inst_id))
                context_menu.addAction(action_unpay)
                
            context_menu.addAction(action_detail)

        context_menu.exec(self.tree.viewport().mapToGlobal(position))

    def mark_installment_paid(self, inst_id):
        if self.db.update_installment_status(inst_id, 'Ödendi'):
            # Check if all installments are now paid - auto-close loan
            try:
                self.db.cursor.execute("SELECT loan_id FROM loan_installments WHERE id=?", (inst_id,))
                result = self.db.cursor.fetchone()
                if result:
                    loan_id = result[0]
                    # Check if all installments for this loan are paid
                    query = "SELECT COUNT(*) FROM loan_installments WHERE loan_id=? AND status != 'Ödendi'"
                    try:
                        cols = self.db._get_table_columns("loan_installments") if hasattr(self.db, "_get_table_columns") else []
                        deleted_col = "is_deleted" if "is_deleted" in cols else ("is_archived" if "is_archived" in cols else None)
                        if deleted_col:
                            query += f" AND ({deleted_col}=0 OR {deleted_col} IS NULL)"
                    except Exception:
                        pass
                    self.db.cursor.execute(query, (loan_id,))
                    unpaid_count = self.db.cursor.fetchone()[0]
                    
                    if unpaid_count == 0:
                        # All paid - close the loan
                        self.db.cursor.execute("UPDATE loans SET status='Kapalı' WHERE id=?", (loan_id,))
                        self.db.conn.commit()
                        show_success(self.main_window, "Son taksit ödendi. Kredi kapatıldı.")
                    else:
                        show_success(self.main_window, "Taksit ödendi olarak işaretlendi.")
            except Exception as e:
                logger.error(f"Installment paid update post-processing error: {e}")
                show_success(self.main_window, "Taksit ödendi olarak işaretlendi.")
            
            self.load_loans()
        else:
            show_error(self.main_window, "İşlem başarısız.")

    def mark_installment_unpaid(self, inst_id):
        if self.db.update_installment_status(inst_id, 'Bekliyor'):
            show_success(self.main_window, "Taksit ödemesi geri alındı.")
            self.load_loans()

    def cancel_loan(self, loan_id, loan_name):
        reply = show_question(
            self,
            "Kredi \u0130ptali",
            f"{loan_name} kredisini iptal etmek istiyor musunuz? Taksit kay\u0131tlar\u0131 silinmeyecektir.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self.db.cursor.execute("SELECT status FROM loans WHERE id=?", (loan_id,))
            row = self.db.cursor.fetchone()
            if not row:
                show_error(self.main_window, "Kredi kayd\u0131 bulunamad\u0131.")
                return
            if str(row[0]).strip().casefold() == "\u0130ptal".casefold():
                show_error(self.main_window, "Bu kredi zaten iptal edilmi\u015f.")
                return
            self.db.cursor.execute("UPDATE loans SET status=? WHERE id=?", ("\u0130ptal", loan_id))
            self.db.conn.commit()
            show_success(self.main_window, "Kredi iptal edildi. Taksit ge\u00e7mi\u015fi korundu.")
            self.load_loans()
        except Exception as exc:
            try:
                self.db.conn.rollback()
            except Exception:
                pass
            logger.exception("Loan cancellation failed: %s", exc)
            show_error(self.main_window, "Kredi iptal edilirken bir hata olu\u015ftu.")

    def delete_loan(self, loan_id):
        reply = show_question(self, "Onay", "Bu krediyi ve t\u00fcm taksitlerini silmek istedi\u011finize emin misiniz")
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.db.delete_loan(loan_id):
                    show_success(self.main_window, "Kredi silindi.")
                    self.load_loans()
                else:
                    show_error(self.main_window, "Silme hatası oluştu.")
            except Exception as e:
                show_error(self.main_window, f"Hata: {e}")

    def open_loan_details(self, loan_id):
        from src.ui.dialogs.loan_detail_dialog import LoanDetailDialog
        LoanDetailDialog(self.db, loan_id, self.main_window).exec()

    def open_bulk_payment(self, loan_id, loan_name):
        """Toplu ödeme dialogunu aç"""
        from src.ui.dialogs.bulk_payment_dialog import BulkPaymentDialog
        dlg = BulkPaymentDialog(self.db, loan_id, loan_name, self)
        if dlg.exec():
            self.load_loans()

    def on_item_double_clicked(self, item, column):
        # Check if installment or loan
        if not item:
            return
            
        item_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
        
        if item_type == 'loan':
            self.toggle_loan_item(item)
            return

        if item_type == 'installment':
            inst_id = item.data(0, Qt.ItemDataRole.UserRole)
            current_status = item.text(5).strip()  # Strip whitespace (Col 5 is Status now)
            
            logger.debug(f"Double-clicked installment ID: {inst_id}, Status: '{current_status}'")
            
            if current_status in ('Ödendi', 'dendi'):
                 if ModernConfirm.ask(self, "Bu taksit odemesini iptal etmek istiyor musunuz?", "Odeme Iptali"):
                     self.mark_installment_unpaid(inst_id)
            else:
                 if ModernConfirm.ask(self, "Bu taksiti 'Odendi' olarak isaretlemek istiyor musunuz?", "Odeme Onayi"):
                     self.mark_installment_paid(inst_id)


class EditLoanDialog(BaseModernDialog):
    def __init__(self, db, loan_id, parent=None):
        super().__init__(parent, title="Kredi Düzenle", width=480, height=580)
        self.db = db
        self.loan_id = loan_id
        self.loan_data = self.db.get_loan_details(loan_id)
        self.setup_ui()
        self.load_loan_data()

    def setup_ui(self):
        form = QFormLayout()

        self.combo_bank = QLineEdit()
        form.addRow("Banka:", self.combo_bank)
        
        self.txt_desc = QLineEdit()
        form.addRow("Açıklama:", self.txt_desc)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 10000000)
        self.spin_amount.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
        form.addRow("Tutar:", self.spin_amount)

        self.spin_rate = QDoubleSpinBox()
        self.spin_rate.setRange(0, 100)
        self.spin_rate.setSingleStep(0.01)
        self.spin_rate.setSuffix(" %")
        form.addRow("Faiz (Aylık):", self.spin_rate)

        self.spin_months = QSpinBox()
        self.spin_months.setRange(1, 120)
        form.addRow("Vade (Ay):", self.spin_months)

        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        form.addRow("Başlangıç:", self.date_start)

        self.combo_status = QLineEdit() # Simpler for now, or use QComboBox
        form.addRow("Durum:", self.combo_status)

        self.content_layout.addLayout(form)

        tip = QLabel("Not: Düzenleme işlemi mevcut taksit planını bozmaz, sadece üst bilgileri günceller.")
        tip.setWordWrap(True)
        tip.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-style: italic; margin: 10px 0;"))
        self.content_layout.addWidget(tip)

        self.content_layout.addStretch()

        btn_box = QHBoxLayout()
        btn_save = QPushButton("Değişiklikleri Kaydet")
        btn_save.clicked.connect(self.save_loan)
        btn_save.setStyleSheet(theme_qss("background-color: @success; color: @selection_text; border-radius: 8px; padding: 10px 20px; font-weight: bold;"))
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(theme_qss("background-color: @disabled_text; color: @selection_text; border-radius: 8px; padding: 10px 20px; font-weight: bold;"))
        
        btn_box.addStretch()
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        self.content_layout.addLayout(btn_box)

    def load_loan_data(self):
        if not self.loan_data: return
        # loan_data: (id, bank_account_id, bank_name, amount, interest_rate, term_months, start_date, total_payment, description, status, ...)
        # Using dict access if possible, or mapping
        d = self.loan_data
        self.combo_bank.setText(str(d.get('bank_name', '')))
        self.txt_desc.setText(str(d.get('description', '')))
        self.spin_amount.setValue(float(d.get('amount', 0)))
        self.spin_rate.setValue(float(d.get('interest_rate', 0)))
        self.spin_months.setValue(int(d.get('term_months', 0)))
        self.date_start.setDate(QDate.fromString(d.get('start_date', ''), "yyyy-MM-dd"))
        self.combo_status.setText(str(d.get('status', '')))

    def save_loan(self):
        bank = self.combo_bank.text()
        if not bank: return
        
        # Yapılandırma Kontrol
        financial_changed = (
            abs(float(self.loan_data.get('amount', 0)) - self.spin_amount.value()) > 0.01 or
            abs(float(self.loan_data.get('interest_rate', 0)) - self.spin_rate.value()) > 0.01 or
            int(self.loan_data.get('term_months', 0)) != self.spin_months.value() or
            self.loan_data.get('start_date', '') != self.date_start.date().toString("yyyy-MM-dd")
        )

        regenerate_plan = False
        if financial_changed:
            if ModernConfirm.ask(
                self,
                "Finansal verilerde degisiklik tespit edildi.\n\nOdeme planini bu bilgilere gore yeniden hesaplayip olusturmak ister misiniz?\n\nMevcut taksit kayitlari silinecektir.",
                "Yapilandirma Onayi",
            ):
                regenerate_plan = True

        ok = self.db.update_loan(
            self.loan_id,
            bank_name=bank,
            principal=self.spin_amount.value(),
            interest_rate=self.spin_rate.value(),
            months=self.spin_months.value(),
            start_date=self.date_start.date().toString("yyyy-MM-dd"),
            description=self.txt_desc.text(),
            status=self.combo_status.text()
        )
        
        if ok:
            if regenerate_plan:
                try:
                    # 1. Eski taksitleri sil
                    self.db.delete_loan_installments(self.loan_id)
                    
                    # 2. Yeni plan hesapla
                    from src.utils.loan_calculator import LoanCalculator
                    calc = LoanCalculator()
                    
                    principal = self.spin_amount.value()
                    interest = self.spin_rate.value()
                    months = self.spin_months.value()
                    start_date = self.date_start.date().toPyDate() # pydate format needed for calculator usually
                    
                    # Default taxes from original loan if not editable here, 
                    # but for simplicity using 0 or common rates if available in data
                    kkdf = self.loan_data.get('kkdf_rate', 0)
                    bsmv = self.loan_data.get('bsmv_rate', 0)
                    
                    from datetime import datetime
                    s_date = datetime.combine(self.date_start.date().toPyDate(), datetime.min.time())
                    
                    plan = calc.generate_payment_plan(principal, interest, months, s_date, kkdf, bsmv)
                    
                    # 3. Yeni taksitleri ekle
                    for row in plan:
                        inst_data = {
                            'loan_id': self.loan_id,
                            'installment_no': row['installment_number'],
                            'due_date': row['due_date'],
                            'amount': row['total_amount']
                        }
                        self.db.add_loan_installment(inst_data)
                    
                    show_success(self.parent(), "Kredi yapılandırıldı ve ödeme planı güncellendi.")
                except Exception as e:
                    show_error(self, f"Yapılandırma hatası: {e}")
            else:
                show_success(self.parent(), "Kredi bilgileri güncellendi.")
            
            self.accept()
        else:
            show_error(self, "Güncelleme başarısız.")


class AddLoanDialog(BaseModernDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent, title="Yeni Kredi Ekle", width=480, height=550)
        self.db = db
        self.setup_ui()

    def _display_currency(self):
        return CurrencyHelper.get_code(self.db)

    def _format_display_money(self, amount_try):
        return CurrencyHelper.format_from_try(amount_try, db=self.db, currency_code=self._display_currency())

    def setup_ui(self):
        form = QFormLayout()

        # Bank Selection
        self.combo_bank = QLineEdit() # Simple text for now, or dropdown if we fetch banks
        self.combo_bank.setPlaceholderText("Banka Adı (örn. Garanti)")
        form.addRow("Banka:", self.combo_bank)
        
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Kredi Açıklaması (örn. İhtiyaç Kredisi)")
        form.addRow("Açıklama:", self.txt_desc)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 10000000)
        self.spin_amount.setSuffix(f" {CurrencyHelper.get_label(db=self.db)}")
        form.addRow("Kredi Tutarı:", self.spin_amount)

        self.spin_rate = QDoubleSpinBox()
        self.spin_rate.setRange(0, 100)
        self.spin_rate.setSingleStep(0.01)
        self.spin_rate.setSuffix(" %")
        form.addRow("Faiz Oranı (Aylık):", self.spin_rate)

        self.spin_months = QSpinBox()
        self.spin_months.setRange(1, 120)
        form.addRow("Vade (Ay):", self.spin_months)

        self.date_start = QDateEdit()
        self.date_start.setDate(QDate.currentDate())
        self.date_start.setCalendarPopup(True)
        form.addRow("Başlangıç Tarihi:", self.date_start)

        self.content_layout.addLayout(form)

        # Plan Button
        btn_calc = QPushButton("📊 Taksit Planı Oluştur (Önizle)")
        btn_calc.setStyleSheet(theme_qss("background-color: @accent; color: @selection_text; border-radius: 8px; padding: 10px; font-weight: bold;"))
        btn_calc.clicked.connect(self.calculate_plan)
        self.content_layout.addWidget(btn_calc)

        # Result Preview
        self.lbl_result = QLabel(
            "Toplam Geri Ödeme: "
            f"{self._format_display_money(0)}"
        )
        self.lbl_result.setStyleSheet(theme_qss("font-weight: bold; font-size: 14px; margin-top: 10px; color: @text;"))
        self.content_layout.addWidget(self.lbl_result)

        self.content_layout.addStretch()

        # Buttons - Premium style
        btn_box = QHBoxLayout()
        btn_save = QPushButton("Kaydet")
        btn_save.clicked.connect(self.save_loan)
        btn_save.setStyleSheet(theme_qss("background-color: @success; color: @selection_text; border-radius: 8px; padding: 10px 20px; font-weight: bold;"))
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(theme_qss("background-color: @disabled_text; color: @selection_text; border-radius: 8px; padding: 10px 20px; font-weight: bold;"))
        
        btn_box.addStretch()
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        self.content_layout.addLayout(btn_box)

    def calculate_plan(self):
        principal = self.spin_amount.value()
        rate_monthly = self.spin_rate.value() / 100
        months = self.spin_months.value()
        
        if principal <= 0 or months <= 0:
            return None

        # Simple Amortization Formula (Annuity)
        # PMT = P * r * (1 + r)^n / ((1 + r)^n - 1)
        if rate_monthly > 0:
            monthly_payment = principal * (rate_monthly * (1 + rate_monthly)**months) / ((1 + rate_monthly)**months - 1)
        else:
            monthly_payment = principal / months
            
        total_payment = monthly_payment * months
        self.lbl_result.setText(
            "Aylık: "
            f"{self._format_display_money(monthly_payment)}\n"
            "Toplam: "
            f"{self._format_display_money(total_payment)}"
        )
        
        return total_payment, monthly_payment

    def save_loan(self):
        bank = self.combo_bank.text()
        if not bank:
            show_warning(self, "Hata", "Banka ad\u0131 giriniz.")
            return

        res = self.calculate_plan()
        if not res: return
        total_pay, monthly_pay = res
        
        loan_data = {
            'bank_account_id': 0, # Not linked to specific account table ID yet for simplicity, or use combo
            'bank_name': bank,
            'amount': self.spin_amount.value(),
            'interest_rate': self.spin_rate.value(),
            'term_months': self.spin_months.value(),
            'start_date': self.date_start.date().toString("yyyy-MM-dd"),
            'total_payment': total_pay,
            'description': self.txt_desc.text()
        }
        
        loan_id = self.db.add_loan(loan_data)
        if loan_id:
            # Generate Installments
            start_date = self.date_start.date()
            for i in range(1, self.spin_months.value() + 1):
                due_date = start_date.addMonths(i)
                inst_data = {
                    'loan_id': loan_id,
                    'installment_no': i,
                    'due_date': due_date.toString("yyyy-MM-dd"),
                    'amount': monthly_pay
                }
                self.db.add_loan_installment(inst_data)
            
            self.accept()
        else:
            show_error(self, "Hata", "Kredi kaydedilemedi.")

