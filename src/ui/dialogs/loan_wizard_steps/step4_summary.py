# -*- coding: utf-8 -*-

"""
Advanced Loan Wizard - Step 4: Summary and Confirmation
Özet ve onay ekranı
"""
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QFrame,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Dict, Tuple

from src.ui.widgets.wizard_step_base import WizardStepBase
from src.utils.theme_colors import theme_qss
from src.utils.loan_calculator import LoanCalculator
from src.utils.currency_helper import CurrencyHelper

class Step4Summary(WizardStepBase):
    """Adım 4: Özet ve Onay"""
    
    def __init__(self, parent=None):
        self.calculator = LoanCalculator()
        super().__init__(parent)

    def _get_db(self):
        wizard = getattr(self, "wizard", lambda: None)()
        return getattr(wizard, "db", None)

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_try_for_display(
            amount,
            db=self._get_db(),
            include_try_reference=include_try_reference,
        )
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 10)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("🏁 Özet ve Onay")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)
        
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        
        # 1. General & Financial Info Cards
        info_row = QHBoxLayout()
        
        # Bank info card
        self.card_bank = self._create_summary_card("🏦 Banka Bilgileri")
        self.lbl_bank_info = QLabel()
        self.lbl_bank_info.setWordWrap(True)
        self.lbl_bank_info.setStyleSheet(theme_qss("color: @text; font-size: 13px; line-height: 1.5;"))
        self.card_bank.layout().addWidget(self.lbl_bank_info)
        info_row.addWidget(self.card_bank)
        
        # Financial info card
        self.card_finance = self._create_summary_card("📊 Finansal Özet")
        self.lbl_finance_info = QLabel()
        self.lbl_finance_info.setWordWrap(True)
        self.lbl_finance_info.setStyleSheet(theme_qss("color: @text; font-size: 13px;"))
        self.card_finance.layout().addWidget(self.lbl_finance_info)
        info_row.addWidget(self.card_finance)
        
        self.content_layout.addLayout(info_row)
        
        # 2. Attachments and Notes
        self.card_extras = self._create_summary_card("📎 Ekler ve Notlar")
        self.lbl_extras_info = QLabel()
        self.lbl_extras_info.setStyleSheet(theme_qss("color: @text; font-size: 13px;"))
        self.lbl_extras_info.setWordWrap(True)
        self.card_extras.layout().addWidget(self.lbl_extras_info)
        self.content_layout.addWidget(self.card_extras)
        
        # 3. Calculated Installments Table
        tbl_label = QLabel("📅 Hesaplanan Ödeme Planı")
        tbl_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        tbl_label.setStyleSheet(theme_qss("color: @text; margin-top: 4px;"))
        self.content_layout.addWidget(tbl_label)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["No", "Tarih", "Taksit", "Anapara", "Faiz+Vergi"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setFixedHeight(220)
        self.table.setStyleSheet(theme_qss("""
            QTableWidget {
                border: 1px solid @border;
                border-radius: 8px;
                background-color: @surface;
            }
            QHeaderView::section {
                background-color: @surface_alt;
                padding: 10px;
                border: none;
                border-bottom: 2px solid @border;
                font-weight: bold;
                color: @text_muted;
            }
        """))
        self.content_layout.addWidget(self.table)
        layout.addLayout(self.content_layout, 1)

    def _create_summary_card(self, title_text):
        card = QFrame()
        card.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface_alt;
                border: 1px solid @border;
                border-radius: 12px;
                padding: 5px;
            }
        """))
        l = QVBoxLayout(card)
        l.setContentsMargins(10, 8, 10, 8)
        l.setSpacing(6)
        
        t = QLabel(title_text)
        t.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        t.setStyleSheet(theme_qss("color: @text; border-bottom: 1px solid @border; padding-bottom: 5px;"))
        l.addWidget(t)
        return card

    def validate(self) -> Tuple[bool, str]:
        return True, ""
    
    def get_data(self) -> Dict:
        return {}
    
    def set_data(self, data: Dict):
        """Tüm wizard verisini alıp özeti doldurur"""
        # Bank info
        bank = data.get('bank', {})
        self.lbl_bank_info.setText(f"""
            <b>Banka:</b> {data.get('bank_name', '-')}<br>
            <b>Başlık:</b> {data.get('title', '-')}<br>
            <b>Tür:</b> {data.get('loan_type', '-')}<br>
            <b>EFT:</b> {data.get('eft_code', '-')}<br>
            <b>Swift:</b> {data.get('swift_code', '-')}
        """)
        
        # Financial info
        principal = data.get('principal', 0)
        interest = data.get('interest_rate', 0)
        months = data.get('months', 0)
        
        from src.utils.date_utils import format_turkish_date
        self.lbl_finance_info.setText(f"""
            <b>Ana Para:</b> {self._fmt_try(principal)}<br>
            <b>Faiz (Yıllık):</b> %{interest}<br>
            <b>Vade:</b> {months} Ay<br>
            <b>İlk Ödeme:</b> {format_turkish_date(data.get('start_date'), 'short') if data.get('start_date') else '-'}
        """)
        
        # Extras
        attachments = data.get('attachments', [])
        notes = data.get('notes', '-')
        att_text = f"<b>Ek Dosyalar:</b> {len(attachments)} adet dosya<br>"
        att_text += f"<b>Notlar:</b> {notes if notes else '-'}"
        self.lbl_extras_info.setText(att_text)
        
        # Table
        self._update_table(data)
        
    def _update_table(self, data):
        principal = data.get('principal', 0)
        interest = data.get('interest_rate', 0)
        months = data.get('months', 0)
        start_date = data.get('start_date')
        kkdf = data.get('kkdf_rate', 0)
        bsmv = data.get('bsmv_rate', 0)
        from src.utils.date_utils import format_turkish_date
        
        if not principal or not interest or not months: return
        
        plan = self.calculator.generate_payment_plan(principal, interest, months, start_date, kkdf, bsmv)
        
        self.table.setRowCount(0)
        for i, row in enumerate(plan):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(str(row['installment_number'])))
            
            # Format date for display: YYYY-MM-DD -> DD.MM.YYYY
            date_str = row['due_date']
            display_date = format_turkish_date(date_str, "short")
                
            self.table.setItem(i, 1, QTableWidgetItem(display_date))
            self.table.setItem(i, 2, QTableWidgetItem(self._fmt_try(row['total_amount'])))
            self.table.setItem(i, 3, QTableWidgetItem(self._fmt_try(row['principal_part'])))
            self.table.setItem(
                i,
                4,
                QTableWidgetItem(self._fmt_try(row['interest_part'] + row['kkdf_amount'] + row['bsmv_amount'])),
            )
            
            # Align right for numbers
            for j in [2, 3, 4]:
                self.table.item(i, j).setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

