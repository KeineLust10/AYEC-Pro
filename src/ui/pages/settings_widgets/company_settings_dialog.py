# -*- coding: utf-8 -*-

"""
Company Settings Dialog
Firma ayarları düzenleme dialog'u
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
                             QScrollArea, QFrame, QGridLayout, QTextEdit, QComboBox,
                             QHBoxLayout, QTabWidget)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import QSignalBlocker, Qt
from PyQt6.QtPrintSupport import QPrinterInfo

from src.utils.theme_manager import ThemeManager
from src.utils.theme_colors import theme_qss
from src.utils.currency_helper import CurrencyHelper
from src.utils import message_helper
from src.ui.dialogs.base_modern_dialog import BaseModernDialog
from src.ui.widgets.navigation_glyph import navigation_icon



class CompanySettingsDialog(BaseModernDialog):
    """Firma Ayarlarını Gir - Detaylı Düzenleme Dialog'u"""

    def __init__(self, db, main_window=None, parent=None):
        super().__init__(parent=parent, title="Firma Ayarlar\u0131n\u0131", width=865, height=558)
        self.setFont(QFont("Segoe UI", 9))
        header_layout = self.header.layout()
        header_layout.removeWidget(self.lbl_title)
        self.logo_label.setFixedSize(34, 34)
        self.logo_label.clear()
        self.logo_label.setText("AE")
        self.logo_label.setStyleSheet(
            "color: #38BDF8; background: #10243A; border: 1px solid #1E3A5F; "
            "border-radius: 9px; font-size: 10px; font-weight: 800;"
        )
        title_block = QWidget(self.header)
        title_block_layout = QVBoxLayout(title_block)
        title_block_layout.setContentsMargins(0, 0, 0, 0)
        title_block_layout.setSpacing(1)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(10)
        title_row.addWidget(self.lbl_title)
        self.lbl_title.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        system_badge = QLabel("SISTEM PARAMETRELERI")
        system_badge.setStyleSheet("color: #38BDF8; background: #10243A; border: 1px solid #1E3A5F; border-radius: 4px; padding: 3px 7px; font-size: 9px; font-weight: 700;")
        title_row.addWidget(system_badge)
        title_row.addStretch(1)
        title_block_layout.addLayout(title_row)
        subtitle = QLabel("Kurumsal kimlik, yazdirma donanimi, baglanti tercihleri ve mali parametreleri yonetin.")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 8px;")
        title_block_layout.addWidget(subtitle)
        header_layout.insertWidget(2, title_block, 1)
        escape_button = QPushButton("ESC")
        escape_button.setFixedSize(34, 24)
        escape_button.setStyleSheet(
            "QPushButton { color: #94A3B8; background: #172334; border: 1px solid #334155; "
            "border-radius: 4px; font-size: 9px; } QPushButton:hover { color: #38BDF8; border-color: #38BDF8; }"
        )
        escape_button.clicked.connect(self.reject)
        header_layout.insertWidget(header_layout.indexOf(self.btn_close), escape_button)
        self.db = db
        self.main_window = main_window
        self.set_wheel_scroll_enabled(True)
        self.setup_ui()
        self._wire_ui_signals()
        self.load_data()

    def setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        section_heading = QWidget()
        section_heading_layout = QHBoxLayout(section_heading)
        section_heading_layout.setContentsMargins(0, 0, 0, 0)
        section_title = QLabel("TEMEL F\u0130RMA B\u0130LG\u0130LER\u0130 & SOSYAL MEDYA")
        section_title.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        section_note = QLabel("G\u00f6r\u00fcnt\u00fclenen Ekran: IMAGE_9")
        section_note.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        section_note.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
        section_heading_layout.addWidget(section_title)
        section_heading_layout.addStretch(1)
        section_heading_layout.addWidget(section_note)
        content_layout.addWidget(section_heading)
        form_widget = QWidget()
        form_layout = QGridLayout(form_widget)
        form_layout.setContentsMargins(6, 4, 6, 8)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(4)
        for row in (2, 4, 6, 8, 10):
            form_layout.setRowMinimumHeight(row, 18)

        def add_field(label, row, col, widget):
            lbl = QLabel(label)
            lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            if isinstance(widget, (QLineEdit, QComboBox)):
                widget.setFixedHeight(28)
                widget.setProperty("skipThemeTransform", True)
                widget.setStyleSheet("QLineEdit, QComboBox { background: #FFFFFF; color: #243248; border: 1px solid #CBD5E1; border-radius: 5px; padding: 5px 7px; selection-background-color: #2563EB; selection-color: #FFFFFF; } QLineEdit:focus, QComboBox:focus { border: 1px solid #2563EB; }")
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

        for field, icon_name, color_token in (
            (self.inp_name, "building", "accent"),
            (self.inp_email, "message", "text_muted"),
            (self.inp_facebook, "link", "info"),
            (self.inp_instagram, "link", "warning"),
            (self.inp_youtube, "message", "danger"),
            (self.inp_website, "globe", "text_muted"),
            (self.inp_gsm, "phone", "text_muted"),
            (self.inp_fax, "document", "text_muted"),
            (self.inp_site_title, "document", "text_muted"),
            (self.inp_phone, "phone", "text_muted"),
            (self.inp_cargo, "truck", "text_muted"),
            (self.inp_cargo_no, "tag", "text_muted"),
        ):
            field.addAction(
                navigation_icon(icon_name, 14, color_token),
                QLineEdit.ActionPosition.LeadingPosition,
            )

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

        field_style = theme_qss("""
            QWidget { background-color: @surface; }
            QLabel { color: @text; }
            QFrame#ModernDialogCard QLineEdit,
            QFrame#ModernDialogCard QTextEdit,
            QFrame#ModernDialogCard QComboBox,
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #CBD5E1;
                border-radius: 5px;
                padding: 6px 8px;
                background-color: #FFFFFF;
                color: #243248;
                selection-background-color: #2563EB;
                selection-color: #FFFFFF;
            }
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                border: 1px solid #2563EB;
            }
        """)
        content_layout.addWidget(form_widget)
        content_widget.setStyleSheet(field_style)
        scroll.setWidget(content_widget)

        tabs = QTabWidget()
        tabs.setObjectName("companySettingsTabs")
        tabs.setMaximumHeight(412)
        tabs.setStyleSheet(theme_qss(
            "QTabWidget::pane { border: 1px solid @border; border-radius: 8px; background: @surface; } "
            "QTabBar::tab { padding: 9px 14px; background: @surface_alt; color: @text_muted; border: 1px solid @border; margin-right: 3px; } "
            "QTabBar::tab:selected { color: @accent; background: @surface; border-bottom: 2px solid @accent; font-weight: 700; }"
        ))
        self.settings_tabs = tabs
        tab_titles = (
            ("Genel & \u0130leti\u015fim", 0, 12),
            ("Sistem, Tema & Para Birimi", 12, 18),
            ("Yaz\u0131c\u0131 & Belge D\u00fczeni", 18, 24),
            ("Adres, Vergi & S\u00f6zle\u015fmeler", 24, 40),
        )
        tab_headers = (
            ("", ""),
            ("Sistem G\u00f6r\u00fcn\u00fcm\u00fc & Para Birimi Standartlar\u0131", "G\u00f6r\u00fcnt\u00fclenen Ekran: IMAGE_8"),
            ("Donan\u0131m S\u00fcr\u00fcc\u00fcleri ve Ka\u011f\u0131t Parametreleri", "G\u00f6r\u00fcnt\u00fclenen Ekran: IMAGE_8 & IMAGE_7"),
            ("Vergi Bilgileri, Adres ve Yasal \u015eartnameler", "G\u00f6r\u00fcnt\u00fclenen Ekran: IMAGE_6 & IMAGE_7"),
        )
        tab_layouts = []
        for index, (tab_title, _start, _end) in enumerate(tab_titles):
            if index == 0:
                tab_scroll = scroll
                tab_grid = form_layout
            else:
                tab_scroll = QScrollArea()
                tab_scroll.setWidgetResizable(True)
                tab_scroll.setFrameShape(QFrame.Shape.NoFrame)
                tab_content = QWidget()
                tab_content.setStyleSheet(field_style)
                tab_grid = QGridLayout(tab_content)
                tab_grid.setContentsMargins(12, 8, 12, 8)
                tab_grid.setHorizontalSpacing(14)
                tab_grid.setVerticalSpacing(4)
                tab_grid.setColumnStretch(0, 1)
                tab_grid.setColumnStretch(1, 1)
                heading = QWidget()
                heading.setStyleSheet(theme_qss(
                    "background: transparent; border: none; border-bottom: 1px solid @border;"
                ))
                heading_layout = QHBoxLayout(heading)
                heading_layout.setContentsMargins(0, 0, 0, 7)
                heading_layout.setSpacing(8)
                heading_title = QLabel(tab_headers[index][0].upper())
                heading_title.setStyleSheet(theme_qss(
                    "color: @text_muted; font-size: 10px; font-weight: 800; "
                    "letter-spacing: 0.5px; border: none; background: transparent;"
                ))
                heading_note = QLabel(tab_headers[index][1])
                heading_note.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                heading_note.setStyleSheet(theme_qss(
                    "color: @text_muted; font-size: 9px; border: none; background: transparent;"
                ))
                heading_layout.addWidget(heading_title)
                heading_layout.addStretch(1)
                heading_layout.addWidget(heading_note)
                tab_grid.addWidget(heading, 0, 0, 1, 2)
                tab_scroll.setWidget(tab_content)
            tab_layouts.append(tab_grid)
            tabs.addTab(tab_scroll, tab_title)

        items_by_tab = [[], [], [], []]
        while form_layout.count():
            row, col, row_span, col_span = form_layout.getItemPosition(0)
            item = form_layout.takeAt(0)
            widget = item.widget()
            if widget is None:
                continue
            if row < 12:
                tab_index, row_offset = 0, 0
            elif row < 18:
                tab_index, row_offset = 1, 12
            elif row < 24:
                tab_index, row_offset = 2, 18
            else:
                tab_index, row_offset = 3, 24
            items_by_tab[tab_index].append(
                (widget, row - row_offset, col, row_span, col_span)
            )

        for tab_index, (tab_layout, items) in enumerate(zip(tab_layouts, items_by_tab)):
            field_row = 1 if tab_index else 0
            field_col = 0
            index = 0
            while index < len(items):
                widget = items[index][0]
                if not isinstance(widget, QLabel) or index + 1 >= len(items):
                    tab_layout.addWidget(widget, field_row, field_col)
                    index += 1
                    continue
                control = items[index + 1][0]
                is_long_field = isinstance(control, QTextEdit) or control is self.inp_scroll_text
                span = 2 if is_long_field else 1
                tab_layout.addWidget(widget, field_row, field_col, 1, span)
                tab_layout.addWidget(
                    control,
                    field_row + 1,
                    field_col,
                    1,
                    span,
                )
                if is_long_field:
                    field_row += 2
                    field_col = 0
                elif field_col:
                    field_row += 2
                    field_col = 0
                else:
                    field_col = 1
                index += 2

        self.content_layout.setContentsMargins(12, 0, 16, 8)
        self.content_layout.setSpacing(8)
        self.content_layout.addWidget(tabs, 1)
        cancel_button = self.add_cancel_button("\u0130ptal")
        save_button = self.add_button("G\u00dcNCELLE", "success", lambda: self.save_data(close_dialog=True))
        self.footer_layout.insertStretch(0, 1)
        self.footer_layout.setContentsMargins(30, 0, 20, 0)
        cancel_button.setFixedSize(96, 36)
        save_button.setFixedSize(132, 36)
        save_button.setStyleSheet(
            save_button.styleSheet() + "QPushButton { font-size: 10px; }"
        )
        save_button.setIcon(navigation_icon("verified", 14, "selection_text"))
        self.footer.setFixedHeight(56)
        self.card.setProperty("skipThemeTransform", True)
        self.card.setStyleSheet(self.card.styleSheet() + "QFrame#ModernDialogCard QLineEdit, QFrame#ModernDialogCard QComboBox { background: #FFFFFF; color: #243248; border: 1px solid #CBD5E1; border-radius: 5px; padding: 5px 7px; } QFrame#ModernDialogCard QLineEdit:focus, QFrame#ModernDialogCard QComboBox:focus { border-color: #2563EB; }")
        self.card.setProperty("skipThemeTransform", False)

    def _wire_ui_signals(self): QLineEdit, QFrame#ModernDialogCard QComboBox { background: #FFFFFF; color: #243248; border: 1px solid #CBD5E1; border-radius: 5px; padding: 5px 7px; } QFrame#ModernDialogCard QLineEdit:focus, QFrame#ModernDialogCard QComboBox:focus { border-color: #2563EB; }"))

    def _wire_ui_signals(self):
        self.cmb_theme.currentIndexChanged.connect(self._preview_theme)
        self.cmb_currency.currentIndexChanged.connect(lambda: self.save_data(close_dialog=False))
        self.cmb_currency_precision.currentIndexChanged.connect(lambda: self.save_data(close_dialog=False))
        self.cmb_online_payment.currentIndexChanged.connect(lambda: self.save_data(close_dialog=False))

    def _preview_theme(self, _index=None):
        selected = ThemeManager.normalize_theme_name(self.cmb_theme.currentText())
        current = ThemeManager.normalize_theme_name(
            getattr(self.main_window, "_current_theme_name", "")
            or self.db.get_setting("color_theme_full", "Koyu Mavi")
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
        blockers = [
            QSignalBlocker(control)
            for control in (
                self.cmb_theme,
                self.cmb_currency,
                self.cmb_currency_precision,
                self.cmb_online_payment,
            )
        ]
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
        del blockers

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
