"""
Company Settings Dialog
Firma ayarları düzenleme dialog'u
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                             QScrollArea, QFrame, QGridLayout, QTextEdit, QComboBox,
                             QHBoxLayout)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from src.utils.theme_manager import ThemeManager
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.utils import message_helper
from src.ui.dialogs.base_modern_dialog import BaseModernDialog


class CompanySettingsDialog(BaseModernDialog):
    """Firma Ayarlarını Gir - Detaylı Düzenleme Dialog'u"""
    
    def __init__(self, db, main_window=None, parent=None):
        super().__init__(parent=parent, title="Firma Ayarlarını Gir", width=980, height=760)
        self.db = db
        self.main_window = main_window
        self.set_wheel_scroll_enabled(True)
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        title = QLabel("Firma Ayarlarını Gir")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; margin-bottom: 10px;"))
        self.content_layout.addWidget(title)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        form_layout = QGridLayout(content_widget)
        form_layout.setSpacing(20)
        
        def add_field(label, row, col, widget):
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            form_layout.addWidget(lbl, row, col)
            form_layout.addWidget(widget, row + 1, col)
        
        self.inp_name = QLineEdit()
        add_field("Firma Adınız", 0, 0, self.inp_name)
        
        self.inp_email = QLineEdit()
        add_field("Firma E-posta Adresiniz", 0, 1, self.inp_email)
        
        self.inp_facebook = QLineEdit()
        add_field("Facebook Adresiniz", 2, 0, self.inp_facebook)
        
        self.inp_instagram = QLineEdit()
        add_field("Instagram Adresiniz", 2, 1, self.inp_instagram)
        
        self.inp_youtube = QLineEdit()
        add_field("Youtube Adresiniz", 4, 0, self.inp_youtube)
        
        self.inp_website = QLineEdit()
        add_field("Web Site Adresiniz", 4, 1, self.inp_website)
        
        self.inp_gsm = QLineEdit()
        add_field("Firma GSM Numaranız", 6, 0, self.inp_gsm)
        
        self.inp_fax = QLineEdit()
        add_field("Firma Fax", 6, 1, self.inp_fax)
        
        self.inp_site_title = QLineEdit()
        add_field("Web Site Title", 8, 0, self.inp_site_title)
        
        self.inp_phone = QLineEdit()
        add_field("Firma Sabit Telefonunuz", 8, 1, self.inp_phone)
        
        self.inp_cargo = QLineEdit()
        add_field("Kargo Firması", 10, 0, self.inp_cargo)
        
        self.inp_cargo_no = QLineEdit()
        add_field("Kargo Anlaşma No", 10, 1, self.inp_cargo_no)
        
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(ThemeManager.get_available_themes(self.db))
        add_field("Tema Rengi", 12, 0, self.cmb_theme)
        
        self.cmb_currency = QComboBox()
        self.cmb_currency.addItems([
            "TRY - Türk Lirası (₺)",
            "USD - Amerikan Doları ($)",
            "EUR - Euro (€)",
        ])
        add_field("Para Biriminiz", 12, 1, self.cmb_currency)
        
        # Para Birimi Ondalık Basamak Ayarı
        self.cmb_currency_precision = QComboBox()
        self.cmb_currency_precision.addItems([
            "0 - Tam Sayı (1)",
            "1 - Ondalık (1,0)",
            "2 - Ondalık (1,00)",
            "3 - Hassas (1,000)",
        ])
        self.cmb_currency_precision.setToolTip("Para birimi gösteriminde kullanılacak ondalık basamak sayısı")
        add_field("Para Birimi Hassasiyeti", 13, 0, self.cmb_currency_precision)
        
        self.cmb_online_payment = QComboBox()
        self.cmb_online_payment.addItems(["Aktif", "Pasif"])
        add_field("Online Ödeme Aktif/Pasif", 14, 0, self.cmb_online_payment)
        
        self.inp_scroll_text = QLineEdit()
        self.inp_scroll_text.setPlaceholderText("BURAYA BİLGİ AMAÇLI YAZI GİREBİLİRSİNİZ...")
        add_field("Müşteri Bilgi Ekranı Kayan Yazı", 14, 1, self.inp_scroll_text)
        
        self.inp_stock_prefix = QLineEdit()
        add_field("Ürün Stok Harf Kodu Ön Ek", 16, 0, self.inp_stock_prefix)
        
        self.inp_quick_stock_prefix = QLineEdit()
        add_field("Hızlı Satış Ürün Stok Harf Kodu Ön Ek", 16, 1, self.inp_quick_stock_prefix)
        
        lbl_addr = QLabel("Firma Adresiniz")
        lbl_addr.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        form_layout.addWidget(lbl_addr, 18, 0)
        self.txt_address = QTextEdit()
        self.txt_address.setMaximumHeight(80)
        form_layout.addWidget(self.txt_address, 19, 0, 1, 2)
        
        lbl_contract = QLabel("Teknik Servis Sözleşmeniz")
        lbl_contract.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        form_layout.addWidget(lbl_contract, 20, 0)
        self.txt_contract = QTextEdit()
        self.txt_contract.setMaximumHeight(110)
        form_layout.addWidget(self.txt_contract, 21, 0, 1, 2)

        lbl_offer_contract = QLabel("Teklif Mektubu Sözleşmesi")
        lbl_offer_contract.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        form_layout.addWidget(lbl_offer_contract, 22, 0)
        self.txt_offer_contract = QTextEdit()
        self.txt_offer_contract.setMaximumHeight(110)
        form_layout.addWidget(self.txt_offer_contract, 23, 0, 1, 2)

        content_widget.setLayout(form_layout)
        scroll.setWidget(content_widget)
        content_widget.setStyleSheet(theme_qss("""
            QWidget { background-color: @surface; }
            QLabel { color: @text; }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid @border;
                border-radius: 6px;
                padding: 8px;
                background-color: @surface_alt;
                color: @text;
                selection-background-color: @selection_bg;
                selection-color: @selection_text;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid @accent;
            }
        """))
        self.content_layout.addWidget(scroll, 1)
        self.add_cancel_button("İptal")
        self.add_button("GÜNCELLE", "success", self.save_data)
    
    def load_data(self):
        self.inp_name.setText(self.db.get_setting("company_name", ""))
        self.inp_email.setText(self.db.get_setting("company_email", ""))
        self.inp_facebook.setText(self.db.get_setting("social_facebook", ""))
        self.inp_instagram.setText(self.db.get_setting("social_instagram", ""))
        self.inp_youtube.setText(self.db.get_setting("social_youtube", ""))
        self.inp_website.setText(self.db.get_setting("company_website", ""))
        self.inp_gsm.setText(self.db.get_setting("company_gsm", ""))
        self.inp_fax.setText(self.db.get_setting("company_fax", ""))
        self.inp_site_title.setText(self.db.get_setting("site_title", ""))
        self.inp_phone.setText(self.db.get_setting("company_phone", ""))
        self.inp_cargo.setText(self.db.get_setting("cargo_company", ""))
        self.inp_cargo_no.setText(self.db.get_setting("cargo_deal_no", ""))
        self.inp_stock_prefix.setText(self.db.get_setting("stock_prefix", "TO"))
        self.inp_quick_stock_prefix.setText(self.db.get_setting("quick_stock_prefix", "TOH"))
        self.txt_address.setText(self.db.get_setting("company_address", ""))
        self.txt_contract.setText(self.db.get_setting("service_contract", ""))
        self.txt_offer_contract.setText(
            self.db.get_setting("offer_contract", self.db.get_setting("service_contract", ""))
        )
        self.inp_scroll_text.setText(self.db.get_setting("marquee_text", ""))
        
        current_theme = self.db.get_setting("color_theme_full", "")
        idx = self.cmb_theme.findText(current_theme)
        if idx >= 0:
            self.cmb_theme.setCurrentIndex(idx)
        
        curr = CurrencyHelper.get_code(self.db)
        idx2 = 0
        if curr == "USD":
            idx2 = 1
        elif curr == "EUR":
            idx2 = 2
        if idx2 >= 0:
            self.cmb_currency.setCurrentIndex(idx2)
        
        # Para birimi hassasiyetini yükle
        precision = self.db.get_setting("currency_precision", "2")
        precision_idx = int(precision) if precision.isdigit() else 2
        if precision_idx > 3:
            precision_idx = 3
        self.cmb_currency_precision.setCurrentIndex(precision_idx)
    
    def save_data(self):
        self.db.set_setting("company_name", self.inp_name.text())
        self.db.set_setting("company_email", self.inp_email.text())
        self.db.set_setting("social_facebook", self.inp_facebook.text())
        self.db.set_setting("social_instagram", self.inp_instagram.text())
        self.db.set_setting("social_youtube", self.inp_youtube.text())
        self.db.set_setting("company_website", self.inp_website.text())
        self.db.set_setting("company_gsm", self.inp_gsm.text())
        self.db.set_setting("company_fax", self.inp_fax.text())
        self.db.set_setting("site_title", self.inp_site_title.text())
        self.db.set_setting("company_phone", self.inp_phone.text())
        self.db.set_setting("cargo_company", self.inp_cargo.text())
        self.db.set_setting("cargo_deal_no", self.inp_cargo_no.text())
        self.db.set_setting("stock_prefix", self.inp_stock_prefix.text())
        self.db.set_setting("quick_stock_prefix", self.inp_quick_stock_prefix.text())
        self.db.set_setting("company_address", self.txt_address.toPlainText())
        self.db.set_setting("service_contract", self.txt_contract.toPlainText())
        self.db.set_setting("offer_contract", self.txt_offer_contract.toPlainText())
        self.db.set_setting("marquee_text", self.inp_scroll_text.text())
        CurrencyHelper.persist_code(self.db, self.cmb_currency.currentText())
        
        # Para birimi hassasiyetini kaydet
        precision_idx = self.cmb_currency_precision.currentIndex()
        self.db.set_setting("currency_precision", str(precision_idx))
        
        new_theme = self.cmb_theme.currentText()
        old_theme = self.db.get_setting("color_theme_full", "Koyu Modern")
        if new_theme != old_theme:
            self.db.set_setting("color_theme_full", new_theme)
            if self.main_window and hasattr(self.main_window, 'apply_theme'):
                self.main_window.apply_theme(new_theme)
        
        if self.main_window and hasattr(self.main_window, 'update_menu_branding'):
            self.main_window.update_menu_branding()
        
        if self.main_window:
            self.main_window.show_notification("Firma bilgileri güncellendi.", "success")
        else:
            message_helper.show_info(self, "Başarılı", "Firma bilgileri güncellendi.")
        self.accept()
