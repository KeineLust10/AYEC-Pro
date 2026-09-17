# -*- coding: utf-8 -*-

"""
Proforma PDF Dialog
Proforma PDF oluşturma dialog'u
"""
from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QGroupBox, QFormLayout,
                             QRadioButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction
from src.utils.theme_colors import theme_qss
from src.utils.toast_notification import show_success, show_error, show_warning
from src.utils.exchange_rate_manager import ExchangeRateManager
from src.utils.logger import logger
from src.ui.widgets.modern_dialog import ModernDialog
import os
from datetime import datetime




class ProformaDialog(ModernDialog):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    """Proforma PDF seçenekleri dialog"""
    
    def __init__(
        self,
        parent,
        db,
        cart_items,
        totals,
        customer_name,
        currency_mode="TL",
        exchange_rate=None,
        totals_in_selected_currency=False,
        totals_try=None,
        parent_currency="TRY",
        customer_id=None,
        customer_company="",
        initial_company="",
        initial_project="",
        preferred_template="",
        source="proforma",
        existing_offer_id=None,
        existing_offer_no="",
        include_approval=True,
    ):
        super().__init__(title="Proforma PDF Olustur", parent=parent, width=920, height=700)
        self.db = db
        self.cart_items = cart_items
        self.totals = totals
        self.totals_try = totals_try
        self.parent_currency = parent_currency
        self.customer_name = customer_name
        self.currency_mode = currency_mode
        self.exchange_rate = exchange_rate
        self.totals_in_selected_currency = totals_in_selected_currency
        self.customer_id = customer_id
        self.customer_company = customer_company
        self.initial_company = initial_company
        self.initial_project = initial_project
        self.preferred_template = preferred_template
        self.source = source
        self.existing_offer_id = existing_offer_id
        self.existing_offer_no = str(existing_offer_no or "").strip()
        self.include_approval = bool(include_approval)
        self.setWindowTitle("Proforma PDF Oluştur")
        self.set_footer_visible(False)
        self.init_ui()

    def _company_setting(self, key, default=""):
        try:
            return str(self.db.get_setting(key, default) or default).strip()
        except Exception:
            return str(default or "").strip()

    def _peek_reference_no(self):
        prefix = str(self.db.get_setting("reference_number_prefix", "REF") or "REF").strip() or "REF"
        next_raw = str(self.db.get_setting("reference_number_next", "1") or "1").strip()
        next_number = int(next_raw) if next_raw.isdigit() else 1
        return f"{prefix}{next_number}"

    def _consume_reference_no(self):
        if hasattr(self.db, "get_next_reference_number"):
            return self.db.get_next_reference_number()
        return self._peek_reference_no()

    def _normalized_totals(self):
        """
        Normalize totals from different caller formats.

        Supported formats:
        - New/expected: (subtotal, discount, vat_rate, vat_amount, total)
        - Legacy transaction page: (subtotal, discount, vat_amount, total, net)
        """
        raw = self.totals_try if self.totals_try else self.totals
        if not raw or len(raw) < 5:
            return 0.0, 0.0, 0.0, 0.0, 0.0

        subtotal = float(raw[0] or 0)
        discount = float(raw[1] or 0)
        third = float(raw[2] or 0)
        fourth = float(raw[3] or 0)
        fifth = float(raw[4] or 0)

        # Expected shape: vat_rate is a ratio between 0 and 1.
        if 0 <= third <= 1:
            vat_rate = third
            vat_amount = fourth
            total = fifth
            return subtotal, discount, vat_rate, vat_amount, total

        # Legacy shape: (subtotal, discount, vat_amount, total, net)
        vat_amount = third
        total = fourth
        net = fifth
        vat_rate = (vat_amount / net) if net else 0.0
        return subtotal, discount, vat_rate, vat_amount, total
    
    def init_ui(self):
        layout = self.content_layout
        layout.setSpacing(24)
        layout.setContentsMargins(34, 34, 34, 34)
        
        # Başlık ve İkon
        header_layout = QHBoxLayout()
        icon_label = QLabel("📄")
        icon_label.setFont(QFont("Segoe UI", 32))
        
        title_vbox = QVBoxLayout()
        header = QLabel("PROFORMA PDF OLUŞTUR")
        header.setObjectName("PageTitle")
        sub_header = QLabel("Müşteri bilgisi ve tasarım şablonunu seçiniz")
        sub_header.setObjectName("PageSubtitle")
        
        title_vbox.addWidget(header)
        title_vbox.addWidget(sub_header)
        
        header_layout.addWidget(icon_label)
        header_layout.addLayout(title_vbox)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # --- Form Alanı ---
        form_group = QGroupBox("Teklif Bilgileri")
        form_layout = QFormLayout()
        form_layout.setSpacing(18)
        form_layout.setHorizontalSpacing(18)
        form_layout.setVerticalSpacing(16)
        
        company = (
            self._company_setting("company_name")
            or self.initial_company
            or self.customer_company
            or ""
        ).strip()
        self.inp_company = QLineEdit(company)
        self.inp_company.setMinimumHeight(38)
        self.inp_company.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @border; border-radius: 4px;"))
        form_layout.addRow("Firma:", self.inp_company)
        
        cust = self.customer_name if self.customer_name and self.customer_name != "Müşteri Seçin..." else ""
        self.inp_customer = QLineEdit(cust)
        self.inp_customer.setMinimumHeight(38)
        self.inp_customer.setPlaceholderText("Yetkili kişi adı / soyadı...")
        self.inp_customer.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @accent; border-radius: 4px; font-weight: bold;"))
        form_layout.addRow("Yetkili:", self.inp_customer)

        self.inp_project = QLineEdit()
        self.inp_project.setMinimumHeight(38)
        self.inp_project.setText((self.initial_project or "").strip())
        self.inp_project.setPlaceholderText("Proje adını giriniz...")
        self.inp_project.setStyleSheet(theme_qss("padding: 8px; border: 1px solid @border; border-radius: 4px;"))
        form_layout.addRow("Proje Adı:", self.inp_project)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # --- Para Birimi Seçimi ---
        cur_group = QGroupBox("Teklif Para Birimi")
        cur_layout = QHBoxLayout()
        cur_layout.setContentsMargins(14, 12, 14, 12)
        cur_layout.setSpacing(24)
        self.rb_tl = QRadioButton("Türk Lirası (₺)")
        self.rb_usd = QRadioButton("Amerikan Doları ($)")
        self.rb_eur = QRadioButton("Euro (€)")
        
        if self.currency_mode == "USD":
            self.rb_usd.setChecked(True)
        elif self.currency_mode == "EUR":
            self.rb_eur.setChecked(True)
        else:
            self.rb_tl.setChecked(True)
        
        # Stil
        for rb in [self.rb_tl, self.rb_usd, self.rb_eur]:
            rb.setStyleSheet(theme_qss("font-size: 13px; padding: 5px;"))
            rb.toggled.connect(self.update_summary)
            
        cur_layout.addWidget(self.rb_tl)
        cur_layout.addWidget(self.rb_usd)
        cur_layout.addWidget(self.rb_eur)
        cur_group.setLayout(cur_layout)
        layout.addWidget(cur_group)

        # --- Şablon Seçimi (Radio Buttons) ---
        tpl_group = QGroupBox("Tasarım Şablonu Seçiniz")
        tpl_layout = QHBoxLayout()
        tpl_layout.setContentsMargins(14, 12, 14, 12)
        tpl_layout.setSpacing(22)
        
        self.rb_modern = QRadioButton("Modern (Premium)")
        self.rb_modern.setChecked(True)
        self.rb_classic = QRadioButton("Kurumsal (Premium)")
        self.rb_simple = QRadioButton("Zebra (Premium)")
        self.rb_bulut_deri = QRadioButton("AYEC Pro (Yeni Taslak)")
        self.rb_custom = QRadioButton("⭐ Kendi Şablonum")
        self.rb_editor = QRadioButton("✏️ Editör Şablonum")
        
        # Stil
        for rb in [self.rb_modern, self.rb_classic, self.rb_simple, self.rb_bulut_deri, self.rb_custom, self.rb_editor]:
            rb.setStyleSheet(theme_qss("font-size: 13px; padding: 5px;"))
        
        tpl_layout.addWidget(self.rb_modern)
        tpl_layout.addWidget(self.rb_classic)
        tpl_layout.addWidget(self.rb_simple)
        tpl_layout.addWidget(self.rb_bulut_deri)
        
        # Only show custom template option if a PDF template is configured
        custom_template_path = self.db.get_setting('proforma_template_path', '')
        if custom_template_path and os.path.exists(custom_template_path) and custom_template_path.lower().endswith('.pdf'):
            self.rb_custom.setToolTip(f"Şablon: {custom_template_path}")
            tpl_layout.addWidget(self.rb_custom)

        # Only show editor template option when a saved editor template exists
        from src.utils.custom_editor_proforma import SETTING_TEMPLATE_HTML, SETTING_USE_CUSTOM
        editor_html = str(self.db.get_setting(SETTING_TEMPLATE_HTML, '') or '').strip()
        editor_active = str(self.db.get_setting(SETTING_USE_CUSTOM, '0') or '0').strip() in {'1', 'true', 'True'}
        if editor_html:
            self.rb_editor.setToolTip("Ayarlar > Proforma \u015eablon Edit\u00f6r\u00fc ile haz\u0131rlanan \u015fablon")
            tpl_layout.addWidget(self.rb_editor)

        if self.preferred_template == "bulut_deri":
            self.rb_bulut_deri.setChecked(True)
        elif self.preferred_template == "corporate":
            self.rb_classic.setChecked(True)
        elif self.preferred_template == "minimal":
            self.rb_simple.setChecked(True)
        elif self.preferred_template == "custom_template" and custom_template_path and os.path.exists(custom_template_path) and custom_template_path.lower().endswith('.pdf'):
            self.rb_custom.setChecked(True)
        elif self.preferred_template == "editor_template" and editor_html:
            self.rb_editor.setChecked(True)
        elif editor_active and editor_html and not self.preferred_template:
            self.rb_editor.setChecked(True)
        
        tpl_group.setLayout(tpl_layout)
        layout.addWidget(tpl_group)
        
        # Özet
        self.summary_label = QLabel()
        self.summary_label.setMinimumHeight(86)
        layout.addWidget(self.summary_label)
        self.update_summary()
        
        # Butonlar
        btn_layout = QHBoxLayout()
        
        btn_cancel = QPushButton("İptal")
        btn_cancel.setMinimumHeight(48)
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.setStyleSheet(theme_qss("""
            QPushButton { background-color: @disabled_text; color: white; padding: 12px; border-radius: 6px; border: none; font-weight: bold; }
            QPushButton:hover { background-color: @text_muted; }
        """))
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_create = QPushButton("\U0001f4c4 PDF OLU\u015eTUR")
        self.btn_create.setMinimumHeight(48)
        self.btn_create.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_create.setStyleSheet(theme_qss("""
            QPushButton { background-color: @accent_hover; color: white; padding: 12px; border-radius: 6px; border: none; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: @accent; }
        """))
        self.btn_create.clicked.connect(self.generate_pdf)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_create)
        
        layout.addLayout(btn_layout)

    def update_summary(self):
        """Özet bilgisini güncelle"""
        subtotal_try, discount_try, vat_rate, vat_amount_try, total_try = self._normalized_totals()
        
        rate = 1.0
        currency_code = "TRY"
        symbol = "₺"
        
        if self.rb_usd.isChecked():
            currency_code = "USD"
            symbol = "$"
        elif self.rb_eur.isChecked():
            currency_code = "EUR"
            symbol = "€"
            
        if currency_code != "TRY":
            rate = ExchangeRateManager.get_current_rate(self.db, currency_code) or 1.0
            
        # Convert values
        c_subtotal = subtotal_try if currency_code == "TRY" else (subtotal_try / rate)
        c_vat_amount = vat_amount_try if currency_code == "TRY" else (vat_amount_try / rate)
        c_total = total_try if currency_code == "TRY" else (total_try / rate)
        
        rate_info = f"<span style='color: gray; font-size: 10px;'> (Kur: 1 {symbol} = {rate:.2f} ₺)</span>" if rate != 1.0 else ""
        
        summary_html = f"""
        <div style='background-color: whitesmoke; padding: 10px; border-radius: 5px; border: 1px solid lightgray;'>
            <table width='100%'>
                <tr><td style='color: black;'>Kalem Sayısı:</td><td align='right' style='color: black;'><b>{len(self.cart_items)}</b></td></tr>
                <tr><td style='color: black;'>Ara Toplam:</td><td align='right' style='color: black;'>{c_subtotal:,.2f} {symbol}</td></tr>
                <tr><td style='color: black;'>KDV Tutarı:</td><td align='right' style='color: black;'>{c_vat_amount:,.2f} {symbol}</td></tr>
                <tr><td style='font-size:14px; color:green;'><b>TOPLAM:</b></td><td align='right' style='font-size:14px; color:green;'><b>{c_total:,.2f} {symbol}</b> {rate_info}</td></tr>
            </table>
        </div>
        """

        self.summary_label.setText(summary_html)
    
    def generate_pdf(self):
        """PDF oluştur"""
        try:
            company = self.inp_company.text().strip()
            customer = self.inp_customer.text().strip()
            project_name = self.inp_project.text().strip()
            
            if not company:
                show_warning(self, "Lütfen firma adı giriniz!")
                return

            if not customer:
                show_warning(self, "Lütfen yetkili adı giriniz!")
                return

            if not project_name:
                show_warning(self, "Lütfen proje adını giriniz!")
                return

            # Auto-save logic
            downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
            save_folder = os.path.join(downloads_path, "AYECPro_Belgeler", 
                                     "".join([c for c in company if c.isalnum() or c in (' ', '_', '-')]).strip())
            
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)
                
            # Şablon seçimi
            if self.rb_editor.isChecked():
                template = "editor_template"
            elif self.rb_custom.isChecked():
                template = "custom_template"
            elif self.rb_bulut_deri.isChecked():
                template = "bulut_deri"
            elif self.rb_modern.isChecked(): 
                template = "modern"
            elif self.rb_classic.isChecked(): 
                template = "corporate"
            else:
                template = "minimal"

            reference_no = self.existing_offer_no or self._consume_reference_no()
            offer_created_at = datetime.now().isoformat(timespec="seconds")
            
            file_name = os.path.join(save_folder, 
                                    f"Proforma_{reference_no}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

            # Para birimi ve kur dönüşüm mantığı
            subtotal_try, discount_try, vat_rate, vat_amount_try, total_try = self._normalized_totals()
            rate = 1.0
            currency_code = "TRY"
            currency_symbol = "₺"

            if self.rb_usd.isChecked():
                currency_code = "USD"
                currency_symbol = "$"
            elif self.rb_eur.isChecked():
                currency_code = "EUR"
                currency_symbol = "€"

            if currency_code != "TRY":
                rate = ExchangeRateManager.get_current_rate(self.db, currency_code) or 1.0

            conv_totals = (
                subtotal_try if currency_code == "TRY" else (subtotal_try / rate),
                discount_try if currency_code == "TRY" else (discount_try / rate),
                vat_rate,
                vat_amount_try if currency_code == "TRY" else (vat_amount_try / rate),
                total_try if currency_code == "TRY" else (total_try / rate)
            )
            try_totals = (
                subtotal_try,
                discount_try,
                vat_rate,
                vat_amount_try,
                total_try,
            )

            # Convert cart items (Prices)
            conv_cart_items = []
            for item in self.cart_items:
                c_item = item.copy()
                base_price = item.get('price', 0.0)
                c_item['price'] = float(base_price) if currency_code == "TRY" else (float(base_price) / rate if rate else float(base_price))
                conv_cart_items.append(c_item)

            from src.ui.utils.background_task import run_cancellable_task

            def produce_pdf(is_cancelled):
                if is_cancelled():
                    return False, "cancelled"
                from src.utils.pdf_manager import PDFManagerQt

                pdf_manager = PDFManagerQt(self.db)
                if template == "editor_template":
                    from src.utils.custom_editor_proforma import build_custom_editor_proforma
                    return build_custom_editor_proforma(
                        pdf_manager,
                        cart_items=conv_cart_items,
                        totals=conv_totals,
                        company_name=company,
                        customer_name=customer,
                        save_path=file_name,
                        currency=currency_symbol,
                        project_name=project_name,
                        contact_name=customer,
                        reference_no=reference_no,
                        offer_date=offer_created_at,
                        customer_company=self.customer_company,
                        currency_code=currency_code,
                        totals_try=try_totals,
                        include_approval=self.include_approval,
                    )
                if template == "custom_template":
                    return pdf_manager.create_proforma_overlay(
                        cart_items=conv_cart_items,
                        totals=conv_totals,
                        company_name=company,
                        customer_name=customer,
                        save_path=file_name,
                        currency=currency_symbol,
                    )
                return pdf_manager.create_proforma(
                    template_type=template,
                    cart_items=conv_cart_items,
                    totals=conv_totals,
                    company_name=company,
                    customer_name=customer,
                    project_name=project_name,
                    contact_name=customer,
                    reference_no=reference_no,
                    offer_date=offer_created_at,
                    customer_company=self.customer_company,
                    currency_code=currency_code,
                    save_path=file_name,
                    currency=currency_symbol,
                    totals_try=try_totals,
                    exchange_rate=rate,
                    include_approval=self.include_approval,
                )

            def pdf_ready(worker_result):
                success, result = worker_result
                if not success:
                    show_error(
                        self,
                        f"PDF olu\u015fturulamad\u0131:\n{result}",
                    )
                    return
                self._save_offer_record(
                    offer_no=reference_no,
                    company=company,
                    customer=customer,
                    project_name=project_name,
                    template=template,
                    currency_code=currency_code,
                    currency_symbol=currency_symbol,
                    rate=rate,
                    totals=conv_totals,
                    totals_try=try_totals,
                    items=conv_cart_items,
                    pdf_path=file_name,
                )
                if self.existing_offer_id and self.parent():
                    try:
                        self.parent()._editing_offer_id = None
                        self.parent()._editing_offer_no = ""
                    except Exception:
                        pass
                try:
                    os.startfile(file_name)
                except Exception as exc:
                    logger.debug(
                        f"ProformaDialog auto-open skipped: {exc}"
                    )
                self.accept()

            self.btn_create.setEnabled(False)
            run_cancellable_task(
                owner=self,
                title="PDF olu\u015fturuluyor...",
                target=produce_pdf,
                on_success=pdf_ready,
                on_error=lambda message: show_error(
                    self,
                    f"PDF olu\u015fturulamad\u0131:\n{message}",
                ),
                on_done=lambda: self.btn_create.setEnabled(True),
                output_path=file_name,
            )
                
        except ImportError as e:
            show_error(self, f"PDF modülü yüklenemedi:\n{e}")
        except Exception as e:
            show_error(self, f"Hata: {e}")

    def _save_offer_record(
        self,
        offer_no,
        company,
        customer,
        project_name,
        template,
        currency_code,
        currency_symbol,
        rate,
        totals,
        totals_try,
        items,
        pdf_path,
    ):
        if not hasattr(self.db, "save_offer_record"):
            return
        try:
            subtotal, discount, vat_rate, vat_amount, total = totals
            subtotal_try, discount_try, _try_vat_rate, vat_amount_try, total_try = totals_try
            parent_page = self.parent()
            main_window = getattr(parent_page, "main_window", None)
            created_by = str(
                getattr(main_window, "username", "")
                or getattr(parent_page, "username", "")
                or self.db.get_setting("last_login_user", "")
                or ""
            ).strip()
            self.db.save_offer_record(
                {
                    "offer_id": self.existing_offer_id,
                    "offer_no": offer_no,
                    "customer_id": self.customer_id,
                    "customer_name": self.customer_name,
                    "company_name": company,
                    "contact_name": customer,
                    "project_name": project_name,
                    "template_type": template,
                    "currency_code": currency_code,
                    "currency_symbol": currency_symbol,
                    "exchange_rate": rate,
                    "totals": {
                        "subtotal": subtotal,
                        "discount": discount,
                        "vat_rate": vat_rate,
                        "vat_amount": vat_amount,
                        "total": total,
                    },
                    "totals_try": {
                        "subtotal": subtotal_try,
                        "discount": discount_try,
                        "vat_rate": vat_rate,
                        "vat_amount": vat_amount_try,
                        "total": total_try,
                    },
                    "status": "created",
                    "source": self.source,
                    "created_by": created_by,
                    "pdf_path": pdf_path,
                    "include_approval": self.include_approval,
                    "items": items,
                }
            )
        except Exception as e:
            logger.error(f"Offer save skipped: {e}")


    def _wire_ui_signals(self):
        self.rb_tl.toggled.connect(self._on_ui_widget_changed)
        self.rb_usd.toggled.connect(self._on_ui_widget_changed)
        self.rb_eur.toggled.connect(self._on_ui_widget_changed)
        self.rb_modern.toggled.connect(self._on_ui_widget_changed)
        self.rb_classic.toggled.connect(self._on_ui_widget_changed)
        self.rb_simple.toggled.connect(self._on_ui_widget_changed)
        self.rb_bulut_deri.toggled.connect(self._on_ui_widget_changed)
        self.rb_custom.toggled.connect(self._on_ui_widget_changed)
        self.rb_editor.toggled.connect(self._on_ui_widget_changed)
