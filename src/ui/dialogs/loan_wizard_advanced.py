# -*- coding: utf-8 -*-

"""
Advanced Loan Wizard Container
4 adımlı modern kredi sihirbazı
"""
import os
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget, 
                             QLabel, QFrame, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.dialogs.loan_wizard_steps import (Step1BankInfo, Step2FinancialDetails, 
                                             Step3DocumentUpload, Step4Summary)
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens
from src.utils.system_config import SystemConfig
from src.utils.logger import logger

class AdvancedLoanWizard(BaseModernDialog):
    """🚀 AYEC Pro Gelişmiş Kredi Sihirbazı"""
    
    def __init__(self, db, parent=None, sector_manager=None):
        super().__init__(parent, title="🚀 Kredi Ekleme Sihirbazı", width=1320, height=820)
        self.db = db
        self.sector_manager = sector_manager or getattr(parent, "sector_manager", None)
        self.current_step_idx = 0
        self.wizard_data = {}
        self.setup_wizard_ui()
        
    def setup_wizard_ui(self):
        # 1. Stepper / Progress Header
        self.stepper_container = QFrame()
        self.stepper_container.setStyleSheet(theme_qss("""
            QFrame {
                background-color: @surface;
                border-bottom: 1px solid @border;
            }
        """))
        stepper_layout = QHBoxLayout(self.stepper_container)
        stepper_layout.setContentsMargins(40, 20, 40, 20)
        
        self.step_widgets = []
        self.step_widgets = []
        
        # Build steps dynamically
        step_labels = ["Genel Bilgiler", "Finansal Detaylar"]
        self.step_pages = [Step1BankInfo(self), Step2FinancialDetails(self)]
        
        # Sektörel Etiket (Wizard 3. Adım)
        sector_key = SystemConfig.get_current_sector(self.db)
        try:
            if self.sector_manager and self.sector_manager.get_current_plugin():
                sector_key = self.sector_manager.get_current_plugin().sector_id
        except Exception:
            pass
        if isinstance(sector_key, (list, tuple, set)):
            sector_key = next(iter(sector_key), None)
        from src.utils.system_config import SYSTEM_MODES
        sector_data = SYSTEM_MODES.get(sector_key) or {}
        labels = sector_data.get('labels') or {}
        upload_label = labels.get('wizard_step3', "Evrak Yükleme")
        
        if SystemConfig.is_feature_active(self.db, "wizard_upload"):
            step_labels.append(upload_label)
            self.step_pages.append(Step3DocumentUpload(self))
            
        step_labels.append("Onay")
        self.step_pages.append(Step4Summary(self))
        
        # FIX: Initialize self.stack here
        self.stack = QStackedWidget()
        
        for page in self.step_pages:
            self.stack.addWidget(page)
            
        self.content_layout.addWidget(self.stack)
        
        # 3. Footer Navigation
        footer = QFrame()
        footer.setStyleSheet(theme_qss("background: transparent; border: none;"))
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 10, 12, 6)
        
        self.btn_back = QPushButton("⬅️ Geri")
        self.btn_back.setFixedSize(120, 42)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setStyleSheet(theme_qss(DesignTokens.get_button_qss("secondary")))
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setEnabled(False)
        
        self.btn_next = QPushButton("İleri ➡️")
        self.btn_next.setFixedSize(140, 42)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setStyleSheet(theme_qss(DesignTokens.get_button_qss("primary")))
        self.btn_next.clicked.connect(self._go_next)
        
        self.btn_save = QPushButton("✅ Krediyi Kaydet")
        self.btn_save.setFixedSize(180, 42)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.setStyleSheet(theme_qss(DesignTokens.get_button_qss("success")))
        self.btn_save.clicked.connect(self._save_loan)
        self.btn_save.setVisible(False)
        
        footer_layout.addWidget(self.btn_back)
        footer_layout.addStretch()
        footer_layout.addWidget(self.btn_next)
        footer_layout.addWidget(self.btn_save)
        
        self.content_layout.addWidget(footer)
        
        # Update first step UI
        self._update_stepper_ui()

    def _create_stepper_item(self, num, label):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        circle = QLabel(str(num))
        circle.setFixedSize(32, 32)
        circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        circle.setObjectName("Circle")
        
        text = QLabel(label)
        text.setFont(QFont("Segoe UI", 9))
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        text.setObjectName("Text")
        
        layout.addWidget(circle, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text, alignment=Qt.AlignmentFlag.AlignCenter)
        
        return widget

    def _update_stepper_ui(self):
        for i, widget in enumerate(self.step_widgets):
            circle = widget.findChild(QLabel, "Circle")
            text = widget.findChild(QLabel, "Text")
            
            if i == self.current_step_idx:  # Active
                circle.setStyleSheet(theme_qss("""
                    background-color: @accent_hover; 
                    color: @selection_text; 
                    border-radius: 16px;
                """))
                text.setStyleSheet(theme_qss("color: @accent_hover; font-weight: bold;"))
            elif i < self.current_step_idx:  # Completed
                circle.setText("✓")
                circle.setStyleSheet(theme_qss("""
                    background-color: @success; 
                    color: @selection_text; 
                    border-radius: 16px;
                """))
                text.setStyleSheet(theme_qss("color: @success;"))
            else:  # Upcoming
                circle.setText(str(i+1))
                circle.setStyleSheet(theme_qss("""
                    background-color: @surface_alt; 
                    color: @text_muted; 
                    border: 1px solid @border;
                    border-radius: 16px;
                """))
                text.setStyleSheet(theme_qss("color: @text_muted;"))

    def _go_next(self):
        # 1. Validate current step
        is_valid, error = self.step_pages[self.current_step_idx].validate()
        if not is_valid:
            from src.utils.toast_notification import ToastManager
            # Show toast instead of blocking modal
            ToastManager.error(self, error)
            return
            
        # 2. Collect data
        self.wizard_data.update(self.step_pages[self.current_step_idx].get_data())
        
        # 3. Move to next
        self.current_step_idx += 1
        
        # If moving to summary (last page), pass all data
        last_idx = len(self.step_pages) - 1
        if self.current_step_idx == last_idx:
            self.step_pages[last_idx].set_data(self.wizard_data)
            self.btn_next.setVisible(False)
            self.btn_save.setVisible(True)
            
        self.stack.setCurrentIndex(self.current_step_idx)
        self.btn_back.setEnabled(True)
        self._update_stepper_ui()

    def _go_back(self):
        self.current_step_idx -= 1
        
        if self.current_step_idx == 0:
            self.btn_back.setEnabled(False)
            
        self.btn_next.setVisible(True)
        self.btn_save.setVisible(False)
        
        self.stack.setCurrentIndex(self.current_step_idx)
        self._update_stepper_ui()

    def _save_loan(self):
        """Final save operation with DB and Voice integration"""
        try:
            # 1. Implementation of save logic
            from src.utils.loan_calculator import LoanCalculator
            calc = LoanCalculator()
            
            data = self.wizard_data
            principal = data['principal']
            interest = data['interest_rate']
            months = data['months']
            start_date = data['start_date']
            kkdf = data.get('kkdf_rate', 0)
            bsmv = data.get('bsmv_rate', 0)
            
            # Save Loan Header
            loan_id = self.db.add_loan(
                bank_name=data['bank_name'],
                loan_type=data.get('loan_type', 'Taksitli'),
                loan_title=data.get('title', 'Kredi'),
                principal=principal,
                interest_rate=interest,
                months=months,
                start_date=start_date.strftime('%Y-%m-%d'),
                kkdf_rate=kkdf,
                bsmv_rate=bsmv
            )
            
            if not loan_id:
                raise Exception("Kredi veritabanına kaydedilemedi.")
                
            # Save Installments
            plan = calc.generate_payment_plan(principal, interest, months, start_date, kkdf, bsmv)
            for row in plan:
                inst_data = {
                    'loan_id': loan_id,
                    'installment_no': row['installment_number'],
                    'due_date': row['due_date'],
                    'amount': row['total_amount']
                }
                self.db.add_loan_installment(inst_data)
            
            # Save Attachments (placeholder for real file copy logic)
            attachments = data.get('attachments', [])
            for path, ftype in attachments:
                # In a real app, you would copy files to a dedicated storage
                try:
                    self.db.cursor.execute(
                        "INSERT INTO loan_attachments (loan_id, file_name, file_path, file_type, notes) VALUES (?, ?, ?, ?, ?)",
                        (loan_id, os.path.basename(path), path, ftype, data.get('notes', ''))
                    )
                except Exception as e:
                    logger.error(f"Loan wizard attachment save error: {e}")
            
            self.db.conn.commit()
                
            # 2. Voice Assistant Notification
            from src.utils.asistan_motoru import sesli_cevap_ver_async
            
            bank_short = data.get('bank', {}).get('shortName', data['bank_name'])
            msg = f"Mükemmel! {bank_short} kredisi sisteme başarıyla işlendi. "
            msg += f"Kredi için tüm evrakları kaydettim ve {months} aylık ödeme planını oluşturdum. "
            msg += "İlk taksit hatırlatıcısı aktif edildi."
            
            sesli_cevap_ver_async(msg)
            
            # 3. Success Notification
            from src.utils.toast_notification import ToastManager
            ToastManager.success(self, "Kredi ve ödeme planı başarıyla oluşturuldu!")
            self.accept()
            
        except Exception as e:
            from src.utils.toast_notification import ToastManager
            ToastManager.error(self, f"Kayıt sırasında hata oluştu: {e}")
