# -*- coding: utf-8 -*-

"""
Advanced Loan Wizard - Step 2: Financial Details
Finansal detaylar adımı
"""
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
                             QDoubleSpinBox, QSpinBox, QDateEdit, QRadioButton,
                             QButtonGroup, QFrame)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont
from typing import Dict, Tuple
from datetime import datetime

from src.ui.widgets.wizard_step_base import WizardStepBase
from src.utils.theme_colors import theme_qss
from src.utils.loan_calculator import LoanCalculator
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens


class Step2FinancialDetails(WizardStepBase):
    """Adım 2: Finansal Detaylar"""
    
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

    def _currency_label(self):
        return CurrencyHelper.get_label(db=self._get_db())
    
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(30)
        
        # Left: Form
        left_layout = QVBoxLayout()
        
        # Title
        title = QLabel("💰 Finansal Detaylar")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        left_layout.addWidget(title)
        
        # Description
        desc = QLabel("Kredi tutarı, faiz oranı ve vade bilgilerini girin.")
        desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        desc.setWordWrap(True)
        left_layout.addWidget(desc)
        
        # Form
        form = QFormLayout()
        form.setSpacing(15)
        form.setContentsMargins(0, 20, 0, 0)
        
        # Ana Para
        self.spin_principal = QDoubleSpinBox()
        self.spin_principal.setRange(1000, 100000000)
        self.spin_principal.setValue(100000)
        self.spin_principal.setSuffix(f" {self._currency_label()}")
        self.spin_principal.setGroupSeparatorShown(True)
        self.spin_principal.setMinimumHeight(40)
        DesignTokens.apply_spinbox_styles(self.spin_principal)
        self.spin_principal.valueChanged.connect(self._update_preview)
        form.addRow("💰 Ana Para *:", self.spin_principal)

        # Faiz Oranı
        interest_layout = QHBoxLayout()

        self.spin_interest = QDoubleSpinBox()
        self.spin_interest.setRange(0, 100)
        self.spin_interest.setValue(24.0)
        self.spin_interest.setSingleStep(0.25)
        self.spin_interest.setSuffix(" %")
        self.spin_interest.setMinimumHeight(40)
        DesignTokens.apply_spinbox_styles(self.spin_interest)
        self.spin_interest.valueChanged.connect(self._update_preview)
        interest_layout.addWidget(self.spin_interest, stretch=3)
        
        # Yıllık/Aylık toggle
        radio_container = QHBoxLayout()
        self.radio_yearly = QRadioButton("Yıllık")
        self.radio_monthly = QRadioButton("Aylık")
        self.radio_yearly.setChecked(True)
        self.radio_yearly.toggled.connect(self._update_preview)
        self.radio_monthly.toggled.connect(self._update_preview)
        
        self.interest_group = QButtonGroup()
        self.interest_group.addButton(self.radio_yearly)
        self.interest_group.addButton(self.radio_monthly)
        self.interest_group.buttonClicked.connect(self._update_preview)
        
        radio_container.addWidget(self.radio_yearly)
        radio_container.addWidget(self.radio_monthly)
        interest_layout.addLayout(radio_container, stretch=2)
        
        form.addRow("📊 Faiz Oranı *:", interest_layout)
        
        # Vade
        self.spin_months = QSpinBox()
        self.spin_months.setRange(1, 240)
        self.spin_months.setValue(36)
        self.spin_months.setSuffix(" Ay")
        self.spin_months.setMinimumHeight(40)
        DesignTokens.apply_spinbox_styles(self.spin_months)
        self.spin_months.valueChanged.connect(self._update_preview)
        form.addRow("📅 Vade (Ay) *:", self.spin_months)
        
        # İlk Ödeme Tarihi
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(1))
        self.date_start.setMinimumHeight(40)
        self.date_start.setDisplayFormat("dd.MM.yyyy")
        self.date_start.setStyleSheet(theme_qss("""
            QDateEdit {
                border: 2px solid @border;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QDateEdit:focus {
                border: 2px solid @accent;
            }
        """))
        form.addRow("📆 İlk Ödeme Tarihi:", self.date_start)
        
        # KKDF/BSMV (Optional, collapsed by default)
        self.spin_kkdf = QDoubleSpinBox()
        self.spin_kkdf.setRange(0, 10)
        self.spin_kkdf.setValue(0.0)
        self.spin_kkdf.setSingleStep(0.01)
        self.spin_kkdf.setSuffix(" %")
        self.spin_kkdf.setMinimumHeight(40)
        DesignTokens.apply_spinbox_styles(self.spin_kkdf)
        self.spin_kkdf.valueChanged.connect(self._update_preview)
        form.addRow("🔖 KKDF Oranı:", self.spin_kkdf)

        self.spin_bsmv = QDoubleSpinBox()
        self.spin_bsmv.setRange(0, 10)
        self.spin_bsmv.setValue(0.0)
        self.spin_bsmv.setSingleStep(0.01)
        self.spin_bsmv.setSuffix(" %")
        self.spin_bsmv.setMinimumHeight(40)
        DesignTokens.apply_spinbox_styles(self.spin_bsmv)
        self.spin_bsmv.valueChanged.connect(self._update_preview)
        form.addRow("🔖 BSMV Oranı:", self.spin_bsmv)
        
        left_layout.addLayout(form)
        left_layout.addStretch()
        
        main_layout.addLayout(left_layout, stretch=1)
        
        # Right: Live Preview
        self.preview_card = self._create_preview_card()
        main_layout.addWidget(self.preview_card, stretch=1)
        
        # Initial preview
        self._update_preview()
    
    def _get_spinbox_style(self):
        return """
            QDoubleSpinBox, QSpinBox {
                border: 2px solid @border;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QDoubleSpinBox:focus, QSpinBox:focus {
                border: 2px solid @accent;
            }
        """
    
    def _create_preview_card(self):
        """Create live preview card"""
        card = QFrame()
        card.setStyleSheet(theme_qss("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 @accent, stop:1 @accent_hover);
                border-radius: 12px;
                padding: 20px;
            }
        """))
        
        layout = QVBoxLayout(card)
        layout.setSpacing(15)
        
        # Title
        preview_title = QLabel("📊 Ödeme Önizleme")
        preview_title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        preview_title.setStyleSheet(theme_qss("color: @selection_text;"))
        layout.addWidget(preview_title)
        
        # Monthly payment
        self.lbl_monthly = QLabel("Aylık Ödeme: Hesaplanıyor...")
        self.lbl_monthly.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.lbl_monthly.setStyleSheet(theme_qss("color: @selection_text; padding: 10px; background: rgba(255,255,255,0.1); border-radius: 8px;"))
        self.lbl_monthly.setWordWrap(True)
        layout.addWidget(self.lbl_monthly)
        
        # Total payment
        self.lbl_total = QLabel("Toplam Ödeme: -")
        self.lbl_total.setStyleSheet(theme_qss("color: rgba(255,255,255,0.9); font-size: 13px;"))
        layout.addWidget(self.lbl_total)
        
        # Total interest
        self.lbl_interest = QLabel("Toplam Faiz: -")
        self.lbl_interest.setStyleSheet(theme_qss("color: rgba(255,255,255,0.9); font-size: 13px;"))
        layout.addWidget(self.lbl_interest)
        
        # Total tax
        self.lbl_tax = QLabel("Toplam Vergi: -")
        self.lbl_tax.setStyleSheet(theme_qss("color: rgba(255,255,255,0.9); font-size: 13px;"))
        layout.addWidget(self.lbl_tax)
        
        layout.addStretch()
        
        return card
    
    def _update_preview(self):
        """Update live preview calculations"""
        try:
            principal = self.spin_principal.value()
            interest_rate = self.spin_interest.value()
            
            # Convert to annual if monthly
            if self.radio_monthly.isChecked():
                interest_rate = interest_rate * 12
            
            months = self.spin_months.value()
            kkdf = self.spin_kkdf.value()
            bsmv = self.spin_bsmv.value()
            
            # Calculate
            cost = self.calculator.calculate_total_cost(principal, interest_rate, months, kkdf, bsmv)
            
            # Update labels
            self.lbl_monthly.setText(f"💳 Aylık Ödeme\n{self._fmt_try(cost['monthly_installment'])}")
            self.lbl_total.setText(f"📊 Toplam Ödeme: {self._fmt_try(cost['total_payment'])}")
            self.lbl_interest.setText(f"📈 Toplam Faiz: {self._fmt_try(cost['total_interest'])}")
            self.lbl_tax.setText(f"🔖 Toplam Vergi: {self._fmt_try(cost['total_tax'])}")
            
        except Exception as e:
            self.lbl_monthly.setText(f"Hesaplama hatası: {e}")
    
    def validate(self) -> Tuple[bool, str]:
        """Validate step data"""
        if self.spin_principal.value() < 1000:
            return False, f"Ana para en az 1,000 {self._currency_label()} olmalıdır"
        
        if self.spin_interest.value() <= 0:
            return False, "Faiz oranı 0'dan büyük olmalıdır"
        
        if self.spin_months.value() < 1:
            return False, "Vade en az 1 ay olmalıdır"
        
        return True, ""
    
    def get_data(self) -> Dict:
        """Return step data"""
        interest_rate = self.spin_interest.value()
        if self.radio_monthly.isChecked():
            interest_rate = interest_rate * 12
        
        return {
            'principal': self.spin_principal.value(),
            'interest_rate': interest_rate,
            'interest_is_monthly': self.radio_monthly.isChecked(),
            'months': self.spin_months.value(),
            'start_date': self.date_start.date().toPyDate(),
            'kkdf_rate': self.spin_kkdf.value(),
            'bsmv_rate': self.spin_bsmv.value()
        }
    
    def set_data(self, data: Dict):
        """Load data into step"""
        if 'principal' in data:
            self.spin_principal.setValue(data['principal'])
        
        if 'interest_rate' in data:
            rate = data['interest_rate']
            if data.get('interest_is_monthly', False):
                self.radio_monthly.setChecked(True)
                rate = rate / 12
            else:
                self.radio_yearly.setChecked(True)
            self.spin_interest.setValue(rate)
        
        if 'months' in data:
            self.spin_months.setValue(data['months'])
        
        if 'kkdf_rate' in data:
            self.spin_kkdf.setValue(data['kkdf_rate'])
        
        if 'bsmv_rate' in data:
            self.spin_bsmv.setValue(data['bsmv_rate'])
        
        self._update_preview()


