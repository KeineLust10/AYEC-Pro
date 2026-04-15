# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QLineEdit,
    QFrame,
    QMenu,
    QGraphicsDropShadowEffect,
    QApplication,
    QFileDialog,
    QMessageBox,
    QDoubleSpinBox,
    QGridLayout,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QTabWidget,
)
from PyQt6.QtGui import QAction
from src.utils.theme_colors import theme_qss, qc, tc
from src.utils.toast_notification import (
    show_success,
    show_error,
    show_warning,
    show_info,
)
from src.utils.design_system import DesignTokens
from PyQt6.QtCore import Qt, QDate, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon
from datetime import datetime
from collections import Counter
import csv
import webbrowser
import os
from src.utils.logger import logger

from src.ui.dialogs.customer_history_dialog import CustomerHistoryDialog
from src.ui.dialogs.add_customer_dialog import AddCustomerDialog
from src.ui.dialogs.customer_notes_dialog import CustomerNotesDialog
from src.ui.dialogs.service_invoice_dialog import ServiceInvoiceDialog
from src.ui.dialogs.customer_360_dialog import Customer360Dialog
from src.ui.dialogs.payment_dialog import ModernPaymentDialog
from src.ui.pages.external_tracking_page import ExternalTrackingDialog
from src.ui.dialogs.partner_profile_dialog import PartnerProfileDialog
from src.ui.dialogs.partner_finance_dialog import PartnerFinanceDialog
from src.ui.dialogs.partner_documents_dialog import PartnerDocumentsDialog
from src.ui.dialogs.partner_shipment_dialog import PartnerShipmentDialog
from src.ui.dialogs.unified_documents_center_dialog import UnifiedDocumentsCenterDialog
from src.ui.pages.appointments_page import AddAppointmentDialog
from src.ui.pages.customers.logic.customer_manager import CustomerManager
from src.ui.widgets.modern_inputs import ModernComboBox
from src.ui.widgets.modern_dialog import ModernDialog
from src.ui.widgets.empty_state import EmptyState
from src.utils.currency_helper import CurrencyHelper
from src.utils.context_menu_settings import is_context_menu_enabled


class CustomerWorker(QThread):
    data_loaded = pyqtSignal(list, int)  # customers, total_count
    load_error = pyqtSignal(str)

    def __init__(self, db, limit, offset, search_query, filter_type):
        super().__init__()
        self.db = db
        self.limit = limit
        self.offset = offset
        self.search_query = search_query
        self.filter_type = filter_type

    def run(self):
        import sqlite3

        conn = None
        try:
            display_currency = CurrencyHelper.get_code(self.db)
            from src.utils.path_helper import PathHelper

            db_path = PathHelper.get_db_path(getattr(self.db, "_db_name", "ayecpro.db"))
            conn = sqlite3.connect(db_path, timeout=30.0)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(customers)")
            customer_columns = {row[1] for row in (cur.fetchall() or [])}
            if "is_partner" not in customer_columns:
                cur.execute(
                    "ALTER TABLE customers ADD COLUMN is_partner INTEGER DEFAULT 0"
                )
            if "contract_type" not in customer_columns:
                cur.execute("ALTER TABLE customers ADD COLUMN contract_type TEXT")
            if "sla_level" not in customer_columns:
                cur.execute("ALTER TABLE customers ADD COLUMN sla_level TEXT")
            conn.commit()
            cur.execute(
                """
                UPDATE customers
                SET is_partner = 1
                WHERE COALESCE(is_partner, 0) = 0
                  AND (
                        UPPER(TRIM(COALESCE(type, ''))) IN ('BAYI', 'BAYİ', 'TEDARIKCI', 'TEDARIKÇI')
                        OR LOWER(TRIM(COALESCE(type, ''))) IN ('bayi', 'tedarikci', 'tedarikçi')
                  )
                """
            )
            conn.commit()

            where_parts = ["(c.is_deleted = 0 OR c.is_deleted IS NULL)"]
            params = []
            if self.filter_type == "PARTNERS":
                where_parts.append("(COALESCE(c.is_partner, 0) = 1)")
            else:
                where_parts.append("(COALESCE(c.is_partner, 0) = 0)")
            if self.search_query:
                where_parts.append(
                    "(c.name LIKE ? OR c.phone LIKE ? OR c.email LIKE ? OR c.company_name LIKE ?)"
                )
                q = f"%{self.search_query}%"
                params.extend([q, q, q, q])
            where_sql = " AND ".join(where_parts)
            debt_where = ""
            if self.filter_type == "OPEN_RECEIVABLES":
                debt_where = """
                    AND EXISTS (
                        SELECT 1
                        FROM currency_transactions ct
                        WHERE ct.customer_id = c.id
                          AND ct.transaction_type = 'DEBIT'
                          AND COALESCE(ct.current_balance, 0) < 0
                    )
                """

            cur.execute(
                "SELECT COUNT(*) FROM customers c WHERE {where_sql} {debt_where}".format(
                    where_sql=where_sql,
                    debt_where=debt_where,
                ),
                tuple(params),
            )
            total = int(cur.fetchone()[0] or 0)

            balance_sub = """
                SELECT customer_id,
                    SUM(CASE WHEN currency='TRY' THEN balance ELSE 0 END) AS balance_try,
                    SUM(CASE WHEN currency='USD' THEN balance ELSE 0 END) AS balance_usd,
                    SUM(CASE WHEN currency='EUR' THEN balance ELSE 0 END) AS balance_eur
                FROM customer_currency_balances
                GROUP BY customer_id
            """
            data_sql = """
                SELECT c.*,
                    COALESCE(b.balance_try, 0) AS balance_try,
                    COALESCE(b.balance_usd, 0) AS balance_usd,
                    COALESCE(b.balance_eur, 0) AS balance_eur
                FROM customers c
                LEFT JOIN ({balance_sub}) b ON b.customer_id = c.id
                WHERE {where_sql}
                {debt_where}
                ORDER BY c.name LIMIT ? OFFSET ?
            """.format(
                balance_sub=balance_sub,
                where_sql=where_sql,
                debt_where=debt_where,
            )
            data_params = list(params) + [int(self.limit), int(self.offset)]
            cur.execute(data_sql, tuple(data_params))
            columns = [col[0] for col in cur.description]
            rows = [dict(zip(columns, row)) for row in cur.fetchall()]

            def _is_partner_row(row):
                try:
                    if int(row.get("is_partner", 0) or 0) == 1:
                        return True
                except Exception:
                    pass
                row_type = str(row.get("type") or "").strip().casefold()
                return row_type in {"bayi", "tedarikçi", "tedarikci"}

            if self.filter_type == "PARTNERS":
                rows = [row for row in rows if _is_partner_row(row)]
            else:
                rows = [row for row in rows if not _is_partner_row(row)]

            if self.filter_type == "DEBTORS":
                filtered_rows = []
                for r in rows:
                    converted_total = 0.0
                    converted_total += CurrencyHelper.convert_amount(
                        self.db,
                        float(r.get("balance_try", 0) or 0),
                        "TRY",
                        display_currency,
                    )
                    converted_total += CurrencyHelper.convert_amount(
                        self.db,
                        float(r.get("balance_usd", 0) or 0),
                        "USD",
                        display_currency,
                    )
                    converted_total += CurrencyHelper.convert_amount(
                        self.db,
                        float(r.get("balance_eur", 0) or 0),
                        "EUR",
                        display_currency,
                    )
                    if converted_total < 0:
                        filtered_rows.append(r)
                rows = filtered_rows
                total = len(rows)

            cur.close()
            conn.close()
            conn = None
            self.data_loaded.emit(rows, total)
        except Exception as e:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            self.load_error.emit(str(e))


