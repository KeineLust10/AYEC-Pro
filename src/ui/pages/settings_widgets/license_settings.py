# -*- coding: utf-8 -*-

"""
License Management Widget
Lisans yönetimi widget'ı
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QFrame, QGroupBox, QLineEdit, QApplication,
                             QSizePolicy)
from PyQt6.QtCore import Qt, QTimer, QDateTime
from PyQt6.QtGui import QFont, QAction
from src.utils.security_manager import SecurityManager
from src.utils.theme_colors import theme_qss


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

        title = QLabel("🛡️ Lisans Yönetimi")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet(theme_qss("color: @text;"))
        layout.addWidget(title)

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
        self.lbl_status.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
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
        self.lbl_countdown.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
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
            
            if license_key:
                self.lbl_status.setText("Durum: <span style='color: #27ae60;'>Aktif ✔</span>")
                self.lbl_details.setText(
                    f"Lisans T\u00fcr\u00fc: {stored_type}\n"
                    f"Ba\u015flang\u0131\u00e7: {license_started or '-'}\n"
                    f"Biti\u015f: {license_expires if license_expires else 'S\u00fcresiz'}\n"
                    f"Lisans Kodu: {license_code or '-'}\n"
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
