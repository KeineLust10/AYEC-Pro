# -*- coding: utf-8 -*-

"""
Kredi Ödeme Planı Sihirbazı (Loan Wizard Dialog)
Premium tasarım ile otomatik taksit oluşturma
"""
from PyQt6.QtWidgets import (QHBoxLayout, QVBoxLayout, QFormLayout, QLineEdit,
                             QDoubleSpinBox, QSpinBox, QDateEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QLabel, QHeaderView)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.utils.theme_colors import theme_qss, qc
from src.utils.loan_calculator import LoanCalculator
from src.utils.toast_notification import show_success, show_error
from src.utils.currency_helper import CurrencyHelper
from src.utils.design_system import DesignTokens
from datetime import datetime


class LoanWizardDialog(BaseModernDialog):
    """
    Kredi Ekle Sihirbazı
    Sol: Form giriş alanları
    Sağ: Canlı önizleme tablosu
    """
    
    def __init__(self, db, parent=None):
        super().__init__(parent, title="🏦 Kredi Ödeme Planı Sihirbazı", width=950, height=650)
        self.db = db
        self.calculator = LoanCalculator()
        self.payment_plan = []  # Hesaplanan plan
        self.currency_code = CurrencyHelper.get_code(self.db)
        self.setup_ui()

    def _fmt_try(self, amount, include_try_reference=False):
        return CurrencyHelper.format_from_try(
            amount,
            db=self.db,
            currency_code=CurrencyHelper.get_code(self.db),
            include_try_reference=include_try_reference,
        )
    
    def setup_ui(self):
        # Ana layout - Yatay bölünmüş
        main_layout = QHBoxLayout()
        
        # ===== SOL PANEL: FORM =====
        left_panel = QVBoxLayout()
        form = QFormLayout()
        
        # Banka Adı
        self.txt_bank = QLineEdit()
        self.txt_bank.setPlaceholderText("Örn: Garanti BBVA")
        form.addRow("🏦 Banka Adı:", self.txt_bank)
        
        # Açıklama
        self.txt_description = QLineEdit()
        self.txt_description.setPlaceholderText("Örn: İhtiyaç Kredisi")
        form.addRow("📝 Açıklama:", self.txt_description)
        
        # Ana Para
        self.spin_principal = QDoubleSpinBox()
        self.spin_principal.setRange(1000, 100000000)
        self.spin_principal.setValue(100000)
        self.spin_principal.setSuffix(f" {CurrencyHelper.get_label(self.currency_code)}")
        self.spin_principal.setGroupSeparatorShown(True)
        DesignTokens.apply_spinbox_styles(self.spin_principal)
        form.addRow("💰 Ana Para:", self.spin_principal)

        # Faiz Oranı (Yıllık)
        self.spin_interest = QDoubleSpinBox()
        self.spin_interest.setRange(0, 100)
        self.spin_interest.setValue(24.0)
        self.spin_interest.setSingleStep(0.25)
        self.spin_interest.setSuffix(" % (Yıllık)")
        DesignTokens.apply_spinbox_styles(self.spin_interest)
        form.addRow("📊 Faiz Oranı:", self.spin_interest)

        # Taksit Sayısı
        self.spin_months = QSpinBox()
        self.spin_months.setRange(1, 120)
        self.spin_months.setValue(36)
        self.spin_months.setSuffix(" Ay")
        DesignTokens.apply_spinbox_styles(self.spin_months)
        form.addRow("📅 Taksit Sayısı:", self.spin_months)

        # KKDF Oranı
        self.spin_kkdf = QDoubleSpinBox()
        self.spin_kkdf.setRange(0, 10)
        self.spin_kkdf.setValue(0.0)
        self.spin_kkdf.setSingleStep(0.01)
        self.spin_kkdf.setSuffix(" %")
        DesignTokens.apply_spinbox_styles(self.spin_kkdf)
        form.addRow("🔖 KKDF Oranı:", self.spin_kkdf)

        # BSMV Oranı
        self.spin_bsmv = QDoubleSpinBox()
        self.spin_bsmv.setRange(0, 10)
        self.spin_bsmv.setValue(0.0)
        self.spin_bsmv.setSingleStep(0.01)
        self.spin_bsmv.setSuffix(" %")
        DesignTokens.apply_spinbox_styles(self.spin_bsmv)
        form.addRow("🔖 BSMV Oranı:", self.spin_bsmv)
        
        # Başlangıç Tarihi
        self.date_start = QDateEdit()
        self.date_start.setDate(QDate.currentDate())
        self.date_start.setCalendarPopup(True)
        form.addRow("📆 Başlangıç:", self.date_start)
        
        left_panel.addLayout(form)
        
        # Hesapla Butonu
        btn_calculate = QPushButton("📊 Ödeme Planını Hesapla")
        btn_calculate.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                border-radius: 8px;
                padding: 12px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: @accent_hover;
            }
        """))
        btn_calculate.clicked.connect(self.calculate_plan)
        left_panel.addWidget(btn_calculate)
        
        # Özet Bilgiler
        self.lbl_summary = QLabel("💡 Formu doldurun ve hesapla butonuna basın")
        self.lbl_summary.setStyleSheet(theme_qss("""
            QLabel {
                background-color: @surface_alt;
                border-left: 4px solid @accent;
                padding: 10px;
                border-radius: 4px;
                color: @text;
                font-size: 13px;
            }
        """))
        self.lbl_summary.setWordWrap(True)
        left_panel.addWidget(self.lbl_summary)
        
        left_panel.addStretch()
        
        # ===== SAĞ PANEL: ÖNİZLEME TABLOSU =====
        right_panel = QVBoxLayout()
        
        # Başlık
        preview_label = QLabel("📋 Ödeme Planı Önizleme")
        preview_label.setStyleSheet(theme_qss("font-weight: bold; font-size: 14px; color: @text;"))
        right_panel.addWidget(preview_label)
        
        # Tablo
        self.table_preview = QTableWidget()
        self.table_preview.setColumnCount(6)
        self.table_preview.setHorizontalHeaderLabels([
            "#", "Vade Tarihi", "Toplam", "Ana Para", "Faiz", "Vergi (KDF+BSMV)"
        ])
        self.table_preview.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_preview.setAlternatingRowColors(True)
        self.table_preview.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_preview.setStyleSheet(theme_qss("""
            QTableWidget {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                outline: none;
            }
            QTableWidget::item {
                outline: none;
            }
            QTableWidget::item:focus {
                outline: none;
                border: none;
            }
            QHeaderView::section {
                background-color: @surface_alt;
                padding: 8px;
                border: none;
                font-weight: bold;
                color: @text_muted;
            }
        """))
        right_panel.addWidget(self.table_preview)
        
        # Layout'ları birleştir
        main_layout.addLayout(left_panel, 40)  # %40 sol
        main_layout.addLayout(right_panel, 60)  # %60 sağ
        
        self.content_layout.addLayout(main_layout)
        
        # ===== ALT BUTONLAR =====
        btn_box = QHBoxLayout()
        
        btn_save = QPushButton("✨ Onayla ve Kaydet")
        btn_save.clicked.connect(self.save_loan)
        btn_save.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @success;
                color: @selection_text;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: @success;
            }
            QPushButton:disabled {
                background-color: @disabled_text;
            }
        """))
        btn_save.setEnabled(False)  # İlk başta pasif
        self.btn_save = btn_save
        
        btn_cancel = QPushButton("❌ İptal")
        btn_cancel.clicked.connect(self.reject)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @disabled_text;
                color: @selection_text;
                border-radius: 8px;
                padding: 12px 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: @text_muted;
            }
        """))
        
        btn_box.addStretch()
        btn_box.addWidget(btn_save)
        btn_box.addWidget(btn_cancel)
        
        self.content_layout.addLayout(btn_box)
    
    def calculate_plan(self):
        """Ödeme planını hesapla ve tabloya yükle"""
        try:
            # Form verilerini al
            principal = self.spin_principal.value()
            annual_rate = self.spin_interest.value()
            months = self.spin_months.value()
            kkdf = self.spin_kkdf.value()
            bsmv = self.spin_bsmv.value()
            start_date = self.date_start.date().toPyDate()
            
            # Planı hesapla
            self.payment_plan = self.calculator.generate_payment_plan(
                principal=principal,
                annual_rate=annual_rate,
                months=months,
                start_date=datetime.combine(start_date, datetime.min.time()),
                kkdf_rate=kkdf,
                bsmv_rate=bsmv
            )
            
            # Toplam maliyet
            cost = self.calculator.calculate_total_cost(principal, annual_rate, months, kkdf, bsmv)
            
            # Özet güncelle
            self.lbl_summary.setText(f"""
            ✅ <b>Plan Hazır!</b><br>
            💰 Aylık Taksit: <b>{self._fmt_try(cost['monthly_installment'])}</b><br>
            📊 Toplam Ödeme: <b>{self._fmt_try(cost['total_payment'])}</b><br>
            📈 Toplam Faiz: <b>{self._fmt_try(cost['total_interest'])}</b><br>
            🔖 Toplam Vergi: <b>{self._fmt_try(cost['total_tax'])}</b>
            """)
            
            # Tabloyu doldur
            self.populate_table()
            
            # Kaydet butonunu aktifleştir
            self.btn_save.setEnabled(True)
            
        except Exception as e:
            show_error(self, f"Hesaplama hatası: {e}")
    
    def populate_table(self):
        """Önizleme tablosunu doldur"""
        self.table_preview.setRowCount(len(self.payment_plan))
        
        for row, inst in enumerate(self.payment_plan):
            # Taksit numarası
            self.table_preview.setItem(row, 0, QTableWidgetItem(str(inst['installment_number'])))
            
            # Vade tarihi
            self.table_preview.setItem(row, 1, QTableWidgetItem(inst['due_date']))
            
            # Toplam tutar
            total_item = QTableWidgetItem(self._fmt_try(inst['total_amount']))
            total_item.setForeground(qc("success"))
            self.table_preview.setItem(row, 2, total_item)
            
            # Ana para
            self.table_preview.setItem(row, 3, QTableWidgetItem(self._fmt_try(inst['principal_part'])))
            
            # Faiz
            self.table_preview.setItem(row, 4, QTableWidgetItem(self._fmt_try(inst['interest_part'])))
            
            # Vergi
            tax = inst.get('kkdf_amount', 0) + inst.get('bsmv_amount', 0)
            self.table_preview.setItem(row, 5, QTableWidgetItem(self._fmt_try(tax)))
    
    def save_loan(self):
        """Krediyi ve taksitleri veritabanına kaydet"""
        if not self.payment_plan:
            show_error(self, "Önce ödeme planını hesaplayın!")
            return
        
        if not self.txt_bank.text():
            show_error(self, "Banka adı boş olamaz!")
            return
        
        try:
            # Kredi bilgilerini hazırla
            loan_data = {
                'bank_name': self.txt_bank.text(),
                'description': self.txt_description.text() or "Kredi",
                'principal_amount': self.spin_principal.value(),
                'interest_rate': self.spin_interest.value(),
                'installment_count': self.spin_months.value(),
                'kkdf_rate': self.spin_kkdf.value(),
                'bsmv_rate': self.spin_bsmv.value(),
                'start_date': self.date_start.date().toString('yyyy-MM-dd')
            }
            
            # Veritabanına kaydet
            loan_id = self.db.add_loan_with_installments(loan_data, self.payment_plan)
            
            if loan_id:
                show_success(self, f"✅ Kredi başarıyla kaydedildi! ({len(self.payment_plan)} taksit oluşturuldu)")
                self.accept()
            else:
                show_error(self, "Kredi kaydedilemedi!")
                
        except Exception as e:
            show_error(self, f"Kayıt hatası: {e}")
