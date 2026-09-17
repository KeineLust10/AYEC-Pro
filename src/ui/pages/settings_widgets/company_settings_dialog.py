# -*- coding: utf-8 -*-

"""
Company Settings Dialog
Firma ayarları düzenleme dialog'u
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                             QScrollArea, QFrame, QGridLayout, QTextEdit, QComboBox,
                             QHBoxLayout)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from PyQt6.QtPrintSupport import QPrinterInfo

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
        self._wire_ui_signals()
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
        self.cmb_currency.addItems(CurrencyHelper.get_choice_texts())
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


        self.cmb_document_printer = QComboBox()
        self.cmb_receipt_printer = QComboBox()
        self.cmb_label_printer = QComboBox()
        printer_names = QPrinterInfo.availablePrinterNames()
        default_printer = "Windows varsay\u0131lan yaz\u0131c\u0131s\u0131"
        for combo in (
            self.cmb_document_printer,
            self.cmb_receipt_printer,
            self.cmb_label_printer,
        ):
            combo.addItem(default_printer, "")
            for printer_name in printer_names:
                combo.addItem(printer_name, printer_name)
        add_field("Belge Yaz\u0131c\u0131s\u0131", 18, 0, self.cmb_document_printer)
        add_field("Fi\u015f Yaz\u0131c\u0131s\u0131", 18, 1, self.cmb_receipt_printer)
        add_field("Barkod / Etiket Yaz\u0131c\u0131s\u0131", 20, 0, self.cmb_label_printer)

        self.cmb_document_page_size = QComboBox()
        self.cmb_document_page_size.addItems(["A4", "A3", "A5"])
        add_field("Detayl\u0131 Fi\u015f Ka\u011f\u0131d\u0131", 20, 1, self.cmb_document_page_size)

        self.cmb_document_orientation = QComboBox()
        self.cmb_document_orientation.addItem("Dikey", "portrait")
        self.cmb_document_orientation.addItem("Yatay", "landscape")
        add_field("Belge Y\u00f6n\u00fc", 22, 0, self.cmb_document_orientation)

        self.inp_label_size = QLineEdit()
        self.inp_label_size.setPlaceholderText("70x45")
        add_field("Etiket Boyutu (mm, GxY)", 22, 1, self.inp_label_size)

        lbl_addr = QLabel("Firma Adresiniz")
        lbl_addr.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        form_layout.addWidget(lbl_addr, 24, 0)
        self.txt_address = QTextEdit()
        self.txt_address.setMaximumHeight(80)
        form_layout.addWidget(self.txt_address, 25, 0, 1, 2)

        lbl_contract = QLabel("Teknik Servis Sözleşmeniz")
        lbl_contract.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        form_layout.addWidget(lbl_contract, 26, 0)
        self.txt_contract = QTextEdit()
        self.txt_contract.setMaximumHeight(110)
        form_layout.addWidget(self.txt_contract, 27, 0, 1, 2)

        lbl_offer_contract = QLabel("Teklif Mektubu Sözleşmesi")
        lbl_offer_contract.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        form_layout.addWidget(lbl_offer_contract, 28, 0)
        self.txt_offer_contract = QTextEdit()
        self.txt_offer_contract.setMaximumHeight(110)
        form_layout.addWidget(self.txt_offer_contract, 29, 0, 1, 2)

        self.inp_authorized_person = QLineEdit()
        add_field("Yetkili Ki\u015fi", 32, 0, self.inp_authorized_person)

        self.inp_tax_office = QLineEdit()
        add_field("Vergi Dairesi", 32, 1, self.inp_tax_office)

        self.inp_tax_number = QLineEdit()
        add_field("Vergi Numaras\u0131", 34, 0, self.inp_tax_number)

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
        self.add_button("GUNCELLE", "success", lambda: self.save_data(close_dialog=True))

    def _wire_ui_signals(self):
        self.cmb_theme.currentIndexChanged.connect(self._preview_theme)
        self.cmb_currency.currentIndexChanged.connect(lambda: self.save_data(close_dialog=False))
        self.cmb_currency_precision.currentIndexChanged.connect(lambda: self.save_data(close_dialog=False))
        self.cmb_online_payment.currentIndexChanged.connect(lambda: self.save_data(close_dialog=False))

    def _preview_theme(self, _index=None):
        selected = ThemeManager.normalize_theme_name(self.cmb_theme.currentText())
        current = ThemeManager.normalize_theme_name(
            getattr(self.main_window, "_current_theme_name", "")
            or self.db.get_setting("color_theme_full", "AYEC")
        )
        if selected == current:
            return
        if self.main_window and hasattr(self.main_window, "apply_theme"):
            self.main_window.apply_theme(selected)
        else:
            self.db.set_setting("color_theme_full", selected)

    def _default_offer_contract(self):
        return "\n".join(
            [
                "Fiyat      : Amerikan Dolar\u0131 cinsinden verilmi\u015f olup, fatura tarihindeki TCMB d\u00f6viz sat\u0131\u015f kuru ge\u00e7erlidir.",
                "\u00d6deme     : Sipari\u015fte toplam tutar\u0131n %50'i, i\u015f bitiminde kalan bakiye nakit \u00f6denecektir.",
                "Teslimat  : Sipari\u015f ve \u00f6n \u00f6demeyi takiben, stok durumuna g\u00f6re 6 (Alt\u0131) haftad\u0131r.",
                "Garanti   : \u00dcretim hatalar\u0131na kar\u015f\u0131 2 (iki) y\u0131ld\u0131r.",
                "Opsiyon   : Fiyat teklifimiz, ta\u015f\u0131d\u0131\u011f\u0131 tarih itibariyle 15 g\u00fcn s\u00fcre ile ge\u00e7erlidir.",
            ]
        )

    def _migrate_setup_company_info(self):
        """Copy initial setup company identity into the editable settings store."""
        try:
            row = self.db.cursor.execute(
                "SELECT company_name, authorized_person, phone, email, address, "
                "tax_office, tax_number FROM company_info ORDER BY rowid DESC LIMIT 1"
            ).fetchone()
            if not row:
                return
            values = {
                "company_name": row[0] or "",
                "company_authorized_person": row[1] or "",
                "company_phone": row[2] or "",
                "company_gsm": row[2] or "",
                "company_email": row[3] or "",
                "company_address": row[4] or "",
                "company_tax_office": row[5] or "",
                "company_tax_number": row[6] or "",
            }
            for setting_key, setting_value in values.items():
                if setting_value and not str(self.db.get_setting(setting_key, "") or "").strip():
                    self.db.set_setting(setting_key, setting_value)
            if values["company_name"] and not self.db.get_setting("site_title", ""):
                self.db.set_setting("site_title", values["company_name"])
        except Exception:
            return

    def load_data(self):
        self._migrate_setup_company_info()
        self.inp_name.setText(self.db.get_setting("company_name", ""))
        self.inp_email.setText(self.db.get_setting("company_email", ""))
        self.inp_authorized_person.setText(
            self.db.get_setting("company_authorized_person", "")
        )
        self.inp_tax_office.setText(self.db.get_setting("company_tax_office", ""))
        self.inp_tax_number.setText(self.db.get_setting("company_tax_number", ""))
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
        for combo, key in (
            (self.cmb_document_printer, "print_document_printer"),
            (self.cmb_receipt_printer, "print_receipt_printer"),
            (self.cmb_label_printer, "print_label_printer"),
        ):
            index = combo.findData(self.db.get_setting(key, ""))
            combo.setCurrentIndex(max(index, 0))
        page_size = self.db.get_setting("print_document_page_size", "A4")
        page_index = self.cmb_document_page_size.findText(page_size)
        self.cmb_document_page_size.setCurrentIndex(max(page_index, 0))
        orientation = self.db.get_setting(
            "print_document_orientation", "portrait"
        )
        orientation_index = self.cmb_document_orientation.findData(orientation)
        self.cmb_document_orientation.setCurrentIndex(max(orientation_index, 0))
        label_width = self.db.get_setting("print_label_width_mm", "70")
        label_height = self.db.get_setting("print_label_height_mm", "45")
        self.inp_label_size.setText(f"{label_width}x{label_height}")
        self.txt_address.setText(self.db.get_setting("company_address", ""))
        self.txt_contract.setText(self.db.get_setting("service_contract", ""))
        offer_contract = self.db.get_setting("offer_contract", "")
        if not str(offer_contract or "").strip():
            offer_contract = self._default_offer_contract()
        self.txt_offer_contract.setText(offer_contract)
        self.inp_scroll_text.setText(self.db.get_setting("marquee_text", ""))

        current_theme = self.db.get_setting("color_theme_full", "")
        idx = self.cmb_theme.findText(current_theme)
        if idx >= 0:
            self.cmb_theme.setCurrentIndex(idx)

        curr = CurrencyHelper.get_code(self.db)
        CurrencyHelper.set_combo_to_code(self.cmb_currency, curr)

        # Para birimi hassasiyetini yükle
        precision = self.db.get_setting("currency_precision", "2")
        precision_idx = int(precision) if precision.isdigit() else 2
        if precision_idx > 3:
            precision_idx = 3
        self.cmb_currency_precision.setCurrentIndex(precision_idx)

        # Online \u00f6deme durumunu y\u00fckle
        online_payment = self.db.get_setting("online_payment_active", "1")
        self.cmb_online_payment.setCurrentIndex(0 if online_payment == "1" else 1)

    def _refresh_main_window_branding(self):
        if not self.main_window:
            return
        try:
            logo_path = self.db.get_setting("logo_path", "") or ""
            company_name = self.db.get_setting("company_name", "AYEC Pro") or "AYEC Pro"
            site_title = self.db.get_setting("site_title", "") or ""
            side_menu = getattr(getattr(self.main_window, "app_sidebar", None), "side_menu", None)
            if side_menu and hasattr(side_menu, "update_branding"):
                side_menu.update_branding(logo_path, company_name, site_title)
            if hasattr(self.main_window, "refresh_side_menu"):
                self.main_window.refresh_side_menu()
        except Exception:
            pass

    def save_data(self, close_dialog=False):
        self.db.set_setting("company_name", self.inp_name.text())
        self.db.set_setting("company_email", self.inp_email.text())
        self.db.set_setting(
            "company_authorized_person", self.inp_authorized_person.text()
        )
        self.db.set_setting("company_tax_office", self.inp_tax_office.text())
        self.db.set_setting("company_tax_number", self.inp_tax_number.text())
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
        self.db.set_setting(
            "print_document_printer",
            self.cmb_document_printer.currentData() or "",
        )
        self.db.set_setting(
            "print_receipt_printer",
            self.cmb_receipt_printer.currentData() or "",
        )
        self.db.set_setting(
            "print_label_printer",
            self.cmb_label_printer.currentData() or "",
        )
        self.db.set_setting(
            "print_document_page_size",
            self.cmb_document_page_size.currentText(),
        )
        self.db.set_setting(
            "print_document_orientation",
            self.cmb_document_orientation.currentData() or "portrait",
        )
        label_size = self.inp_label_size.text().lower().replace(" ", "")
        try:
            label_width, label_height = label_size.split("x", 1)
            if float(label_width) <= 0 or float(label_height) <= 0:
                raise ValueError
        except (TypeError, ValueError):
            label_width, label_height = "70", "45"
        self.db.set_setting("print_label_width_mm", str(label_width))
        self.db.set_setting("print_label_height_mm", str(label_height))
        self.db.set_setting("company_address", self.txt_address.toPlainText())
        try:
            self.db.cursor.execute("DELETE FROM company_info")
            self.db.cursor.execute(
                "INSERT INTO company_info "
                "(company_name, authorized_person, phone, email, address, tax_office, tax_number) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    self.inp_name.text().strip(),
                    self.inp_authorized_person.text().strip(),
                    self.inp_phone.text().strip() or self.inp_gsm.text().strip(),
                    self.inp_email.text().strip(),
                    self.txt_address.toPlainText().strip(),
                    self.inp_tax_office.text().strip(),
                    self.inp_tax_number.text().strip(),
                ),
            )
            self.db.conn.commit()
        except Exception:
            pass
        self.db.set_setting("service_contract", self.txt_contract.toPlainText())
        self.db.set_setting("offer_contract", self.txt_offer_contract.toPlainText())
        self.db.set_setting("marquee_text", self.inp_scroll_text.text())
        CurrencyHelper.persist_code(self.db, self.cmb_currency.currentText())

        # Para birimi hassasiyetini kaydet
        precision_idx = self.cmb_currency_precision.currentIndex()
        self.db.set_setting("currency_precision", str(precision_idx))

        # Online \u00f6deme durumunu kaydet
        self.db.set_setting("online_payment_active", "1" if self.cmb_online_payment.currentIndex() == 0 else "0")

        new_theme = self.cmb_theme.currentText()
        old_theme = self.db.get_setting("color_theme_full", "Koyu Modern")
        if new_theme != old_theme:
            self.db.set_setting("color_theme_full", new_theme)
            if self.main_window and hasattr(self.main_window, 'apply_theme'):
                self.main_window.apply_theme(new_theme)

        self._refresh_main_window_branding()
        if self.main_window and hasattr(self.main_window, "refresh_currency_context"):
            self.main_window.refresh_currency_context()

        if self.main_window:
            self.main_window.show_notification("Firma bilgileri guncellendi.", "success")
        else:
            message_helper.show_info(self, "Basarili", "Firma bilgileri guncellendi.")
        if close_dialog:
            self.accept()