class LegacyPartnersPageListUnused(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.customer_manager = CustomerManager(db)
        self.all_partners = []
        self.current_service_type = None
        self.current_commission_filter = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)
        self.setup_ui()
        # Gecikmeli yükleme
        QTimer.singleShot(100, self.load_data)

    def notify(self, message, level="info"):
        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(message, level)
        else:
            if level == "error":
                show_error(self, message)
            elif level == "success":
                show_success(self, message)
            elif level == "warning":
                show_warning(self, message)
            else:
                show_info(self, message)

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(16)

        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(
            theme_qss(
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1e293b, stop:0.5 #334155, stop:1 #475569);"
                "border-radius: 16px;"
            )
        )
        h_layout = QHBoxLayout(self.header_frame)
        h_layout.setContentsMargins(20, 16, 20, 16)

        title_box = QVBoxLayout()
        lbl_title = QLabel("🤝 Çalışma Ortaklarımız")
        lbl_title.setStyleSheet(
            theme_qss(f"color: #f8fafc; font-size: 22px; font-weight: 800;")
        )
        lbl_sub = QLabel(
            "Hizmet sağlayıcılar, bayiler ve tedarikçileri tek ekranda yönetin."
        )
        lbl_sub.setStyleSheet(theme_qss("color: #94a3b8; font-size: 12px;"))
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        self.lbl_title = lbl_title
        self.lbl_sub = lbl_sub

        h_layout.addLayout(title_box)
        h_layout.addStretch()

        self.layout.addWidget(self.header_frame)

        filter_card = QFrame()
        filter_card.setStyleSheet(
            theme_qss(
                "background: @surface; border-radius: 12px; border: 1px solid @border;"
            )
        )
        f_layout = QHBoxLayout(filter_card)
        f_layout.setContentsMargins(16, 10, 16, 10)
        f_layout.setSpacing(12)

        btn_add = QPushButton("+ Yeni Çalışma Ortağı")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setFixedHeight(36)
        btn_add.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        btn_add.clicked.connect(self.add_partner)
        f_layout.addWidget(btn_add)
        f_layout.addSpacing(16)

        self.cmb_service_type = ModernComboBox()
        self.cmb_service_type.setMinimumWidth(180)
        self.cmb_service_type.setPlaceholderText("Hizmet Türü")
        self.cmb_service_type.currentIndexChanged.connect(self.on_service_type_changed)
        f_layout.addWidget(QLabel("Hizmet Türü:"))
        f_layout.addWidget(self.cmb_service_type)

        self.cmb_commission = ModernComboBox()
        self.cmb_commission.setMinimumWidth(180)
        self.cmb_commission.addItems(
            ["Tümü", "Komisyonu Olanlar", "Komisyonu Olmayanlar"]
        )
        self.cmb_commission.currentIndexChanged.connect(
            self.on_commission_filter_changed
        )
        f_layout.addSpacing(12)
        f_layout.addWidget(QLabel("Komisyon:"))
        f_layout.addWidget(self.cmb_commission)

        f_layout.addStretch()

        f_layout.addWidget(QLabel("Arama:"))
        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Ortak adı, telefon, hizmet türü...")
        self.inp_search.setFixedWidth(260)
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(250))
        f_layout.addWidget(self.inp_search)

        self.layout.addWidget(filter_card)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            [
                "#",
                "ORTAK ADI",
                "TÜR",
                "HİZMET TÜRÜ",
                "KOMİSYON",
                "TELEFON",
                "E-POSTA",
                "ŞEHİR",
                "İŞLEMLER",
            ]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 260)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 120)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 160)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 120)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 130)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 170)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(7, 130)
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(8, 170)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self._on_table_cell_entered)
        self.table.setStyleSheet(
            theme_qss(
                """
            QTableWidget { border-radius: 10px; border: 1px solid @border; background: @surface; }
            QHeaderView::section { background-color: @surface_alt; color: @text; padding: 14px; font-weight: bold; border: none; }
            QTableWidget::item { padding: 10px; color: @text; border-bottom: 1px solid @surface_alt; }
            QTableWidget::item:selected { background-color: @accent; color: @selection_text; border: none; }
            QTableWidget::item:focus { outline: none; }
            """
            )
        )
        self.layout.addWidget(self.table)

        footer = QFrame()
        footer.setStyleSheet(
            theme_qss(
                "background: @surface_alt; border-top: 1px solid @border; border-radius: 8px;"
            )
        )
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(12, 6, 12, 6)
        self.lbl_total = QLabel("Toplam Çalışma Ortağı: 0")
        self.lbl_total.setStyleSheet(
            theme_qss("color: @selection_text; font-weight: 600;")
        )
        fl.addWidget(self.lbl_total)
        fl.addStretch()
        self.layout.addWidget(footer)
        self.apply_theme_styles()

    def _on_table_cell_entered(self, row, _column):
        if row >= 0:
            self.table.selectRow(row)

    def on_service_type_changed(self, index):
        text = self.cmb_service_type.currentText().strip()
        self.current_service_type = None if not text or text == "Tümü" else text
        self.apply_filters()

    def on_commission_filter_changed(self, index):
        text = self.cmb_commission.currentText().strip()
        if text == "Komisyonu Olanlar":
            self.current_commission_filter = "HAS"
        elif text == "Komisyonu Olmayanlar":
            self.current_commission_filter = "NONE"
        else:
            self.current_commission_filter = None
        self.apply_filters()

    def load_data(self):
        try:
            self.all_partners = self.customer_manager.get_customers("PARTNERS") or []
        except Exception as e:
            self.all_partners = []
            self.notify(f"Çalışma ortakları yüklenemedi: {e}", "error")
        self.rebuild_service_type_filter()
        self.apply_filters()

    def rebuild_service_type_filter(self):
        values = set()
        try:
            for c in self.all_partners:
                if "service_type" in c.keys():
                    val = str(c["service_type"] or "").strip()
                    if val:
                        values.add(val)
        except Exception:
            values = set()
        items = ["Tümü"] + sorted(values)
        self.cmb_service_type.blockSignals(True)
        self.cmb_service_type.clear()
        self.cmb_service_type.addItems(items)
        self.cmb_service_type.blockSignals(False)
        self.cmb_service_type.setCurrentIndex(0)
        self.current_service_type = None

    def apply_filters(self):
        search = self.inp_search.text().strip().lower()
        rows = []
        for c in self.all_partners:
            try:
                name = str(c["name"] or "")
                company = str(c["company_name"] if "company_name" in c.keys() else "")
                phone = str(c["phone"] or "")
                email = str(c["email"] or "")
                city = str(c["city"] if "city" in c.keys() else "")
                service_type = str(
                    c["service_type"] if "service_type" in c.keys() else ""
                )
                if search:
                    text_blob = " ".join(
                        [
                            name.lower(),
                            company.lower(),
                            phone.lower(),
                            email.lower(),
                            city.lower(),
                            service_type.lower(),
                        ]
                    )
                    if search not in text_blob:
                        continue
                if self.current_service_type:
                    if service_type != self.current_service_type:
                        continue
                if self.current_commission_filter:
                    commission = 0.0
                    if (
                        "commission_rate" in c.keys()
                        and c["commission_rate"] is not None
                    ):
                        try:
                            commission = float(c["commission_rate"])
                        except Exception:
                            commission = 0.0
                    if self.current_commission_filter == "HAS" and commission <= 0:
                        continue
                    if self.current_commission_filter == "NONE" and commission > 0:
                        continue
                rows.append(c)
            except Exception:
                continue

        self.table.setRowCount(0)
        for idx, c in enumerate(rows):
            self.add_row(idx, c)
        self.lbl_total.setText(f"Toplam Çalışma Ortağı: {len(rows)}")

    def apply_theme_styles(self):
        if hasattr(self, "lbl_title"):
            self.lbl_title.setStyleSheet(
                theme_qss(
                    "color: @selection_text; font-size: 22px; font-weight: 800; background: transparent; border: none;"
                )
            )
        if hasattr(self, "lbl_sub"):
            self.lbl_sub.setStyleSheet(
                theme_qss(
                    "color: rgba(255,255,255,0.80); font-size: 12px; background: transparent; border: none;"
                )
            )
        if hasattr(self, "lbl_total"):
            self.lbl_total.setStyleSheet(theme_qss("color: @text; font-weight: 600;"))

    def refresh_theme(self):
        self.apply_theme_styles()

    def add_row(self, row_idx, c):
        self.table.insertRow(row_idx)
        idx_item = QTableWidgetItem(str(row_idx + 1))
        idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 0, idx_item)

        name = str(c["name"] or "")
        cust_type = str(c["type"] or "") if "type" in c.keys() else ""
        display_name = name
        if cust_type:
            if cust_type == "Kurumsal":
                badge = "[Kurumsal]"
            elif cust_type == "Bayi":
                badge = "[Bayi]"
            elif cust_type == "Tedarikçi":
                badge = "[Tedarikçi]"
            else:
                badge = f"[{cust_type}]"
            display_name = f"{name}  {badge}"
        name_item = QTableWidgetItem(display_name)
        name_item.setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.table.setItem(row_idx, 1, name_item)

        type_item = QTableWidgetItem(cust_type or "—")
        type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 2, type_item)

        service_type = ""
        if "service_type" in c.keys() and c["service_type"]:
            service_type = str(c["service_type"])
        service_item = QTableWidgetItem(service_type or "Genel")
        service_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 3, service_item)

        commission_val = 0.0
        if "commission_rate" in c.keys() and c["commission_rate"] is not None:
            try:
                commission_val = float(c["commission_rate"])
            except Exception:
                commission_val = 0.0
        commission_text = f"{commission_val:.2f} %" if commission_val else "—"
        commission_item = QTableWidgetItem(commission_text)
        commission_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 4, commission_item)

        phone_item = QTableWidgetItem(str(c["phone"] or "—"))
        phone_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 5, phone_item)

        email_item = QTableWidgetItem(str(c["email"] or "—"))
        email_item.setTextAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.table.setItem(row_idx, 6, email_item)

        city_val = ""
        if "city" in c.keys() and c["city"]:
            city_val = str(c["city"])
        city_item = QTableWidgetItem(city_val or "—")
        city_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 7, city_item)

        self.table.setCellWidget(row_idx, 8, self.create_action_widget(c))
        self.table.setRowHeight(row_idx, 80)

    def create_action_widget(self, c):
        btn = QPushButton("İşlem Yap ▼")
        btn.setMinimumWidth(150)
        btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            theme_qss(
                "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 @accent, stop:1 @success);"
                "color: @selection_text; border-radius: 16px; font-weight: 600; font-size: 11px; border: none; }"
                "QPushButton:hover { background: @accent; }"
            )
        )
        btn.clicked.connect(
            lambda checked=False, data=c: self.open_partner_menu(data, btn)
        )
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(btn)
        return container

    def open_partner_menu(self, c, source_btn):
        menu = QMenu(self)
        menu.addAction(
            "🔄 Ortak 360°",
            lambda: Customer360Dialog(self.db, c["id"], c["name"], self).exec(),
        )
        menu.addAction(
            "⚙️ Hizmet & Komisyon",
            lambda: self.edit_partner(c),
        )
        menu.addAction(
            "📝 Notlar",
            lambda: CustomerNotesDialog(self.db, c["id"], c["name"], self).exec(),
        )
        menu.addSeparator()
        menu.addAction(
            "🆕 Yeni Servis Kaydı",
            lambda: self.create_service_for_partner(c),
        )
        menu.addAction(
            "💰 Ödeme / Tahsilat",
            lambda: self.record_payment_for_partner(c),
        )
        menu.addSeparator()
        menu.addAction(
            "📱 WhatsApp Mesaj",
            lambda: self.send_whatsapp_for_partner(c),
        )
        pos = source_btn.mapToGlobal(source_btn.rect().bottomLeft())
        menu.exec(pos)

    def create_service_for_partner(self, c):
        from src.ui.dialogs.new_service_dialog import NewServiceDialog

        sector_manager = getattr(self.main_window, "sector_manager", None)
        NewServiceDialog(
            self.db, self, customer_name=c["name"], sector_manager=sector_manager
        ).exec()

    def record_payment_for_partner(self, c):
        dlg = ModernPaymentDialog(self, self.db, c)
        if dlg.exec():
            data = dlg.get_data()
            if data:
                date_value = data.get("date")
                if date_value:
                    d = QDate.fromString(date_value, "dd.MM.yyyy")
                    if d.isValid():
                        date_value = d.toString("yyyy-MM-dd")
                res = self.db.add_transaction_with_customer(
                    customer_id=c["id"],
                    date=date_value,
                    description=data["notes"] or f"{data['method']} ile ödeme",
                    amount=data["amount"],
                    t_type="Gelir",
                    category="Tahsilat",
                    payment_method=data.get("method"),
                    bank_account_id=data.get("bank_account_id"),
                )
                if res:
                    show_success(
                        self,
                        f"{CurrencyHelper.format_try_for_display(data['amount'], db=self.db, include_try_reference=False)} "
                        "tahsilat kaydedildi.",
                    )
                    self.load_data()
                else:
                    show_error(self, "Ödeme kaydedilirken bir hata oluştu.")

    def send_whatsapp_for_partner(self, c):
        phone = "".join(filter(str.isdigit, str(c["phone"])))
        if phone:
            if phone.startswith("0"):
                phone = "9" + phone
            webbrowser.open(f"https://wa.me/{phone}")

    def add_partner(self):
        if PartnerDialog(self.db, self).exec():
            self.load_data()

    def edit_partner(self, c):
        if PartnerDialog(self.db, self, c).exec():
            self.load_data()


