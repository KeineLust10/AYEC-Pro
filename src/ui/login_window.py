# -*- coding: utf-8 -*-


import secrets

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFrame, QGraphicsDropShadowEffect, QHBoxLayout, QStackedWidget,
                             QGridLayout, QSizePolicy, QApplication, QCheckBox)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QLinearGradient, QBrush, QIcon, QAction

from src.utils.toast_notification import show_success, show_error, show_warning, show_info
from src.utils.design_system import DesignTokens


class FramelessWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # Şeffaflık kapalı - Arka planı QSS ile vereceğiz
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.draggable = True
        self.dragging = False
        self.dragPosition = QPoint()
        
        # Dark Background explicitly set via QSS
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a; 
                color: white;
            }
        """)

    # Paint event kaldırıldı, QSS kullanılıyor.

    def mousePressEvent(self, event):
        if self.draggable and event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.dragPosition = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.dragPosition)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.dragging = False

class StyledInput(QLineEdit):
    def __init__(self, placeholder, is_password=False):
        super().__init__()
        self.setPlaceholderText(placeholder)
        if is_password:
            self.setEchoMode(QLineEdit.EchoMode.Password)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QLineEdit {
                background-color: #f1f5f9; /* Slate 100 */
                border: 1px solid #cbd5e1; /* Slate 300 */
                border-radius: 12px;
                color: #334155; /* Slate 700 */
                padding-left: 15px;
                font-family: 'Segoe UI';
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
                background-color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #94a3b8; /* Slate 400 */
            }
        """)

