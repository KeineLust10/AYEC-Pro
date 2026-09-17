# -*- coding: utf-8 -*-

"""
Bulk Payment Dialog - Toplu Ödeme Ekranı
Birden fazla taksiti aynı anda ödeme işlemi için.
"""
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                              QTableWidget, QTableWidgetItem, QCheckBox, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.theme_colors import theme_qss, qc
from src.utils.currency_helper import CurrencyHelper
from src.utils.toast_notification import show_success, show_error
from src.utils.logger import logger

class BulkPaymentDialog(BaseModernDialog):
    """Toplu ödeme dialogu."""
    
    def __init__(self, db, loan_id, loan_name, parent=None):
        super().__init__(parent, title="Toplu Ödeme", width=700, height=500)
        self.db = db
        self.loan_id = loan_id
        self.loan_name = loan_name
        self.checkboxes = {}
        self.setup_ui()
        self.load_installments()
        
    def setup_ui(self):
        # Header
        header = QLabel(f" {self.loan_name}")
        header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header.setStyleSheet(theme_qss("color: @text; margin-bottom: 10px;"))
        self.content_layout.addWidget(header)
        
        desc = QLabel("Ödemek istediğiniz taksitleri seçin ve 'Seçilenleri Öde' butonuna tıklayın.")
        desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px; margin-bottom: 15px;"))
        desc.setWordWrap(True)
        self.content_layout.addWidget(desc)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Seç", "Taksit No", "Tutar", "Vade Tarihi", "Durum"])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.resizeSection(0, 50)
        header.resizeSection(1, 150)
        header.resizeSection(2, 120)
        header.resizeSection(3, 150)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)  # Status takes rest
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setStyleSheet(theme_qss("""
            QTableWidget {
                font-size: 13px;
                border: 1px solid @border;
                border-radius: 8px;
                outline: none;
            }
            QTableWidget::item {
                padding: 8px;
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
            }
        """))
        self.content_layout.addWidget(self.table)
        
        # Summary
        self.lbl_summary = QLabel("")
        self.lbl_summary.setStyleSheet(theme_qss("color: @text; font-weight: bold; font-size: 14px; margin-top: 10px;"))
        self.content_layout.addWidget(self.lbl_summary)
        
        # Early Closure Savings
        self.lbl_savings = QLabel("")
        self.lbl_savings.setStyleSheet(theme_qss("color: @success; font-weight: bold; font-size: 13px; margin-top: 5px;"))
        self.lbl_savings.setVisible(False)
        self.content_layout.addWidget(self.lbl_savings)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_select_all = QPushButton("Tümünü Seç")
        self.btn_select_all.setFixedSize(140, 42)
        self.btn_select_all.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @disabled_text;
                color: @selection_text;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: @text_muted; }
        """))
        self.btn_select_all.clicked.connect(self.select_all)
        
        self.btn_early_close = QPushButton("Erken Kapat")
        self.btn_early_close.setFixedSize(150, 42)
        self.btn_early_close.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: @accent; }
        """))
        self.btn_early_close.clicked.connect(self.early_close_loan)
        
        self.btn_pay_all = QPushButton("Tümünü Öde")
        self.btn_pay_all.setFixedSize(140, 42)
        self.btn_pay_all.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @warning;
                color: @selection_text;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: @warning; }
        """))
        self.btn_pay_all.clicked.connect(self.pay_all)
        
        self.btn_pay_selected = QPushButton("Seçilenleri Öde")
        self.btn_pay_selected.setFixedSize(160, 42)
        self.btn_pay_selected.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @success;
                color: @selection_text;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: @success; }
        """))
        self.btn_pay_selected.clicked.connect(self.pay_selected)
        
        btn_cancel = QPushButton("Kapat")
        btn_cancel.setFixedSize(100, 42)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface_alt;
                color: @text_muted;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: @surface_alt; }
        """))
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_select_all)
        btn_layout.addWidget(self.btn_early_close)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_pay_all)
        btn_layout.addWidget(self.btn_pay_selected)
        btn_layout.addWidget(btn_cancel)
        
        self.content_layout.addLayout(btn_layout)
        
    def load_installments(self):
        """Ödenmemiş taksitleri yükle."""
        self.table.setRowCount(0)
        self.checkboxes.clear()
        
        installments = self.db.get_loan_installments(self.loan_id)
        unpaid = [inst for inst in installments if inst['status'] not in ('Ödendi', 'dendi')]
        
        if not unpaid:
            self.table.setRowCount(1)
            no_data = QTableWidgetItem("Tüm taksitler ödenmiş")
            no_data.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(0, 1, no_data)
            self.table.setSpan(0, 1, 1, 4)
            self.btn_pay_all.setEnabled(False)
            self.btn_pay_selected.setEnabled(False)
            self.btn_select_all.setEnabled(False)
            return
        
        self.table.setRowCount(len(unpaid))
        total_unpaid = 0.0
        
        for row, inst in enumerate(unpaid):
            # Checkbox
            checkbox = QCheckBox()
            checkbox.setStyleSheet(theme_qss("margin-left: 20px;"))
            checkbox.stateChanged.connect(self.update_summary)
            self.checkboxes[inst['id']] = checkbox
            self.table.setCellWidget(row, 0, checkbox)
            
            # Taksit No
            self.table.setItem(row, 1, QTableWidgetItem(f"Taksit #{inst['installment_no']}"))
            
            # Tutar
            amount_item = QTableWidgetItem(
                CurrencyHelper.format_try_for_display(inst['amount'], db=self.db, include_try_reference=False)
            )
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            amount_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self.table.setItem(row, 2, amount_item)
            
            # Vade
            self.table.setItem(row, 3, QTableWidgetItem(inst['due_date']))
            
            # Durum
            status_item = QTableWidgetItem(inst['status'])
            if inst['status'] == 'Gecikmiş':
                status_item.setForeground(qc("danger"))
            else:
                status_item.setForeground(qc("warning"))
            self.table.setItem(row, 4, status_item)
            
            total_unpaid += inst['amount']
        
        self.lbl_summary.setText(
            f"Toplam ödenmemiş: {len(unpaid)} Taksit - "
            f"{CurrencyHelper.format_try_for_display(total_unpaid, db=self.db, include_try_reference=False)}"
        )
        
    def select_all(self):
        """Tümünü seç."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)
        self.update_summary()
        
    def update_summary(self):
        """Seçili taksitlerin özetini güncelle."""
        selected_count = 0
        selected_total = 0.0
        
        installments = self.db.get_loan_installments(self.loan_id)
        
        for inst in installments:
            if inst['id'] in self.checkboxes and self.checkboxes[inst['id']].isChecked():
                selected_count += 1
                selected_total += inst['amount']
        
        if selected_count > 0:
            self.lbl_summary.setText(
                f"Seçili: {selected_count} Taksit - "
                f"{CurrencyHelper.format_try_for_display(selected_total, db=self.db, include_try_reference=False)}"
            )
        else:
            unpaid = [i for i in installments if i['status'] not in ('Ödendi', 'dendi')]
            total_unpaid = sum(i['amount'] for i in unpaid)
            self.lbl_summary.setText(
                f"Toplam ödenmemiş: {len(unpaid)} Taksit - "
                f"{CurrencyHelper.format_try_for_display(total_unpaid, db=self.db, include_try_reference=False)}"
            )
    
    def pay_selected(self):
        """Seçili taksitleri öde."""
        selected_ids = [inst_id for inst_id, cb in self.checkboxes.items() if cb.isChecked()]
        
        if not selected_ids:
            show_error(self.parent(), "Lütfen en az bir taksit seçin")
            return
        
        success_count = 0
        for inst_id in selected_ids:
            if self.db.update_installment_status(inst_id, 'Ödendi'):
                success_count += 1
        
        if success_count > 0:
            show_success(self.parent(), f"{success_count} taksit ödendi olarak işaretlendi")
            self.accept()
        else:
            show_error(self.parent(), "Ödeme işlemi başarısız")
    
    def pay_all(self):
        """Tüm ödenmemiş taksitleri öde."""
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(True)
        self.pay_selected()
    
    def early_close_loan(self):
        """Krediyi erken kapat - Profesyonel hesaplama ile"""
        installments = self.db.get_loan_installments(self.loan_id)
        unpaid = [inst for inst in installments if inst['status'] not in ('Ödendi', 'dendi')]
        
        if not unpaid:
            show_error(self.parent(), "Tüm taksitler zaten ödenmiş")
            return
        
        # Get loan details for better calculation
        try:
            loan_query = self.db.cursor.execute(
                "SELECT * FROM loans WHERE id=?", (self.loan_id,)
            ).fetchone()
            
            if loan_query:
                # Convert to dict
                loan_dict = dict(loan_query) if hasattr(loan_query, 'keys') else {
                    'id': loan_query[0],
                    'bank_account_id': loan_query[1],
                    'bank_name': loan_query[2],
                    'amount': loan_query[3],
                    'interest_rate': loan_query[4],
                    'term_months': loan_query[5],
                    'start_date': loan_query[6],
                    'total_payment': loan_query[7],
                    'description': loan_query[8],
                    'status': loan_query[9]
                }
            else:
                loan_dict = {'bank_name': 'Bilinmeyen Kredi'}
        except Exception as e:
            logger.debug(f"BulkPayment loan details fallback used: {e}")
            loan_dict = {'bank_name': 'Bilinmeyen Kredi'}
        
        # Convert sqlite3.Row to dict if needed for unpaid installments
        if unpaid and hasattr(unpaid[0], 'keys'):
            unpaid = [dict(row) for row in unpaid]
        
        # Recalculate installments with detailed breakdown if not available
        if unpaid and unpaid[0].get('principal_part') is None:
            # Need to recalculate payment plan
            from src.utils.loan_calculator import LoanCalculator
            from datetime import datetime
            
            try:
                principal = loan_dict.get('amount', 0)
                annual_rate = loan_dict.get('interest_rate', 0)
                term_months = loan_dict.get('term_months', 0)
                start_date_str = loan_dict.get('start_date', datetime.now().strftime('%Y-%m-%d'))
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                
                # Generate full plan
                full_plan = LoanCalculator.generate_payment_plan(
                    principal=principal,
                    annual_rate=annual_rate,
                    months=term_months,
                    start_date=start_date,
                    kkdf_rate=15,  # %15 KKDF
                    bsmv_rate=10   # %10 BSMV
                )
                
                # Match unpaid installments with calculated data
                for inst in unpaid:
                    inst_no = inst.get('installment_no', 0)
                    if inst_no > 0 and inst_no <= len(full_plan):
                        calculated = full_plan[inst_no - 1]
                        inst['principal_part'] = calculated['principal_part']
                        inst['interest_part'] = calculated['interest_part']
                        inst['kkdf_amount'] = calculated['kkdf_amount']
                        inst['bsmv_amount'] = calculated['bsmv_amount']
            except Exception as e:
                # Fallback to estimation if calculation fails
                logger.debug(f"BulkPayment early-closure plan fallback used: {e}")
        
        # Show professional dialog
        from src.ui.dialogs.early_closure_dialog import EarlyClosureDialog
        
        dlg = EarlyClosureDialog(loan_dict, unpaid, self)
        if dlg.exec():
            # User confirmed - mark all as paid
            success_count = 0
            for inst in unpaid:
                if self.db.update_installment_status(inst['id'], 'Ödendi'):
                    success_count += 1
            
            # Update loan status to "Erken Kapatıldı"
            try:
                self.db.cursor.execute("UPDATE loans SET status='Erken Kapatıldı' WHERE id=?", (self.loan_id,))
                self.db.conn.commit()
            except Exception as e:
                logger.debug(f"BulkPayment loan status update failed: {e}")
            
            if success_count > 0:
                savings_msg = f"""
 Kredi başarıyla erken kapatıldı!

 Ödenen Taksit: {success_count} adet
 Toplam Kazancınız: {CurrencyHelper.format_try_for_display(dlg.total_savings, db=self.db, include_try_reference=False)}

 Faiz Tasarrufu: {CurrencyHelper.format_try_for_display(dlg.total_interest, db=self.db, include_try_reference=False)}
 Vergi Tasarrufu: {CurrencyHelper.format_try_for_display(dlg.total_tax, db=self.db, include_try_reference=False)}
"""
                if dlg.penalty_amount > 0:
                    savings_msg += (
                        " Tazminat: -"
                        f"{CurrencyHelper.format_try_for_display(dlg.penalty_amount, db=self.db, include_try_reference=False)}\n"
                    )
                
                show_success(self.parent(), savings_msg)
                self.accept()
            else:
                show_error(self.parent(), "İşlem başarısız")