class PartnersPage(QWidget):
    def __init__(self, db, main_window=None):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self.customer_manager = CustomerManager(db)
        self.all_partners = []
        self.filtered_partners = []
        self.selected_partner = None
        self.current_service_type = None
        self.current_commission_filter = None
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.apply_filters)
        self.setup_ui()
        QTimer.singleShot(100, self.load_data)

    def notify(self, message, level="info"):
        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(message, level)
            return
        if level == "error":
            show_error(self, message)
        elif level == "success":
            show_success(self, message)
        elif level == "warning":
            show_warning(self, message)
        else:
            show_info(self, message)

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(16)

        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(
            theme_qss(
                "background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #0f172a, stop:0.55 #1e293b, stop:1 #334155);"
                "border-radius: 18px; border: 1px solid @border;"
            )
        )
        header_layout = QHBoxLayout(self.header_frame)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(18)

        title_box = QVBoxLayout()
        self.lbl_title = QLabel("Calisma Ortaklari")
        self.lbl_sub = QLabel(
            "Partner kartlarinizi, gonderdiginiz urunleri ve donus surecini tek ekranda yonetin."
        )
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_sub)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.btn_add_partner = QPushButton("+ Yeni Ortak")
        self.btn_add_partner.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_partner.setFixedHeight(38)
        self.btn_add_partner.clicked.connect(self.add_partner)
        header_layout.addWidget(self.btn_add_partner)
        self.layout.addWidget(self.header_frame)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(1)
        self.layout.addWidget(self.splitter, 1)

        self._build_partner_sidebar()
        self._build_partner_workspace()
        self.splitter.setSizes([340, 980])
        self.apply_theme_styles()

    def _build_partner_sidebar(self):
        self.sidebar = QFrame()
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(14)

        filter_card = QFrame()
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(16, 16, 16, 16)
        filter_layout.setSpacing(10)

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Ortak ara: ad, sehir, telefon, hizmet...")
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(200))
        filter_layout.addWidget(self.inp_search)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        self.cmb_service_type = ModernComboBox()
        self.cmb_service_type.setPlaceholderText("Hizmet")
        self.cmb_service_type.currentIndexChanged.connect(self.on_service_type_changed)
        filter_row.addWidget(self.cmb_service_type, 1)

        self.cmb_commission = ModernComboBox()
        self.cmb_commission.addItems(["Tumu", "Komisyonlu", "Komisyonsuz"])
        self.cmb_commission.currentIndexChanged.connect(
            self.on_commission_filter_changed
        )
        filter_row.addWidget(self.cmb_commission, 1)
        filter_layout.addLayout(filter_row)
        sidebar_layout.addWidget(filter_card)

        self.partner_list = QListWidget()
        self.partner_list.currentRowChanged.connect(self.on_partner_selected)
        sidebar_layout.addWidget(self.partner_list, 1)
        self.partner_list_empty = EmptyState(
            icon="🤝",
            title="Partner bulunamadı",
            message="Henüz çalışma ortağı kaydı yok veya arama kriteri sonuç vermedi.",
            action_text="+ Yeni Ortak",
            action_callback=self.add_partner,
        )
        sidebar_layout.addWidget(self.partner_list_empty)
        self.partner_list_empty.hide()

        self.lbl_total = QLabel("Toplam partner: 0")
        sidebar_layout.addWidget(self.lbl_total)
        self.splitter.addWidget(self.sidebar)

    def _build_partner_workspace(self):
        self.workspace = QFrame()
        workspace_layout = QVBoxLayout(self.workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(14)

        self.partner_hero = QFrame()
        hero_layout = QVBoxLayout(self.partner_hero)
        hero_layout.setContentsMargins(20, 18, 20, 18)
        hero_layout.setSpacing(12)

        top_row = QHBoxLayout()
        text_col = QVBoxLayout()
        self.partner_name = QLabel("Partner secin")
        self.partner_meta = QLabel(
            "Soldan bir calisma ortagi secerek sevk ve takip ekranini acin."
        )
        self.partner_scorecard = QLabel(
            "Scorecard metrikleri partner secildiginde guncellenir."
        )
        text_col.addWidget(self.partner_name)
        text_col.addWidget(self.partner_meta)
        text_col.addWidget(self.partner_scorecard)
        top_row.addLayout(text_col)
        top_row.addStretch()

        actions = QHBoxLayout()
        actions.setSpacing(10)
        self.btn_add_shipment = QPushButton("+ Gonderi Kaydi")
        self.btn_add_shipment.clicked.connect(self.add_partner_tracking)
        self.btn_documents = QPushButton("Belgeler")
        self.btn_documents.clicked.connect(self.open_selected_partner_documents)
        self.btn_docs_center = QPushButton("Belge Merkezi")
        self.btn_docs_center.clicked.connect(self.open_unified_documents_center)
        self.btn_edit_partner = QPushButton("Ortak Bilgilerini Duzenle")
        self.btn_edit_partner.clicked.connect(self.edit_selected_partner)
        self.btn_more = QPushButton("Daha Fazla")
        self.btn_more.clicked.connect(self.open_selected_partner_menu)
        for btn in (
            self.btn_add_shipment,
            self.btn_documents,
            self.btn_docs_center,
            self.btn_edit_partner,
            self.btn_more,
        ):
            btn.setFixedHeight(36)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            actions.addWidget(btn)
        top_row.addLayout(actions)
        hero_layout.addLayout(top_row)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(12)
        self.stat_total = self._create_stat_card("Toplam Gonderi", "0")
        self.stat_active = self._create_stat_card("Surecte", "0")
        self.stat_done = self._create_stat_card("Tamamlanan", "0")
        self.stat_last = self._create_stat_card("Son Gonderim", "-")
        for card in (self.stat_total, self.stat_active, self.stat_done, self.stat_last):
            stats_row.addWidget(card, 1)
        hero_layout.addLayout(stats_row)
        workspace_layout.addWidget(self.partner_hero)

        self.shipment_card = QFrame()
        shipment_layout = QVBoxLayout(self.shipment_card)
        shipment_layout.setContentsMargins(18, 18, 18, 18)
        shipment_layout.setSpacing(12)
        self.lbl_shipments_title = QLabel("Gonderilen Urunler")
        self.lbl_shipments_sub = QLabel(
            "Secili partnerin acik, servis ve gecmis kayitlari."
        )
        shipment_layout.addWidget(self.lbl_shipments_title)
        shipment_layout.addWidget(self.lbl_shipments_sub)

        self.partner_tabs = QTabWidget()
        self.partner_tabs.setDocumentMode(True)

        self.tab_active = QWidget()
        active_layout = QVBoxLayout(self.tab_active)
        active_layout.setContentsMargins(0, 8, 0, 0)
        self.shipment_table = self._create_tracking_table()
        active_layout.addWidget(self.shipment_table)
        self.empty_label = QLabel("Bu partner icin henuz aktif sevk kaydi yok.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        active_layout.addWidget(self.empty_label)

        self.tab_history = QWidget()
        history_layout = QVBoxLayout(self.tab_history)
        history_layout.setContentsMargins(0, 8, 0, 0)
        self.history_table = self._create_tracking_table()
        history_layout.addWidget(self.history_table)
        self.history_empty_label = QLabel("Tamamlanmis veya kapanmis kayit bulunmuyor.")
        self.history_empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_layout.addWidget(self.history_empty_label)

        self.tab_notes = QWidget()
        notes_layout = QVBoxLayout(self.tab_notes)
        notes_layout.setContentsMargins(0, 12, 0, 0)
        self.notes_summary = QLabel(
            "Secili partner icin hizli notlar ve baglamsal aciklamalar."
        )
        self.notes_summary.setWordWrap(True)
        self.btn_open_notes = QPushButton("Partner Notlarini Ac")
        self.btn_open_notes.setFixedHeight(38)
        self.btn_open_notes.clicked.connect(self.open_selected_partner_notes)
        notes_layout.addWidget(self.notes_summary)
        notes_layout.addWidget(self.btn_open_notes, 0, Qt.AlignmentFlag.AlignLeft)
        notes_layout.addStretch()

        self.tab_finance = QWidget()
        finance_layout = QVBoxLayout(self.tab_finance)
        finance_layout.setContentsMargins(0, 12, 0, 0)
        self.finance_summary = QLabel(
            "Komisyon, tahsilat ve partner bazli finans hareketlerini yonetin."
        )
        self.finance_summary.setWordWrap(True)
        self.finance_card = QFrame()
        finance_card_layout = QVBoxLayout(self.finance_card)
        finance_card_layout.setContentsMargins(16, 16, 16, 16)
        finance_card_layout.setSpacing(6)
        self.finance_commission = QLabel("Komisyon: -")
        self.finance_contact = QLabel("Iletisim: -")
        self.btn_open_finance = QPushButton("Tahsilat / Finans Islemi")
        self.btn_open_finance.setFixedHeight(38)
        self.btn_open_finance.clicked.connect(self.open_selected_partner_finance)
        finance_card_layout.addWidget(self.finance_commission)
        finance_card_layout.addWidget(self.finance_contact)
        finance_card_layout.addWidget(
            self.btn_open_finance, 0, Qt.AlignmentFlag.AlignLeft
        )
        finance_layout.addWidget(self.finance_summary)
        finance_layout.addWidget(self.finance_card)
        finance_layout.addStretch()

        self.tab_documents = QWidget()
        documents_layout = QVBoxLayout(self.tab_documents)
        documents_layout.setContentsMargins(0, 12, 0, 0)
        self.documents_summary = QLabel(
            "Secili partnerin sozlesme, teklif, fatura ve sevk belgeleri."
        )
        self.documents_summary.setWordWrap(True)
        self.btn_open_documents = QPushButton("Belgeleri Ac")
        self.btn_open_documents.setFixedHeight(38)
        self.btn_open_documents.clicked.connect(self.open_selected_partner_documents)
        self.documents_table = QTableWidget()
        self.documents_table.setColumnCount(4)
        self.documents_table.setHorizontalHeaderLabels(
            ["Baslik", "Kategori", "Sevk", "Eklenme"]
        )
        self.documents_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.documents_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.documents_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.documents_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.documents_table.setShowGrid(False)
        self.documents_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.documents_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.documents_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.documents_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        documents_layout.addWidget(self.documents_summary)
        documents_layout.addWidget(
            self.btn_open_documents, 0, Qt.AlignmentFlag.AlignLeft
        )
        documents_layout.addWidget(self.documents_table)

        self.tab_timeline = QWidget()
        timeline_layout = QVBoxLayout(self.tab_timeline)
        timeline_layout.setContentsMargins(0, 12, 0, 0)
        self.timeline_summary = QLabel(
            "Partner sevklerinin olusturma, teklif, onay, gonderim ve donus olaylari."
        )
        self.timeline_summary.setWordWrap(True)
        self.timeline_table = QTableWidget()
        self.timeline_table.setColumnCount(4)
        self.timeline_table.setHorizontalHeaderLabels(["Tarih", "Tip", "Detay", "Sevk"])
        self.timeline_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.timeline_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.timeline_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.timeline_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.timeline_table.setShowGrid(False)
        self.timeline_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.timeline_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.timeline_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Stretch
        )
        self.timeline_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents
        )
        timeline_layout.addWidget(self.timeline_summary)
        timeline_layout.addWidget(self.timeline_table)

        self.partner_tabs.addTab(self.tab_active, "Aktif Gonderiler")
        self.partner_tabs.addTab(self.tab_history, "Gecmis")
        self.partner_tabs.addTab(self.tab_notes, "Notlar")
        self.partner_tabs.addTab(self.tab_finance, "Finans")
        self.partner_tabs.addTab(self.tab_documents, "Belgeler")
        self.partner_tabs.addTab(self.tab_timeline, "Zaman Cizelgesi")
        self.tab_trends = QWidget()
        trends_layout = QVBoxLayout(self.tab_trends)
        trends_layout.setContentsMargins(0, 12, 0, 0)
        self.trends_summary = QLabel(
            "Partnerin aylik sevk, donus, maliyet ve teklif trendleri."
        )
        self.trends_summary.setWordWrap(True)
        self.trend_table = QTableWidget()
        self.trend_table.setColumnCount(6)
        self.trend_table.setHorizontalHeaderLabels(
            [
                "Donem",
                "Sevk",
                "Tamamlanan",
                "Partner Maliyeti",
                "Musteriye Yansiyan",
                "Teklif",
            ]
        )
        self.trend_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.trend_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.trend_table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.trend_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.trend_table.setShowGrid(False)
        self.trend_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self.trend_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.trend_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.ResizeToContents
        )
        self.trend_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Stretch
        )
        self.trend_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self.trend_table.horizontalHeader().setSectionResizeMode(
            5, QHeaderView.ResizeMode.Stretch
        )
        trends_layout.addWidget(self.trends_summary)
        trends_layout.addWidget(self.trend_table)
        self.partner_tabs.addTab(self.tab_trends, "Trendler")
        shipment_layout.addWidget(self.partner_tabs)
        workspace_layout.addWidget(self.shipment_card, 1)
        self.splitter.addWidget(self.workspace)

    def _create_tracking_table(self):
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            [
                "Emanet No",
                "Musteri",
                "Urun",
                "Gonderim",
                "Durum",
                "Kargo / Servis No",
            ]
        )
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        table.setColumnWidth(0, 130)
        table.setColumnWidth(3, 120)
        table.setColumnWidth(4, 150)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setShowGrid(False)
        table.setStyleSheet(
            theme_qss(
                "QTableWidget { border-radius: 12px; border: 1px solid @border; background: @surface; outline: none; }"
                "QTableWidget::item { color: @text; padding: 10px; border: none; outline: none; }"
                "QTableWidget::item:selected { background: @accent; color: @selection_text; border: none; outline: none; }"
                "QTableWidget::item:focus { border: none; outline: none; }"
                "QTableCornerButton::section { background: @surface_alt; border: none; }"
            )
        )
        table.cellDoubleClicked.connect(self.open_selected_tracking)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(
            self._show_partner_tracking_context_menu
        )
        return table

    def _create_stat_card(self, title, value):
        card = QFrame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        value_label = QLabel(value)
        title_label = QLabel(title)
        card._value_label = value_label
        card._title_label = title_label
        layout.addWidget(value_label)
        layout.addWidget(title_label)
        return card

    def load_data(self):
        try:
            rows = self.customer_manager.get_customers() or []
            self.all_partners = [
                row
                for row in rows
                if hasattr(row, "keys") and self._is_partner_row(row)
            ]
        except Exception as e:
            self.all_partners = []
            self.notify(f"Calisma ortaklari yuklenemedi: {e}", "error")
        self.rebuild_service_type_filter()
        self.apply_filters()

    def _is_partner_row(self, row):
        try:
            if "is_partner" in row.keys() and int(row["is_partner"] or 0) == 1:
                return True
        except Exception:
            pass
        row_type = (
            str(row["type"] or "").strip().casefold() if "type" in row.keys() else ""
        )
        return row_type in {"bayi", "tedarikçi", "tedarikci"}

    def _partner_badge(self, partner):
        name = str(partner["name"] or "").strip()
        initials = "".join(part[0].upper() for part in name.split()[:2] if part)
        return initials or "PT"

    def rebuild_service_type_filter(self):
        values = set()
        for row in self.all_partners:
            value = (
                str(row["service_type"] or "").strip()
                if "service_type" in row.keys()
                else ""
            )
            if value:
                values.add(value)
        self.cmb_service_type.blockSignals(True)
        self.cmb_service_type.clear()
        self.cmb_service_type.addItems(["Tumu"] + sorted(values))
        self.cmb_service_type.blockSignals(False)

    def on_service_type_changed(self, _index):
        text = self.cmb_service_type.currentText().strip()
        self.current_service_type = None if not text or text == "Tumu" else text
        self.apply_filters()

    def on_commission_filter_changed(self, _index):
        text = self.cmb_commission.currentText().strip()
        if text == "Komisyonlu":
            self.current_commission_filter = "HAS"
        elif text == "Komisyonsuz":
            self.current_commission_filter = "NONE"
        else:
            self.current_commission_filter = None
        self.apply_filters()

    def apply_filters(self):
        search = self.inp_search.text().strip().lower()
        rows = []
        for row in self.all_partners:
            name = str(row["name"] or "")
            phone = str(row["phone"] or "")
            email = str(row["email"] or "")
            city = str(row["city"] or "") if "city" in row.keys() else ""
            service_type = (
                str(row["service_type"] or "") if "service_type" in row.keys() else ""
            )
            blob = " ".join([name, phone, email, city, service_type]).lower()
            if search and search not in blob:
                continue
            if self.current_service_type and service_type != self.current_service_type:
                continue
            commission = 0.0
            try:
                commission = float(row["commission_rate"] or 0)
            except Exception:
                commission = 0.0
            if self.current_commission_filter == "HAS" and commission <= 0:
                continue
            if self.current_commission_filter == "NONE" and commission > 0:
                continue
            rows.append(row)
        self.filtered_partners = rows
        self.populate_partner_list()

    def populate_partner_list(self):
        selected_id = (
            self.selected_partner["id"]
            if self.selected_partner and "id" in self.selected_partner.keys()
            else None
        )
        self.partner_list.blockSignals(True)
        self.partner_list.clear()
        for partner in self.filtered_partners:
            service_type = (
                str(partner["service_type"] or "Genel")
                if "service_type" in partner.keys()
                else "Genel"
            )
            city = str(partner["city"] or "") if "city" in partner.keys() else ""
            label = "{name}\n{service}  |  {city}".format(
                name="{badge} {name}".format(
                    badge=self._partner_badge(partner),
                    name=str(partner["name"] or "Adsiz Partner"),
                ),
                service=service_type,
                city=city or "Sehir yok",
            )
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, int(partner["id"]))
            self.partner_list.addItem(item)
        self.partner_list.blockSignals(False)
        has_partners = len(self.filtered_partners) > 0
        self.partner_list.setVisible(has_partners)
        self.partner_list_empty.setVisible(not has_partners)
        self.lbl_total.setText(
            "Toplam partner: {count}".format(count=len(self.filtered_partners))
        )
        if self.filtered_partners:
            target_row = 0
            if selected_id is not None:
                for idx in range(self.partner_list.count()):
                    if (
                        self.partner_list.item(idx).data(Qt.ItemDataRole.UserRole)
                        == selected_id
                    ):
                        target_row = idx
                        break
            self.partner_list.setCurrentRow(target_row)
        else:
            self.selected_partner = None
            self.render_partner_details()

    def on_partner_selected(self, row):
        self.selected_partner = (
            self.filtered_partners[row]
            if 0 <= row < len(self.filtered_partners)
            else None
        )
        self.render_partner_details()

    def _normalize_tracking(self, row):
        if isinstance(row, dict):
            return {
                "id": row.get("id"),
                "internal_no": row.get("internal_no") or row.get("serial_no") or "",
                "customer": row.get("customer_name") or row.get("customer") or "",
                "product": row.get("product_name") or row.get("product") or "",
                "service": row.get("partner_name") or row.get("service") or "",
                "service_no": row.get("external_ref_no") or row.get("service_no") or "",
                "date": row.get("sent_at") or row.get("date") or "",
                "out_cargo": row.get("outbound_tracking_no")
                or row.get("out_cargo")
                or "",
                "in_cargo": row.get("return_tracking_no") or row.get("in_cargo") or "",
                "status": row.get("status") or "",
                "notes": row.get("notes") or "",
            }
        return {
            "id": row[0],
            "internal_no": row[1] or "",
            "customer": row[2] or "",
            "product": row[3] or "",
            "service": row[4] or "",
            "service_no": row[5] or "",
            "date": row[6] or "",
            "out_cargo": row[7] or "",
            "in_cargo": row[8] or "",
            "status": row[9] or "",
            "notes": row[10] or "",
        }

    def _ensure_partner_runtime_tables(self):
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
            CREATE TABLE IF NOT EXISTS partner_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                shipment_id INTEGER,
                title TEXT NOT NULL,
                category TEXT,
                file_path TEXT NOT NULL,
                added_at TEXT NOT NULL
            )
            """
        )
        self.db.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS partner_timeline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                partner_id INTEGER NOT NULL,
                shipment_id INTEGER,
                event_type TEXT NOT NULL,
                detail TEXT,
                event_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self.db.conn.commit()

    def _partner_trackings(self, partner):
        if not partner:
            return []
        self._ensure_partner_runtime_tables()
        try:
            self.db.cursor.execute(
                """
                SELECT id, COALESCE(serial_no, ''), COALESCE(customer_name, ''), COALESCE(product_name, ''),
                       COALESCE(partner_name, ''), COALESCE(external_ref_no, ''), COALESCE(sent_at, ''),
                       COALESCE(outbound_tracking_no, ''), COALESCE(return_tracking_no, ''), COALESCE(status, ''),
                       COALESCE(notes, '')
                FROM partner_shipments
                WHERE partner_id = ?
                ORDER BY COALESCE(sent_at, created_at, updated_at) DESC, id DESC
                """,
                (int(partner["id"]),),
            )
            rows = [
                self._normalize_tracking(row)
                for row in (self.db.cursor.fetchall() or [])
            ]
        except Exception as e:
            logger.error("Partner tracking load error: %s", e)
            rows = []
        return rows

    def _partner_finance_summary(self, partner):
        if not partner:
            return {
                "partner_cost": 0.0,
                "paid_total": 0.0,
                "customer_total": 0.0,
                "balance": 0.0,
            }
        self._ensure_partner_runtime_tables()
        self.db.cursor.execute(
            "SELECT COALESCE(SUM(partner_cost), 0), COALESCE(SUM(customer_price), 0) FROM partner_shipments WHERE partner_id = ?",
            (int(partner["id"]),),
        )
        partner_cost, customer_total = self.db.cursor.fetchone() or (0, 0)
        self.db.cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM partner_finance_entries
            WHERE partner_id = ? AND entry_type = 'PAYMENT'
            """,
            (int(partner["id"]),),
        )
        paid_total = float((self.db.cursor.fetchone() or [0])[0] or 0)
        partner_cost = float(partner_cost or 0)
        customer_total = float(customer_total or 0)
        balance = partner_cost - paid_total
        return {
            "partner_cost": partner_cost,
            "paid_total": paid_total,
            "customer_total": customer_total,
            "balance": balance,
        }

    def _partner_quote_summary(self, partner):
        if not partner:
            return {"quote_total": 0.0, "waiting_count": 0, "approved_count": 0}
        self._ensure_partner_runtime_tables()
        self.db.cursor.execute(
            """
            SELECT COALESCE(SUM(quote_amount), 0),
                   SUM(CASE WHEN COALESCE(approval_status, '') LIKE '%Bekliyor%' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN COALESCE(approval_status, '') LIKE '%Onay%' THEN 1 ELSE 0 END)
            FROM partner_shipments
            WHERE partner_id = ?
            """,
            (int(partner["id"]),),
        )
        quote_total, waiting_count, approved_count = self.db.cursor.fetchone() or (
            0,
            0,
            0,
        )
        return {
            "quote_total": float(quote_total or 0),
            "waiting_count": int(waiting_count or 0),
            "approved_count": int(approved_count or 0),
        }

    def _sla_hours(self, partner):
        try:
            raw = str(partner.get("sla_level") or "")
            digits = "".join(ch for ch in raw if ch.isdigit())
            return int(digits) if digits else 24
        except Exception:
            return 24

    def _partner_scorecard(self, partner, tracks):
        sla_hours = self._sla_hours(partner)
        turnaround_values = []
        on_time = 0
        completed = 0
        serials = []
        quality_issue_count = 0
        self.db.cursor.execute(
            """
            SELECT COALESCE(serial_no, ''), COALESCE(sent_at, ''), COALESCE(returned_at, ''),
                   COALESCE(return_qc, ''), COALESCE(missing_parts, '')
            FROM partner_shipments
            WHERE partner_id = ?
            """,
            (int(partner["id"]),),
        )
        for serial_no, sent_at, returned_at, return_qc, missing_parts in (
            self.db.cursor.fetchall() or []
        ):
            if serial_no:
                serials.append(serial_no)
            if missing_parts and str(missing_parts).strip().casefold() not in {
                "",
                "yok",
                "-",
            }:
                quality_issue_count += 1
            if return_qc and str(return_qc).strip().casefold() not in {
                "gecti",
                "basarili",
                "tamam",
            }:
                quality_issue_count += 1
            try:
                if sent_at and returned_at:
                    sent_dt = datetime.strptime(sent_at, "%Y-%m-%d")
                    ret_dt = datetime.strptime(returned_at, "%Y-%m-%d")
                    hours = max((ret_dt - sent_dt).total_seconds() / 3600.0, 0)
                    turnaround_values.append(hours)
                    completed += 1
                    if hours <= sla_hours:
                        on_time += 1
            except Exception:
                continue
        avg_turnaround = (
            round(sum(turnaround_values) / len(turnaround_values), 1)
            if turnaround_values
            else 0.0
        )
        repeat_serials = sum(1 for count in Counter(serials).values() if count > 1)
        on_time_rate = round((on_time / completed) * 100, 1) if completed else 0.0
        active_count = len(
            [r for r in tracks if not self._is_completed_status(r["status"])]
        )
        comeback_ratio = (
            round((repeat_serials / len(serials)) * 100, 1) if serials else 0.0
        )
        return {
            "avg_turnaround": avg_turnaround,
            "on_time_rate": on_time_rate,
            "repeat_serials": repeat_serials,
            "quality_issues": quality_issue_count,
            "active_count": active_count,
            "comeback_ratio": comeback_ratio,
        }

    def _partner_document_rows(self, partner):
        if not partner:
            return []
        self._ensure_partner_runtime_tables()
        self.db.cursor.execute(
            """
            SELECT title, COALESCE(category, ''), COALESCE(shipment_id, ''), added_at
            FROM partner_documents
            WHERE partner_id = ?
            ORDER BY added_at DESC, id DESC
            """,
            (int(partner["id"]),),
        )
        return self.db.cursor.fetchall() or []

    def _partner_timeline_rows(self, partner):
        if not partner:
            return []
        self._ensure_partner_runtime_tables()
        self.db.cursor.execute(
            """
            SELECT event_date, event_type, COALESCE(detail, ''), COALESCE(shipment_id, '')
            FROM partner_timeline
            WHERE partner_id = ?
            ORDER BY event_date DESC, id DESC
            LIMIT 100
            """,
            (int(partner["id"]),),
        )
        return self.db.cursor.fetchall() or []

    def _partner_trend_rows(self, partner):
        if not partner:
            return []
        self._ensure_partner_runtime_tables()
        self.db.cursor.execute(
            """
            SELECT
                COALESCE(substr(COALESCE(sent_at, created_at), 1, 7), '-') AS period,
                COUNT(*) AS shipment_count,
                SUM(CASE WHEN COALESCE(status, '') IN ('Geri Geldi', 'Musteriye Teslim Edildi', 'Tamamlandi', 'Teslim Edildi') THEN 1 ELSE 0 END) AS completed_count,
                COALESCE(SUM(partner_cost), 0) AS partner_cost,
                COALESCE(SUM(customer_price), 0) AS customer_total,
                COALESCE(SUM(quote_amount), 0) AS quote_total
            FROM partner_shipments
            WHERE partner_id = ?
            GROUP BY COALESCE(substr(COALESCE(sent_at, created_at), 1, 7), '-')
            ORDER BY period DESC
            """,
            (int(partner["id"]),),
        )
        return self.db.cursor.fetchall() or []

    def _populate_simple_table(self, table, rows):
        table.setRowCount(0)
        for row_idx, row in enumerate(rows):
            table.insertRow(row_idx)
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value if value not in (None, "") else "-"))
                if col_idx in (0, 1, 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row_idx, col_idx, item)
            table.setRowHeight(row_idx, 44)

    def _is_completed_status(self, status):
        text = str(status or "").strip().casefold()
        return text in {
            "geri geldi",
            "musteriye teslim edildi",
            "tamamlandi",
            "teslim edildi",
        }

    def render_partner_details(self):
        if not self.selected_partner:
            self.partner_name.setText("Partner secin")
            self.partner_meta.setText(
                "Soldaki listeden bir partner secin veya yeni ortak ekleyin."
            )
            self._set_stat_card(self.stat_total, "0")
            self._set_stat_card(self.stat_active, "0")
            self._set_stat_card(self.stat_done, "0")
            self._set_stat_card(self.stat_last, "-")
            self.partner_scorecard.setText(
                "Ortalama donus, SLA uyumu, tekrar ariza ve kalite sorunlari bu alanda gorunur."
            )
            self.shipment_table.setRowCount(0)
            self.history_table.setRowCount(0)
            self.empty_label.show()
            self.history_empty_label.show()
            self.notes_summary.setText(
                "Secili partnerin operasyon notlari burada ozetlenir."
            )
            self.finance_summary.setText(
                "Komisyon, tahsilat ve partner bazli finans hareketlerini yonetin."
            )
            self.finance_commission.setText("Komisyon: -")
            self.finance_contact.setText("Iletisim: -")
            self.documents_summary.setText(
                "Secili partnerin belge havuzu burada listelenir."
            )
            self.timeline_summary.setText(
                "Secili partnerin operasyon zaman cizelgesi burada listelenir."
            )
            self.trends_summary.setText(
                "Partnerin aylik sevk, donus, maliyet ve teklif trendleri."
            )
            self.documents_table.setRowCount(0)
            self.timeline_table.setRowCount(0)
            self.trend_table.setRowCount(0)
            for btn in (
                self.btn_add_shipment,
                self.btn_documents,
                self.btn_docs_center,
                self.btn_edit_partner,
                self.btn_more,
            ):
                btn.setEnabled(False)
            for btn in (
                self.btn_open_notes,
                self.btn_open_finance,
                self.btn_open_documents,
            ):
                btn.setEnabled(False)
            return

        for btn in (
            self.btn_add_shipment,
            self.btn_documents,
            self.btn_docs_center,
            self.btn_edit_partner,
            self.btn_more,
        ):
            btn.setEnabled(True)
        for btn in (
            self.btn_open_notes,
            self.btn_open_finance,
            self.btn_open_documents,
        ):
            btn.setEnabled(True)

        partner_type = (
            str(self.selected_partner["type"] or "Partner")
            if "type" in self.selected_partner.keys()
            else "Partner"
        )
        service_type = (
            str(self.selected_partner["service_type"] or "Genel")
            if "service_type" in self.selected_partner.keys()
            else "Genel"
        )
        city = (
            str(self.selected_partner["city"] or "")
            if "city" in self.selected_partner.keys()
            else ""
        )
        contract_type = (
            str(self.selected_partner["contract_type"] or "Standart Anlasma")
            if "contract_type" in self.selected_partner.keys()
            else "Standart Anlasma"
        )
        sla_level = (
            str(self.selected_partner["sla_level"] or "24 Saat Donus")
            if "sla_level" in self.selected_partner.keys()
            else "24 Saat Donus"
        )
        commission = 0.0
        try:
            commission = float(self.selected_partner["commission_rate"] or 0)
        except Exception:
            commission = 0.0
        meta = [partner_type, service_type]
        if city:
            meta.append(city)
        if commission:
            meta.append("Komisyon %{0:.2f}".format(commission))
        self.partner_name.setText(
            "{badge}  {name}".format(
                badge=self._partner_badge(self.selected_partner),
                name=str(self.selected_partner["name"] or "Partner"),
            )
        )
        self.partner_meta.setText("  |  ".join(meta))
        self.notes_summary.setText(
            "Bu partner icin acik notlar, iletisim dili ve operasyonel ozel kosullar Notlar sekmesinden yonetilir."
        )
        finance = self._partner_finance_summary(self.selected_partner)
        quote = self._partner_quote_summary(self.selected_partner)
        self.finance_summary.setText(
            "Partnere gonderilen urunlerin maliyeti, partner odemeleri, teklif/onay ve musteriye yansitilan tutarlar bu alandan takip edilir."
        )
        phone = str(self.selected_partner["phone"] or "-")
        email = str(self.selected_partner["email"] or "-")
        self.finance_commission.setText(
            "Partner Borcu: {cost} | Odenen: {paid} | Kalan: {balance}".format(
                cost=CurrencyHelper.format_try_for_display(
                    finance["partner_cost"], db=self.db, include_try_reference=False
                ),
                paid=CurrencyHelper.format_try_for_display(
                    finance["paid_total"], db=self.db, include_try_reference=False
                ),
                balance=CurrencyHelper.format_try_for_display(
                    finance["balance"], db=self.db, include_try_reference=False
                ),
            )
        )
        self.finance_contact.setText(
            "Iletisim: {phone}  |  {email}  |  Sozlesme: {contract}  |  SLA: {sla}  |  Teklif Toplami: {quote_total}  |  Onay Bekleyen: {waiting}  |  Onaylanan: {approved}  |  Musteriye Yansiyan: {customer_total}".format(
                phone=phone,
                email=email,
                contract=contract_type,
                sla=sla_level,
                quote_total=CurrencyHelper.format_try_for_display(
                    quote["quote_total"], db=self.db, include_try_reference=False
                ),
                waiting=quote["waiting_count"],
                approved=quote["approved_count"],
                customer_total=CurrencyHelper.format_try_for_display(
                    finance["customer_total"], db=self.db, include_try_reference=False
                ),
            )
        )
        doc_count = len(self._partner_document_rows(self.selected_partner))
        self.documents_summary.setText(
            "Sozlesme, teklif, fatura ve sevk belgeleri. Bu partner icin toplam belge: {count}".format(
                count=doc_count
            )
        )
        self.timeline_summary.setText(
            "Partnerin sevk, teklif, onay ve donus olaylari son 100 kayit ile izlenir."
        )
        self.trends_summary.setText(
            "Aylik trendler sevk hacmi, kapanan is, partner maliyeti ve teklif toplamlarini gosterir."
        )
        self._populate_simple_table(
            self.documents_table, self._partner_document_rows(self.selected_partner)
        )
        self._populate_simple_table(
            self.timeline_table, self._partner_timeline_rows(self.selected_partner)
        )
        self._populate_trend_table(
            self.trend_table, self._partner_trend_rows(self.selected_partner)
        )

        tracks = self._partner_trackings(self.selected_partner)
        scorecard = self._partner_scorecard(self.selected_partner, tracks)
        self.partner_scorecard.setText(
            "Ortalama Donus: {avg} saat  |  SLA Uyum: %{sla}  |  Tekrar Ariza: {repeat}  |  Geri Donus Orani: %{comeback}  |  Kalite Sorunu: {quality}  |  Aktif Is: {active}".format(
                avg=scorecard["avg_turnaround"],
                sla=scorecard["on_time_rate"],
                repeat=scorecard["repeat_serials"],
                comeback=scorecard["comeback_ratio"],
                quality=scorecard["quality_issues"],
                active=scorecard["active_count"],
            )
        )
        self._set_stat_card(self.stat_total, str(len(tracks)))
        self._set_stat_card(
            self.stat_active,
            str(len([r for r in tracks if not self._is_completed_status(r["status"])])),
        )
        self._set_stat_card(
            self.stat_done,
            str(len([r for r in tracks if self._is_completed_status(r["status"])])),
        )
        self._set_stat_card(self.stat_last, tracks[0]["date"] if tracks else "-")

        self.shipment_table.setRowCount(0)
        self.history_table.setRowCount(0)
        active_tracks = [
            track for track in tracks if not self._is_completed_status(track["status"])
        ]
        history_tracks = [
            track for track in tracks if self._is_completed_status(track["status"])
        ]
        for row_idx, track in enumerate(active_tracks):
            self.shipment_table.insertRow(row_idx)
            values = [
                track["internal_no"] or "-",
                track["customer"] or "-",
                track["product"] or "-",
                track["date"] or "-",
                track["status"] or "-",
                " / ".join([v for v in [track["out_cargo"], track["service_no"]] if v])
                or "-",
            ]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, track["id"])
                if col_idx in (0, 3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.shipment_table.setItem(row_idx, col_idx, item)
            self.shipment_table.setRowHeight(row_idx, 54)
        for row_idx, track in enumerate(history_tracks):
            self.history_table.insertRow(row_idx)
            values = [
                track["internal_no"] or "-",
                track["customer"] or "-",
                track["product"] or "-",
                track["date"] or "-",
                track["status"] or "-",
                " / ".join([v for v in [track["in_cargo"], track["service_no"]] if v])
                or "-",
            ]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setData(Qt.ItemDataRole.UserRole, track["id"])
                if col_idx in (0, 3, 4):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.history_table.setItem(row_idx, col_idx, item)
            self.history_table.setRowHeight(row_idx, 54)
        self.empty_label.setVisible(len(active_tracks) == 0)
        self.history_empty_label.setVisible(len(history_tracks) == 0)

    def _set_stat_card(self, card, value):
        card._value_label.setText(str(value))

    def apply_theme_styles(self):
        self.lbl_title.setStyleSheet(
            theme_qss(
                "color: @text; font-size: 24px; font-weight: 800; background: transparent; border: none;"
            )
        )
        self.lbl_sub.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 12px; background: transparent; border: none;"
            )
        )
        self.sidebar.setStyleSheet(theme_qss("background: transparent;"))
        self.workspace.setStyleSheet(theme_qss("background: transparent;"))
        for frame in (self.partner_hero, self.shipment_card):
            frame.setStyleSheet(
                theme_qss(
                    "background: @surface; border: 1px solid @border; border-radius: 18px;"
                )
            )
        self.partner_name.setStyleSheet(
            theme_qss(
                "color: @text; font-size: 26px; font-weight: 800; background: transparent; border: none;"
            )
        )
        self.partner_meta.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 12px; background: transparent; border: none;"
            )
        )
        self.partner_scorecard.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 12px; font-weight: 700; background: transparent; border: none;"
            )
        )
        self.lbl_shipments_title.setStyleSheet(
            theme_qss(
                "color: @text; font-size: 16px; font-weight: 700; background: transparent; border: none;"
            )
        )
        self.lbl_shipments_sub.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 11px; background: transparent; border: none;"
            )
        )
        self.lbl_total.setStyleSheet(theme_qss("color: @text_muted; font-weight: 600;"))
        self.partner_list.setStyleSheet(
            theme_qss(
                "QListWidget { background: @surface; border: 1px solid @border; border-radius: 16px; padding: 8px; }"
                "QListWidget::item { background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 12px; padding: 12px; margin: 0 0 8px 0; }"
                "QListWidget::item:selected { background: @accent; color: @selection_text; border: none; }"
                "QListWidget::item:hover { border-color: @accent; }"
            )
        )
        table_qss = theme_qss(
            "QTableWidget { border-radius: 12px; border: 1px solid @border; background: @surface; }"
            "QHeaderView::section { background: @surface_alt; color: @text; padding: 12px; font-weight: 700; border: none; }"
            "QTableWidget::item { color: @text; padding: 10px; border-bottom: 1px solid @border; }"
            "QTableWidget::item:selected { background: @accent; color: @selection_text; }"
        )
        self.shipment_table.setStyleSheet(table_qss)
        self.history_table.setStyleSheet(table_qss)
        self.empty_label.setStyleSheet(theme_qss("color: @text_muted; padding: 18px;"))
        self.history_empty_label.setStyleSheet(
            theme_qss("color: @text_muted; padding: 18px;")
        )
        self.partner_tabs.setStyleSheet(
            theme_qss(
                "QTabWidget::pane { border: none; background: transparent; }"
                "QTabBar::tab { background: @surface_alt; color: @text; padding: 10px 16px; border-radius: 12px; margin-right: 6px; border: 1px solid @border; font-weight: 700; }"
                "QTabBar::tab:selected { background: @accent; color: @selection_text; border: none; }"
            )
        )
        self.notes_summary.setStyleSheet(
            theme_qss(
                "color: @text; background: transparent; border: none; line-height: 1.5;"
            )
        )
        self.finance_summary.setStyleSheet(
            theme_qss(
                "color: @text; background: transparent; border: none; line-height: 1.5;"
            )
        )
        self.documents_summary.setStyleSheet(
            theme_qss(
                "color: @text; background: transparent; border: none; line-height: 1.5;"
            )
        )
        self.timeline_summary.setStyleSheet(
            theme_qss(
                "color: @text; background: transparent; border: none; line-height: 1.5;"
            )
        )
        self.finance_card.setStyleSheet(
            theme_qss(
                "background: @surface_alt; border: 1px solid @border; border-radius: 14px;"
            )
        )
        self.finance_commission.setStyleSheet(
            theme_qss(
                "color: @text; font-size: 14px; font-weight: 700; background: transparent; border: none;"
            )
        )
        self.finance_contact.setStyleSheet(
            theme_qss(
                "color: @text_muted; font-size: 12px; background: transparent; border: none;"
            )
        )
        for btn in (
            self.btn_add_partner,
            self.btn_add_shipment,
            self.btn_documents,
            self.btn_docs_center,
            self.btn_edit_partner,
            self.btn_more,
        ):
            btn.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        for btn in (
            self.btn_open_notes,
            self.btn_open_finance,
            self.btn_open_documents,
        ):
            btn.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        for card in (self.stat_total, self.stat_active, self.stat_done, self.stat_last):
            card.setStyleSheet(
                theme_qss(
                    "background: @surface_alt; border: 1px solid @border; border-radius: 14px;"
                )
            )
            card._value_label.setStyleSheet(
                theme_qss(
                    "color: @text; font-size: 22px; font-weight: 800; background: transparent; border: none;"
                )
            )
            card._title_label.setStyleSheet(
                theme_qss(
                    "color: @text_muted; font-size: 11px; font-weight: 700; background: transparent; border: none;"
                )
            )
        aux_table_qss = theme_qss(
            "QTableWidget { border-radius: 12px; border: 1px solid @border; background: @surface; }"
            "QHeaderView::section { background: @surface_alt; color: @text; padding: 10px; font-weight: 700; border: none; }"
            "QTableWidget::item { color: @text; padding: 8px; border-bottom: 1px solid @border; }"
            "QTableWidget::item:selected { background: @accent; color: @selection_text; }"
        )
        self.documents_table.setStyleSheet(aux_table_qss)
        self.timeline_table.setStyleSheet(aux_table_qss)
        self.trend_table.setStyleSheet(aux_table_qss)

    def refresh_theme(self):
        self.apply_theme_styles()

    def add_partner_tracking(self):
        if not self.selected_partner:
            return
        try:
            dlg = PartnerShipmentDialog(
                self.db, self.selected_partner, self.window() or self
            )
            if dlg.exec():
                self.render_partner_details()
        except Exception as e:
            logger.error("Partner tracking dialog open error: %s", e)
            show_error(self, f"Gonderi kaydi acilamadi: {e}")

    def edit_selected_partner(self):
        if self.selected_partner:
            self.edit_partner(self.selected_partner)

    def open_selected_partner_menu(self):
        if self.selected_partner:
            self.open_partner_menu(self.selected_partner, self.btn_more)

    def open_selected_partner_notes(self):
        if self.selected_partner:
            CustomerNotesDialog(
                self.db,
                self.selected_partner["id"],
                self.selected_partner["name"],
                self,
            ).exec()

    def open_selected_partner_finance(self):
        if self.selected_partner:
            self.record_payment_for_partner(self.selected_partner)

    def open_selected_partner_documents(self):
        if self.selected_partner:
            dlg = PartnerDocumentsDialog(
                self.db, self.selected_partner, self.window() or self
            )
            dlg.exec()
            self.render_partner_details()

    def open_unified_documents_center(self):
        if self.selected_partner:
            dlg = UnifiedDocumentsCenterDialog(
                self.db, self.selected_partner, self.window() or self
            )
            dlg.exec()
            self.render_partner_details()

    def open_selected_tracking(self, row, _column=0):
        if row < 0:
            return
        sender_table = self.sender()
        item = (
            sender_table.item(row, 0)
            if sender_table
            else self.shipment_table.item(row, 0)
        )
        if not item:
            return
        track_id = item.data(Qt.ItemDataRole.UserRole)
        dlg = PartnerShipmentDialog(
            self.db, self.selected_partner, self.window() or self, shipment_id=track_id
        )
        if dlg.exec():
            self.render_partner_details()

    def open_partner_menu(self, c, source_btn):
        menu = QMenu(self)
        menu.addAction(
            "Ortak 360",
            lambda: Customer360Dialog(self.db, c["id"], c["name"], self).exec(),
        )
        menu.addAction("Hizmet ve Komisyon", lambda: self.edit_partner(c))
        menu.addAction(
            "Notlar",
            lambda: CustomerNotesDialog(self.db, c["id"], c["name"], self).exec(),
        )
        menu.addAction("Belgeler", lambda: self._open_partner_documents_from_menu(c))
        menu.addAction("Belge Merkezi", self.open_unified_documents_center)
        menu.addSeparator()
        menu.addAction("Yeni Servis Kaydi", lambda: self.create_service_for_partner(c))
        menu.addAction("Partner Finans", lambda: self.record_payment_for_partner(c))
        menu.addAction("Excel Disa Aktar", self.export_partner_shipments_csv)
        menu.addSeparator()
        menu.addAction("WhatsApp Mesaj", lambda: self.send_whatsapp_for_partner(c))
        menu.exec(source_btn.mapToGlobal(source_btn.rect().bottomLeft()))

    def create_service_for_partner(self, c):
        from src.ui.dialogs.new_service_dialog import NewServiceDialog

        sector_manager = getattr(self.main_window, "sector_manager", None)
        NewServiceDialog(
            self.db, self, customer_name=c["name"], sector_manager=sector_manager
        ).exec()

    def record_payment_for_partner(self, c):
        dlg = ModernPaymentDialog(self, self.db, c)
        if dlg.exec():
            data = dlg.get_data()
            if not data:
                return
            date_value = data.get("date")
            if date_value:
                d = QDate.fromString(date_value, "dd.MM.yyyy")
                if d.isValid():
                    date_value = d.toString("yyyy-MM-dd")
            res = self.db.add_transaction_with_customer(
                customer_id=c["id"],
                date=date_value,
                description=data["notes"] or f"{data['method']} ile odeme",
                amount=data["amount"],
                t_type="Gelir",
                category="Tahsilat",
                payment_method=data.get("method"),
                bank_account_id=data.get("bank_account_id"),
            )
            if res:
                show_success(
                    self,
                    f"{CurrencyHelper.format_try_for_display(data['amount'], db=self.db, include_try_reference=False)} tahsilat kaydedildi.",
                )
                self.load_data()
            else:
                show_error(self, "Odeme kaydedilirken bir hata olustu.")

    def send_whatsapp_for_partner(self, c):
        phone = "".join(filter(str.isdigit, str(c["phone"])))
        if phone:
            if phone.startswith("0"):
                phone = "9" + phone
            webbrowser.open(f"https://wa.me/{phone}")

    def _open_partner_documents_from_menu(self, c):
        dlg = PartnerDocumentsDialog(self.db, c, self.window() or self)
        dlg.exec()
        self.load_data()

    def _populate_trend_table(self, table, rows):
        table.setRowCount(0)
        for row_idx, row in enumerate(rows):
            table.insertRow(row_idx)
            (
                period,
                shipment_count,
                completed_count,
                partner_cost,
                customer_total,
                quote_total,
            ) = row
            values = [
                period,
                shipment_count,
                completed_count,
                CurrencyHelper.format_try_for_display(
                    float(partner_cost or 0), db=self.db, include_try_reference=False
                ),
                CurrencyHelper.format_try_for_display(
                    float(customer_total or 0), db=self.db, include_try_reference=False
                ),
                CurrencyHelper.format_try_for_display(
                    float(quote_total or 0), db=self.db, include_try_reference=False
                ),
            ]
            for col_idx, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if col_idx != 0:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row_idx, col_idx, item)
            table.setRowHeight(row_idx, 42)

    def _selected_tracking_id_from_table(self, table):
        row = table.currentRow()
        if row < 0:
            return None
        item = table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _show_partner_tracking_context_menu(self, pos):
        if not is_context_menu_enabled(self.db, page_id=21):
            return
        table = self.sender()
        if not table or not self.selected_partner:
            return
        row = table.rowAt(pos.y())
        if row < 0:
            return
        table.selectRow(row)
        shipment_id = self._selected_tracking_id_from_table(table)
        menu = QMenu(self)
        menu.addAction("Ac / Duzenle", lambda: self.open_selected_tracking(row, 0))
        menu.addAction("Belgeler", lambda: self._open_shipment_documents(shipment_id))
        menu.addAction("Belge Merkezi", self.open_unified_documents_center)
        menu.addAction("Partner Finans", self.open_selected_partner_finance)
        menu.addSeparator()
        menu.addAction("Excel Disa Aktar", self.export_partner_shipments_csv)
        menu.exec(table.viewport().mapToGlobal(pos))

    def _open_shipment_documents(self, shipment_id):
        if not self.selected_partner or not shipment_id:
            return
        dlg = PartnerDocumentsDialog(
            self.db,
            self.selected_partner,
            self.window() or self,
            shipment_id=shipment_id,
        )
        dlg.exec()
        self.render_partner_details()

    def export_partner_shipments_csv(self):
        if not self.selected_partner:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Partner Sevklerini Disa Aktar",
            "partner_sevkleri.xlsx",
            "Excel (*.xlsx)",
        )
        if not file_path:
            return
        tracks = self._partner_trackings(self.selected_partner)
        try:
            with open(file_path, "w", newline="", encoding="utf-8-sig") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(
                    [
                        "Emanet No",
                        "Musteri",
                        "Urun",
                        "Tarih",
                        "Durum",
                        "Gidis",
                        "Donus",
                        "Servis No",
                    ]
                )
                for track in tracks:
                    writer.writerow(
                        [
                            track["internal_no"] or "-",
                            track["customer"] or "-",
                            track["product"] or "-",
                            track["date"] or "-",
                            track["status"] or "-",
                            track["out_cargo"] or "-",
                            track["in_cargo"] or "-",
                            track["service_no"] or "-",
                        ]
                    )
            show_success(self, "Partner sevkleri Excel olarak disa aktarildi.")
        except Exception as e:
            show_error(self, f"Excel disa aktarimi basarisiz: {e}")

    def add_partner(self):
        if PartnerProfileDialog(self.db, self).exec():
            self.load_data()

    def edit_partner(self, c):
        if PartnerProfileDialog(self.db, self, c).exec():
            self.load_data()

    def record_payment_for_partner(self, c):
        try:
            dlg = PartnerFinanceDialog(self.db, c, self.window() or self)
            dlg.exec()
            self.load_data()
        except Exception as e:
            logger.error("Partner finance dialog error: %s", e)
            show_error(self, f"Tahsilat / finans islemi acilamadi: {e}")


