# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
                             QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QDialog as QtDialog,
                             QFormLayout, QLineEdit, QComboBox, QDateEdit, QDoubleSpinBox,
                             QMessageBox, QTreeWidget, QTreeWidgetItem, QSplitter, QFrame,
                             QSpinBox, QAbstractSpinBox, QScrollArea, QToolButton, QAbstractItemView, QMenu,
                             QGridLayout, QInputDialog, QProgressDialog, QApplication, QFileDialog, QProgressBar,
                             QListWidget, QListWidgetItem, QSizePolicy, QTextEdit, QButtonGroup)
from PyQt6.QtCore import Qt, QDate, QEvent, QTimer
from PyQt6.QtGui import QColor, QFont, QAction
import json
import csv
import html
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtGui import QTextDocument
from src.utils.theme_colors import theme_qss, tc, qc
from src.utils.design_system import DesignTokens
from src.utils.toast_notification import show_success, show_error
from src.utils.language_manager import LanguageManager
from src.utils.logger import logger
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled
from src.ui.dialogs.base_modern_dialog import BaseModernDialog

from src.ui.pages.project_management.project_detail_dialogs import AddUnitDialog, AddSubDialog


class FinanceTab(QWidget):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, project_id):
        super().__init__()
        self.db = db
        self.project_id = project_id
        self.lang = LanguageManager()
        self.init_ui()

    def init_ui(self):
        fallback_font = QFont()
        fallback_font.setFamilies(["Segoe UI", "Arial"])
        self.setFont(fallback_font)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 10, 12, 10)
        self.setStyleSheet("QWidget{background:#0e1321;color:#dee2f6;font-family:'Segoe UI','Arial';font-size:10px} QLineEdit,QComboBox{background:#161b2a;color:#dee2f6;border:1px solid #424754;border-radius:5px;padding:7px} QTableWidget{background:#0e1321;alternate-background-color:#161b2a;color:#dee2f6;gridline-color:#252a39;border:1px solid #252a39} QTableWidget::item{background:#0e1321;color:#dee2f6;padding:6px} QTableWidget::item:alternate{background:#161b2a;color:#dee2f6} QHeaderView::section{background:#161b2a;color:#c2c6d6;border:0;border-bottom:1px solid #252a39;padding:7px;font-weight:600} QPushButton{background:#252a39;color:#dee2f6;border:1px solid #424754;border-radius:5px;padding:7px 10px} QPushButton:hover{background:#303444}")
        self.dashboard_title = QLabel("Proje Finans Durumu & Nakit Ak\u0131\u015f\u0131 | CANLI DEFTER")
        self.dashboard_title.setFont(QFont("Segoe UI", 16, QFont.Weight.DemiBold))
        self.dashboard_title.setStyleSheet("color:#dee2f6;padding:4px 2px;")
        self.dashboard_title.setMaximumHeight(42)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)
        toolbar.addWidget(self.dashboard_title, 1)
        layout.addLayout(toolbar)

        # ── Özet Kartları (2 satır) ────────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        self.card_income   = self.create_summary_card("✅ Tahsil Edilen Gelir",  self._fmt_try(0), tc("success"))
        self.card_expense  = self.create_summary_card("💸 Ödenen Gider",         self._fmt_try(0), tc("danger"))
        self.card_profit   = self.create_summary_card("📈 Net Kâr",              self._fmt_try(0), tc("accent"))
        row1.addWidget(self.card_income)
        row1.addWidget(self.card_expense)
        row1.addWidget(self.card_profit)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        self.card_income_pending  = self.create_summary_card("⏳ Bekleyen Gelir",  self._fmt_try(0), tc("warning"), small=True)
        self.card_expense_pending = self.create_summary_card("⏳ Bekleyen Gider",  self._fmt_try(0), tc("warning"), small=True)
        row1.addWidget(self.card_income_pending)
        row1.addWidget(self.card_expense_pending)
        self.card_income_pending.setFixedHeight(80)
        self.card_expense_pending.setFixedHeight(80)

        # ── Butonlar ─────────────────────────────────────────────────────────
        btn_layout = QHBoxLayout()
        self.btn_income = QPushButton("➕ Gelir Ekle")
        self.btn_income.setStyleSheet(theme_qss("background-color: @success; color: @selection_text; border-radius: 6px; padding: 6px 14px; font-weight: bold;"))
        self.btn_income.clicked.connect(lambda: self.open_transaction_dialog("Gelir"))

        self.btn_expense = QPushButton("➖ Gider Ekle")
        self.btn_expense.setStyleSheet(theme_qss("background-color: @danger; color: @selection_text; border-radius: 6px; padding: 6px 14px; font-weight: bold;"))
        self.btn_expense.clicked.connect(lambda: self.open_transaction_dialog("Gider"))

        btn_layout.addWidget(self.btn_income)
        btn_layout.addWidget(self.btn_expense)
        self.btn_pdf = QPushButton("PDF Raporu \u0130ndir")
        self.btn_pdf.clicked.connect(lambda: self._export_report("pdf"))
        self.btn_excel = QPushButton("Excel D\u00f6k\u00fcm\u00fc")
        self.btn_excel.clicked.connect(lambda: self._export_report("csv"))
        btn_layout.addWidget(self.btn_pdf)
        btn_layout.addWidget(self.btn_excel)
        btn_layout.addStretch()
        toolbar.addLayout(btn_layout)
        self.budget_label = QLabel("Proje B\u00fct\u00e7e Ger\u00e7ekle\u015fme Oran\u0131 | Nakit/Banka | Hakedi\u015f Avans | Bor\u00e7/Alacak Denge")
        self.budget_label.setMinimumHeight(46)
        self.budget_label.setMaximumHeight(64)
        self.budget_label.setStyleSheet("background:#161b2a;color:#adc6ff;border-radius:6px;padding:9px;font-weight:600;")
        layout.addWidget(self.budget_label)

        # ── İşlem Tablosu (6 sütun — Durum dahil) ────────────────────────────
        filter_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("\u0130\u015flem no, a\u00e7\u0131klama, fatura veya cari ara...")
        self.filter_date = QComboBox()
        self.filter_date.addItem("T\u00fcm Tarihler", "all")
        self.filter_date.addItem("Bug\u00fcn", "today")
        self.filter_date.addItem("Bu Hafta", "this_week")
        self.filter_date.addItem("Eyl\u00fcl 2026", "2026-09")
        self.filter_type = QComboBox()
        self.filter_type.addItem("T\u00fcm T\u00fcrler", "all")
        self.filter_type.addItem("Gelir", "Gelir")
        self.filter_type.addItem("Gider", "Gider")
        self.filter_category = QComboBox()
        self.filter_category.addItem("T\u00fcm Kategoriler", "all")
        self.filter_channel = QComboBox()
        self.filter_channel.addItem("T\u00fcm \u00d6deme Kanallar\u0131", "all")
        self.filter_status = QComboBox()
        self.filter_status.addItem("T\u00fcm Durumlar", "all")
        self.filter_status.addItem("\u00d6dendi / Tahsil Edildi", "paid")
        self.filter_status.addItem("Bekliyor", "pending")
        self.filter_reset = QPushButton("Filtreleri Temizle")
        for widget in (self.search_input, self.filter_date, self.filter_type, self.filter_category, self.filter_channel, self.filter_status, self.filter_reset):
            filter_layout.addWidget(widget, 1)
        layout.addLayout(filter_layout)
        self.search_input.textChanged.connect(self.load_data)
        for widget in (self.filter_date, self.filter_type, self.filter_category, self.filter_channel, self.filter_status):
            widget.currentIndexChanged.connect(self.load_data)
        self.filter_reset.clicked.connect(self._reset_filters)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["#", "\u0130\u015flem Tarihi", "T\u00fcr", "Kategori", "A\u00e7\u0131klama / Detay", "\u00d6deme Kanal\u0131", "Vade / Belge No", "Tutar & Durum"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemDoubleClicked.connect(self.open_detail_dialog)
        self.table.setMaximumHeight(260)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        layout.addWidget(self.table)
        self.footer_label = QLabel("0 hareket g\u00f6steriliyor | Net denge: 0")
        self.footer_label.setStyleSheet("color:#c2c6d6;padding:6px;")
        self.footer_label.setFixedHeight(32)
        layout.addWidget(self.footer_label)
        self.sync_label = QLabel("E-Fatura & Mali Senkronizasyon Durumu | Senkronize Edildi")
        self.sync_label.setMinimumHeight(34)
        self.sync_label.setMaximumHeight(42)
        self.sync_label.setStyleSheet("background:#161b2a;color:#4cd7f6;border-radius:5px;padding:7px;")
        layout.addWidget(self.sync_label)

    def _reset_filters(self):
        self.search_input.clear()
        for widget in (self.filter_date, self.filter_type, self.filter_category, self.filter_channel, self.filter_status):
            widget.setCurrentIndex(0)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()

    def update_texts(self):
        self.load_data()

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_try_for_display(
            amount,
            db=self.db,
            include_try_reference=include_try_reference,
        )

    def _get_project_currency(self):
        try:
            currency, rate = self.db.get_project_currency(self.project_id)
            return (currency or "TRY").upper(), float(rate or 1.0)
        except Exception:
            return "TRY", 1.0

    def _fmt_project_amount(self, amount_try):
        project_currency, _project_rate = self._get_project_currency()
        amount_try = float(amount_try or 0)
        if project_currency == "TRY":
            return CurrencyHelper.format_amount(amount_try, db=self.db, currency_code="TRY")
        converted = CurrencyHelper.convert_amount(self.db, amount_try, "TRY", project_currency)
        primary = CurrencyHelper.format_amount(converted, db=self.db, currency_code=project_currency)
        secondary = CurrencyHelper.format_amount(amount_try, db=self.db, currency_code="TRY")
        return f"{primary} ({secondary})"

    def _effective_rate(self, amount_try, original_amount, stored_rate, project_rate):
        try:
            original_amount = float(original_amount or 0)
            amount_try = float(amount_try or 0)
            stored_rate = float(stored_rate or 0)
            if stored_rate > 1.0001:
                return stored_rate
            if original_amount > 0 and amount_try > 0:
                derived = amount_try / original_amount
                if derived > 1.0001:
                    return derived
            if float(project_rate or 0) > 1.0001:
                return float(project_rate)
        except Exception:
            pass
        return 1.0

    def _pretty_txn_description(self, txn, project_currency, project_rate):
        desc = (txn["description"] or "") if "description" in txn.keys() else ""
        original_amount = txn["original_amount"] if "original_amount" in txn.keys() else None
        original_currency = ((txn["original_currency"] if "original_currency" in txn.keys() else project_currency) or project_currency).upper()
        amount_try = float(txn["amount"] or 0)
        stored_rate = txn["exchange_rate"] if "exchange_rate" in txn.keys() else None

        if original_amount in (None, "", 0) or original_currency == "TRY":
            return desc

        rate = self._effective_rate(amount_try, original_amount, stored_rate, project_rate)
        symbol = CurrencyHelper.get_symbol(db=self.db, currency_code=original_currency)
        kind = "Proje bütçesi" if (txn["type"] or "").lower() == "gelir" else "Proje maliyeti"
        project_name = desc.split(":", 1)[1].split("[", 1)[0].strip() if ":" in desc else ""
        base_text = f"{kind}: {project_name}".strip(": ").strip()
        return (
            f"{base_text} "
            f"[{float(original_amount):,.2f} {symbol} @ {rate:.4f} = {amount_try:,.2f} TL]"
        )

    def create_summary_card(self, title, value, color, small=False):
        frame = QFrame()
        accent = "#4cd7f6" if small else "#4edea3" if color == tc("success") else "#ffb4ab" if color == tc("danger") else "#adc6ff"
        frame.setStyleSheet(f"QFrame{{background:#1a1f2e;border:1px solid #252a39;border-left:3px solid {accent};border-radius:7px;color:#dee2f6;}}")
        h, font_size = (92, 11) if small else (92, 14)
        frame.setFixedHeight(h)
        l = QVBoxLayout(frame)
        l.setContentsMargins(10, 6, 10, 6)
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color:#c2c6d6;font-size:10px;letter-spacing:1px;")
        lbl_v = QLabel(value)
        lbl_v.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
        lbl_v.setStyleSheet("color:#dee2f6;font-size:18px;font-weight:700;")
        l.addWidget(lbl_t)
        l.addWidget(lbl_v)
        frame.lbl_title_ref = lbl_t
        frame.lbl_value = lbl_v
        return frame

    def load_data(self):
        project_currency, project_rate = self._get_project_currency()

        # ── Özet kartları ──────────────────────────────────────────────────
        fin = self.db.get_project_financials(self.project_id)
        self.card_income.lbl_value.setText(self._fmt_project_amount(fin.get('income', 0)))
        self.card_expense.lbl_value.setText(self._fmt_project_amount(fin.get('expense', 0)))
        self.card_profit.lbl_value.setText(self._fmt_project_amount(fin.get('profit', 0)))
        self.card_income_pending.lbl_value.setText(self._fmt_project_amount(fin.get('income_pending', 0)))
        self.card_expense_pending.lbl_value.setText(self._fmt_project_amount(fin.get('expense_pending', 0)))

        # ── İşlem tablosu ─────────────────────────────────────────────────
        txns = list(self.db.get_project_transactions(self.project_id))
        categories = sorted({str(txn["category"] or "") for txn in txns if txn["category"]})
        channels = sorted({str(txn["payment_method"] or "") for txn in txns if txn["payment_method"]})
        for widget, values in ((self.filter_category, categories), (self.filter_channel, channels)):
            current = widget.currentData()
            widget.blockSignals(True)
            while widget.count() > 1:
                widget.removeItem(1)
            for value in values:
                widget.addItem(value, value)
            index = widget.findData(current)
            widget.setCurrentIndex(max(0, index))
            widget.blockSignals(False)
        normalize = lambda value: str(value or "").casefold().translate(str.maketrans({"\u00f6": "o", "\u00fc": "u", "\u015f": "s", "\u0131": "i", "\u00e7": "c", "\u011f": "g"}))
        query = normalize(self.search_input.text().strip())
        type_filter = self.filter_type.currentData()
        category_filter = self.filter_category.currentData()
        channel_filter = self.filter_channel.currentData()
        status_filter = self.filter_status.currentData()
        date_filter = self.filter_date.currentData()
        today = QDate.currentDate()
        week_start = today.addDays(1 - today.dayOfWeek())
        def matches_date(txn):
            value = str(txn["date"] or "")[:10]
            if date_filter == "all":
                return True
            if date_filter == "today":
                return value == today.toString("yyyy-MM-dd")
            if date_filter == "this_week":
                return week_start.toString("yyyy-MM-dd") <= value <= today.toString("yyyy-MM-dd")
            return value.startswith(str(date_filter))
        txns = [txn for txn in txns if
                matches_date(txn) and
                (not query or query in normalize(" ".join(str(txn[key] or "") for key in txn.keys()))) and
                (type_filter == "all" or str(txn["type"] or "") == type_filter) and
                (category_filter == "all" or str(txn["category"] or "") == category_filter) and
                (channel_filter == "all" or str(txn["payment_method"] or "") == channel_filter) and
                (status_filter == "all" or (status_filter == "paid" and normalize(txn["status"]) in ("odendi", "tahsil edildi")) or (status_filter == "pending" and normalize(txn["status"]) not in ("odendi", "tahsil edildi")))]
        self.visible_transactions = txns
        self.footer_label.setText(f"{len(txns)} hareket g\u00f6steriliyor | Net denge: {self._fmt_project_amount(fin.get('profit', 0))}")
        self.table.setRowCount(len(txns))
        for row, txn in enumerate(txns):
            date_str  = txn['date'] or ''
            t_type    = txn['type'] or ''
            category  = txn['category'] or ''
            desc      = self._pretty_txn_description(txn, project_currency, project_rate)
            pmethod   = txn['payment_method'] or ''
            amount    = float(txn['amount'] or 0)
            status    = txn['status'] or 'Ödenmedi'
            original_amount = txn['original_amount'] if 'original_amount' in txn.keys() else None
            original_currency = (txn['original_currency'] if 'original_currency' in txn.keys() else 'TRY') or 'TRY'

            self.table.setItem(row, 0, QTableWidgetItem(str(row + 1).zfill(2)))
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            self.table.item(row, 1).setData(Qt.ItemDataRole.UserRole, txn)
            self.table.setItem(row, 2, QTableWidgetItem(t_type))
            self.table.setItem(row, 3, QTableWidgetItem(category))
            party = str(txn["counterparty"] or "") if "counterparty" in txn.keys() else ""
            desc_item = QTableWidgetItem(f"{desc}\n{party}" if party else desc)
            desc_item.setToolTip(f"{desc}\n{party}" if party else desc)
            self.table.setItem(row, 4, desc_item)
            self.table.setItem(row, 5, QTableWidgetItem(pmethod))
            invoice = str(txn["invoice_no"] or txn["document_no"] or "") if "invoice_no" in txn.keys() and "document_no" in txn.keys() else ""
            due_date = str(txn["due_date"] or "") if "due_date" in txn.keys() else ""
            due_document = " / ".join(value for value in (due_date, invoice) if value)
            self.table.setItem(row, 6, QTableWidgetItem(due_document or "-"))

            # Tutar + durum ikonu
            durum_icon = "✅" if status == 'Ödendi' else "⏳"
            if original_amount not in (None, "", 0) and str(original_currency).upper() != "TRY":
                amount_text = CurrencyHelper.format_original_and_try(
                    float(original_amount),
                    original_currency,
                    db=self.db,
                )
            else:
                amount_text = self._fmt_project_amount(amount if project_currency != "TRY" else amount)
            amt_item = QTableWidgetItem(f"{durum_icon} {amount_text}")
            if t_type == 'Gelir':
                amt_item.setForeground(qc("success"))
            else:
                amt_item.setForeground(qc("danger"))
            self.table.setItem(row, 7, amt_item)
            if party:
                amt_item.setToolTip(f"{amount_text}\n{status}\n{party}")

        try:
            self.table.resizeRowsToContents()
        except Exception:
            pass

    def open_transaction_dialog(self, txn_type):
        from src.ui.dialogs.project_transaction_dialog import ProjectTransactionDialog
        dlg = ProjectTransactionDialog(self.db, self.project_id, txn_type, self)
        if dlg.exec():
            self.load_data()

    def _export_report(self, file_type):
        extension = "pdf" if file_type == "pdf" else "csv"
        path, _selected = QFileDialog.getSaveFileName(self, "Finans Raporunu Kaydet", f"proje-finans.{extension}", f"{extension.upper()} (*.{extension})")
        if not path:
            return
        headers = ["No", "Tarih", "Tur", "Kategori", "Aciklama", "Odeme", "Vade / Belge No", "Tutar / Durum"]
        rows = [[self.table.item(row, column).text() if self.table.item(row, column) else "" for column in range(8)] for row in range(self.table.rowCount())]
        if file_type == "csv":
            with open(path, "w", encoding="utf-8-sig", newline="") as output:
                writer = csv.writer(output, delimiter=";")
                writer.writerow(headers)
                writer.writerows(rows)
            show_success(self, "CSV raporu kaydedildi.")
            return
        table_rows = "".join("<tr>" + "".join(f"<td>{html.escape(value)}</td>" for value in row) + "</tr>" for row in rows)
        document = QTextDocument()
        document.setDefaultFont(QFont("Segoe UI", 9))
        document.setHtml("<h2>Proje Finans Durumu</h2><table border='1' cellspacing='0' cellpadding='5'><tr>" + "".join(f"<th>{html.escape(value)}</th>" for value in headers) + "</tr>" + table_rows + "</table>")
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        document.print(printer)
        show_success(self, "PDF raporu kaydedildi.")

    def open_detail_dialog(self, item):
        row = item.row()
        txn_data = self.table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        if txn_data:
            from src.ui.dialogs.transaction_detail_dialog import TransactionDetailDialog
            TransactionDetailDialog(self, txn_data).exec()

# --- TAB 2: UNITS / STOCK (Akıllı Ev Oda/Ürün Takibi) ---

class UnitsTab(QWidget):
    def __init__(self, db, project_id, project_page=None):
        super().__init__()
        self.db = db
        self.project_id = project_id
        self.project_page = project_page   # ProjectDetailPage referansı
        self.lang = LanguageManager()
        self.init_ui()

    def init_ui(self):
        fallback_font = QFont()
        fallback_font.setFamilies(["Segoe UI", "Arial"])
        self.setFont(fallback_font)
        self.setStyleSheet("QWidget{background:#0e1321;color:#dee2f6;font-family:'Segoe UI','Arial'} QComboBox { background: #1e293b; color: #e2e8f0; border: 1px solid #26364d; border-radius: 5px; padding: 4px 8px; } QComboBox QAbstractItemView { background: #0b1222; color: #e2e8f0; selection-background-color: #2563eb; } QPushButton{background:#1e293b;color:#cbd5e1;border:1px solid #26334a;border-radius:4px;padding:6px 10px}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # ── Araç Çubuğu ──────────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self.btn_add = QPushButton("+ Blok ve Daire Olu\u015ftur")
        self.btn_add.setFixedHeight(36)
        self.btn_add.setStyleSheet(theme_qss(
            "QPushButton { background-color: @accent; color: @selection_text; "
            "border-radius: 7px; font-weight: bold; font-size: 13px; padding: 0 16px; } "
            "QPushButton:hover { background-color: @accent_hover; }"
        ))
        self.btn_add.clicked.connect(self.open_add_unit_dialog)
        toolbar.addWidget(self.btn_add)
        self.btn_add_single = QPushButton("+ Tekil Daire / Oda Ekle")
        self.btn_add_single.setFixedHeight(36)
        self.btn_add_single.clicked.connect(self.open_add_unit_dialog)
        toolbar.addWidget(self.btn_add_single)

        self.filter_status = QComboBox()
        self.filter_status.addItem("T\u00fcm\u00fc", "all")
        self.filter_status.addItem("Devam Eden", "active")
        self.filter_status.addItem("Tamamlanan", "completed")
        self.filter_status.currentIndexChanged.connect(self.load_data)
        self.filter_status.hide()
        status_row = QHBoxLayout()
        status_row.setSpacing(4)
        self.status_filter_group = QButtonGroup(self)
        self.status_filter_group.setExclusive(True)
        self.status_filter_buttons = {}
        for key, label in (("all", "T\u00fcm\u00fc"), ("active", "Devam Eden"), ("completed", "Tamamlanan")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setProperty("status_key", key)
            button.setProperty("skipThemeTransform", True)
            button.setStyleSheet("QPushButton { background: #111827; color: #9aa7ba; border: 1px solid #26334a; border-radius: 4px; padding: 5px 9px; font-size: 10px; } QPushButton:checked { background: #1e3a5f; color: #93c5fd; border-color: #3b82f6; }")
            button.clicked.connect(lambda checked, value=key: self._set_status_filter(value))
            self.status_filter_group.addButton(button)
            self.status_filter_buttons[key] = button
            status_row.addWidget(button)
        self.status_filter_buttons["all"].setChecked(True)
        toolbar.addLayout(status_row)
        self.btn_bulk_status = QPushButton("Toplu Durum G\u00fcncelle")
        self.btn_bulk_status.clicked.connect(self.update_all_unit_statuses)
        toolbar.addWidget(self.btn_bulk_status)
        self.btn_view_mode = QPushButton("Kompakt Liste")
        self.btn_view_mode.setCheckable(True)
        self.btn_view_mode.toggled.connect(self.load_data)
        toolbar.addWidget(self.btn_view_mode)
        toolbar.addStretch(1)

        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("\U0001F50D Oda / daire ara... (\u00f6rn: A-1, B-4, Salon, Engin)")
        self.search_inp.setFixedHeight(36)
        self.search_inp.setMinimumWidth(320)
        self.search_inp.setStyleSheet(theme_qss(
            "QLineEdit { border: 1px solid @border; border-radius: 7px; padding: 0 10px; "
            "background: @surface; color: @text; font-size: 12px; }"
        ))
        self.search_inp.textChanged.connect(self.load_data)
        search_row = QHBoxLayout()
        search_row.addWidget(self.search_inp, 1)

        self.btn_export = QPushButton("\u25a6 Excel Raporu")
        self.btn_export.setFixedHeight(36)
        self.btn_export.setStyleSheet(theme_qss(
            "QPushButton { background-color: @success; color: @selection_text; "
            "border-radius: 7px; font-weight: bold; font-size: 12px; padding: 0 14px; } "
            "QPushButton:hover { background-color: @success; }"
        ))
        self.btn_export.clicked.connect(self.export_to_excel)
        toolbar.addWidget(self.btn_export)

        lbl_info = QLabel("\u00c7ift t\u0131k: \u00dcr\u00fcn ekle   |   Sa\u011f t\u0131k: Durum de\u011fi\u015ftir")
        lbl_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
        search_row.addWidget(lbl_info)
        layout.addLayout(toolbar)
        layout.addLayout(search_row)

        # ── Grid ─────────────────────────────────────────────────────────────
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(theme_qss("QScrollArea { border: none; background: transparent; }"))

        self.scroll_content = QWidget()
        self.scroll_content.setStyleSheet("background-color: #0e1321; color: #dee2f6;")
        content_layout = QVBoxLayout(self.scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)
        self.block_summary = QLabel("")
        self.block_summary.setMinimumHeight(48)
        self.block_summary.setStyleSheet("background:#161b2a;color:#dee2f6;border-radius:6px;padding:8px;font-weight:600;")
        content_layout.addWidget(self.block_summary)
        self.grid_host = QWidget()
        self.grid_host.setStyleSheet("background:transparent;")
        self.grid = QGridLayout(self.grid_host)
        self.grid.setSpacing(14)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.addWidget(self.grid_host, 1)

        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

        self.load_data()

    def update_texts(self):
        pass

    def _set_status_filter(self, key):
        index = self.filter_status.findData(key)
        if index == self.filter_status.currentIndex():
            self.load_data()
        else:
            self.filter_status.setCurrentIndex(index)

    def load_data(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                widget = item.widget()
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        units = list(self.db.get_project_root_units(self.project_id))
        all_units = units[:]

        # Arama filtresi
        normalize_search = lambda value: str(value or "").casefold().translate(str.maketrans({"\u0131": "i", "\u00f6": "o", "\u00fc": "u", "\u015f": "s", "\u00e7": "c", "\u011f": "g"}))
        status_counts = {"all": len(all_units), "active": 0, "completed": 0}
        for item in all_units:
            raw_status = item["status"] if hasattr(item, "keys") else (item[5] if len(item) > 5 else "")
            normalized_status = normalize_search(raw_status)
            if "tamam" in normalized_status:
                status_counts["completed"] += 1
            elif "devam" in normalized_status:
                status_counts["active"] += 1
        for key, label in (("all", "T\u00fcm\u00fc"), ("active", "Devam Eden"), ("completed", "Tamamlanan")):
            button = self.status_filter_buttons[key]
            button.setText(f"{label} ({status_counts[key]})")
            button.setChecked(self.filter_status.currentData() == key)
        search = normalize_search(self.search_inp.text().strip()) if hasattr(self, 'search_inp') else ""
        selected_status = self.filter_status.currentData() if hasattr(self, "filter_status") else "all"
        if search:
            def _match(u):
                def field(name, index):
                    if hasattr(u, "keys"):
                        return u[name] if name in u.keys() else ""
                    return u[index] if len(u) > index else ""
                searchable = " ".join(str(field(name, index) or "") for name, index in (("unit_no", 4), ("block_name", 2), ("floor_no", 3), ("direction", 6), ("unit_kind", 7), ("status", 5), ("responsible_name", 8), ("room_names", 9)))
                return search in normalize_search(searchable)
            units = [u for u in units if _match(u)]
        if selected_status != "all":
            def status_matches(unit):
                status = unit["status"] if hasattr(unit, "keys") else (unit[5] if len(unit) > 5 else "")
                normalized = str(status or "").casefold().replace("\u0131", "i").replace("\u00f6", "o").replace("\u015f", "s")
                return ("tamam" in normalized) if selected_status == "completed" else ("devam" in normalized)
            units = [unit for unit in units if status_matches(unit)]

        block_names = [str((unit["block_name"] or "A Blok") if hasattr(unit, "keys") else (unit[2] or "A Blok")) for unit in all_units]
        block_name = block_names[0] if block_names else "A Blok"
        completion_values = []
        for unit in all_units:
            status = unit["status"] if hasattr(unit, "keys") else (unit[5] if len(unit) > 5 else "")
            normalized = str(status or "").casefold().replace("\u0131", "i").replace("\u00f6", "o").replace("\u015f", "s")
            completion_values.append(100 if "tamam" in normalized else 50 if "devam" in normalized else 0)
        average = round(sum(completion_values) / len(completion_values), 1) if completion_values else 0
        self.block_summary.setText(f"{block_name} Daireleri   |   {len(all_units)} Ba\u011f\u0131ms\u0131z B\u00f6l\u00fcm   |   Ortalama Tamamlanma %{average}")

        if not units:
            empty_lbl = QLabel("Henüz oda/daire eklenmedi veya arama sonucu bulunamadı.")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet(theme_qss("color: @text_muted; font-size: 14px;"))
            self.grid.addWidget(empty_lbl, 0, 0)
            if self.project_page:
                self.project_page.refresh_summary()
            return

        cols = 1 if self.btn_view_mode.isChecked() else max(1, min(4, self.scroll.viewport().width() // 240))
        for column in range(cols):
            self.grid.setColumnStretch(column, 1)
        for idx, unit in enumerate(units):
            ri, ci = idx // cols, idx % cols
            card = UnitCard(unit, self)
            self.grid.addWidget(card, ri, ci)
            card.show()
        self.grid.activate()

        if self.project_page:
            self.project_page.refresh_summary()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self.load_data)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.load_data)

    def open_add_unit_dialog(self):
        dlg = AddUnitDialog(self.db, self.project_id, self)
        if dlg.exec():
            self.load_data()

    def open_unit_products(self, unit):
        dlg = UnitProductsDialog(self.db, self.project_id, unit, self)
        dlg.exec()
        self.load_data()

    def change_unit_status(self, unit_id, status):
        self.db.set_unit_install_status(unit_id, status)
        self.load_data()

    def update_all_unit_statuses(self):
        statuses = ["Bekliyor", "Devam Ediyor", "Tamamland\u0131"]
        status, accepted = QInputDialog.getItem(self, "Toplu Durum G\u00fcncelle", "Yeni durum:", statuses, 0, False)
        if not accepted:
            return
        for unit in self.db.get_project_root_units(self.project_id):
            unit_id = unit["id"] if hasattr(unit, "keys") else unit[0]
            self.db.set_unit_install_status(unit_id, status)
        self.load_data()

    # ── Excel Export ─────────────────────────────────────────────────────────
    def export_to_excel(self):
        try:
            import pandas as pd
            from PyQt6.QtWidgets import QFileDialog
            import os, datetime
            from src.ui.utils.ui_helpers import show_success, show_error, show_warning

            path, _ = QFileDialog.getSaveFileName(
                self, "Excel Raporu Kaydet", 
                f"kurulum_raporu_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", 
                "Excel Dosyası (*.xlsx);;CSV Dosyası (*.csv)"
            )
            if not path:
                return

            units = self.db.get_project_units(self.project_id)
            if not units:
                show_warning(self, "Raporlanacak oda/daire bulunamadı.")
                return

            all_products = self.db.get_project_unit_products(self.project_id)
            products_by_unit = {}
            direct_counts = {}
            for product in all_products:
                product_unit_id = (
                    product["unit_id"]
                    if hasattr(product, "keys")
                    else product[1]
                )
                products_by_unit.setdefault(product_unit_id, []).append(product)
                direct_counts[product_unit_id] = (
                    direct_counts.get(product_unit_id, 0) + 1
                )

            child_units = {}
            for unit in units:
                unit_id = unit["id"] if hasattr(unit, "keys") else unit[0]
                parent_id = (
                    unit["parent_unit_id"]
                    if hasattr(unit, "keys")
                    else (unit[12] if len(unit) > 12 else None)
                )
                if parent_id is not None:
                    child_units.setdefault(parent_id, []).append(unit_id)

            # Sheet 1: Unit Summary
            unit_data = []
            for unit in units:
                if isinstance(unit, dict):
                    uid, block, uno, st = unit.get('id'), unit.get('block_name',''), unit.get('unit_no',''), unit.get('status','Bekliyor')
                else:
                    uid, block, uno, st = unit[0], unit[2], unit[4], (unit[5] if len(unit) > 5 else 'Bekliyor')

                installed_count = direct_counts.get(uid, 0)
                installed_count += sum(
                    direct_counts.get(child_id, 0)
                    for child_id in child_units.get(uid, [])
                )
                unit_data.append({
                    "Blok": block,
                    "Daire / Oda": uno,
                    "Durum": st,
                    "Kurulu \u00dcr\u00fcn Say\u0131s\u0131": installed_count,
                })
            
            df_units = pd.DataFrame(unit_data)

            # Sheet 2: Product Details
            prod_data = []
            for unit in units:
                if isinstance(unit, dict):
                    uid, block, uno = unit.get('id'), unit.get('block_name',''), unit.get('unit_no','')
                else:
                    uid, block, uno = unit[0], unit[2], unit[4]
                
                for prod in products_by_unit.get(uid, []):
                    if isinstance(prod, dict):
                        pname, pcode, qty, note, added = prod.get('part_name',''), prod.get('part_code','-') or '-', prod.get('quantity',1), prod.get('notes','') or '', prod.get('added_at','') or ''
                    else:
                        pname = prod[4] if len(prod) > 4 else ''
                        pcode = prod[5] if len(prod) > 5 else '-'
                        qty   = prod[6] if len(prod) > 6 else 1
                        note  = prod[7] if len(prod) > 7 else ''
                        added = prod[8] if len(prod) > 8 else ''
                    
                    prod_data.append({
                        "Blok": block,
                        "Daire / Oda": uno,
                        " \u00dcr\u00fcn Ad\u0131": pname,
                        "Kod": pcode,
                        "Adet": qty,
                        "Teknik Not": note,
                        "Eklenme Tarihi": added
                    })
            
            df_prods = pd.DataFrame(prod_data)

            if path.endswith(".csv"):
                # For CSV, we can only save one sheet. Usually we save the more detailed one.
                df_prods.to_csv(path, index=False, encoding="utf-8-sig", sep=";")
            else:
                with pd.ExcelWriter(path) as writer:
                    df_units.to_excel(writer, sheet_name="Oda Özeti", index=False)
                    df_prods.to_excel(writer, sheet_name="Ürün Detayları", index=False)
                
            show_success(self, f"Rapor oluşturuldu:\n{os.path.basename(path)}")
            try:
                os.startfile(path)
            except Exception:
                pass
        except Exception as e:
            show_error(self, f"Rapor oluşturulamadı: {e}")


# --- UNIT CARD (küçük kutu) ---

class UnitCard(QFrame):
    """Tek bir daire/odayı temsil eden küçük kart widgeti."""

    # Durum → (kenarlık rengi, etiket metni, etiket rengi)
    _STATUS_MAP = {
        'Tamamlandı':   ('#4CAF50', '✅ Tamamlandı',   '#4CAF50'),
        'Devam Ediyor': ('#4cd7f6', '\U0001f504 Devam Ediyor', '#4cd7f6'),
        'Bekliyor':     (None,      '⏳ Bekliyor',      None),
    }
    _STATUS_ORDER = ['Bekliyor', 'Devam Ediyor', 'Tamamlandı']

    def __init__(self, unit, parent_tab):
        super().__init__()
        fallback_font = QFont()
        fallback_font.setFamilies(["Segoe UI", "Arial"])
        self.setFont(fallback_font)
        self.unit = unit
        self.parent_tab = parent_tab
        def value(key, index=None, default=""):
            if hasattr(unit, "keys"):
                try:
                    return unit[key] if unit[key] is not None else default
                except (KeyError, IndexError):
                    return default
            return unit[index] if index is not None and len(unit) > index and unit[index] is not None else default
        self.unit_id = value("id", 0)
        self.block_name = str(value("block_name", 2, "A Blok") or "A Blok")
        self.unit_no = str(value("unit_no", 4, "") or "")
        raw_status = str(value("status", 5, "Bekliyor") or "Bekliyor")
        self.status = raw_status if raw_status in self._STATUS_MAP else "Bekliyor"
        self.setMinimumSize(220, 238)
        self.setMaximumWidth(340)
        self.setMaximumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setProperty("skipThemeTransform", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.setStyleSheet("QFrame{background:#161b2a;border:1px solid #1e293b;border-radius:7px;} QLabel{border:0;background:transparent;color:#dee2f6;}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 9, 10, 8)
        layout.setSpacing(7)
        header = QHBoxLayout()
        block = QLabel(self.block_name[:1])
        block.setFixedSize(30, 30)
        block.setAlignment(Qt.AlignmentFlag.AlignCenter)
        block.setStyleSheet("background:#252a39;color:#adc6ff;border-radius:5px;font-weight:bold;font-size:13px;")
        header.addWidget(block)
        identity = QVBoxLayout()
        title = QLabel(f"Daire {self.unit_no}")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        floor = value("floor_no", 3, "-")
        direction = value("direction", 6, value("unit_kind", 7, "Daire"))
        details = QLabel(f"Kat {floor}  |  {direction}")
        details.setStyleSheet("color:#c2c6d6;font-size:9px;")
        identity.addWidget(title)
        identity.addWidget(details)
        header.addLayout(identity, 1)
        _, status_text, status_color = self._STATUS_MAP.get(self.status, (None, self.status, "#8c909f"))
        status = QLabel(status_text)
        status.setStyleSheet(f"background:#252a39;color:{status_color or '#8c909f'};border-radius:4px;padding:4px;font-size:8px;font-weight:700;")
        header.addWidget(status)
        layout.addLayout(header)
        try:
            count = self.parent_tab.db.get_unit_total_product_count(self.unit_id)
            room_rows = self.parent_tab.db.get_unit_rooms(self.unit_id) or []
        except Exception:
            count, room_rows = int(value("product_count", default=0) or 0), []
        room_names = ", ".join(str(room["name"] if hasattr(room, "keys") else room[1] if len(room) > 1 else room[0]) for room in room_rows[:3])
        room_text = f"{len(room_rows)} Oda ({room_names})" if room_rows else str(value("room_names", default="Oda tan\u0131mlanmam\u0131\u015f"))
        lead = str(value("responsible_name", default=value("assigned_to", default="Atanmad\u0131")))
        for icon, label, text, accent in (("\u2699", "Kurulu Cihaz", f"{count} Cihaz" if count else "0 \u00dcr\u00fcn", "#4cd7f6"), ("\u25a3", "Oda / B\u00f6l\u00fcm", room_text, "#adc6ff"), ("\u2659", "Saha Sorumlusu", lead, "#4edea3")):
            row = QFrame()
            row.setStyleSheet("QFrame{background:#090e1c;border:0;border-radius:4px;}")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(7, 4, 7, 4)
            left = QLabel(f"{icon}  {label}")
            left.setStyleSheet("color:#c2c6d6;font-size:9px;")
            right = QLabel(text)
            right.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            right.setStyleSheet(f"color:{accent};font-size:9px;font-weight:600;")
            row_layout.addWidget(left)
            row_layout.addWidget(right, 1)
            layout.addWidget(row)
        completion = int(value("completion_percent", default=100 if self.status == "Tamamland\u0131" else 50 if self.status == "Devam Ediyor" else 0) or 0)
        progress_row = QHBoxLayout()
        progress_row.addWidget(QLabel("Fiziksel Kurulum"))
        progress_value = QLabel(f"%{completion}")
        progress_value.setStyleSheet("color:#4cd7f6;font-weight:700;")
        progress_row.addWidget(progress_value)
        layout.addLayout(progress_row)
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(max(0, min(100, completion)))
        progress.setTextVisible(False)
        progress.setFixedHeight(5)
        progress.setStyleSheet("QProgressBar{background:#252a39;border:0;border-radius:2px;} QProgressBar::chunk{background:#4cd7f6;border-radius:2px;}")
        layout.addWidget(progress)
        footer = QHBoxLayout()
        self.btn_products = QPushButton("\u25a3 \u00dcr\u00fcnleri G\u00f6r / Ekle")
        self.btn_products.setStyleSheet("background:#4d8eff;color:#00285d;border:0;font-size:9px;font-weight:600;padding:6px;")
        self.btn_products.clicked.connect(lambda: self.parent_tab.open_unit_products(self.unit))
        footer.addWidget(self.btn_products, 1)
        self.btn_edit = QToolButton()
        self.btn_edit.setText("\u270e")
        self.btn_edit.setToolTip("Durum de\u011fi\u015ftir")
        self.btn_edit.clicked.connect(lambda: self._show_context_menu(self.rect().center()))
        self.btn_qr = QToolButton()
        self.btn_qr.setText("\u25a6")
        self.btn_qr.setToolTip("QR birim bilgisi")
        self.btn_qr.clicked.connect(lambda: QMessageBox.information(self, "Birim QR", f"{self.block_name} {self.unit_no}"))
        footer.addWidget(self.btn_edit)
        footer.addWidget(self.btn_qr)
        layout.addLayout(footer)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_tab.open_unit_products(self.unit)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.parent_tab.open_unit_products(self.unit)

    def _show_context_menu(self, pos):
        if not is_context_menu_enabled(self.parent_tab.db, page_id=200):
            return
        menu = QMenu(self)
        menu.setStyleSheet(theme_qss(
            "QMenu { background: @surface; border: 1px solid @border; border-radius: 6px; } "
            "QMenu::item { padding: 6px 20px; color: @text; } "
            "QMenu::item:selected { background: @surface_alt; }"
        ))
        act_bek  = menu.addAction("⏳ Bekliyor")
        act_dev  = menu.addAction("🔄 Devam Ediyor")
        act_tam  = menu.addAction("✅ Tamamlandı")
        menu.addSeparator()
        act_prod = menu.addAction("📦 Ürünleri Yönet")

        # Aktif durumu işaretle
        for act, st in [(act_bek,'Bekliyor'),(act_dev,'Devam Ediyor'),(act_tam,'Tamamlandı')]:
            act.setCheckable(True)
            act.setChecked(self.status == st)

        action = menu.exec(self.mapToGlobal(pos))
        if action == act_bek:
            self.parent_tab.change_unit_status(self.unit_id, 'Bekliyor')
        elif action == act_dev:
            self.parent_tab.change_unit_status(self.unit_id, 'Devam Ediyor')
        elif action == act_tam:
            self.parent_tab.change_unit_status(self.unit_id, 'Tamamlandı')
        elif action == act_prod:
            self.parent_tab.open_unit_products(self.unit)


# --- UNIT PRODUCTS DIALOG ---

class UnitProductsDialog(BaseModernDialog):
    """Bir daire/odaya kurulu akıllı ev ürünlerini gösteren ve yönetilen dialog."""

    def __init__(self, db, project_id, unit, parent=None):
        project_details = db.get_project_details(project_id) if hasattr(db, "get_project_details") else None
        if isinstance(project_details, dict):
            project_name = project_details.get("name", "")
        else:
            project_name = project_details[1] if project_details and len(project_details) > 1 else ""
        if isinstance(unit, dict):
            unit_no = unit.get('unit_no', '')
            self.unit_id = unit.get('id')
            self.block_name = unit.get('block_name', '') or ''
        else:
            unit_no = unit[4] if len(unit) > 4 else ''
            self.unit_id = unit[0]
            self.block_name = unit[2] if len(unit) > 2 else ''

        super().__init__(parent, title=f"Kurulu \u00dcr\u00fcnler \u2014 Daire: {unit_no}", width=1240, height=720)
        dialog_font = QFont()
        dialog_font.setFamilies(["Segoe UI", "Arial"])
        dialog_font.setPointSize(9)
        self.setFont(dialog_font)
        self.content_container.setStyleSheet("background-color: #0e1321; color: #dee2f6;")
        self.scroll_area.setStyleSheet(
            "QScrollArea { background-color: #0e1321; border: 0; } QWidget { background-color: #0e1321; } "
            "QScrollBar:vertical { width: 8px; background: #0e1321; margin: 0; } "
            "QScrollBar::handle:vertical { background: #424754; border-radius: 4px; min-height: 24px; } "
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        self.set_wheel_scroll_enabled(True)
        self.db = db
        self.project_id = project_id
        self.project_name = project_name
        self.unit_no = unit_no
        self._all_parts = []
        self.active_target_unit_id = self.unit_id
        self.setup_ui()
        self._wire_ui_signals()
        self.load_rooms()
        self._load_general_note()
        self.load_installed()
        self.load_stock_items()
        self.footer_layout.addWidget(QLabel("Adet:"))
        self.footer_layout.addWidget(self.spin_qty)
        self.footer_layout.addWidget(QLabel("Teknik Not:"))
        self.footer_layout.addWidget(self.txt_note, 1)
        self.add_button("Kapat", "ghost", self.accept)
        self.add_button("Se\u00e7ilenleri Daireye Ekle", "primary", self.add_selected_items)
        self._apply_part9_reference_style()
        QTimer.singleShot(0, lambda: self.scroll_area.verticalScrollBar().setValue(0))

    def _apply_part9_reference_style(self):
        def style(widget, qss):
            widget.setProperty("skipThemeTransform", True)
            widget.setStyleSheet(qss)

        style(self, "QDialog { background: rgba(0, 0, 0, 220); }")
        style(self.card, "QFrame#ModernDialogCard { background: #0b1222; color: #dce4f2; border: 1px solid #1e3a5f; border-radius: 10px; }")
        style(self.header, "background: #0e172a; color: #e2e8f0; border-bottom: 1px solid #22304a;")
        style(self.content_container, "QFrame#ModernDialogContent { background: #0b1222; color: #dce4f2; border: none; }")
        style(self.footer, "background: #0b1222; color: #dce4f2; border-top: 1px solid #22304a;")
        style(self.scroll_area, "QScrollArea { background: #0b1222; border: none; } QScrollArea::viewport { background: #0b1222; border: none; } QScrollBar:vertical { width: 8px; background: #0b1222; } QScrollBar::handle:vertical { background: #334155; border-radius: 4px; }")
        style(self.scroll_area.viewport(), "background: #0b1222; border: none;")
        if self.scroll_area.widget():
            style(self.scroll_area.widget(), "background: #0b1222; color: #dce4f2;")
        for label in self.card.findChildren(QLabel):
            style(label, "color: #cbd5e1; background: transparent; border: none; font-family: 'Segoe UI', Arial;")
        style(self.lbl_title, "color: #f8fafc; background: transparent; border: none; font-weight: 700; font-family: 'Segoe UI', Arial;")
        control_style = "QLineEdit, QTextEdit, QComboBox { background: #080e1a; color: #dce4f2; border: 1px solid #26364d; border-radius: 6px; padding: 6px 9px; selection-background-color: #2563eb; font-family: 'Segoe UI', Arial; } QComboBox QAbstractItemView { background: #0b1222; color: #dce4f2; selection-background-color: #2563eb; }"
        for widget_type in (QLineEdit, QTextEdit, QComboBox):
            for control in self.card.findChildren(widget_type):
                style(control, control_style)
        for table in self.card.findChildren(QTableWidget):
            style(table, "QTableWidget { background: #0b1222; alternate-background-color: #111a2a; color: #dce4f2; gridline-color: #1e293b; border: 1px solid #26364d; } QHeaderView::section { background: #111a2a; color: #9ba8bc; border: none; border-bottom: 1px solid #26364d; padding: 7px; font-weight: 700; } QTableWidget::item { background: #0b1222; color: #dce4f2; padding: 6px; } QTableWidget::item:alternate { background: #111a2a; color: #dce4f2; }")
        for listing in self.card.findChildren(QListWidget):
            style(listing, "QListWidget { background: #0b1222; color: #dce4f2; border: 1px solid #26364d; border-radius: 6px; } QListWidget::item { background: #111a2a; color: #dce4f2; border: 1px solid #26364d; border-radius: 6px; padding: 8px; margin: 3px; } QListWidget::item:selected { background: #172a45; border-color: #2563eb; }")
        for button in self.card.findChildren(QPushButton):
            if button in self.footer.findChildren(QPushButton):
                continue
            style(button, "QPushButton { background: #111a2a; color: #cbd5e1; border: 1px solid #26364d; border-radius: 5px; padding: 6px 10px; font-family: 'Segoe UI', Arial; } QPushButton:hover { background: #1e293b; }")
        style(self.btn_add_room, "QPushButton { background: #111a2a; color: #fbbf24; border: 1px solid #6b4f1d; border-radius: 5px; padding: 6px 10px; font-family: 'Segoe UI', Arial; }")
        footer_buttons = self.footer.findChildren(QPushButton)
        for button in footer_buttons:
            primary = "Ekle" in button.text()
            colors = ("#2563eb", "#ffffff", "#2563eb") if primary else ("#111a2a", "#dce4f2", "#26364d")
            style(button, "QPushButton { background: %s; color: %s; border: 1px solid %s; border-radius: 6px; padding: 7px 12px; font-weight: 700; font-family: 'Segoe UI', Arial; }" % colors)

    def setup_ui(self):
        content = self.content_layout
        content.setSpacing(10)

        self.lbl_target_info = QLabel()
        self.lbl_target_info.setStyleSheet("color: #94a3b8; background: transparent; border: none; font-size: 10px;")
        self.btn_add_room = QPushButton("🚪 Oda Ekle")
        self.btn_add_room.setFixedHeight(32)
        self.btn_add_room.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_add_room.clicked.connect(self.add_room)
        header_layout = self.header.layout()
        header_layout.removeWidget(self.lbl_title)
        title_block = QWidget(self.header)
        title_layout = QVBoxLayout(title_block)
        title_layout.setContentsMargins(0, 2, 0, 0)
        title_layout.setSpacing(2)
        self.lbl_title.setStyleSheet("color: #f8fafc; background: transparent; border: none; font-weight: 700;")
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title_row.addWidget(self.lbl_title)
        self.lbl_install_status = QLabel("\u2022 Aktif Kurulum")
        self.lbl_install_status.setStyleSheet("color:#4edea3;background:#0d2f2a;border:1px solid #145748;border-radius:4px;padding:3px 7px;font-size:9px;font-weight:700")
        title_row.addWidget(self.lbl_install_status)
        title_row.addStretch(1)
        title_layout.addLayout(title_row)
        title_layout.addWidget(self.lbl_target_info)
        header_layout.insertWidget(1, title_block, 1)
        header_layout.insertWidget(header_layout.indexOf(self.btn_close), self.btn_add_room)

        overview_row = QHBoxLayout()
        overview_row.setSpacing(12)

        room_card = QFrame()
        room_card.setStyleSheet("QFrame { background: #161b2a; border: 1px solid #26334a; border-radius: 8px; }")
        room_card_layout = QVBoxLayout(room_card)
        room_card_layout.setContentsMargins(12, 10, 12, 10)
        room_title_row = QHBoxLayout()
        lbl_rooms_title = QLabel("Hedef Kurulum Alan\u0131")
        lbl_rooms_title.setStyleSheet("color: #dee2f6; font-weight: bold; background: transparent; border: 0;")
        room_title_row.addWidget(lbl_rooms_title)
        room_title_row.addStretch()
        self.lbl_room_count = QLabel("Toplam: 0 B\u00f6lge Tan\u0131ml\u0131")
        self.lbl_room_count.setStyleSheet("color: #8c909f; font-size: 10px; background: transparent; border: 0;")
        room_title_row.addWidget(self.lbl_room_count)
        self.cmb_target_room = QComboBox()
        self.cmb_target_room.setFixedHeight(36)
        self.cmb_target_room.setStyleSheet(theme_qss(DesignTokens.get_combobox_qss()))
        self.cmb_target_room.currentIndexChanged.connect(self._on_room_changed)
        room_card_layout.addLayout(room_title_row)
        room_card_layout.addWidget(self.cmb_target_room)
        room_hint = QLabel("Se\u00e7ilen alt b\u00f6lgeye g\u00f6re \u00fcr\u00fcn listesi filtrelenir.")
        room_hint.setStyleSheet("color: #8c909f; background: transparent; border: 0; font-size: 11px;")
        room_card_layout.addWidget(room_hint)
        overview_row.addWidget(room_card, 5)

        note_card = QFrame()
        note_card.setStyleSheet("QFrame { background: #161b2a; border: 1px solid #26334a; border-radius: 8px; }")
        note_card_layout = QVBoxLayout(note_card)
        note_card_layout.setContentsMargins(12, 10, 12, 10)
        note_title_row = QHBoxLayout()
        lbl_general_note = QLabel("\U0001f4dd Genel Teknik Not")
        lbl_general_note.setStyleSheet("font-weight: bold; font-size: 13px; color: #dee2f6; background: transparent; border: 0;")
        note_title_row.addWidget(lbl_general_note)
        note_title_row.addStretch()
        note_card_layout.addLayout(note_title_row)
        self.txt_general_note = QTextEdit()
        self.txt_general_note.setPlaceholderText("Daire veya seçili oda için genel teknik not yazın...")
        self.txt_general_note.setFixedHeight(56)
        note_font = QFont("Segoe UI")
        note_font.setPixelSize(9)
        self.txt_general_note.setFont(note_font)
        self.txt_general_note.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        note_card_layout.addWidget(self.txt_general_note)
        self.btn_save_general_note = QPushButton("\U0001f4be Genel Notu Kaydet")
        self.btn_save_general_note.setFixedHeight(28)
        self.btn_save_general_note.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_save_general_note.clicked.connect(self.save_general_note)
        note_actions = QHBoxLayout()
        note_actions.addStretch()
        note_actions.addWidget(self.btn_save_general_note)
        note_card_layout.addLayout(note_actions)
        overview_row.addWidget(note_card, 7)
        content.addLayout(overview_row)

        # ── Kurulu Ürünler ─────────────────────────────────────────
        lbl_installed = QLabel("✅ Kurulu Ürünler")
        lbl_installed.setStyleSheet(theme_qss("font-weight: bold; font-size: 13px; color: @text;"))
        self.lbl_installed_count = QLabel("0 \u00fcr\u00fcn")
        self.lbl_installed_count.setStyleSheet("color: #8c909f; background: transparent; border: 0;")
        self.btn_refresh_installed = QPushButton("Yenile")
        self.btn_refresh_installed.setFixedHeight(30)
        self.btn_refresh_installed.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary", size="sm")))
        self.btn_refresh_installed.clicked.connect(self.load_installed)
        installed_title_row = QHBoxLayout()
        installed_title_row.addWidget(lbl_installed)
        installed_title_row.addWidget(self.lbl_installed_count)
        installed_title_row.addStretch()
        installed_title_row.addWidget(self.btn_refresh_installed)
        content.addLayout(installed_title_row)

        self.table_installed = QTableWidget()
        self.table_installed.setColumnCount(6)
        self.table_installed.setHorizontalHeaderLabels([" \u00dcr\u00fcn Ad\u0131", "SKU", "Adet", "Teknik Not / IP / Yap\u0131land\u0131rma", "Durum", "\u0130\u015flemler"])
        self.table_installed.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_installed.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table_installed.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table_installed.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table_installed.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table_installed.setColumnWidth(1, 110)
        self.table_installed.setColumnWidth(2, 70)
        self.table_installed.setColumnWidth(4, 105)
        self.table_installed.setColumnWidth(5, 72)
        self.table_installed.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) # We will trigger edit on specific column
        self.table_installed.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_installed.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_installed.verticalHeader().setVisible(False)
        self.table_installed.verticalHeader().setDefaultSectionSize(38)
        self.table_installed.setAlternatingRowColors(True)
        self.table_installed.setWordWrap(False)
        self.table_installed.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_installed.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_installed.setMinimumHeight(124)
        self.table_installed.setStyleSheet(
            "QTableWidget { border: 1px solid #26334a; border-radius: 8px; background: #0e1321; "
            "alternate-background-color: #161b2a; color: #dee2f6; gridline-color: #252a39; } "
            "QTableWidget::item { padding: 6px 8px; color: #dee2f6; } "
            "QTableWidget::item:hover { background: #252a39; color: #dee2f6; } "
            "QTableWidget::item:selected { background: #1d4ed8; color: #ffffff; } "
            "QHeaderView::section { background: #161b2a; color: #c2c6d6; border: 0; padding: 8px; font-weight: bold; }"
        )
        # Allow editing only on first double click or similar (we'll handle it below)
        self.table_installed.cellDoubleClicked.connect(self._on_cell_double_clicked)
        content.addWidget(self.table_installed)

        # ── Teknik Notları Kaydet Butonu ───────────────────────
        save_notes_row = QHBoxLayout()
        self.btn_save_notes = QPushButton("💾 Teknik Notları Kaydet")
        self.btn_save_notes.setFixedHeight(30)
        self.btn_save_notes.setStyleSheet(theme_qss(
            "QPushButton { background-color: @surface_alt; color: @text; border: 1px solid @border; "
            "border-radius: 6px; padding: 0 12px; font-weight: bold; font-size: 11px; } "
            "QPushButton:hover { background-color: @border; }"
        ))
        self.btn_save_notes.clicked.connect(self.save_notes)
        save_notes_row.addWidget(self.btn_save_notes)
        save_notes_row.addStretch()
        content.addLayout(save_notes_row)

        # ── Stoktan Ürün Ekle ──────────────────────────────────────
        lbl_add = QLabel("➕ Stoktan Ürün Ekle")
        lbl_add.setStyleSheet(theme_qss("font-weight: bold; font-size: 13px; color: @text; margin-top: 6px;"))
        self.lbl_stock_count = QLabel("0 se\u00e7ili")
        self.lbl_stock_count.setStyleSheet("color: #8c909f; background: transparent; border: 0;")
        stock_title_row = QHBoxLayout()
        stock_title_row.addWidget(lbl_add)
        stock_title_row.addStretch()
        stock_title_row.addWidget(self.lbl_stock_count)
        content.addLayout(stock_title_row)

        # Arama
        self.search_inp = QLineEdit()
        self.search_inp.setPlaceholderText("🔍 Ürün adı veya kod ile filtrele...")
        self.search_inp.setFixedHeight(36)
        self.search_inp.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))
        self.search_inp.textChanged.connect(self.filter_stock_list)
        content.addWidget(self.search_inp)

        # Stok listesi (checkbox ile çoklu seçim)
        self.list_stock = QListWidget()
        self.list_stock.setAlternatingRowColors(True)
        self.list_stock.itemChanged.connect(self._update_selected_stock_count)
        self.list_stock.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.list_stock.setMinimumHeight(180)
        self.list_stock.setStyleSheet(
            "QListWidget { border: 1px solid #26334a; border-radius: 8px; background: #161b2a; color: #dee2f6; } "
            "QListWidget::item { padding: 7px 10px; border-radius: 6px; margin: 2px 4px; color: #dee2f6; } "
            "QListWidget::item:hover { background: #252a39; color: #dee2f6; } "
            "QListWidget::item:selected { background: #1d4ed8; color: #ffffff; }"
        )
        content.addWidget(self.list_stock)

        self.spin_qty = QSpinBox()
        self.spin_qty.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.spin_qty.setRange(1, 999)
        self.spin_qty.setValue(1)
        self.spin_qty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spin_qty.setFixedWidth(88)
        self.spin_qty.setFixedHeight(34)
        self.spin_qty.setStyleSheet(theme_qss(
            "QSpinBox { background: @surface; color: @text; border: 1px solid @border; "
            "border-radius: 7px; padding: 0 10px; font-weight: 700; } "
            "QSpinBox:focus { border: 1px solid @accent; }"
        ))

        self.txt_note = QLineEdit()
        self.txt_note.setPlaceholderText("Örn: IP: 192.168.1.12  /  Kanal 3  /  WiFi: Ev_Ag")
        self.txt_note.setFixedHeight(34)
        self.txt_note.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))



    def _wire_ui_signals(self):
        if hasattr(self, "cmb_cat"):
            self.cmb_cat.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _emit_data_changed(self):
        parent = self.parent()
        project_page = getattr(parent, "project_page", None)
        main_window = getattr(project_page, "main_window", None)
        if main_window is None:
            return
        for signal_name in ("stock_updated", "financial_data_changed"):
            signal = getattr(main_window, signal_name, None)
            if signal is not None:
                try:
                    signal.emit()
                except Exception:
                    pass

    def load_installed(self):
        products = self.db.get_unit_products(self.active_target_unit_id)
        self.table_installed.setRowCount(len(products))
        if hasattr(self, "lbl_installed_count"):
            self.lbl_installed_count.setText(f"{len(products)} \u00fcr\u00fcn")
        for row, prod in enumerate(products):
            if isinstance(prod, dict):
                pid   = prod.get('id')
                pname = prod.get('part_name', '') or ''
                pcode = prod.get('part_code')    or '-'
                qty   = prod.get('quantity', 1)
                note  = prod.get('notes', '')    or ''
                status = prod.get('status', 'Kurulu') or 'Kurulu'
            else:
                pid   = prod[0]
                pname = prod[4] if len(prod) > 4 else ''
                pcode = (prod[5] if len(prod) > 5 else '-') or '-'
                qty   = prod[6] if len(prod) > 6 else 1
                note  = prod[7] if len(prod) > 7 else ''
                status = 'Kurulu'

            self.table_installed.setItem(row, 0, QTableWidgetItem(str(pname)))
            self.table_installed.setItem(row, 1, QTableWidgetItem(str(pcode)))
            self.table_installed.setItem(row, 2, QTableWidgetItem(str(qty)))
            
            note_item = QTableWidgetItem(str(note))
            note_item.setData(Qt.ItemDataRole.UserRole, pid) # Store entry ID
            note_item.setToolTip(str(note))
            self.table_installed.setItem(row, 3, note_item)

            btn_rm = QToolButton()
            btn_rm.setText("\U0001f5d1")
            btn_rm.setToolTip("Kald\u0131r")
            btn_rm.setAccessibleName("Kald\u0131r")
            btn_rm.setFixedSize(24, 24)
            btn_rm.setStyleSheet("QToolButton { color:#94a3b8; background:transparent; border:0; border-radius:4px; } QToolButton:hover { color:#dee2f6; background:#252a39; }")
            btn_rm.clicked.connect(lambda _checked, eid=pid: self.remove_product(eid))
            remove_widget = QWidget(self.table_installed)
            remove_layout = QHBoxLayout(remove_widget)
            remove_layout.setContentsMargins(4, 2, 4, 2)
            remove_layout.addWidget(btn_rm, alignment=Qt.AlignmentFlag.AlignCenter)
            status_item = QTableWidgetItem(str(status))
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item.setForeground(QColor("#4edea3" if str(status).casefold() in ("\u00e7evrimi\u00e7i", "online") else "#c2c6d6"))
            self.table_installed.setItem(row, 4, status_item)
            edit_button = QToolButton()
            edit_button.setText("\u270e")
            edit_button.setToolTip("D\u00fczenle")
            edit_button.setAccessibleName("D\u00fczenle")
            edit_button.setFixedSize(24, 24)
            edit_button.setStyleSheet("QToolButton { color:#94a3b8; background:transparent; border:0; border-radius:4px; } QToolButton:hover { color:#dee2f6; background:#252a39; }")
            edit_button.clicked.connect(lambda _checked, r=row: self._on_cell_double_clicked(r, 3))
            action_widget = QWidget(self.table_installed)
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)
            action_layout.addWidget(edit_button)
            action_layout.addWidget(btn_rm)
            self.table_installed.setCellWidget(row, 5, action_widget)
            self.table_installed.setRowHeight(row, 46)

    def load_stock_items(self, search=""):
        rows, _ = self.db.get_parts_paginated(limit=300, search_query=search)
        self._all_parts = rows
        self._populate_list(rows)
        self._update_selected_stock_count()

    def _update_selected_stock_count(self, *_args):
        if not hasattr(self, "list_stock") or not hasattr(self, "lbl_stock_count"):
            return
        count = sum(self.list_stock.item(i).checkState() == Qt.CheckState.Checked for i in range(self.list_stock.count()))
        self.lbl_stock_count.setText(f"{count} se\u00e7ili / {self.list_stock.count()} \u00fcr\u00fcn")

    def _populate_list(self, parts):
        self.list_stock.clear()
        for part in parts:
            if isinstance(part, dict):
                part_id = part.get('id')
                code    = part.get('code', '') or ''
                name    = part.get('name', '') or ''
                stock   = part.get('stock', 0) or 0
            else:
                part_id = part[0]
                name    = part[1] if len(part) > 1 else ''
                code    = (part[7] if len(part) > 7 else '') or '-'
                stock   = part[3] if len(part) > 3 else 0

            item = QListWidgetItem(f"{name}   ({code})   —   Stok: {stock}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, {'id': part_id, 'name': name, 'code': code})
            self.list_stock.addItem(item)

    def filter_stock_list(self, text):
        text = text.lower()
        for i in range(self.list_stock.count()):
            item = self.list_stock.item(i)
            item.setHidden(text not in item.text().lower())

    def add_selected_items(self):
        qty  = self.spin_qty.value()
        note = self.txt_note.text().strip()
        added = 0
        for i in range(self.list_stock.count()):
            item = self.list_stock.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                d = item.data(Qt.ItemDataRole.UserRole)
                self.db.add_unit_product({
                    'unit_id':    self.active_target_unit_id,
                    'project_id': self.project_id,
                    'part_id':    d['id'],
                    'part_name':  d['name'],
                    'part_code':  d['code'],
                    'quantity':   qty,
                    'notes':      note,
                })
                item.setCheckState(Qt.CheckState.Unchecked)
                added += 1
        if added > 0:
            self.txt_note.clear()
            show_success(self, f"{added} ürün eklendi.")
            self.load_installed()
            self._emit_data_changed()
            if isinstance(self.parent(), UnitsTab):
                self.parent().load_data()
        else:
            show_error(self, "Lütfen listeden en az bir ürün seçin.")

    def load_rooms(self):
        self.cmb_target_room.blockSignals(True)
        self.cmb_target_room.clear()
        self.cmb_target_room.addItem(f"Daire: {self.unit_no}", self.unit_id)
        rooms = self.db.get_unit_rooms(self.unit_id) or []
        self.lbl_room_count.setText(f"Toplam: {len(rooms)} B\u00f6lge Tan\u0131ml\u0131")
        for room in rooms:
            if isinstance(room, dict):
                room_id = room.get("id")
                room_name = room.get("unit_no", "")
            else:
                room_id = room[0]
                room_name = room[4] if len(room) > 4 else ""
            self.cmb_target_room.addItem(f"Daire: {self.unit_no} / {room_name}", room_id)
        idx = self.cmb_target_room.findData(self.active_target_unit_id)
        self.cmb_target_room.setCurrentIndex(idx if idx >= 0 else 0)
        self.cmb_target_room.blockSignals(False)
        self._refresh_target_label()

    def _refresh_target_label(self):
        project_name = self.project_name or f"Proje {self.project_id}"
        block_name = self.block_name or "Blok"
        if not block_name.lower().startswith("blok "):
            block_name = "Blok " + block_name.removesuffix(" Blok").strip()
        self.lbl_target_info.setText(f"{project_name}  \u203a  {block_name}  \u203a  Daire {self.unit_no}")

    def _on_room_changed(self):
        self.active_target_unit_id = self.cmb_target_room.currentData() or self.unit_id
        self._refresh_target_label()
        self._load_general_note()
        self.load_installed()

    def _load_general_note(self):
        unit = self.db.get_project_unit(self.active_target_unit_id)
        if not unit:
            self.txt_general_note.clear()
            return
        if isinstance(unit, dict):
            note = unit.get("description", "") or ""
        else:
            note = unit[12] if len(unit) > 12 else ""
        self.txt_general_note.setPlainText(str(note))

    def save_general_note(self):
        if self.db.update_project_unit_note(self.active_target_unit_id, self.txt_general_note.toPlainText().strip()):
            show_success(self, "Genel teknik not kaydedildi.")
        else:
            show_error(self, "Genel teknik not kaydedilemedi.")

    def add_room(self):
        room_name, ok = QInputDialog.getText(self, "Oda Ekle", "Oda Adı:")
        if not ok:
            return
        room_name = str(room_name or "").strip()
        if not room_name:
            show_error(self, "Oda adı boş bırakılamaz.")
            return
        room_id = self.db.add_project_room(self.project_id, self.unit_id, room_name)
        if room_id:
            self.active_target_unit_id = room_id
            self.load_rooms()
            self._load_general_note()
            self.load_installed()
            if isinstance(self.parent(), UnitsTab):
                self.parent().load_data()
            show_success(self, "Oda eklendi.")
        else:
            show_error(self, "Oda eklenemedi. Aynı isim zaten kullanılıyor olabilir.")

    def remove_product(self, entry_id):
        if self.db.remove_unit_product(entry_id):
            show_success(self, "Ürün kaldırıldı.")
            self.load_installed()
            self._emit_data_changed()
            if isinstance(self.parent(), UnitsTab):
                self.parent().load_data()

    def _on_cell_double_clicked(self, row, col):
        # Sadece "Teknik Not" (index 3) kolonu düzenlenebilir olsun
        if col == 3:
            item = self.table_installed.item(row, col)
            if item is None:
                return
            note, accepted = QInputDialog.getMultiLineText(
                self,
                "Teknik Not",
                "Teknik notu d\u00fczenleyin:",
                item.text(),
            )
            if not accepted:
                return
            entry_id = item.data(Qt.ItemDataRole.UserRole)
            if not entry_id or not self.db.update_unit_product_note(entry_id, note):
                show_error(self, "Teknik not kaydedilemedi.")
                return
            item.setText(note)
            item.setToolTip(note)
            self.table_installed.resizeRowToContents(row)
            show_success(self, "Teknik not g\u00fcncellendi.")

    def save_notes(self):
        """Tablodaki tüm ürünlerin teknik notlarını kaydeder."""
        success_count = 0
        for row in range(self.table_installed.rowCount()):
            item = self.table_installed.item(row, 3)
            if item:
                entry_id = item.data(Qt.ItemDataRole.UserRole)
                note     = item.text().strip()
                if entry_id:
                    if self.db.update_unit_product_note(entry_id, note):
                        success_count += 1
        
        if success_count > 0:
            show_success(self, f"{success_count} ürünün teknik notu güncellendi.")
            self.load_installed()
        else:
            show_error(self, "Güncellenecek not bulunamadı veya bir hata oluştu.")

# --- TAB 3: SUBCONTRACTORS ---

class SubcontractorsTab(QWidget):
    def __init__(self, db, project_id):
        super().__init__()
        self.db = db
        self.project_id = project_id
        self.lang = LanguageManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("👥 Ekip Üyesi Ekle")
        self.btn_add.setFixedHeight(36)
        self.btn_add.setStyleSheet(theme_qss(
            "QPushButton { background-color: @accent; color: @selection_text; "
            "border-radius: 7px; font-weight: bold; font-size: 13px; padding: 0 16px; } "
            "QPushButton:hover { background-color: @accent_hover; }"
        ))
        self.btn_add.clicked.connect(self.add_sub)
        toolbar.addWidget(self.btn_add)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Ad / Firma", "Uzmanl\u0131k Alan\u0131", "\u00dccret", "Kalan Bakiye", "\u0130\u015flemler"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        
        self.load_data()

    def update_texts(self):
        pass

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_try_for_display(
            amount,
            db=self.db,
            include_try_reference=include_try_reference,
        )

    def load_data(self):
        subs = self.db.get_subcontractors_with_balance(self.project_id)
        self.table.setRowCount(len(subs))
        for row, sub in enumerate(subs):
            self.table.setRowHeight(row, 32)
            # sub: id, proj_id, name, job_type, total, contact, created
            self.table.setItem(row, 0, QTableWidgetItem(sub['name']))
            self.table.setItem(row, 1, QTableWidgetItem(sub['job_type']))
            self.table.setItem(row, 2, QTableWidgetItem(self._fmt_try(sub['total_contract_amount'])))
            
            balance = float(sub["remaining_balance"] or 0.0)
            bal_item = QTableWidgetItem(self._fmt_try(balance))
            bal_item.setForeground(qc("danger") if balance > 0 else qc("success"))
            self.table.setItem(row, 3, bal_item)
            
            btn_pay = QPushButton("\u00d6deme Yap")
            btn_pay.setFixedSize(92, 24)
            btn_pay.setStyleSheet(theme_qss(
                "QPushButton { background-color: @accent; color: @selection_text; "
                "border: 1px solid @accent; border-radius: 5px; font-weight: 700; "
                "font-size: 11px; padding: 0 8px; } "
                "QPushButton:hover { background-color: @accent_hover; }"
            ))
            # We need to pass sub_id to the slot. Lambdas capture variable by reference in loops unless defaulted.
            btn_pay.clicked.connect(lambda _, s_id=sub['id']: self.make_payment(s_id))
            action_widget = QWidget(self.table)
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 0, 2, 0)
            action_layout.addStretch()
            action_layout.addWidget(btn_pay)
            action_layout.addStretch()
            self.table.setCellWidget(row, 4, action_widget)

    def add_sub(self):
        dlg = AddSubDialog(self.db, self.project_id, self)
        if dlg.exec():
            self.load_data()

    def make_payment(self, sub_id):
        # Open Transaction Dialog pre-filled for this subcontractor
        dlg = TransactionDialog(self.db, self.project_id, "Gider", self, sub_id=sub_id)
        if dlg.exec():
            self.load_data()

# --- DIALOGS ---

class TransactionDialog(QtDialog):
    def __init__(self, db, project_id, txn_type, parent=None, sub_id=None):
        super().__init__(parent)
        self.db = db
        self.project_id = project_id
        self.txn_type = txn_type
        self.sub_id = sub_id
        self.currency_code = CurrencyHelper.get_code(self.db)
        self.setWindowTitle(f"{txn_type} Ekle")
        self.setFixedSize(350, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.cmb_cat = QComboBox()
        if self.txn_type == "Gider":
            cats = ["Malzeme", "İşçilik", "Taşeron Ödemesi", "Nakliye", "Resmi Gider", "Diğer"]
            self.cmb_cat.addItems(cats)
            if self.sub_id: 
                self.cmb_cat.setCurrentText("Taşeron Ödemesi")
                self.cmb_cat.setEnabled(False) 
        else:
            self.cmb_cat.addItems(["Daire Satışı", "Proje Hakedişi", "Diğer"])
            
        form.addRow("Kategori:", self.cmb_cat)
        
        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0, 100000000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(f" {CurrencyHelper.get_label(self.currency_code)}")
        self.spin_amount.setGroupSeparatorShown(True)
        self.spin_amount.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.spin_amount.setKeyboardTracking(False)
        form.addRow("Tutar:", self.spin_amount)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        form.addRow("Tarih:", self.date_edit)
        
        self.txt_desc = QLineEdit()
        form.addRow("Açıklama:", self.txt_desc)
        
        layout.addLayout(form)
        
        self.btn_save = QPushButton("Kaydet")
        self.btn_save.clicked.connect(self.save)
        layout.addWidget(self.btn_save)

    def save(self):
        if getattr(self, "_saving", False):
            return
        self._saving = True
        self.btn_save.setEnabled(False)
        data = {
            'project_id': self.project_id,
            'type': self.txn_type,
            'category': self.cmb_cat.currentText(),
            'amount': self.spin_amount.value(),
            'payment_method': 'Nakit', # Simplified
            'date': self.date_edit.date().toString("yyyy-MM-dd"),
            'description': self.txt_desc.text(),
            'status': 'Ödendi',
            'ref_table': 'subcontractors' if self.sub_id else None,
            'ref_id': self.sub_id
        }
        try:
            transaction_id = self.db.add_project_transaction(data, commit=False)
            if not transaction_id:
                raise RuntimeError("Project transaction could not be created")

            self.db.conn.commit()
            show_success(self, f"{self.txn_type} başarıyla kaydedildi!")
            self.accept()
        except Exception as e:
            self.db.conn.rollback()
            self._saving = False
            self.btn_save.setEnabled(True)
            show_error(self, f"Kaydetme hatas\u0131: {str(e)}")


