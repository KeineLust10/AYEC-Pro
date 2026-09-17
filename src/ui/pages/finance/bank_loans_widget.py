# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QFormLayout, QDoubleSpinBox, QSpinBox,
    QDateEdit, QLineEdit, QMessageBox, QTreeWidget, QTreeWidgetItem, QMenu,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QFont, QIcon, QAction

from src.utils.theme_colors import theme_qss, qc
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
        
        # Toolbar
        toolbar = QHBoxLayout()
        toolbar.addStretch()  # Push button to right
        
        self.btn_add_loan = QPushButton("Yeni Kredi Ekle")
        self.btn_add_loan.clicked.connect(self.open_loan_wizard)
        self.btn_add_loan.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @success; 
                color: @selection_text; 
                padding: 12px 24px; 
                font-weight: bold; 
                font-size: 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: @success;
            }
        """))
        toolbar.addWidget(self.btn_add_loan)
        
        layout.addLayout(toolbar)

        # Loans Tree (Drill-down)
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
            }
            QTreeWidget::item {
                padding-right: 20px;
                padding-left: 5px;
                height: 50px;
            }
        """))
        layout.addWidget(self.tree)

        self.load_loans()

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
        
        font_bold = QFont("Segoe UI", 10, QFont.Weight.Bold)
        font_normal = QFont("Segoe UI", 10)
        
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