class PartnerDialog(ModernDialog):
    def __init__(self, db, parent=None, data=None):
        self.db = db
        self.data = data
        title = "Çalışma Ortağı Düzenle" if data else "Yeni Çalışma Ortağı"
        super().__init__(title, parent, width=720, height=520)
        self.setup_content()
        if data:
            self.load_data()

    def setup_content(self):
        card = QFrame()
        card.setStyleSheet(theme_qss(DesignTokens.get_card_qss()))
        grid = QGridLayout(card)
        grid.setContentsMargins(20, 20, 20, 20)
        grid.setSpacing(12)

        def add_field(label_text, widget, row, col, colspan=1):
            lbl = QLabel(label_text)
            lbl.setStyleSheet(
                theme_qss(f"color: {DesignTokens.MUTED_FOREGROUND}; font-weight: 700;")
            )
            v = QVBoxLayout()
            v.setSpacing(6)
            v.addWidget(lbl)
            v.addWidget(widget)
            grid.addLayout(v, row, col, 1, colspan)

        self.cmb_type = ModernComboBox(items=["Kurumsal", "Bayi", "Tedarikçi"])
        self.cmb_type.setMinimumHeight(42)

        self.inp_name = QLineEdit()
        self.inp_name.setPlaceholderText("Ortak adı / Ünvan")
        self.inp_name.setFixedHeight(42)
        self.inp_name.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_phone = QLineEdit()
        self.inp_phone.setPlaceholderText("05xx ...")
        self.inp_phone.setFixedHeight(42)
        self.inp_phone.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_email = QLineEdit()
        self.inp_email.setPlaceholderText("email@example.com")
        self.inp_email.setFixedHeight(42)
        self.inp_email.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.cmb_service_type = ModernComboBox(
            items=["Genel", "Telefon Servisi", "Bilgisayar Servisi", "Aksesuar / Satış"]
        )
        self.cmb_service_type.setEditable(True)
        self.cmb_service_type.setMinimumHeight(42)

        self.spin_commission = QDoubleSpinBox()
        self.spin_commission.setRange(0, 100)
        self.spin_commission.setDecimals(2)
        self.spin_commission.setSuffix(" %")
        self.spin_commission.setFixedHeight(42)
        self.spin_commission.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        self.inp_city = QLineEdit()
        self.inp_city.setPlaceholderText("Şehir")
        self.inp_city.setFixedHeight(42)
        self.inp_city.setStyleSheet(theme_qss(DesignTokens.get_input_qss()))

        add_field("Ortak Tipi", self.cmb_type, 0, 0)
        add_field("Ortak Adı", self.inp_name, 0, 1)
        add_field("Telefon", self.inp_phone, 1, 0)
        add_field("E-Posta", self.inp_email, 1, 1)
        add_field("Hizmet Türü", self.cmb_service_type, 2, 0)
        add_field("Komisyon Oranı", self.spin_commission, 2, 1)
        add_field("Şehir", self.inp_city, 3, 0, 2)

        self.add_widget(card)
        self.add_cancel_button("Vazgeç")
        self.add_button("Kaydet", "primary", self.save)

    def load_data(self):
        d = self.data
        try:
            self.inp_name.setText(str(d["name"] or ""))
            self.inp_phone.setText(str(d["phone"] or ""))
            self.inp_email.setText(str(d["email"] or ""))
            self.inp_city.setText(str(d["city"] or ""))
            stype = str(d["service_type"] or "")
            if stype:
                self.cmb_service_type.setCurrentText(stype)
            ctype = str(d["type"] or "")
            if ctype:
                self.cmb_type.setCurrentText(ctype)
            try:
                self.spin_commission.setValue(float(d["commission_rate"] or 0))
            except Exception:
                self.spin_commission.setValue(0)
        except Exception:
            pass

    def save(self):
        name = (self.inp_name.text() or "").strip()
        if not name:
            show_error(self, "Ortak adı zorunludur.")
            return

        data = {
            "name": name,
            "phone": (self.inp_phone.text() or "").strip(),
            "email": (self.inp_email.text() or "").strip(),
            "type": self.cmb_type.currentText().strip(),
            "city": (self.inp_city.text() or "").strip(),
            "service_type": self.cmb_service_type.currentText().strip(),
            "commission_rate": float(self.spin_commission.value() or 0),
        }

        try:
            if self.data and "id" in self.data.keys():
                set_clause = ", ".join([f"{k}=?" for k in data.keys()])
                values = list(data.values()) + [self.data["id"]]
                self.db.cursor.execute(
                    f"UPDATE customers SET {set_clause} WHERE id=?", values
                )
                self.db.conn.commit()
            else:
                data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.db.add_customer(data)
            show_success(self, "Çalışma ortağı kaydedildi.")
            self.accept()
        except Exception as e:
            show_error(self, f"Kayıt başarısız: {e}")
