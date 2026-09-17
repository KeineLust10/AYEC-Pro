# -*- coding: utf-8 -*-


from PyQt6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QComboBox, QFrame, QWidget, QStackedWidget)
from src.utils.toast_notification import show_success, show_error, show_warning
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect # QGraphicsDropShadowEffect moved to QtWidgets in PyQt6
import os
from src.utils.license_manager import LicenseManager
from src.utils.logger import logger
from src.ui.widgets.modern_dialog import ModernDialog


class ModernInput(QLineEdit):

    def _on_ui_widget_changed(self, *args):
        from src.ui.utils.ui_signal_helpers import on_ui_widget_changed
        on_ui_widget_changed(self, *args)
    def __init__(self, placeholder, is_password=False):
        super().__init__()
        self.setPlaceholderText(placeholder)
        if is_password:
            self.setEchoMode(QLineEdit.EchoMode.Password)
        self.setFixedHeight(55) # Taller inputs
        self.setStyleSheet("""
            QLineEdit {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 0 20px;
                font-size: 15px;
                color: #334155;
                font-family: 'Segoe UI';
            }
            QLineEdit:focus {
                border: 2px solid #2563eb;
                background-color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
            }
        """)

class RegistrationDialog(ModernDialog):
    """
    Onboarding Dialog: Premium Split-Screen Design
    """
    registration_completed = pyqtSignal(dict) 

    def __init__(self, db=None, parent=None, start_on_login=False):
        super().__init__(title="Kayit Ol", parent=parent, width=1000, height=680)
        self.db = db
        self.setMinimumSize(1000, 680) # Allow resize if needed by OS
        self.set_footer_visible(False)
        
        self.is_dragging = False
        self.drag_pos = QPoint()

        # Main Layout
        self.layout = self.content_layout
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(0)

        # Container Frame
        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame#Container {
                background-color: white;
                border-radius: 24px;
            }
        """)
        self.container.setObjectName("Container")
        
        # Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.container.setGraphicsEffect(shadow)

        self.container_layout = QHBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(0)

        # --- LEFT PANEL (BRANDING) ---
        self.left_panel = QFrame()
        self.left_panel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e293b, stop:1 #0f172a);
                border-top-left-radius: 24px;
                border-bottom-left-radius: 24px;
            }
        """)
        self.setup_left_panel()
        
        # --- RIGHT PANEL (FORMS) ---
        self.right_panel = QFrame()
        self.right_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border-top-right-radius: 24px;
                border-bottom-right-radius: 24px;
            }
        """)
        self.setup_right_panel(start_on_login)

        self.container_layout.addWidget(self.left_panel, 40)
        self.container_layout.addWidget(self.right_panel, 60)
        self.layout.addWidget(self.container)

    def paintEvent(self, event):
        super().paintEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_dragging:
            self.move(event.globalPosition().toPoint() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False

    def setup_left_panel(self):
        layout = QVBoxLayout(self.left_panel)
        layout.setContentsMargins(50, 60, 50, 60)
        
        # Logo Container
        logo_container = QFrame()
        logo_container.setFixedSize(140, 140)
        logo_container.setStyleSheet("""
            background-color: white;
            border-radius: 70px;
            border: 4px solid rgba(255, 255, 255, 0.1);
        """)
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(15, 15, 15, 15)
        
        self.logo_label = QLabel()
        from PyQt6.QtGui import QPixmap
        logo_path = os.path.join(os.getcwd(), "assets", "logo.png")
        
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            # Center fit - Keep aspect ratio to fit text+icon
            self.logo_label.setPixmap(pixmap.scaled(110, 110, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.logo_label.setText("☁️")
            self.logo_label.setStyleSheet("font-size: 60px; color: white;")
            
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_layout.addWidget(self.logo_label)
        
        layout.addStretch(1)
        layout.addWidget(logo_container, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(30)
        
        title = QLabel("AYEC Pro\nServis Takip")
        title.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
        title.setStyleSheet("color: white; line-height: 1.1;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Accent
        accent = QFrame()
        accent.setFixedHeight(4)
        accent.setFixedWidth(50)
        accent.setStyleSheet("background: #f59e0b; border-radius: 2px;")
        layout.addSpacing(15)
        layout.addWidget(accent, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(15)
        
        sub = QLabel("İşletmenizi yönetmenin en premium, hızlı ve güvenli yolu.")
        sub.setFont(QFont("Segoe UI", 12))
        sub.setStyleSheet("color: #94a3b8; font-weight: 400;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)
        layout.addWidget(sub)
        
        layout.addStretch(2)
        
        footer = QLabel("© 2026 AYEC Pro\nPremium Edition v2.1")
        footer.setStyleSheet("color: #475569; font-size: 11px; font-weight: 500;")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer)

    def setup_right_panel(self, start_on_login=False):
        layout = QVBoxLayout(self.right_panel)
        layout.setContentsMargins(60, 50, 60, 50)
        layout.setSpacing(15)

        # Top Bar (Close)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.reject)
        btn_close.setStyleSheet("""
            QPushButton { border: none; color: #cbd5e1; font-size: 18px; }
            QPushButton:hover { color: #ef4444; }
        """)
        top_bar.addWidget(btn_close)
        layout.addLayout(top_bar)

        # Pages
        self.stack = QStackedWidget()
        self.register_view = self.create_register_view()
        self.stack.addWidget(self.register_view)
        
        self.login_view = self.create_login_view()
        self.stack.addWidget(self.login_view)
        
        layout.addWidget(self.stack)
        
        if start_on_login:
            self.stack.setCurrentIndex(1)

    def create_register_view(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)

        lbl_head = QLabel("Hesap Oluştur")
        lbl_head.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        lbl_head.setStyleSheet("color: #0f172a;")
        layout.addWidget(lbl_head)

        lbl_desc = QLabel("Bilgilerinizi girerek hemen başlayın.")
        lbl_desc.setStyleSheet("color: #64748b; font-size: 15px; margin-bottom: 5px;")
        layout.addWidget(lbl_desc)

        self.inp_name = ModernInput("Ad Soyad")
        layout.addWidget(self.inp_name)
        
        self.inp_email = ModernInput("E-posta Adresi")
        layout.addWidget(self.inp_email)
        
        self.inp_password = ModernInput("Şifre", is_password=True)
        layout.addWidget(self.inp_password)
        
        row = QHBoxLayout()
        row.setSpacing(15)
        self.inp_company = ModernInput("Firma Adı")
        self.inp_phone = ModernInput("Telefon")
        row.addWidget(self.inp_company)
        row.addWidget(self.inp_phone)
        layout.addLayout(row)
        
        self.cmb_purpose = QComboBox()
        self.cmb_purpose.setFixedHeight(55)
        self.cmb_purpose.addItems(["Teknik Servis", "Mağaza Satış", "Kurumsal Takip", "Diğer"])
        self.cmb_purpose.setStyleSheet("""
            QComboBox {
                background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: 0 20px;
                color: #334155; font-family: 'Segoe UI'; font-size: 15px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { 
                image: none; border: none; 
            }
        """)
        layout.addWidget(self.cmb_purpose)

        layout.addSpacing(10)

        btn_reg = QPushButton("HESABI OLUŞTUR")
        btn_reg.setFixedHeight(60)
        btn_reg.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reg.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: white; 
                font-weight: 700; 
                font-size: 15px; 
                border-radius: 16px;
                letter-spacing: 0.5px;
                border: none;
            }
            QPushButton:hover { background: #1d4ed8; }
            QPushButton:pressed { background: #1e40af; }
        """)
        btn_reg.clicked.connect(self.handle_registration)
        layout.addWidget(btn_reg)

        # Login Link
        link_box = QHBoxLayout()
        link_box.addStretch()
        lbl_link = QLabel("Zaten hesabınız var mı")
        lbl_link.setStyleSheet("color: #64748b; font-size: 14px;")
        
        btn_link = QPushButton("Giriş Yap")
        btn_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_link.setStyleSheet("border: none; color: #2563eb; font-weight: 700; background: transparent; font-size: 14px;")
        btn_link.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        
        link_box.addWidget(lbl_link)
        link_box.addWidget(btn_link)
        link_box.addStretch()
        layout.addLayout(link_box)
        layout.addStretch()

        return widget

    def create_login_view(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        layout.addStretch()
        
        lbl_head = QLabel("Tekrar Hoş Geldiniz")
        lbl_head.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        lbl_head.setStyleSheet("color: #0f172a;")
        layout.addWidget(lbl_head)

        lbl_desc = QLabel("Servis yönetim panelinize erişmek için giriş yapın.")
        lbl_desc.setStyleSheet("color: #64748b; font-size: 15px;")
        layout.addWidget(lbl_desc)
        
        layout.addSpacing(10)

        self.inp_login_email = ModernInput("E-posta Adresi")
        layout.addWidget(self.inp_login_email)
        
        self.inp_login_pass = ModernInput("Şifre", is_password=True)
        self.inp_login_pass.returnPressed.connect(self.handle_login)
        layout.addWidget(self.inp_login_pass)

        # Options Row
        opt_row = QHBoxLayout()
        self.chk_remember = QPushButton("☐ Beni Hatırla")
        self.chk_remember.setCheckable(True)
        self.chk_remember.clicked.connect(lambda: self.chk_remember.setText("☑ Beni Hatırla" if self.chk_remember.isChecked() else "☐ Beni Hatırla"))
        self.chk_remember.setStyleSheet("border:none; color: #64748b; text-align: left; font-size: 14px;")
        
        self.btn_forgot = QPushButton("Şifremi Unuttum")
        self.btn_forgot.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_forgot.setStyleSheet("border: none; color: #2563eb; font-weight: 600; background: transparent; font-size: 14px;")
        self.btn_forgot.clicked.connect(self._open_password_reset)
        
        opt_row.addWidget(self.chk_remember)
        opt_row.addStretch()
        opt_row.addWidget(self.btn_forgot)
        layout.addLayout(opt_row)

        layout.addSpacing(10)

        btn_login = QPushButton("GÜVENLİ GİRİŞ YAP")
        btn_login.setFixedHeight(60)
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.setStyleSheet("""
            QPushButton {
                background: #0f172a;
                color: white; 
                font-weight: 700; 
                font-size: 15px; 
                border-radius: 16px;
                letter-spacing: 0.5px;
                border: none;
            }
            QPushButton:hover { background: #1e293b; }
            QPushButton:pressed { }
        """)
        btn_login.clicked.connect(self.handle_login)
        layout.addWidget(btn_login)

        # Register Link
        link_box = QHBoxLayout()
        link_box.addStretch()
        lbl_link = QLabel("Hesabınız yok mu")
        lbl_link.setStyleSheet("color: #64748b; font-size: 14px;")
        
        btn_link = QPushButton("Kayıt Ol")
        btn_link.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_link.setStyleSheet("border: none; color: #2563eb; font-weight: 700; background: transparent; font-size: 14px;")
        btn_link.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        
        link_box.addWidget(lbl_link)
        link_box.addWidget(btn_link)
        link_box.addStretch()
        layout.addLayout(link_box)
        
        layout.addStretch()

        return widget

    def handle_registration(self):
        data = {
            "full_name": self.inp_name.text(),
            "email": self.inp_email.text(),
            "password": self.inp_password.text(),
            "company_name": self.inp_company.text(),
            "phone": self.inp_phone.text(),
            "purpose": self.cmb_purpose.currentText()
        }
        if not data["full_name"] or not data["email"] or not data["password"]:
            show_warning(self, "Lütfen gerekli alanları (Ad, E-posta, Şifre) doldurun.")
            return

        # Generate Trial License
        try:
            lm = LicenseManager()
            trial_lic = lm.create_trial_license()
            data["license"] = trial_lic
            logger.debug(f"Trial license generated: {trial_lic}")
        except Exception as e:
            logger.error(f"Trial license generation error: {e}")
        # Send registration emails (Customer Welcome + Admin Alert)
        try:
            from src.utils.mail_manager import send_registration_emails_async
            send_registration_emails_async(data, db=self.db)
        except Exception as mail_err:
            logger.warning("Registration email send failed: %s", mail_err)

        self.registration_completed.emit(data)
        self.accept()


    def handle_login(self):
        email = self.inp_login_email.text()
        pwd = self.inp_login_pass.text()
        
        if not email or not pwd:
            show_warning(self, "Giriş bilgileri eksik.")
            return

        # --- REAL AUTHENTICATION ---
        if self.db:
            user = self.db.authenticate_user(email, pwd)
            if user:
                # User found (id, username, password, email, role, created_at, ...)
                # Construct data for main app
                data = {
                    "full_name": user['username'], # Or fetch name if available
                    "email": user['email'],
                    "company_name": "AYEC Pro", # Default if not found in reg
                    "phone": "",
                    "purpose": user['role'],
                    "remember_me": self.chk_remember.isChecked(),
                    "license": "EXISTING_USER" # Signal to skip new license gen
                }
                
                # Try to fetch existing registration info for better data
                try:
                    reg = self.db.get_registration()
                    if reg:
                        data["full_name"] = reg["full_name"]
                        data["company_name"] = reg["company_name"]
                        data["phone"] = reg["phone"]
                except Exception as e:
                    logger.debug(f"Registration lookup fallback failed during login: {e}")
                
                # Save remember_me preference
                if self.chk_remember.isChecked():
                    self.db.set_setting('remember_me', 'true')
                    self.db.set_setting('last_login_user', user['username'])
                else:
                    self.db.set_setting('remember_me', 'false')
                    self.db.set_setting('last_login_user', '')
                
                show_success(self, f"Giriş Başarılı!\nHoş geldiniz, {data['full_name']}")
                
                QTimer.singleShot(500, lambda: self._finish_auth(data))
                return
            else:
                show_error(self, "Hatalı E-posta veya Şifre!")
                return
        else:
            # Fallback for mock if DB not passed (should not happen in prod)
            logger.warning("DB not passed to RegistrationDialog! Using Mock Login.")
            if email == "admin" and pwd == "admin":
                 self._finish_login(email)
                 return
            show_error(self, "Veritabanı bağlantısı yok!")

    def _finish_auth(self, data):
        self.registration_completed.emit(data)
        self.accept()


    def _wire_ui_signals(self):
        self.cmb_purpose.currentIndexChanged.connect(self._on_ui_widget_changed)

    def _open_password_reset(self):
        from src.ui.dialogs.password_reset_dialog import PasswordResetDialog
        dialog = PasswordResetDialog(self.db, self)
        dialog.exec()