class LoginWindow(FramelessWindow):
    login_successful = pyqtSignal(object)

    def _on_remember_changed(self, _state=None):
        if self.chk_remember.isChecked():
            user = self.log_user.text().strip()
            if user:
                self.db.set_setting("login_remember_user", user)

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.setFixedSize(450, 680)
        self.center()
        self.setup_ui()
        remembered = self.db.get_setting("login_remember_user", "")
        if remembered:
            self.log_user.setText(remembered)
            self.chk_remember.setChecked(True)
        self.chk_remember.stateChanged.connect(self._on_remember_changed)
    def center(self):
        # QDesktopWidget removed in PyQt6, use QScreen
        screen = QApplication.primaryScreen()
        qr = self.frameGeometry()
        cp = screen.availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def setup_ui(self):
        # White Background
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff; 
                color: #1e293b;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # --- Window Controls (Close/Minimize) ---
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        
        btn_min = QPushButton("-") 
        btn_min.setFixedSize(30, 30)
        btn_min.clicked.connect(self.showMinimized)
        pass_style = "QPushButton { color: #64748b; border: none; font-weight: bold; border-radius: 5px; background: transparent; } QPushButton:hover { background-color: #f1f5f9; color: #334155; }"
        btn_min.setStyleSheet(pass_style)
        
        btn_close = QPushButton("✕")
        btn_close.setFixedSize(30, 30)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("QPushButton { color: #64748b; border: none; border-radius: 5px; background: transparent; } QPushButton:hover { background-color: #ef4444; color: white; }")
        
        controls_layout.addWidget(btn_min)
        controls_layout.addWidget(btn_close)
        main_layout.addLayout(controls_layout)

        # --- Logo Area (Programmatic Re-creation) ---
        brand_layout = QVBoxLayout()
        brand_layout.setContentsMargins(0, 0, 0, 30)
        brand_layout.setSpacing(5)
        
        # Logo Text Row
        logo_row = QHBoxLayout()
        logo_row.setSpacing(0)
        logo_row.addStretch()
        
        # Cloud Icon (Unicode) or just text
        lbl_icon = QLabel("☁️") # Simple Cloud
        lbl_icon.setFont(QFont("Segoe UI", 36))
        lbl_icon.setStyleSheet("color: #3b82f6; margin-right: 10px;")
        
        # "bulut" (Blue)
        lbl_bulut = QLabel("bulut")
        lbl_bulut.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        lbl_bulut.setStyleSheet("color: #3b82f6; letter-spacing: -1px;")
        
        # "teknoloji" (Orange/Yellow)
        lbl_tek = QLabel("teknoloji")
        lbl_tek.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        lbl_tek.setStyleSheet("color: #f59e0b; letter-spacing: -1px;")
        
        logo_row.addWidget(lbl_icon)
        logo_row.addWidget(lbl_bulut)
        logo_row.addWidget(lbl_tek)
        logo_row.addStretch()
        
        # Slogan
        lbl_slogan = QLabel("Bilişim ve Güvenlik Sistemleri")
        lbl_slogan.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_slogan.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_slogan.setStyleSheet("color: #1e293b; letter-spacing: 2px; text-transform: uppercase;")
        
        brand_layout.addLayout(logo_row)
        brand_layout.addWidget(lbl_slogan)
        
        main_layout.addLayout(brand_layout)

        # --- Stacked Pages (Login vs Register) ---
        self.stack = QStackedWidget()
        
        # 1. REGISTER PAGE
        page_register = QWidget()
        reg_layout = QVBoxLayout(page_register)
        reg_layout.setContentsMargins(0,0,0,0)
        reg_layout.setSpacing(15)
        
        self.reg_name = StyledInput("Ad Soyad & Firma Adı")
        self.reg_email = StyledInput("E-posta Adresi")
        self.reg_phone = StyledInput("Telefon Numarası")
        self.reg_purpose = StyledInput("Kullanım Amacı (Örn: Telefon Tamiri)")
        
        btn_register = QPushButton("HESAP OLUŞTUR")
        btn_register.setFixedHeight(50)
        btn_register.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_register.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #2563eb);
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
                font-size: 14px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #60a5fa, stop:1 #3b82f6);
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        btn_register.clicked.connect(self.handle_register)
        
        link_login = QPushButton("Zaten bir hesabım var")
        link_login.setCursor(Qt.CursorShape.PointingHandCursor)
        link_login.setStyleSheet("color: #64748b; border: none; font-size: 13px; text-decoration: underline; background: transparent;")
        link_login.clicked.connect(lambda: self.switch_page(1))
        
        reg_layout.addWidget(self.reg_name)
        reg_layout.addWidget(self.reg_email)
        reg_layout.addWidget(self.reg_phone)
        reg_layout.addWidget(self.reg_purpose)
        reg_layout.addSpacing(10)
        reg_layout.addWidget(btn_register)
        reg_layout.addWidget(link_login)
        reg_layout.addStretch()

        # 2. LOGIN PAGE
        page_login = QWidget()
        log_layout = QVBoxLayout(page_login)
        log_layout.setContentsMargins(0,0,0,0)
        log_layout.setSpacing(20)
        
        self.log_user = StyledInput("Kullanıcı Adı")
        self.log_pass = StyledInput("Şifre", is_password=True)
        self.log_pass.returnPressed.connect(self.handle_login)
        
        btn_login = QPushButton("GİRİŞ YAP")
        btn_login.setFixedHeight(50)
        btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_login.setStyleSheet(btn_register.styleSheet().replace("#3b82f6", "#10b981").replace("#2563eb", "#059669")) 
        btn_login.clicked.connect(self.handle_login)
        
        link_back = QPushButton("← Yeni Kayıt Oluştur")
        link_back.setCursor(Qt.CursorShape.PointingHandCursor)
        link_back.setStyleSheet("color: #64748b; border: none; font-size: 13px; background: transparent;")
        link_back.clicked.connect(lambda: self.switch_page(0))
        
        from PyQt6.QtWidgets import QCheckBox
        self.chk_remember = QCheckBox("Beni Hatırla")
        self.chk_remember.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_remember.setStyleSheet("""
            QCheckBox { color: #64748b; font-size: 13px; }
            QCheckBox::indicator { width: 18px; height: 18px; border: 1px solid #cbd5e1; border-radius: 4px; background: white; }
            QCheckBox::indicator:checked { background-color: #10b981; border-color: #10b981; image: url(assets/check.png); } /* Simple check visual even without icon */
        """)
        
        log_layout.addWidget(self.log_user)
        log_layout.addWidget(self.log_pass)
        log_layout.addWidget(self.chk_remember) # Added Remember Me
        log_layout.addSpacing(10)
        log_layout.addWidget(btn_login)
        log_layout.addWidget(link_back)
        log_layout.addStretch()
        
        self.stack.addWidget(page_register) # Index 0
        self.stack.addWidget(page_login)    # Index 1
        
        main_layout.addWidget(self.stack)
        main_layout.addStretch()
        
        # Footer Info
        lbl_footer = QLabel("v2.0.0 • Secure Connection • 2026")
        lbl_footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_footer.setStyleSheet("color: #94a3b8; font-size: 11px;")
        main_layout.addWidget(lbl_footer)

        # Shadow Effect for entire window content
        # Note: In a frameless un-translucent window, shadow might be clipped by OS unless margins used.
        # We stuck to simple rect for now.

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)

    def handle_login(self):
        user = self.log_user.text().strip()
        pwd = self.log_pass.text().strip()
        
        if not user or not pwd:
            show_warning(self, "Kullanıcı adı ve şifre gereklidir.")
            return

        user_data = self.db.authenticate_user(user, pwd)
        if user_data:
            if self.chk_remember.isChecked():
                self.db.set_setting("login_remember_user", user)
            else:
                self.db.set_setting("login_remember_user", "")
            self.login_successful.emit(user_data)
            self.close()
        else:
            show_error(self, "Hatalı kullanıcı adı veya şifre!")

    def handle_register(self):
        name = self.reg_name.text().strip()
        email = self.reg_email.text().strip()
        phone = self.reg_phone.text().strip()
        purpose = self.reg_purpose.text().strip()
        
        if not name or not email:
            show_warning(self, "İsim ve E-posta alanları zorunludur.")
            return
            
        data = {'full_name': name, 'email': email, 'phone': phone, 'purpose': purpose, 'company_name': name}
        success = self.db.save_registration(data)
        
        if success:
            show_success(self, "Kayıt talebiniz alındı! Demo sürümü başlatılıyor...")
            temporary_password = secrets.token_urlsafe(8) + "Aa1"
            existing_user = self.db.authenticate_user(email, temporary_password)
            if not existing_user:
                self.db.add_user(
                    email,
                    temporary_password,
                    email,
                    "Admin",
                    must_change_password=True,
                )
            
            self.log_user.setText(email)
            self.log_pass.setText(temporary_password)
            show_info(
                self,
                "Hesabiniz olusturuldu.\n"
                f"Kullanici: {email}\n"
                f"Gecici sifre: {temporary_password}",
            )
            self.switch_page(1)
            return
            
        else:
            show_error(self, "Kayıt sırasında bir hata oluştu.")
