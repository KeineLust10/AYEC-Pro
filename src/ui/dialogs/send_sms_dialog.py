# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QPushButton, QComboBox, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from src.utils.theme_colors import theme_qss
from PyQt6.QtGui import QFont, QIcon
from src.services.sms_service import SMSService
from src.ui.widgets.modern_dialog import ModernDialog
from src.utils.message_helper import show_error, show_info, show_warning

class SendSMSDialog(ModernDialog):
    """
    Dialog for sending SMS to customers.
    Allows template selection or custom message entry.
    """
    def __init__(self, db, parent=None, customer_name="", phone="", tracking_no=""):
        super().__init__(title=f"SMS Gonder - {customer_name}", parent=parent, width=500, height=450)
        self.db = db
        self.customer_name = customer_name
        self.phone = phone
        self.tracking_no = tracking_no
        self.sms_service = SMSService(db)
        
        self.set_footer_visible(False)
        self.setStyleSheet(theme_qss("""
            QDialog { background-color: @surface; }
            QLabel { font-size: 13px; color: @text; }
            QTextEdit { 
                border: 1px solid @border; 
                border-radius: 8px; 
                padding: 10px;
                font-size: 13px;
                background-color: @surface_alt;
            }
            QComboBox {
                border: 1px solid @border;
                border-radius: 8px;
                padding: 5px 10px;
                background-color: @surface;
            }
        """))
        
        self.init_ui()
        
    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("Müşteri Bilgilendirme SMS'i")
        header.setStyleSheet(theme_qss("font-size: 16px; font-weight: 700; color: @text;"))
        layout.addWidget(header)
        
        # Info Box
        info_box = QLabel(f"<b>Alıcı:</b> {self.customer_name}<br><b>Tel:</b> {self.phone}")
        info_box.setStyleSheet(theme_qss("""
            background-color: @selection_bg; 
            border: 1px solid @border; 
            border-radius: 6px; 
            padding: 10px;
            color: @accent_pressed;
        """))
        layout.addWidget(info_box)
        
        # Template Selector
        layout.addWidget(QLabel("Şablon Seçiniz:"))
        self.cmb_templates = QComboBox()
        self.cmb_templates.addItem("Özel Mesaj Yaz", "")
        self.cmb_templates.addItem("Cihaz Alındı", "Cihazınız servisimize kabul edilmiştir. Takip No: {tracking_no}")
        self.cmb_templates.addItem("Fiyat Onayı Bekleniyor", "Cihazınız için fiyat onayı gerekmektedir. Lütfen iletişime geçiniz.")
        self.cmb_templates.addItem("Onarım Tamamlandı", "Cihazınızın onarımı tamamlanmıştır. Teslim alabilirsiniz.")
        self.cmb_templates.addItem("Yedek Parça Bekleniyor", "Cihazınız için yedek parça siparişi verilmiştir.")
        self.cmb_templates.addItem("Cihaz İade/İptal", "Cihazınız iade/iptal edilmiştir.")
        
        self.cmb_templates.currentIndexChanged.connect(self.on_template_change)
        layout.addWidget(self.cmb_templates)
        
        # Message Area
        layout.addWidget(QLabel("Mesaj İçeriği:"))
        self.txt_message = QTextEdit()
        self.txt_message.setPlaceholderText("Mesajınızı buraya yazınız...")
        self.txt_message.textChanged.connect(self.update_char_count)
        layout.addWidget(self.txt_message)
        
        # Character Count
        self.lbl_chars = QLabel("0 karakter")
        self.lbl_chars.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_chars.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
        layout.addWidget(self.lbl_chars)
        
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @surface;
                border: 1px solid @border;
                border-radius: 8px;
                padding: 10px 20px;
                color: @text_muted;
                font-weight: 600;
            }
            QPushButton:hover { background-color: @surface_alt; }
        """))
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_send = QPushButton("  SMS Gönder")
        self.btn_send.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: @selection_text;
                font-weight: 700;
            }
            QPushButton:hover { background-color: @accent_hover; }
            QPushButton:disabled { background-color: @disabled_text; }
        """))
        self.btn_send.clicked.connect(self.send_sms)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_send)
        
        layout.addLayout(btn_layout)
        
        # Check Service Status
        if not self.sms_service.enabled:
            show_warning(
                self,
                "SMS Servisi Pasif",
                "SMS servisi yapılandırılmamış veya devre dışı.\nLütfen ayarlardan Twilio bilgilerinizi kontrol edin.",
            )
            self.btn_send.setEnabled(False)
            self.txt_message.setEnabled(False)
        elif not self.phone:
            show_warning(self, "Telefon Yok", "Bu müşterinin telefon numarası kayıtlı değil.")
            self.btn_send.setEnabled(False)
            
    def on_template_change(self):
        data = self.cmb_templates.currentData()
        if data:
            # Format simple templates
            msg = data.replace("{tracking_no}", self.tracking_no)
            self.txt_message.setText(msg)
            
    def update_char_count(self):
        text = self.txt_message.toPlainText()
        count = len(text)
        self.lbl_chars.setText(f"{count} karakter")
        
        # Basic validation (1 SMS ~ 160 chars, but we allow more)
        if count > 160:
             self.lbl_chars.setStyleSheet(theme_qss("color: @danger; font-size: 11px; font-weight: bold;"))
             self.lbl_chars.setText(f"{count} karakter (Birden fazla SMS gönderilecek)")
        else:
             self.lbl_chars.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px;"))
             
    def send_sms(self):
        message = self.txt_message.toPlainText().strip()
        if not message:
            show_warning(self, "Uyarı", "Lütfen bir mesaj metni giriniz.")
            return
            
        try:
            self.btn_send.setEnabled(False)
            self.btn_send.setText("Gönderiliyor...")
            # Use processEvents to update UI
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            success = self.sms_service.send_custom_sms(self.phone, message)
            
            if success:
                show_info(self, "Başarılı", "SMS başarıyla gönderildi.")
                self.accept()
            else:
                show_error(self, "Hata", "SMS gönderilemedi. Lütfen bağlantınızı ve bakiyenizi kontrol edin.")
                self.btn_send.setEnabled(True)
                self.btn_send.setText("SMS Gönder")
                
        except Exception as e:
            show_error(self, "Hata", f"Beklenmeyen bir hata oluştu: {e}")
            self.btn_send.setEnabled(True)
            self.btn_send.setText("SMS Gönder")

