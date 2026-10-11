# -*- coding: utf-8 -*-

"""
License Management Widget
Lisans yönetimi widget'ı
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGroupBox, QLineEdit, QApplication,
                             QSizePolicy, QGridLayout)
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtGui import QFont, QAction
from src.utils.security_manager import SecurityManager
from src.utils.theme_colors import theme_qss
from src.utils.design_system import DesignTokens


class LicenseManagementWidget(QWidget):
    """Lisans Yönetimi Sekmesi (Kurumsal Adım 3)"""
    
    def __init__(self, db, main_window):
        super().__init__()
        self.db = db
        self.main_window = main_window
        self._license_expires_str = ""
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._update_countdown)
        self.setup_ui()
        self.refresh_license_info()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        title = QLabel("[SECURE] Lisans Y\u00f6netimi & G\u00fcvenlik Matrisi")
        title.setFont(QFont(DesignTokens.FONT_NAME, 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text; background: transparent; border: none;"))
        header_row = QHBoxLayout()
        header_row.addWidget(title)
        header_row.addStretch()
        layout.addLayout(header_row)
        actions_row = QHBoxLayout()
        actions_row.addStretch()
        for button_text in ("Mali Belgelerim", "Lisans Transferi", "Sureyi Uzat"):
            header_button = QPushButton(button_text)
            header_button.setStyleSheet(theme_qss("background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 6px; padding: 7px 12px;"))
            header_button.clicked.connect(self.request_license)
            actions_row.addWidget(header_button)
        layout.addLayout(actions_row)
        subtitle = QLabel("Saha terminal donanimi, HWID, model abonelikleri ve banka mutabakat merkezi")
        subtitle.setStyleSheet(theme_qss("color: @text_muted; font-size: 11px; background: transparent; border: none;"))
        layout.addWidget(subtitle)

        # Status Card
        self.status_card = QFrame()
        self.status_card.setStyleSheet(theme_qss(
            "QFrame { background-color: @surface; border-radius: 10px; "
            "border: 1px solid @border; }"
        ))
        card_layout = QVBoxLayout(self.status_card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(12)

        self.lbl_status = QLabel("Durum: Yükleniyor...")
        self.lbl_status.setFont(QFont(DesignTokens.FONT_NAME, 12, QFont.Weight.Bold))
        self.lbl_status.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_status.setMinimumHeight(28)
        card_layout.addWidget(self.lbl_status)

        self.lbl_details = QLabel("Lisans Türü: -\nGeçerlilik: -\nKalan Gün: -")
        self.lbl_details.setWordWrap(True)
        self.lbl_details.setMinimumHeight(58)
        self.lbl_details.setStyleSheet(theme_qss(
            "color: @text_muted; font-size: 10pt;"
        ))
        card_layout.addWidget(self.lbl_details)

        # Countdown label – visible only when license is active
        self.lbl_countdown = QLabel("")
        self.lbl_countdown.setFont(QFont(DesignTokens.MONO_FONT_NAME, 13, QFont.Weight.Bold))
        self.lbl_countdown.setStyleSheet(
            "color: #27ae60; font-size: 14pt; padding-top: 6px;"
        )
        self.lbl_countdown.setVisible(False)
        card_layout.addWidget(self.lbl_countdown)

        layout.addWidget(self.status_card)

        # HWID Display
        self.hwid_box = QFrame()
        self.hwid_box.setStyleSheet(theme_qss(
            "QFrame { background-color: @surface_alt; border-radius: 6px; border: 1px solid @border; }"
        ))
        hwid_layout = QHBoxLayout(self.hwid_box)
        hwid_layout.setContentsMargins(20, 14, 20, 14)
        hwid_layout.setSpacing(12)
        self.lbl_hwid = QLabel(
            f"<b>Cihaz Kimliği (HWID):</b> {SecurityManager.get_hwid()[:16]}..."
        )
        self.lbl_hwid.setTextFormat(Qt.TextFormat.RichText)
        self.lbl_hwid.setWordWrap(True)
        self.lbl_hwid.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn_copy = QPushButton("Kopyala")
        btn_copy.setFixedWidth(80)
        btn_copy.setMinimumHeight(36)
        btn_copy.clicked.connect(self.copy_hwid)
        hwid_layout.addWidget(self.lbl_hwid)
        hwid_layout.addStretch()
        hwid_layout.addWidget(btn_copy)
        layout.addWidget(self.hwid_box)

        # License Key Entry
        entry_group = QGroupBox("Yeni Lisans Anahtarı Ekle")
        entry_group.setMinimumHeight(104)
        entry_group.setStyleSheet(theme_qss("""
            QGroupBox {
                background-color: @surface_alt;
                border: 1px solid @border;
                border-radius: 8px;
                margin-top: 18px;
                padding-top: 18px;
                font-weight: 700;
                color: @text;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
        """))
        entry_layout = QVBoxLayout(entry_group)
        entry_layout.setContentsMargins(10, 18, 10, 10)
        entry_layout.setSpacing(8)
        
        self.inp_key = QLineEdit()
        self.inp_key.setPlaceholderText("Lisans anahtarınızı buraya yapıştırın...")
        self.inp_key.setMinimumHeight(34)
        entry_layout.addWidget(self.inp_key)
        
        btn_activate = QPushButton("✅ Lisansı Etkinleştir")
        btn_activate.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @success;
                color: @selection_text;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        btn_activate.setMinimumHeight(38)
        btn_activate.clicked.connect(self.activate_license)
        entry_layout.addWidget(btn_activate)

        layout.addWidget(entry_group)

        packages = QGridLayout()
        packages.setSpacing(8)
        self.plan_cards = []
        for column, (plan_code, tag, name, price, detail, color, features) in enumerate((
            ("monthly", "BASLANGIC", "Aylik Esnek", "990 TL / Ay", "1 Teknisyen Hesabi", "@finance_primary", ("Standart servis fisi modulu", "SMS gonderim altyapisi", "Santiye ve saha haritasi pasif")),
            ("six_months", "AVANTAJLI", "6 Aylik Avantaj", "5.490 TL", "5 Teknisyen & 1 Atolye", "@finance_secondary", ("WhatsApp & SMS entegrasyonu", "Stok ve kritik parca alarmi", "Haftalik otomatik bulut yedek")),
            ("one_year", "EN COK TERCIH", "1 Yillik Profesyonel", "9.900 TL", "Sinirsiz Teknisyen & Kullanici", "@finance_tertiary", ("Sinirsiz teknisyen ve kullanici", "Canli saha GPS harita takibi", "Gunluk sifreli harici bulut yedek")),
            ("three_years", "VIP DESTEK", "3 Yillik Kurumsal", "24.900 TL", "Tum v2.x ve v3.0 guncellemeleri", "@warning", ("Tum guncellemeler ucretsiz", "7/24 ozel kendini mudahale destegi", "Coklu sube ve konsolide mali raporlama")),
        )):
            package = QFrame()
            package.setStyleSheet(theme_qss(f"""
                QFrame {{ background: @finance_surface_alt; border: 1px solid @finance_outline; border-top: 3px solid {color}; border-radius: 7px; }}
                QLabel {{ border: none; }}
                QPushButton {{ background: @finance_surface_high; color: @finance_text; border: 1px solid @finance_outline; border-radius: 5px; padding: 7px; font-weight: 700; }}
                QPushButton:hover {{ background: {color}; color: @selection_text; }}
            """))
            package_layout = QVBoxLayout(package)
            package_layout.setContentsMargins(10, 8, 10, 8)
            package_tag = QLabel(tag)
            package_tag.setStyleSheet(theme_qss(f"color: {color}; font-size: 10px; font-weight: 800;"))
            package_name = QLabel(name)
            package_name.setWordWrap(True)
            package_name.setStyleSheet(theme_qss("color: @finance_text; font-size: 14px; font-weight: 800;"))
            package_price = QLabel(price)
            package_price.setFont(QFont(DesignTokens.MONO_FONT_NAME, 14, QFont.Weight.Bold))
            package_price.setTextFormat(Qt.TextFormat.PlainText)
            package_price.setToolTip(price)
            package_price.setStyleSheet(theme_qss("color: @finance_text; font-size: 17px; font-weight: 800;"))
            package_detail = QLabel(detail)
            package_detail.setWordWrap(True)
            package_detail.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 10px;"))
            choose = QPushButton("Paketi Sec")
            choose.setText("Paketi Se\u00e7 ve \u00d6deme Ad\u0131m\u0131na Ge\u00e7")
            choose.clicked.connect(
                lambda _checked=False, code=plan_code: self.open_plan_checkout(code)
            )
            package_layout.addWidget(package_tag); package_layout.addWidget(package_name)
            package_layout.addWidget(package_price); package_layout.addWidget(package_detail); package_layout.addWidget(choose)
            for feature in features:
                feature_label = QLabel("+ " + feature)
                feature_label.setWordWrap(True)
                feature_label.setStyleSheet(theme_qss("color: @finance_text_muted; font-size: 9px;"))
                package_layout.insertWidget(package_layout.count() - 1, feature_label)
            packages.addWidget(package, column // 2, column % 2)
            self.plan_cards.append(choose)
        layout.addLayout(packages)

        payment_grid = QGridLayout()
        payment_grid.setSpacing(10)
        bank_card = QFrame()
        bank_card.setStyleSheet(theme_qss(
            "QFrame { background: @surface; border: 1px solid @border; border-radius: 8px; }"
        ))
        bank_layout = QVBoxLayout(bank_card)
        bank_layout.setContentsMargins(16, 12, 16, 12)
        bank_title = QLabel("Resmi Sirket Banka Bilgileri")
        bank_title.setStyleSheet(theme_qss("color: @text; font-weight: 800; font-size: 12px;"))
        bank_info = QLabel(
            "Hesap Sahibi: Engin ASLAN / Aslan Computer Yazilim Ltd. Sti.\n"
            "Banka: VakifBank Ticari - Istanbul Subesi\n"
            "IBAN: TR66 0001 5001 5800 7321 0690 01"
        )
        bank_info.setWordWrap(True)
        bank_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
        bank_layout.addWidget(bank_title)
        bank_layout.addWidget(bank_info)

        deposit_card = QFrame()
        deposit_card.setStyleSheet(theme_qss(
            "QFrame { background: @surface; border: 1px solid @border; border-radius: 8px; }"
        ))
        deposit_layout = QVBoxLayout(deposit_card)
        deposit_layout.setContentsMargins(16, 12, 16, 12)
        deposit_title = QLabel("Dekont Yukleme ve Onay")
        deposit_title.setStyleSheet(theme_qss("color: @text; font-weight: 800; font-size: 12px;"))
        deposit_info = QLabel("Odemeyi tamamladiktan sonra dekont dosyanizi yukleyin.\nPDF, JPG veya PNG kabul edilir.")
        deposit_info.setWordWrap(True)
        deposit_info.setStyleSheet(theme_qss("color: @text_muted; font-size: 10px;"))
        deposit_button = QPushButton("Dekont Sec ve Yukle")
        deposit_button.setMinimumHeight(32)
        deposit_button.setStyleSheet(theme_qss("background: @surface_alt; color: @text; border: 1px solid @border; border-radius: 5px;"))
        deposit_layout.addWidget(deposit_title)
        deposit_layout.addWidget(deposit_info)
        deposit_layout.addWidget(deposit_button)
        payment_grid.addWidget(bank_card, 0, 0)
        payment_grid.addWidget(deposit_card, 0, 1)
        payment_grid.setColumnStretch(0, 1)
        payment_grid.setColumnStretch(1, 1)
        layout.addLayout(payment_grid)
        
        # Request License Button
        btn_request = QPushButton("📩 Lisans Talep Et (E-posta Gönder)")
        btn_request.setStyleSheet(theme_qss("""
            QPushButton {
                background-color: @accent;
                color: @selection_text;
                padding: 12px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: @accent_hover; }
        """))
        btn_request.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_request.clicked.connect(self.request_license)
        layout.addWidget(btn_request)
        
        layout.addStretch()

    def copy_hwid(self):
        """HWID'yi panoya kopyala"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(SecurityManager.get_hwid())
        if self.main_window:
            self.main_window.show_notification("HWID panoya kopyalandı!", "success")

    def refresh_license_info(self):
        """Lisans bilgilerini güncelle"""
        try:
            manager = getattr(self.main_window, "license_manager", None)
            status = manager.check_license_status() if manager else {}
            license_type = str(status.get("type") or "").upper()
            if status.get("status") == "active" and license_type == "TRIAL":
                expiry = str(status.get("expiry_date") or "-")
                days_left = int(status.get("days_left") or 0)
                self._countdown_timer.stop()
                self.lbl_countdown.setVisible(False)
                self.lbl_status.setText(
                    "Durum: <span style='color: #e67e22;'>Deneme Aktif</span>"
                )
                self.lbl_details.setText(
                    "Lisans T\u00fcr\u00fc: 15 G\u00fcnl\u00fck Deneme\n"
                    f"Ge\u00e7erlilik: {expiry}\n"
                    f"Kalan G\u00fcn: {days_left}"
                )
                return
            license_key = self.db.get_setting("license_key", "")
            license_expires = self.db.get_setting("license_expires", "")
            stored_type = self.db.get_setting("license_type", "Kurumsal") or "Kurumsal"
            license_started = self.db.get_setting("license_started", "")
            updated_at = self.db.get_setting("license_updated_at", "")
            license_code = self.db.get_setting("license_code", "")
            license_code_display = self._mask_license_code(license_code)
            
            if license_key:
                self.lbl_status.setText("Durum: <span style='color: #27ae60;'>Aktif ✔</span>")
                self.lbl_details.setText(
                    f"Lisans T\u00fcr\u00fc: {stored_type}\n"
                    f"Ba\u015flang\u0131\u00e7: {license_started or '-'}\n"
                    f"Biti\u015f: {license_expires if license_expires else 'S\u00fcresiz'}\n"
                    f"Lisans Kodu: {license_code_display or '-'}\n"
                    f"Sunucu G\u00fcncellemesi: {updated_at or '-'}\n"
                )
                self._license_expires_str = license_expires or ""
                self.lbl_countdown.setVisible(True)
                self._update_countdown()
                self._countdown_timer.start(1000)
            else:
                self._countdown_timer.stop()
                self.lbl_countdown.setVisible(False)
                self.lbl_status.setText("Durum: <span style='color: #e74c3c;'>Aktif Değil ✘</span>")
                self.lbl_details.setText(
                    "Lisans Türü: Deneme Sürümü\nGeçerlilik: -\nKalan Gün: -"
                )
        except Exception as e:
            self._countdown_timer.stop()
            self.lbl_countdown.setVisible(False)
            self.lbl_status.setText("Durum: Hata")
            self.lbl_details.setText(f"Hata: {e}")

    @staticmethod
    def _mask_license_code(value):
        code = str(value or "").strip()
        if not code:
            return ""
        if len(code) <= 4:
            return "*" * len(code)
        return "*" * (len(code) - 4) + code[-4:]

    def _update_countdown(self):
        """Geri sayım etiketini her saniye güncelle"""
        if not self._license_expires_str:
            self.lbl_countdown.setText("⏳ Kalan Süre: Süresiz")
            return

        try:
            date_only = len(self._license_expires_str.strip()) == 10
            expiry = QDateTime.fromString(
                self._license_expires_str.replace("T", " "),
                "yyyy-MM-dd HH:mm:ss",
            )
            if not expiry.isValid():
                expiry = QDateTime.fromString(self._license_expires_str, "yyyy-MM-dd")
            if not expiry.isValid():
                expiry = QDateTime.fromString(self._license_expires_str, "dd.MM.yyyy")

            if not expiry.isValid():
                self.lbl_countdown.setText("⏳ Kalan Süre: Süresiz")
                return

            if date_only:
                expiry.setTime(expiry.time().addSecs(86399))

            now = QDateTime.currentDateTime()
            remaining_secs = now.secsTo(expiry)

            if remaining_secs <= 0:
                self._countdown_timer.stop()
                self.lbl_countdown.setStyleSheet("color: #e74c3c; font-size: 14pt; padding-top: 6px;")
                self.lbl_countdown.setText("⚠️ Lisans Süresi Doldu!")
                self.lbl_status.setText("Durum: <span style='color: #e74c3c;'>Süresi Doldu ✘</span>")
                return

            days = remaining_secs // 86400
            remaining_secs %= 86400
            hours = remaining_secs // 3600
            remaining_secs %= 3600
            minutes = remaining_secs // 60
            seconds = remaining_secs % 60

            if days > 0:
                text = f"⏳ Kalan Süre: {days} gün {hours:02d}:{minutes:02d}:{seconds:02d}"
            else:
                text = f"⏳ Kalan Süre: {hours:02d}:{minutes:02d}:{seconds:02d}"

            # Color warning when < 7 days
            if days < 7:
                self.lbl_countdown.setStyleSheet(
                    "color: #e67e22; font-size: 14pt; font-weight: bold; padding-top: 6px;"
                )
            else:
                self.lbl_countdown.setStyleSheet(
                    "color: #27ae60; font-size: 14pt; font-weight: bold; padding-top: 6px;"
                )

            self.lbl_countdown.setText(text)

        except Exception:
            self.lbl_countdown.setText("⏳ Kalan Süre: Süresiz")

    def activate_license(self):
        """Lisansı etkinleştir"""
        key = self.inp_key.text().strip()
        if not key:
            if self.main_window:
                self.main_window.show_notification("Lütfen lisans anahtarı girin!", "warning")
            return
        
        try:
            self.db.set_setting("license_key", key)
            self.refresh_license_info()
            self.inp_key.clear()
            if self.main_window:
                self.main_window.show_notification("Lisans başarıyla etkinleştirildi!", "success")
        except Exception as e:
            if self.main_window:
                self.main_window.show_notification(f"Lisans etkinleştirme hatası: {e}", "error")

    def request_license(self):
        """Yöneticiye lisans talep maili gönder"""
        try:
            from src.ui.dialogs.license_lock_screen import LicenseLockScreen

            current_user = dict(getattr(self.main_window, "current_user", {}) or {})
            username = str(current_user.get("username") or current_user.get("email") or "")

            self._license_request_dialog = LicenseLockScreen(
                self.main_window or self,
                hwid=SecurityManager.get_hwid(),
                message="Lisans paketinizi secin ve odeme bildiriminizi gonderin.",
                request_only=True,
                username=username,
                product_code="teknik_servis",
            )
            self._license_request_dialog.exec()
            return

            from src.utils.mail_manager import MailWorker
            
            reg = self.db.get_registration()
            if not reg:
                self.main_window.show_notification("Kayıt bilgisi bulunamadı!", "error")
                return

            hwid = SecurityManager.get_hwid()
            company = reg[2] # company_name
            email = reg[1] # email
            phone = reg[3] # phone
            
            subject = f"Lisans Talebi: {company}"
            body = f"""
            YENİ LİSANS TALEBİ
            ------------------
            Firma: {company}
            E-posta: {email}
            Telefon: {phone}
            
            HWID: {hwid}
            
            Lütfen benimle iletişime geçin.
            """
            
            self.mail_worker = MailWorker("gnnckrk@gmail.com", subject, body)
            self.mail_worker.finished.connect(lambda s, m: self.main_window.show_notification(
                "Lisans talebiniz yöneticiye iletildi. En kısa sürede dönüş yapılacaktır.", "success"
            ) if s else self.main_window.show_notification(f"Talep gönderilemedi: {m}", "error"))
            
            self.mail_worker.start()
            self.main_window.show_notification("Talep gönderiliyor...", "info")
            
        except Exception as e:
            if self.main_window:
                self.main_window.show_notification(f"Hata: {e}", "error")

    def open_plan_checkout(self, plan_code):
        """Open the payment request screen with the chosen plan preselected."""
        try:
            from src.ui.dialogs.license_lock_screen import LicenseRequestDialog

            self._license_checkout_dialog = LicenseRequestDialog(
                SecurityManager.get_hwid(),
                self.main_window or self,
                product_code="teknik_servis",
                initial_plan_code=plan_code,
            )
            self._license_checkout_dialog.exec()
        except Exception as error:
            if self.main_window:
                self.main_window.show_notification(
                    f"\u00d6deme ekran\u0131 a\u00e7\u0131lamad\u0131: {error}", "error"
                )
