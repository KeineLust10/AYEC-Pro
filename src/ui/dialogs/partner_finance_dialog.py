# -*- coding: utf-8 -*-

from datetime import datetime

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_error, show_success



class PartnerFinanceDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, db, partner, parent=None):
        self.db = db
        self.partner = dict(partner) if hasattr(partner, "keys") else (partner or {})
        self.currency_code = CurrencyHelper.get_code(self.db)
        super().__init__("Partner Finans Hareketleri", parent, width=920, height=760)
        self.set_wheel_scroll_enabled(True)
        self._ensure_tables()
        self._build_ui()
        self._load_shipment_options()
        self._load_summary()
        self._load_entries()
        self._load_reconciliation()

    def _ensure_tables(self):
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_finance_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                shipment_id INTEGER,
                entry_type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'TRY',
                payment_method TEXT,
                description TEXT,
                invoice_no TEXT,
                invoice_date TEXT,
                entry_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_shipments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                partner_name TEXT NOT NULL,
                customer_name TEXT,
                product_name TEXT,
                serial_no TEXT,
                issue_summary TEXT,
                shipment_reason TEXT,
                outbound_tracking_no TEXT,
                return_tracking_no TEXT,
                external_ref_no TEXT,
                status TEXT DEFAULT 'Hazirlaniyor',
                partner_cost REAL DEFAULT 0,
                customer_price REAL DEFAULT 0,
                quote_status TEXT DEFAULT 'Beklemede',
                quote_amount REAL DEFAULT 0,
                approval_status TEXT DEFAULT 'Onay Bekliyor',
                contract_type TEXT,
                sla_level TEXT,
                notes TEXT,
                sent_at TEXT,
                returned_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.db.cursor.execute("PRAGMA table_info(partner_shipments)")
        shipment_columns = {row[1] for row in (self.db.cursor.fetchall() or [])}
        for column_name, column_sql in (
            ("partner_id", "INTEGER DEFAULT 0"),
            ("partner_name", "TEXT DEFAULT ''"),
            ("customer_name", "TEXT"),
            ("product_name", "TEXT"),
            ("serial_no", "TEXT"),
            ("issue_summary", "TEXT"),
            ("shipment_reason", "TEXT"),
            ("outbound_tracking_no", "TEXT"),
            ("return_tracking_no", "TEXT"),
            ("external_ref_no", "TEXT"),
            ("status", "TEXT DEFAULT 'Hazirlaniyor'"),
            ("partner_cost", "REAL DEFAULT 0"),
            ("customer_price", "REAL DEFAULT 0"),
            ("currency", "TEXT DEFAULT 'TRY'"),
            ("quote_status", "TEXT DEFAULT 'Beklemede'"),
            ("quote_amount", "REAL DEFAULT 0"),
            ("approval_status", "TEXT DEFAULT 'Onay Bekliyor'"),
            ("contract_type", "TEXT"),
            ("sla_level", "TEXT"),
            ("notes", "TEXT"),
            ("sent_at", "TEXT"),
            ("returned_at", "TEXT"),
            ("created_at", "TEXT"),
            ("updated_at", "TEXT"),
        ):
            if column_name not in shipment_columns:
                self.db.cursor.execute(f"ALTER TABLE partner_shipments ADD COLUMN {column_name} {column_sql}")
        self.db.conn.commit()

    def _build_ui(self):
        card = QFrame()
        card.setStyleSheet(theme_qss(DesignTokens.get_card_qss()))
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        self.lbl_title = QLabel(str(self.partner.get("name") or "Partner Finans"))
        self.lbl_title.setStyleSheet(theme_qss("color: @text; font-size: 24px; font-weight: 800;"))
        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        layout.addWidget(self.lbl_title)
        layout.addWidget(self.lbl_summary)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        self.lbl_total_cost = QLabel("-")
        self.lbl_total_paid = QLabel("-")
        self.lbl_balance = QLabel("-")
        for idx, (title, label) in enumerate(
            (
                ("Toplam Partner Borcu", self.lbl_total_cost),
                ("Yapilan Odeme", self.lbl_total_paid),
                ("Kalan Borc", self.lbl_balance),
            )
        ):
            frame = QFrame()
            frame.setStyleSheet(theme_qss("background: @surface_alt; border: 1px solid @border; border-radius: 14px;"))
            v = QVBoxLayout(frame)
            text = QLabel(title)
            text.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-weight: 700;"))
            label.setStyleSheet(theme_qss("color: @text; font-size: 24px; font-weight: 900;"))
            v.addWidget(text)
            v.addWidget(label)
            grid.addWidget(frame, 0, idx)
        layout.addLayout(grid)

        from PyQt6.QtWidgets import QAbstractItemView
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Tarih", "Tip", "Aciklama", "Yontem", "Fatura No", "Fatura Tarihi", "Tutar"])
        self.table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        layout.addWidget(self.table)

        self.reconciliation_table = QTableWidget()
        self.reconciliation_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.reconciliation_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.reconciliation_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.reconciliation_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.reconciliation_table.setColumnCount(6)
        self.reconciliation_table.setHorizontalHeaderLabels(
            ["Sevk", "Urun", "Partner Maliyeti", "Eslesen Odeme", "Kalan", "Son Fatura"]
        )
        self.reconciliation_table.setStyleSheet(theme_qss(DesignTokens.get_table_qss()))
        layout.addWidget(self.reconciliation_table)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)

        self.date_entry = QDateEdit(QDate.currentDate())
        self.date_entry.setCalendarPopup(True)
        self.date_entry.setDisplayFormat("dd.MM.yyyy")
        self.date_entry.setFixedHeight(42)
        self.date_entry.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_amount = QDoubleSpinBox()
        self.inp_amount.setRange(0, 10_000_000)
        self.inp_amount.setDecimals(2)
        self.inp_amount.setSuffix(f" {CurrencyHelper.get_symbol(currency_code=self.currency_code)}")
        self.inp_amount.setFixedHeight(42)
        self.inp_amount.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_method = QLineEdit("Havale / EFT")
        self.inp_method.setFixedHeight(42)
        self.inp_method.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_desc = QLineEdit()
        self.inp_desc.setPlaceholderText("Partner odeme aciklamasi")
        self.inp_desc.setFixedHeight(42)
        self.inp_desc.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_invoice_no = QLineEdit()
        self.inp_invoice_no.setPlaceholderText("Partner fatura no")
        self.inp_invoice_no.setFixedHeight(42)
        self.inp_invoice_no.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.date_invoice = QDateEdit(QDate.currentDate())
        self.date_invoice.setCalendarPopup(True)
        self.date_invoice.setDisplayFormat("dd.MM.yyyy")
        self.date_invoice.setFixedHeight(42)
        self.date_invoice.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.cmb_shipment = QComboBox()
        self.cmb_shipment.setFixedHeight(42)
        self.cmb_shipment.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        labels = ("Odeme Tarihi", "Odeme Tutari", "Yontem", "Aciklama", "Fatura No", "Fatura Tarihi", "Sevk Eslestirme")
        widgets = (self.date_entry, self.inp_amount, self.inp_method, self.inp_desc, self.inp_invoice_no, self.date_invoice, self.cmb_shipment)
        for idx, (label_text, widget) in enumerate(zip(labels, widgets)):
            label = QLabel(label_text)
            label.setStyleSheet(theme_qss("color: @text_muted; font-weight: 700;"))
            box = QVBoxLayout()
            box.setSpacing(6)
            box.addWidget(label)
            box.addWidget(widget)
            form.addLayout(box, idx // 2, idx % 2)
        layout.addLayout(form)

        btn_add_payment = QPushButton("Partner Odemesi Kaydet")
        btn_add_payment.setFixedHeight(42)
        btn_add_payment.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_add_payment.clicked.connect(self.save_payment)
        layout.addWidget(btn_add_payment)

        self.add_widget(card)
        self.add_cancel_button("Kapat")

    def _load_shipment_options(self):
        partner_id = int(self.partner.get("id") or 0)
        self.cmb_shipment.clear()
        self.cmb_shipment.addItem("Genel Partner Odemesi", None)
        self.db.cursor.execute(
            """
            SELECT id, COALESCE(product_name, ''), COALESCE(serial_no, ''), COALESCE(sent_at, '')
            FROM partner_shipments
            WHERE partner_id = ?
            ORDER BY COALESCE(sent_at, created_at, updated_at) DESC, id DESC
            """,
            (partner_id,),
        )
        for shipment_id, product_name, serial_no, sent_at in (self.db.cursor.fetchall() or []):
            label = "#{id} | {product} | {serial} | {date}".format(
                id=shipment_id,
                product=product_name or "Urun",
                serial=serial_no or "-",
                date=sent_at or "-",
            )
            self.cmb_shipment.addItem(label, shipment_id)

    def _fetch_summary(self):
        partner_id = int(self.partner.get("id") or 0)
        self.db.cursor.execute(
            "SELECT COALESCE(partner_cost, 0), COALESCE(customer_price, 0), COALESCE(currency, 'TRY') FROM partner_shipments WHERE partner_id = ?",
            (partner_id,),
        )
        cost_total = 0.0
        customer_total = 0.0
        for partner_cost, customer_price, currency in (self.db.cursor.fetchall() or []):
            source_currency = str(currency or "TRY").upper()
            cost_total += CurrencyHelper.convert_amount(self.db, float(partner_cost or 0), source_currency, self.currency_code)
            customer_total += CurrencyHelper.convert_amount(self.db, float(customer_price or 0), source_currency, self.currency_code)

        self.db.cursor.execute(
            """
            SELECT COALESCE(amount, 0), COALESCE(currency, 'TRY')
            FROM partner_finance_entries
            WHERE partner_id = ? AND entry_type = 'PAYMENT'
            """,
            (partner_id,),
        )
        paid_total = 0.0
        for amount, currency in (self.db.cursor.fetchall() or []):
            paid_total += CurrencyHelper.convert_amount(self.db, float(amount or 0), str(currency or "TRY").upper(), self.currency_code)
        return cost_total, paid_total, customer_total

    def _load_summary(self):
        partner_cost_total, paid_total, customer_total = self._fetch_summary()
        balance = partner_cost_total - paid_total
        self.lbl_total_cost.setText(CurrencyHelper.format_amount(partner_cost_total, db=self.db, currency_code=self.currency_code))
        self.lbl_total_paid.setText(CurrencyHelper.format_amount(paid_total, db=self.db, currency_code=self.currency_code))
        self.lbl_balance.setText(CurrencyHelper.format_amount(balance, db=self.db, currency_code=self.currency_code))
        self.lbl_summary.setText(
            "Musteriye yansitilan toplam: {customer_total} | Kalan partner borcu: {balance}".format(
                customer_total=CurrencyHelper.format_amount(customer_total, db=self.db, currency_code=self.currency_code),
                balance=CurrencyHelper.format_amount(balance, db=self.db, currency_code=self.currency_code),
            )
        )

    def _load_entries(self):
        partner_id = int(self.partner.get("id") or 0)
        self.db.cursor.execute(
            """
            SELECT entry_date, entry_type, COALESCE(description, ''), COALESCE(payment_method, ''),
                   COALESCE(invoice_no, ''), COALESCE(invoice_date, ''), amount, COALESCE(currency, 'TRY')
            FROM partner_finance_entries
            WHERE partner_id = ?
            ORDER BY entry_date DESC, id DESC
            """,
            (partner_id,),
        )
        rows = self.db.cursor.fetchall() or []
        self.table.setRowCount(0)
        for row_idx, row in enumerate(rows):
            self.table.insertRow(row_idx)
            for col_idx, value in enumerate(row[:7]):
                text = value
                if col_idx == 6:
                    entry_currency = str(row[7] or "TRY").upper()
                    converted = CurrencyHelper.convert_amount(self.db, float(value or 0), entry_currency, self.currency_code)
                    text = CurrencyHelper.format_amount(converted, db=self.db, currency_code=self.currency_code)
                item = QTableWidgetItem(str(text))
                if col_idx in (0, 1, 5, 6):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(row_idx, col_idx, item)
        self.table.resizeColumnsToContents()

    def _load_reconciliation(self):
        partner_id = int(self.partner.get("id") or 0)
        self.db.cursor.execute(
            """
            SELECT ps.id,
                   COALESCE(ps.product_name, ''),
                   COALESCE(ps.partner_cost, 0),
                   COALESCE(ps.currency, 'TRY'),
                   COALESCE(SUM(CASE WHEN pfe.entry_type='PAYMENT' THEN pfe.amount ELSE 0 END), 0),
                   COALESCE(MAX(COALESCE(pfe.currency, 'TRY')), 'TRY'),
                   COALESCE(MAX(COALESCE(pfe.invoice_no, '')), '')
            FROM partner_shipments ps
            LEFT JOIN partner_finance_entries pfe
              ON pfe.partner_id = ps.partner_id AND pfe.shipment_id = ps.id
            WHERE ps.partner_id = ?
            GROUP BY ps.id, ps.product_name, ps.partner_cost, ps.currency
            ORDER BY ps.id DESC
            """,
            (partner_id,),
        )
        rows = self.db.cursor.fetchall() or []
        self.reconciliation_table.setRowCount(0)
        for row_idx, (shipment_id, product_name, partner_cost, shipment_currency, paid_match, payment_currency, invoice_no) in enumerate(rows):
            self.reconciliation_table.insertRow(row_idx)
            shipment_currency = str(shipment_currency or "TRY").upper()
            payment_currency = str(payment_currency or shipment_currency).upper()
            partner_cost_display = CurrencyHelper.convert_amount(self.db, float(partner_cost or 0), shipment_currency, self.currency_code)
            paid_display = CurrencyHelper.convert_amount(self.db, float(paid_match or 0), payment_currency, self.currency_code)
            remaining = partner_cost_display - paid_display
            values = [
                f"#{shipment_id}",
                product_name or "-",
                CurrencyHelper.format_amount(partner_cost_display, db=self.db, currency_code=self.currency_code),
                CurrencyHelper.format_amount(paid_display, db=self.db, currency_code=self.currency_code),
                CurrencyHelper.format_amount(remaining, db=self.db, currency_code=self.currency_code),
                invoice_no or "-",
            ]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col_idx in (0, 2, 3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.reconciliation_table.setItem(row_idx, col_idx, item)
        self.reconciliation_table.resizeColumnsToContents()

    def save_payment(self):
        partner_id = int(self.partner.get("id") or 0)
        amount = float(self.inp_amount.value() or 0)
        if not partner_id or amount <= 0:
            show_error(self, "Gecerli partner ve odeme tutari zorunludur.")
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        shipment_id = self.cmb_shipment.currentData()
        try:
            self.db.cursor.execute(
                """
                INSERT INTO partner_finance_entries (
                    partner_id, shipment_id, entry_type, amount, currency,
                    payment_method, description, invoice_no, invoice_date, entry_date, created_at
                ) VALUES (?, ?, 'PAYMENT', ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    partner_id,
                    shipment_id,
                    amount,
                    self.currency_code,
                    self.inp_method.text().strip(),
                    self.inp_desc.text().strip() or "Partner odemesi",
                    self.inp_invoice_no.text().strip(),
                    self.date_invoice.date().toString("yyyy-MM-dd"),
                    self.date_entry.date().toString("yyyy-MM-dd"),
                    now,
                ),
            )
            self.db.conn.commit()
            self._load_summary()
            self._load_entries()
            self._load_reconciliation()
            self.inp_amount.setValue(0)
            self.inp_desc.clear()
            self.inp_invoice_no.clear()
            show_success(self, "Partner odemesi kaydedildi.")
        except Exception as exc:
            show_error(self, f"Partner finans kaydi olusturulamadi: {exc}")

    def _wire_ui_signals(self):
        self.cmb_shipment.currentIndexChanged.connect(self._on_ui_widget_changed)
