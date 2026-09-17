# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QLineEdit, QFrame, QMenu
)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QFont
import webbrowser
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.design_system import DesignTokens
from src.ui.dialogs.customer_notes_dialog import CustomerNotesDialog
from src.ui.dialogs.customer_360_dialog import Customer360Dialog
from src.ui.dialogs.payment_dialog import ModernPaymentDialog
from src.ui.pages.customers.logic.customer_manager import CustomerManager
from src.ui.widgets.modern_inputs import ModernComboBox
from src.utils.currency_helper import CurrencyHelper

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
        QTimer.singleShot(100, self.load_data)

    def notify(self, message, level="info"):
        if self.main_window and hasattr(self.main_window, "show_notification"):
            self.main_window.show_notification(message, level)
        else:
            if level == "error": show_error(self, message)
            elif level == "success": show_success(self, message)
            elif level == "warning": show_warning(self, message)
            else: show_info(self, message)

    def setup_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(16)

        self.header_frame = QFrame()
        self.header_frame.setStyleSheet(theme_qss(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1e293b, stop:0.5 #334155, stop:1 #475569); border-radius: 16px;"
        ))
        h_layout = QHBoxLayout(self.header_frame)
        h_layout.setContentsMargins(20, 16, 20, 16)

        title_box = QVBoxLayout()
        lbl_title = QLabel("🤝 Çalışma Ortaklarımız")
        lbl_title.setStyleSheet(theme_qss(f"color: #f8fafc; font-size: 22px; font-weight: 800;"))
        lbl_sub = QLabel("Hizmet sağlayıcılar, bayiler ve tedarikçileri tek ekranda yönetin.")
        lbl_sub.setStyleSheet(theme_qss("color: #94a3b8; font-size: 12px;"))
        title_box.addWidget(lbl_title)
        title_box.addWidget(lbl_sub)
        self.lbl_title = lbl_title
        self.lbl_sub = lbl_sub
        h_layout.addLayout(title_box)
        h_layout.addStretch()
        self.layout.addWidget(self.header_frame)

        filter_card = QFrame()
        filter_card.setStyleSheet(theme_qss("background: @surface; border-radius: 12px; border: 1px solid @border;"))
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
        self.cmb_service_type.setPlaceholderText("Hizmet Türü")
        self.cmb_service_type.currentIndexChanged.connect(self.on_service_type_changed)
        f_layout.addWidget(QLabel("Hizmet Türü:"))
        f_layout.addWidget(self.cmb_service_type)

        self.cmb_commission = ModernComboBox()
        self.cmb_commission.addItems(["Tümü", "Komisyonu Olanlar", "Komisyonu Olmayanlar"])
        self.cmb_commission.currentIndexChanged.connect(self.on_commission_filter_changed)
        f_layout.addWidget(QLabel("Komisyon:"))
        f_layout.addWidget(self.cmb_commission)
        f_layout.addStretch()

        self.inp_search = QLineEdit()
        self.inp_search.setPlaceholderText("Ortak adı, telefon...")
        self.inp_search.textChanged.connect(lambda: self.search_timer.start(250))
        f_layout.addWidget(self.inp_search)
        self.layout.addWidget(filter_card)

        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["#", "ORTAK ADI", "TÜR", "HİZMET TÜRÜ", "KOMİSYON", "TELEFON", "E-POSTA", "ŞEHİR", "İŞLEMLER"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(1, 260)
        for i in range(2, 9): header.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 120); self.table.setColumnWidth(3, 160); self.table.setColumnWidth(4, 120)
        self.table.setColumnWidth(5, 130); self.table.setColumnWidth(6, 170); self.table.setColumnWidth(7, 130); self.table.setColumnWidth(8, 170)

        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellEntered.connect(self._on_table_cell_entered)
        self.table.setStyleSheet(theme_qss(
            "QTableWidget { border-radius: 10px; border: 1px solid @border; background: @surface; }"
            "QHeaderView::section { background-color: @surface_alt; color: @text; padding: 14px; font-weight: bold; border: none; }"
            "QTableWidget::item { padding: 10px; color: @text; border-bottom: 1px solid @surface_alt; }"
            "QTableWidget::item:selected { background-color: @accent; color: @selection_text; border: none; }"
        ))
        self.layout.addWidget(self.table)

        footer = QFrame()
        footer.setStyleSheet(theme_qss("background: @surface_alt; border-top: 1px solid @border; border-radius: 8px;"))
        fl = QHBoxLayout(footer); fl.setContentsMargins(12, 6, 12, 6)
        self.lbl_total = QLabel("Toplam Çalışma Ortağı: 0")
        self.lbl_total.setStyleSheet(theme_qss("color: @selection_text; font-weight: 600;"))
        fl.addWidget(self.lbl_total); fl.addStretch()
        self.layout.addWidget(footer)
        self.apply_theme_styles()

    def _on_table_cell_entered(self, row, _column):
        if row >= 0: self.table.selectRow(row)

    def on_service_type_changed(self, index):
        text = self.cmb_service_type.currentText().strip()
        self.current_service_type = None if not text or text == "Tümü" else text
        self.apply_filters()

    def on_commission_filter_changed(self, index):
        text = self.cmb_commission.currentText().strip()
        if text == "Komisyonu Olanlar": self.current_commission_filter = "HAS"
        elif text == "Komisyonu Olmayanlar": self.current_commission_filter = "NONE"
        else: self.current_commission_filter = None
        self.apply_filters()

    def load_data(self):
        try:
            raw_partners = self.customer_manager.get_customers("PARTNERS") or []
            self.all_partners = [dict(r) if hasattr(r, "keys") else r for r in raw_partners]
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
                    if val: values.add(val)
        except Exception: values = set()
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
                service_type = str(c["service_type"] if "service_type" in c.keys() else "")
                if search:
                    blob = " ".join([name.lower(), company.lower(), phone.lower(), email.lower(), city.lower(), service_type.lower()])
                    if search not in blob: continue
                if self.current_service_type and service_type != self.current_service_type: continue
                if self.current_commission_filter:
                    commission = 0.0
                    if "commission_rate" in c.keys() and c["commission_rate"] is not None:
                        try: commission = float(c["commission_rate"])
                        except Exception: commission = 0.0
                    if self.current_commission_filter == "HAS" and commission <= 0: continue
                    if self.current_commission_filter == "NONE" and commission > 0: continue
                rows.append(c)
            except Exception: continue
        self.table.setRowCount(0)
        for idx, c in enumerate(rows): self.add_row(idx, c)
        self.lbl_total.setText(f"Toplam Çalışma Ortağı: {len(rows)}")

    def apply_theme_styles(self):
        if hasattr(self, "lbl_title"): self.lbl_title.setStyleSheet(theme_qss("color: @selection_text; font-size: 22px; font-weight: 800; background: transparent; border: none;"))
        if hasattr(self, "lbl_sub"): self.lbl_sub.setStyleSheet(theme_qss("color: rgba(255,255,255,0.80); font-size: 12px; background: transparent; border: none;"))
        if hasattr(self, "lbl_total"): self.lbl_total.setStyleSheet(theme_qss("color: @text; font-weight: 600;"))

    def refresh_theme(self): self.apply_theme_styles()

    def add_row(self, row_idx, c):
        self.table.insertRow(row_idx)
        idx_item = QTableWidgetItem(str(row_idx + 1))
        idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row_idx, 0, idx_item)
        name = str(c["name"] or "")
        cust_type = str(c["type"] or "") if "type" in c.keys() else ""
        badge = f"[{cust_type}]" if cust_type else ""
        display_name = f"{name}  {badge}"
        name_item = QTableWidgetItem(display_name)
        name_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.table.setItem(row_idx, 1, name_item)
        self.table.setItem(row_idx, 2, QTableWidgetItem(cust_type or "—"))
        self.table.setItem(row_idx, 3, QTableWidgetItem(str(c.get("service_type") or "Genel")))
        comm = c.get("commission_rate")
        comm_text = f"{float(comm):.2f} %" if comm is not None else "—"
        self.table.setItem(row_idx, 4, QTableWidgetItem(comm_text))
        self.table.setItem(row_idx, 5, QTableWidgetItem(str(c["phone"] or "—")))
        self.table.setItem(row_idx, 6, QTableWidgetItem(str(c["email"] or "—")))
        self.table.setItem(row_idx, 7, QTableWidgetItem(str(c.get("city") or "—")))
        self.table.setCellWidget(row_idx, 8, self.create_action_widget(c))
        self.table.setRowHeight(row_idx, 80)

    def create_action_widget(self, c):
        btn = QPushButton("İşlem Yap ▼")
        btn.setMinimumWidth(150); btn.setFixedHeight(34)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(theme_qss(
            "QPushButton { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 @accent, stop:1 @success); color: @selection_text; border-radius: 16px; font-weight: 600; border: none; }"
            "QPushButton:hover { background: @accent; }"
        ))
        btn.clicked.connect(lambda checked=False, data=c: self.open_partner_menu(data, btn))
        container = QWidget()
        lay = QHBoxLayout(container); lay.setContentsMargins(0,0,0,0); lay.setAlignment(Qt.AlignmentFlag.AlignCenter); lay.addWidget(btn)
        return container

    def open_partner_menu(self, c, source_btn):
        menu = QMenu(self)
        menu.addAction("🔄 Ortak 360°", lambda: Customer360Dialog(self.db, c["id"], c["name"], self).exec())
        menu.addAction("⚙️ Hizmet & Komisyon", lambda: self.edit_partner(c))
        menu.addAction("📝 Notlar", lambda: CustomerNotesDialog(self.db, c["id"], c["name"], self).exec())
        menu.addSeparator()
        menu.addAction("🆕 Yeni Servis Kaydı", lambda: self.create_service_for_partner(c))
        menu.addAction("💰 Ödeme / Tahsilat", lambda: self.record_payment_for_partner(c))
        menu.addSeparator()
        menu.addAction("📱 WhatsApp Mesaj", lambda: self.send_whatsapp_for_partner(c))
        menu.exec(source_btn.mapToGlobal(source_btn.rect().bottomLeft()))

    def create_service_for_partner(self, c):
        sector_manager = getattr(self.main_window, "sector_manager", None)
        try: is_automotive = (sector_manager.get_current_plugin().sector_id == "otomotiv") if sector_manager else False
        except Exception: is_automotive = False
        if is_automotive:
            from src.ui.dialogs.automotive_new_service_dialog import AutomotiveNewServiceDialog as dialog_cls
        else:
            from src.ui.dialogs.technical_service_new_service_dialog import TechnicalServiceNewServiceDialog as dialog_cls
        dialog_cls(self.db, self, customer_name=c["name"], sector_manager=sector_manager).exec()

    def record_payment_for_partner(self, c):
        dlg = ModernPaymentDialog(self, self.db, c)
        if dlg.exec():
            data = dlg.get_data()
            if data:
                date_val = data.get("date")
                if date_val:
                    d = QDate.fromString(date_val, "dd.MM.yyyy")
                    if d.isValid(): date_val = d.toString("yyyy-MM-dd")
                res = self.db.add_transaction_with_customer(
                    customer_id=c["id"], date=date_val, description=data["notes"] or f"{data['method']} ile ödeme",
                    amount=data["amount"], t_type="Gelir", category="Tahsilat", payment_method=data.get("method"),
                    bank_account_id=data.get("bank_account_id")
                )
                if res:
                    show_success(self, f"{CurrencyHelper.format_try_for_display(data['amount'], db=self.db)} tahsilat kaydedildi.")
                    self.load_data()
                else: show_error(self, "Ödeme kaydedilirken bir hata oluştu.")

    def send_whatsapp_for_partner(self, c):
        phone = "".join(filter(str.isdigit, str(c["phone"])))
        if phone:
            if phone.startswith("0"): phone = "9" + phone
            webbrowser.open(f"https://wa.me/{phone}")

    def add_partner(self):
        from src.ui.pages.customers_page_parts import PartnerDialog # Sürpriz circular import önlemi
        if PartnerDialog(self.db, self).exec(): self.load_data()

    def edit_partner(self, c):
        from src.ui.pages.customers_page_parts import PartnerDialog
        if PartnerDialog(self.db, self, c).exec(): self.load_data()
