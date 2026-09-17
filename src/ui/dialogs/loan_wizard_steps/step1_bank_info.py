# -*- coding: utf-8 -*-

"""
Advanced Loan Wizard - Step 1: Bank and General Information
Banka ve genel kredi bilgileri adımı
"""
from PyQt6.QtWidgets import (QVBoxLayout, QFormLayout, QComboBox, QLineEdit, 
                             QLabel, QCompleter)
from PyQt6.QtCore import Qt, QEvent, QTimer
from PyQt6.QtGui import QFont
from typing import Dict, Tuple

from src.ui.widgets.wizard_step_base import WizardStepBase
from src.utils.theme_colors import theme_qss
from src.utils.bank_helper import get_bank_helper


class Step1BankInfo(WizardStepBase):
    """Adım 1: Banka ve Genel Bilgiler"""
    
    def __init__(self, parent=None):
        self.bank_helper = get_bank_helper()
        self.selected_bank = None
        super().__init__(parent)
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("🏦 Banka ve Genel Bilgiler")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Kredi bilgilerinizi girin. Banka seçimi yapıldığında EFT ve Swift kodları otomatik doldurulacaktır.")
        desc.setStyleSheet(theme_qss("color: @text_muted; font-size: 12px;"))
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Form
        form = QFormLayout()
        form.setSpacing(15)
        form.setContentsMargins(0, 20, 0, 0)
        
        # Banka Seçimi
        self.cmb_bank = QComboBox()
        self.cmb_bank.setEditable(True)
        self.cmb_bank.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.cmb_bank.setMinimumHeight(40)
        self.cmb_bank.setStyleSheet(theme_qss("""
            QComboBox {
                border: 2px solid @border;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: @surface;
                font-size: 13px;
            }
            QComboBox:focus {
                border: 2px solid @accent;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid @border;
                selection-background-color: @selection_bg;
                selection-color: @accent;
            }
        """))
        
        # Populate banks
        banks = self.bank_helper.get_all_banks()
        for bank in banks:
            display_text = f"{bank['name']} ({bank['shortName']})"
            self.cmb_bank.addItem(display_text, bank)
        
        # Auto-completer
        completer = QCompleter([f"{b['name']} ({b['shortName']})" for b in banks])
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.cmb_bank.setCompleter(completer)
        self.cmb_bank.currentIndexChanged.connect(self._on_bank_selected)
        
        self.cmb_bank.installEventFilter(self)
        self.cmb_bank.lineEdit().installEventFilter(self)

        
        form.addRow("🏦 Banka Seçimi *:", self.cmb_bank)
        
        # Kredi Türü
        self.cmb_loan_type = QComboBox()
        self.cmb_loan_type.setMinimumHeight(40)
        self.cmb_loan_type.setStyleSheet(theme_qss(self.cmb_bank.styleSheet()))
        self.cmb_loan_type.addItems([
            "Taksitli Ticari Kredi",
            "Rotatif Kredi",
            "İhtiyaç Kredisi",
            "Taşıt Kredisi",
            "Konut Kredisi",
            "İşletme Kredisi",
            "Nakit Kredisi",
            "İhracat Kredisi"
        ])
        self.cmb_loan_type.currentTextChanged.connect(self._on_loan_type_changed)
        form.addRow("📋 Kredi Türü:", self.cmb_loan_type)
        
        # Kredi Başlığı
        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Örn: 2026 Filo Yenileme Kredisi")
        self.txt_title.setMinimumHeight(40)
        self.txt_title.setStyleSheet(theme_qss("""
            QLineEdit {
                border: 2px solid @border;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 2px solid @accent;
            }
        """))
        form.addRow("✏️ Kredi Başlığı *:", self.txt_title)
        
        # EFT Kodu (Read-only)
        self.txt_eft = QLineEdit()
        self.txt_eft.setReadOnly(True)
        self.txt_eft.setPlaceholderText("Banka seçilince otomatik doldurulur")
        self.txt_eft.setMinimumHeight(40)
        self.txt_eft.setStyleSheet(theme_qss("""
            QLineEdit {
                border: 2px solid @border;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                background-color: @surface_alt;
                color: @text_muted;
            }
        """))
        form.addRow("💳 EFT Kodu:", self.txt_eft)
        
        # Swift Kodu (Read-only)
        self.txt_swift = QLineEdit()
        self.txt_swift.setReadOnly(True)
        self.txt_swift.setPlaceholderText("Banka seçilince otomatik doldurulur")
        self.txt_swift.setMinimumHeight(40)
        self.txt_swift.setStyleSheet(theme_qss(self.txt_eft.styleSheet()))
        form.addRow("✈️ Swift Kodu:", self.txt_swift)
        
        layout.addLayout(form)
        layout.addStretch()
        
        # Required fields note
        note = QLabel("* İşaretli alanlar zorunludur")
        note.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; font-style: italic;"))
        layout.addWidget(note)
        self._on_loan_type_changed(self.cmb_loan_type.currentText())
    
    def _on_bank_selected(self, index):
        """Banka seçildiğinde EFT/Swift otomatik doldur"""
        if index < 0:
            self.selected_bank = None
            self.txt_eft.clear()
            self.txt_swift.clear()
            return
        
        self.selected_bank = self.cmb_bank.itemData(index)
        if self.selected_bank:
            self.txt_eft.setText(self.selected_bank.get('eftCode', ''))
            self.txt_swift.setText(self.selected_bank.get('swift', ''))

    def _on_loan_type_changed(self, loan_type):
        examples = {
            "Taksitli Ticari Kredi": "Örn: 2026 Ticari Yatırım Kredisi",
            "Rotatif Kredi": "Örn: 2026 Rotatif Finansman",
            "İhtiyaç Kredisi": "Örn: 2026 Operasyon Destek Kredisi",
            "Taşıt Kredisi": "Örn: 2026 Araç Finansmanı",
            "Konut Kredisi": "Örn: 2026 Gayrimenkul Kredisi",
            "İşletme Kredisi": "Örn: 2026 İşletme Sermayesi",
            "Nakit Kredisi": "Örn: 2026 Nakit Akış Kredisi",
            "İhracat Kredisi": "Örn: 2026 İhracat Finansmanı"
        }
        self.txt_title.setPlaceholderText(examples.get(loan_type, "Örn: 2026 Filo Yenileme Kredisi"))
    
    def validate(self) -> Tuple[bool, str]:
        """Validate step data"""
        if not self.selected_bank:
            return False, "Lütfen bir banka seçin"
        
        title = self.txt_title.text().strip()
        if not title:
            return False, "Kredi başlığı boş olamaz"
        
        return True, ""
    
    def get_data(self) -> Dict:
        """Return step data"""
        return {
            'bank': self.selected_bank,
            'bank_name': self.cmb_bank.currentText(),
            'loan_type': self.cmb_loan_type.currentText(),
            'title': self.txt_title.text().strip(),
            'eft_code': self.txt_eft.text(),
            'swift_code': self.txt_swift.text()
        }
    
    def set_data(self, data: Dict):
        """Load data into step"""
        if 'bank' in data and data['bank']:
            # Find bank in combobox
            bank_name = data.get('bank_name', '')
            index = self.cmb_bank.findText(bank_name, Qt.MatchFlag.MatchContains)
            if index >= 0:
                self.cmb_bank.setCurrentIndex(index)
        
        if 'loan_type' in data:
            index = self.cmb_loan_type.findText(data['loan_type'])
            if index >= 0:
                self.cmb_loan_type.setCurrentIndex(index)
        
        if 'title' in data:
            self.txt_title.setText(data['title'])

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonRelease and obj in (self.cmb_bank, self.cmb_bank.lineEdit()):
            if not self.cmb_bank.view().isVisible():
                QTimer.singleShot(0, self.cmb_bank.showPopup)
        return super().eventFilter(obj, event)


